"""Order and shipment API routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from neo4j.exceptions import Neo4jError, ServiceUnavailable
from pydantic import BaseModel

from aura_graphdb.aura_hubs import list_cities, list_hubs
from aura_graphdb.aura_route_queries import get_order_route, get_recent_order_routes
from aura_graphdb.aura_courier import (
    create_courier_user,
    get_courier_by_email,
    list_active_couriers,
    list_couriers_with_orders,
)
from dependencies.auth import TokenUser, require_roles, get_current_user
from schemas.orders import (
    CreateCourierRequest,
    CreateShipmentRequest,
    CreateShipmentResponse,
    OrderResponse,
)
from services import orders as orders_svc
from services import courier_route as route_svc


class RouteRequest(BaseModel):
    delivery_day: str  # YYYY-MM-DD

router = APIRouter(prefix="/orders", tags=["orders"])
couriers_router = APIRouter(prefix="/couriers", tags=["couriers"])

LogisticsUser = Annotated[
    TokenUser,
    Depends(require_roles("admin", "logistics_manager")),
]

AnyAuthUser = Annotated[TokenUser, Depends(get_current_user)]


@router.get("/shipments")
def list_shipments(
    current_user: AnyAuthUser,
    limit: int = Query(default=50, ge=1, le=200),
    courier_id: str | None = Query(default=None),
    delivery_day: str | None = Query(default=None),
):
    """List shipments. Couriers see only their own; managers can filter by any courier."""
    if current_user.role == "courier":
        # Force the courier_id to their own account (JWT claim or GraphDB lookup)
        effective_courier_id = current_user.courier_id
        if not effective_courier_id and current_user.email:
            courier = get_courier_by_email(current_user.email)
            effective_courier_id = courier.get("courier_id") if courier else None
        if not effective_courier_id:
            return {"success": True, "shipments": [], "count": 0}
    elif current_user.role in ("admin", "logistics_manager"):
        effective_courier_id = courier_id
    else:
        raise HTTPException(status_code=403, detail="Access denied.")

    try:
        rows = get_recent_order_routes(
            limit=limit,
            courier_id=effective_courier_id,
            delivery_day=delivery_day,
        )
    except (ConnectionError, ServiceUnavailable, Neo4jError, OSError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    shipments = [
        {
            "order_id": row.get("order_id"),
            "from_hub_name": row.get("from_hub_name"),
            "to_hub_name": row.get("to_hub_name"),
            "city_name": row.get("city_name"),
            "delivery_day": row.get("delivery_day"),
            "receipt_time": row.get("receipt_time"),
            "assigned_courier_id": row.get("assigned_courier_id"),
            "assigned_courier_name": row.get("assigned_courier_name"),
            "status": "In Transit",
        }
        for row in rows
    ]
    return {"success": True, "shipments": shipments, "count": len(shipments)}


@router.get("/cities")
def list_cities_endpoint(current_user: LogisticsUser):
    """List cities that have hubs (for shipment / courier forms)."""
    del current_user
    try:
        cities = list_cities()
    except (ConnectionError, ServiceUnavailable, Neo4jError, OSError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"success": True, "cities": cities, "count": len(cities)}


@router.get("/hubs")
def list_hubs_endpoint(
    current_user: LogisticsUser,
    city_name: str = Query(..., min_length=1),
):
    """List hubs in a city (for shipment / courier forms)."""
    del current_user
    try:
        hubs = list_hubs(city_name=city_name)
    except (ConnectionError, ServiceUnavailable, Neo4jError, OSError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"success": True, "hubs": hubs, "count": len(hubs)}


@router.get("/{order_id}")
def get_shipment(order_id: str, current_user: AnyAuthUser):
    if current_user.role not in ("admin", "logistics_manager"):
        raise HTTPException(status_code=403, detail="Access denied.")
    try:
        row = get_order_route(order_id)
    except (ConnectionError, ServiceUnavailable, Neo4jError, OSError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if not row:
        raise HTTPException(status_code=404, detail="Order not found.")
    return {"success": True, "order": row}


@router.post("/shipments", response_model=CreateShipmentResponse, status_code=201)
def create_shipment(body: CreateShipmentRequest, current_user: LogisticsUser):
    del current_user
    try:
        result = orders_svc.create_shipment(body.model_dump())
    except (ConnectionError, ServiceUnavailable, Neo4jError, OSError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("message", "Order creation failed."))

    order = result.get("order")

    return CreateShipmentResponse(
        success=True,
        message=result.get("message", "Shipment created."),
        order=OrderResponse(**order) if order else None,
    )


# ── Couriers ──────────────────────────────────────────────────────────────────

@couriers_router.get("")
def list_couriers(
    current_user: LogisticsUser,
    limit: int = Query(default=200, ge=1, le=500),
    delivery_day: str | None = Query(default=None),
    with_orders_only: bool = Query(default=False),
):
    """List couriers for the manager dropdown; optionally only those with assigned orders."""
    del current_user
    try:
        if with_orders_only:
            couriers = list_couriers_with_orders(delivery_day=delivery_day, limit=limit)
        else:
            couriers = list_active_couriers(limit=limit)
    except (ConnectionError, ServiceUnavailable, Neo4jError, OSError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"success": True, "couriers": couriers, "count": len(couriers)}


@couriers_router.post("", status_code=201)
def create_courier(body: CreateCourierRequest, current_user: LogisticsUser):
    del current_user
    result = create_courier_user(
        name=body.name,
        email=body.email,
        password=body.password,
        city_name=body.city_name,
        hub_name=body.hub_name,
    )

    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("message", "Courier creation failed."))

    return result


@couriers_router.post("/me/route")
def my_route(body: RouteRequest, current_user: Annotated[TokenUser, Depends(require_roles("courier"))]):
    """Courier requests their own route + ETA for a delivery day."""
    courier_id = current_user.courier_id
    if not courier_id and current_user.email:
        courier = get_courier_by_email(current_user.email)
        courier_id = courier.get("courier_id") if courier else None
    if not courier_id:
        raise HTTPException(status_code=400, detail="No courier_id associated with this account.")
    result = route_svc.predict_courier_route(
        courier_id=courier_id,
        delivery_day=body.delivery_day,
    )
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("message", "Route prediction failed."))
    return result


@couriers_router.post("/{courier_id}/route")
def courier_route_by_id(
    courier_id: str,
    body: RouteRequest,
    current_user: LogisticsUser,
):
    """Logistics manager requests route + ETA for a specific courier on a delivery day."""
    del current_user
    result = route_svc.predict_courier_route(
        courier_id=courier_id,
        delivery_day=body.delivery_day,
    )
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("message", "Route prediction failed."))
    return result
