from pydantic import BaseModel


class OrderRequest(BaseModel):
    delivery_user_id: int
    city_name: str
    typecode: str
    aoi_id: int
    poi_lat: float
    poi_lng: float
    receipt_lat: float
    receipt_lng: float
    receipt_time: str
