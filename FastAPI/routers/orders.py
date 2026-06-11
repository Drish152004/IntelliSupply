"""Order and shipment API routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from neo4j.exceptions import Neo4jError, ServiceUnavailable

from aura_graphdb.aura_route_queries import get_order_route, get_recent_order_routes
from dependencies.auth import TokenUser, require_roles
from schemas.orders import (
    CreateCourierRequest,
    CreateShipmentRequest,
    CreateShipmentResponse,
    OrderResponse,
    RoutePredictionResponse,
)
from services import orders as orders_svc
from aura_graphdb.aura_courier import create_courier_user

router = APIRouter(prefix="/orders", tags=["orders"])
couriers_router = APIRouter(prefix="/couriers", tags=["couriers"])

LogisticsUser = Annotated[
    TokenUser,
    Depends(require_roles("admin", "logistics_manager")),
]


@router.get("/shipments")
def list_shipments(current_user: LogisticsUser, limit: int = 20):
    del current_user
    try:
        rows = get_recent_order_routes(limit=limit)
    except (ConnectionError, ServiceUnavailable, Neo4jError, OSError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    shipments = []
    for row in rows:
        shipments.append(
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
        )
    return {"success": True, "shipments": shipments, "count": len(shipments)}


@router.get("/{order_id}")
def get_shipment(order_id: str, current_user: LogisticsUser):
    del current_user
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
    route_prediction = result.get("route_prediction")

    return CreateShipmentResponse(
        success=True,
        message=result.get("message", "Shipment created."),
        order=OrderResponse(**order) if order else None,
        route_prediction=RoutePredictionResponse(**route_prediction)
        if route_prediction
        else None,
        route_error=result.get("route_error"),
    )


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
