from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# 设备分组基础模型
class DeviceGroupBase(BaseModel):
    name: str
    description: Optional[str] = None

# 创建设备分组请求
class DeviceGroupCreate(DeviceGroupBase):
    pass

# 设备分组响应
class DeviceGroup(DeviceGroupBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# 设备成员基础模型
class DeviceMemberBase(BaseModel):
    device_name: str
    ip_address: str
    location: Optional[str] = None

# 设备成员响应
class DeviceMember(DeviceMemberBase):
    id: int
    group_id: int
    device_id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        arbitrary_types_allowed = True

# 设备筛选条件
class DeviceFilter(BaseModel):
    name: Optional[str] = None
    ip_address: Optional[str] = None
    device_type: Optional[str] = None
    location: Optional[str] = None

# 批量添加设备请求
class BatchAddDevices(BaseModel):
    device_ids: List[int] 