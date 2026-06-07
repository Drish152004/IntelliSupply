"""Pydantic schemas for order/shipment endpoints."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

_TIME_PATTERN = re.compile(r"^\d{2}:\d{2}:\d{2}$")


class CreateShipmentRequest(BaseModel):
    from_hub_name: str = Field(..., min_length=1)
    to_hub_name: str = Field(..., min_length=1)
    delivery_date: str = Field(..., description="YYYY-MM-DD")
    ds: int
    receipt_time: str | None = Field(None, description="HH:MM:SS; defaults to current IST")
    notes: str | None = None

    @field_validator("from_hub_name", "to_hub_name")
    @classmethod
    def strip_hub_names(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Hub name cannot be empty.")
        return cleaned

    @field_validator("delivery_date")
    @classmethod
    def validate_delivery_date(cls, value: str) -> str:
        from datetime import date

        try:
            date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("delivery_date must be YYYY-MM-DD.") from exc
        return value

    @field_validator("receipt_time")
    @classmethod
    def validate_receipt_time(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        if not _TIME_PATTERN.match(value):
            raise ValueError("receipt_time must be HH:MM:SS.")
        return value

    @model_validator(mode="after")
    def hubs_must_differ(self):
        if self.from_hub_name == self.to_hub_name:
            raise ValueError("from_hub_name and to_hub_name must be different.")
        return self


class OrderResponse(BaseModel):
    order_id: str
    lat_wgs84: float | None = None
    lon_wgs84: float | None = None
    city_name: str | None = None
    ds: int | None = None
    delivery_day: str | None = None
    receipt_time: str | None = None
    typecode: str | None = None
    aoi_id: str | None = None
    receipt_lat_wgs84: float | None = None
    receipt_lon_wgs84: float | None = None
    notes: str | None = None
    assigned_courier_id: str | None = None
    assigned_courier_name: str | None = None
    nearest_courier_distance_m: float | None = None
    from_hub_name: str | None = None
    to_hub_name: str | None = None
    cluster_id: int | None = None

    @field_validator("cluster_id", mode="before")
    @classmethod
    def coerce_cluster_id(cls, value: Any) -> int | None:
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None


class RoutePredictionResponse(BaseModel):
    route_prediction_id: str
    courier_id: str
    cluster_id: int
    city_name: str
    ds: int
    delivery_day: str
    order_ids: list[str]
    predicted_sequence: list[str]
    stops: list[dict[str, Any]]
    stop_count: int


class CreateShipmentResponse(BaseModel):
    success: bool
    message: str
    order: OrderResponse | None = None
    route_prediction: RoutePredictionResponse | None = None
    route_error: str | None = None


class CreateCourierRequest(BaseModel):
    name: str = Field(..., min_length=1)
    email: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)
    city_name: str = Field(..., min_length=1)
    hub_name: str = Field(..., min_length=1)
    ds: int = 318
