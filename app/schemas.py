from pydantic import BaseModel
from typing import List, Dict, Optional

class LoginRequest(BaseModel):
    login: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class Material1C(BaseModel):
    name: str
    rack: str
    weight: str
    height: str
    width: str
    depth: str
    barcode: Optional[str]

class OrderItem1C(BaseModel):
    material_id: str
    qty: int

class Order1C(BaseModel):
    order_id: str
    created_at: str
    assigned_to: str
    status: str = "new"
    items: List[OrderItem1C]

class PickerInfo(BaseModel):
    login: str
    password: str
    full_name: str

class OrderCreatePayload(BaseModel):
    order: Order1C
    materials: Dict[str, Material1C]
    picker: PickerInfo

class ScanRequest(BaseModel):
    barcode: str

class ScanResponse(BaseModel):
    status: str
    message: str
    progress: float
    material_name: Optional[str] = None

class RouteStep(BaseModel):
    step: int
    from_: str
    to: str
    time_sec: float
    dist_m: float
    cum_dist_m: float

class RouteSegmentImage(BaseModel):
    name: str
    png_url: str

class RouteResponse(BaseModel):
    order_id: str
    total_time_sec: float
    total_distance_m: float
    steps: List[RouteStep]
    segments: List[RouteSegmentImage]
    full_png_url: str
    map_warning: Optional[str] = None

class OrderStatusUpdate(BaseModel):
    status: str
    progress: Optional[float] = None

class OrderSummaryOut(BaseModel):
    order_id: str
    status: str