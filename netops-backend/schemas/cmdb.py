from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# 导出所有CMDB相关的Schema
from .cmdb_base import (
    DeviceType, DeviceTypeCreate, DeviceTypeUpdate, DeviceTypeInDB,
    Vendor, VendorCreate, VendorUpdate, VendorInDB,
    Location, LocationCreate, LocationUpdate, LocationInDB,
    Department, DepartmentCreate, DepartmentUpdate, DepartmentInDB,
    AssetStatus, AssetStatusCreate, AssetStatusUpdate, AssetStatusInDB
)

from .cmdb_asset import (
    Asset, AssetCreate, AssetUpdate, AssetInDB,
    AssetQueryParams, AssetStatistics
)

from .cmdb_network import (
    NetworkDevice, NetworkDeviceCreate, NetworkDeviceUpdate, NetworkDeviceInDB,
    NetworkInterface, NetworkInterfaceCreate, NetworkInterfaceUpdate, NetworkInterfaceInDB
)

from .cmdb_server import (
    Server, ServerCreate, ServerUpdate, ServerInDB
)

try:
    from .cmdb_server import (
        VirtualMachine, VirtualMachineCreate, VirtualMachineUpdate, VirtualMachineInDB,
        ServerWithVMs
    )
except ImportError:
    pass

from .cmdb_kubernetes import (
    K8sCluster, K8sClusterCreate, K8sClusterUpdate, K8sClusterInDB,
    K8sNodeBase, K8sNodeCreate, K8sNodeUpdate, K8sNodeInDB, K8sNode, K8sClusterWithNodes
)

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

# 统计数据Schema
class AssetStatistics(BaseModel):
    total_assets: int
    by_device_type: Dict[str, int]
    by_vendor: Dict[str, int]
    by_department: Dict[str, int]
    by_location: Dict[str, int]
    by_status: Dict[str, int] 