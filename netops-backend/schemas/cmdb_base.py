from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# 基础数据模型Schema
class DeviceTypeBase(BaseModel):
    name: str
    description: Optional[str] = None

class DeviceTypeCreate(DeviceTypeBase):
    pass

class DeviceTypeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class DeviceTypeInDB(DeviceTypeBase):
    id: int
    created_at: str
    updated_at: str

    class Config:
        orm_mode = True

class DeviceType(DeviceTypeInDB):
    pass

class VendorBase(BaseModel):
    name: str
    description: Optional[str] = None
    contact: Optional[str] = None
    website: Optional[str] = None

class VendorCreate(VendorBase):
    pass

class VendorUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    contact: Optional[str] = None
    website: Optional[str] = None

class VendorInDB(VendorBase):
    id: int
    created_at: str
    updated_at: str

    class Config:
        orm_mode = True

class Vendor(VendorInDB):
    pass

class LocationBase(BaseModel):
    name: str
    address: Optional[str] = None
    description: Optional[str] = None

class LocationCreate(LocationBase):
    pass

class LocationUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    description: Optional[str] = None

class LocationInDB(LocationBase):
    id: int
    created_at: str
    updated_at: str

    class Config:
        orm_mode = True

class Location(LocationInDB):
    pass

class DepartmentBase(BaseModel):
    name: str
    description: Optional[str] = None

class DepartmentCreate(DepartmentBase):
    pass

class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class DepartmentInDB(DepartmentBase):
    id: int
    created_at: str
    updated_at: str

    class Config:
        orm_mode = True

class Department(DepartmentInDB):
    pass

class AssetStatusBase(BaseModel):
    name: str
    description: Optional[str] = None

class AssetStatusCreate(AssetStatusBase):
    pass

class AssetStatusUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class AssetStatusInDB(AssetStatusBase):
    id: int
    created_at: str
    updated_at: str

    class Config:
        orm_mode = True

class AssetStatus(AssetStatusInDB):
    pass

# 系统类型模型
class SystemType(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    created_at: str
    updated_at: str

    class Config:
        orm_mode = True 