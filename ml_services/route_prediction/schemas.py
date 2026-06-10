from datetime import datetime

from pydantic import BaseModel, Field


class OrderStop(BaseModel):
    order_id: str
    poi_lat: float
    poi_lng: float
    receipt_time: datetime
    receipt_lat: float
    receipt_lng: float
    city_name: str
    typecode: str
    aoi_id: str | int


class NextStopRequest(BaseModel):
    current_lat: float = Field(..., description="Courier position (Web Mercator)")
    current_lng: float = Field(..., description="Courier position (Web Mercator)")
    stops_completed: int = Field(0, ge=0, description="Deliveries already completed on this route")
    route_start_time: datetime = Field(
        ..., description="Route clock anchor (usually first stop receipt_time)"
    )
    remaining_orders: list[OrderStop] = Field(..., min_length=1)


class CandidateScore(BaseModel):
    order_id: str
    score: float


class ChosenStop(BaseModel):
    order_id: str
    poi_lat: float
    poi_lng: float
    dist_to_candidate: float | None = None
    stops_remaining: int | None = None


class NextStopResponse(BaseModel):
    order_id: str
    candidate_scores: list[CandidateScore]
    chosen: ChosenStop


class RouteSequenceRequest(BaseModel):
    orders: list[OrderStop] = Field(
        ...,
        min_length=1,
        description="All stops for one route; first row supplies start lat/lng/time",
    )


class RouteSequenceResponse(BaseModel):
    sequence: list[str] = Field(..., description="order_id values in predicted visit order")


class HealthResponse(BaseModel):
    status: str
    model_version: str | None = None
    model_path: str | None = None
    feature_count: int | None = None
