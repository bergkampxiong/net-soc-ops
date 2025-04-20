from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# 网络设备Schema
class NetworkInterfaceBase(BaseModel):
    name: str
    type: Optional[str] = None
    mac_address: Optional[str] = None
    ip_address: Optional[str] = None
    subnet_mask: Optional[str] = None
    status: Optional[str] = None
    speed: Optional[str] = None
    description: Optional[str] = None

class NetworkInterfaceCreate(NetworkInterfaceBase):
    device_id: int

class NetworkInterfaceUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    mac_address: Optional[str] = None
    ip_address: Optional[str] = None
    subnet_mask: Optional[str] = None
    status: Optional[str] = None
    speed: Optional[str] = None
    description: Optional[str] = None

class NetworkInterfaceInDB(NetworkInterfaceBase):
    id: int
    device_id: int
    created_at: str
    updated_at: str

    class Config:
        orm_mode = True

class NetworkInterface(NetworkInterfaceInDB):
    pass

class NetworkDeviceBase(BaseModel):
    device_model: Optional[str] = None
    os_version: Optional[str] = None
    management_ip: Optional[str] = None
    console_port: Optional[str] = None
    device_role: Optional[str] = None

class NetworkDeviceCreate(NetworkDeviceBase):
    asset_id: int

class NetworkDeviceUpdate(BaseModel):
    device_model: Optional[str] = None
    os_version: Optional[str] = None
    management_ip: Optional[str] = None
    console_port: Optional[str] = None
    device_role: Optional[str] = None

class NetworkDeviceInDB(NetworkDeviceBase):
    id: int
    asset_id: int
    created_at: str
    updated_at: str

    class Config:
        orm_mode = True

class NetworkDevice(NetworkDeviceInDB):
    interfaces: Optional[List[NetworkInterface]] = None 