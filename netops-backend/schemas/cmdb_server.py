from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# 服务器Schema
class ServerBase(BaseModel):
    server_type: Optional[str] = None
    cpu_model: Optional[str] = None
    cpu_cores: Optional[int] = None
    memory_size: Optional[float] = None
    disk_size: Optional[float] = None
    os_type: Optional[str] = None
    os_version: Optional[str] = None
    management_ip: Optional[str] = None

class ServerCreate(ServerBase):
    asset_id: int

class ServerUpdate(BaseModel):
    server_type: Optional[str] = None
    cpu_model: Optional[str] = None
    cpu_cores: Optional[int] = None
    memory_size: Optional[float] = None
    disk_size: Optional[float] = None
    os_type: Optional[str] = None
    os_version: Optional[str] = None
    management_ip: Optional[str] = None

class ServerInDB(ServerBase):
    id: int
    asset_id: int
    created_at: str
    updated_at: str

    class Config:
        orm_mode = True

class Server(ServerInDB):
    pass

# 虚拟机Schema
class VirtualMachineBase(BaseModel):
    vm_type: Optional[str] = None
    vcpu_count: Optional[int] = None
    memory_size: Optional[float] = None
    disk_size: Optional[float] = None
    os_type: Optional[str] = None
    os_version: Optional[str] = None
    host_server_id: Optional[int] = None

class VirtualMachineCreate(VirtualMachineBase):
    asset_id: int

class VirtualMachineUpdate(BaseModel):
    vm_type: Optional[str] = None
    vcpu_count: Optional[int] = None
    memory_size: Optional[float] = None
    disk_size: Optional[float] = None
    os_type: Optional[str] = None
    os_version: Optional[str] = None
    host_server_id: Optional[int] = None

class VirtualMachineInDB(VirtualMachineBase):
    id: int
    asset_id: int
    created_at: str
    updated_at: str

    class Config:
        orm_mode = True

class VirtualMachine(VirtualMachineInDB):
    pass

# 服务器详情（包含虚拟机）
class ServerWithVMs(Server):
    virtual_machines: Optional[List[VirtualMachine]] = None 