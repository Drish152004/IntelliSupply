"""ETA prediction request schema (mirrors ml_services/eta-prediction/api/schemas.py)."""

from pydantic import BaseModel


class ETARequest(BaseModel):
    delivery_user_id: str
    from_dipan_id: str
    aoi_id: str
    receipt_time: str
    receipt_lat: float
    receipt_lng: float
    poi_lat: float
    poi_lng: float
    city_name: str | None = ""
    typecode: str | None = ""
