"""Order and shipment API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from neo4j.exceptions import Neo4jError, ServiceUnavailable

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


@router.post("/shipments", response_model=CreateShipmentResponse, status_code=201)
def create_shipment(body: CreateShipmentRequest):
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
def create_courier(body: CreateCourierRequest):
    result = create_courier_user(
        name=body.name,
        email=body.email,
        password=body.password,
        city_name=body.city_name,
        hub_name=body.hub_name,
        ds=body.ds,
    )

    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("message", "Courier creation failed."))

    return result
