from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from .cmdb_base import DeviceType, Vendor, Department, Location, AssetStatus, SystemType

# 资产模型Schema
class AssetBase(BaseModel):
    name: str
    asset_tag: str
    ip_address: Optional[str] = None
    serial_number: Optional[str] = None
    device_type_id: Optional[int] = None
    vendor_id: Optional[int] = None
    department_id: Optional[int] = None
    location_id: Optional[int] = None
    status_id: Optional[int] = None
    system_type_id: Optional[int] = None
    owner: Optional[str] = None
    purchase_date: Optional[str] = None
    purchase_cost: Optional[float] = None
    current_value: Optional[float] = None
    online_date: Optional[str] = None
    warranty_expiry: Optional[str] = None
    notes: Optional[str] = None

class AssetCreate(AssetBase):
    pass

class AssetUpdate(BaseModel):
    name: Optional[str] = None
    asset_tag: Optional[str] = None
    ip_address: Optional[str] = None
    serial_number: Optional[str] = None
    device_type_id: Optional[int] = None
    vendor_id: Optional[int] = None
    department_id: Optional[int] = None
    location_id: Optional[int] = None
    status_id: Optional[int] = None
    system_type_id: Optional[int] = None
    owner: Optional[str] = None
    purchase_date: Optional[str] = None
    purchase_cost: Optional[float] = None
    current_value: Optional[float] = None
    online_date: Optional[str] = None
    warranty_expiry: Optional[str] = None
    notes: Optional[str] = None

class AssetInDB(AssetBase):
    id: int
    created_at: str
    updated_at: str

    class Config:
        orm_mode = True

class Asset(AssetInDB):
    device_type: Optional[DeviceType] = None
    vendor: Optional[Vendor] = None
    department: Optional[Department] = None
    location: Optional[Location] = None
    status: Optional[AssetStatus] = None
    system_type: Optional[SystemType] = None

# 资产查询参数
class AssetQueryParams(BaseModel):
    name: Optional[str] = None
    asset_tag: Optional[str] = None
    ip_address: Optional[str] = None
    serial_number: Optional[str] = None
    device_type_id: Optional[int] = None
    vendor_id: Optional[int] = None
    department_id: Optional[int] = None
    location_id: Optional[int] = None
    status_id: Optional[int] = None
    system_type_id: Optional[int] = None
    owner: Optional[str] = None
    
# 统计数据Schema
class AssetStatistics(BaseModel):
    total_assets: int
    by_device_type: Dict[str, int]
    by_vendor: Dict[str, int]
    by_department: Dict[str, int]
    by_location: Dict[str, int]
    by_status: Dict[str, int]

# CSV导入响应
class ImportResponse(BaseModel):
    imported: int
    failed: int
    errors: Optional[List[str]] = None 