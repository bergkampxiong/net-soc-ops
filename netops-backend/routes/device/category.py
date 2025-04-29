from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, inspect
from typing import List, Optional, Dict
from database.session import get_db
from database.category_models import DeviceGroup, DeviceGroupMember
from database.cmdb_models import Asset, DeviceType, Location
from schemas.category import (
    DeviceGroupCreate,
    DeviceGroup as DeviceGroupSchema,
    DeviceMember as DeviceMemberSchema,
    DeviceFilter,
    BatchAddDevices
)
import httpx
from datetime import datetime
import asyncio

router = APIRouter(
    prefix="/api/device/category",
    tags=["device-category"]
)

# 获取所有设备分组
@router.get("/groups", response_model=List[DeviceGroupSchema])
def get_device_groups(
    db: Session = Depends(get_db)
):
    groups = db.query(DeviceGroup).all()
    # 确保返回的每个分组对象都包含所需的字段
    return [
        {
            "id": group.id,
            "name": group.name,
            "description": group.description,
            "created_at": group.created_at
        }
        for group in groups
    ]

# 创建设备分组
@router.post("/groups", response_model=DeviceGroupSchema)
def create_device_group(
    group: DeviceGroupCreate,
    db: Session = Depends(get_db)
):
    db_group = DeviceGroup(
        name=group.name,
        description=group.description
    )
    db.add(db_group)
    db.commit()
    db.refresh(db_group)
    return db_group

# 更新设备分组
@router.put("/groups/{group_id}", response_model=DeviceGroupSchema)
def update_device_group(
    group_id: int,
    group: DeviceGroupCreate,
    db: Session = Depends(get_db)
):
    db_group = db.query(DeviceGroup).filter(DeviceGroup.id == group_id).first()
    if not db_group:
        raise HTTPException(status_code=404, detail="设备分组不存在")
    
    db_group.name = group.name
    db_group.description = group.description
    db.commit()
    db.refresh(db_group)
    return db_group

# 删除设备分组
@router.delete("/groups/{group_id}")
def delete_device_group(
    group_id: int,
    db: Session = Depends(get_db)
):
    db_group = db.query(DeviceGroup).filter(DeviceGroup.id == group_id).first()
    if not db_group:
        raise HTTPException(status_code=404, detail="设备分组不存在")
    
    # 删除分组下的所有成员
    db.query(DeviceGroupMember).filter(DeviceGroupMember.group_id == group_id).delete()
    db.delete(db_group)
    db.commit()
    return {"message": "设备分组删除成功"}

# 获取分组成员
@router.get("/groups/{group_id}/members", response_model=List[DeviceMemberSchema])
def get_group_members(
    group_id: int,
    db: Session = Depends(get_db)
):
    members = db.query(DeviceGroupMember).filter(DeviceGroupMember.group_id == group_id).all()
    return members

# 添加分组成员
@router.post("/groups/{group_id}/members")
def add_group_member(
    group_id: int,
    member: DeviceMemberSchema,
    db: Session = Depends(get_db)
):
    # 检查分组是否存在
    group = db.query(DeviceGroup).filter(DeviceGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="设备分组不存在")
    
    # 检查成员是否已存在
    existing_member = db.query(DeviceGroupMember).filter(
        DeviceGroupMember.group_id == group_id,
        DeviceGroupMember.device_id == member.device_id
    ).first()
    
    if existing_member:
        raise HTTPException(status_code=400, detail="设备已存在于该分组中")
    
    # 创建新成员
    db_member = DeviceGroupMember(
        group_id=group_id,
        device_id=member.device_id,
        device_name=member.device_name,
        ip_address=member.ip_address,
        device_type=member.device_type,
        location=member.location
    )
    db.add(db_member)
    db.commit()
    db.refresh(db_member)
    return db_member

# 批量添加分组成员
@router.post("/groups/{group_id}/members/batch")
def batch_add_group_members(
    group_id: int,
    batch: BatchAddDevices,
    db: Session = Depends(get_db)
):
    # 检查分组是否存在
    group = db.query(DeviceGroup).filter(DeviceGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="设备分组不存在")
    
    # 获取现有成员
    existing_members = db.query(DeviceGroupMember).filter(
        DeviceGroupMember.group_id == group_id
    ).all()
    existing_device_ids = {member.device_id for member in existing_members}
    
    # 过滤掉已存在的设备
    new_devices = [device for device in batch.devices if device.device_id not in existing_device_ids]
    
    if not new_devices:
        return {"message": "没有新设备需要添加"}
    
    # 批量添加新成员
    for device in new_devices:
        db_member = DeviceGroupMember(
            group_id=group_id,
            device_id=device.device_id,
            device_name=device.device_name,
            ip_address=device.ip_address,
            device_type=device.device_type,
            location=device.location
        )
        db.add(db_member)
    
    db.commit()
    return {"message": f"成功添加 {len(new_devices)} 个设备到分组"}

# 删除分组成员
@router.delete("/groups/{group_id}/members/{member_id}")
def delete_group_member(
    group_id: int,
    member_id: int,
    db: Session = Depends(get_db)
):
    member = db.query(DeviceGroupMember).filter(
        DeviceGroupMember.group_id == group_id,
        DeviceGroupMember.id == member_id
    ).first()
    
    if not member:
        raise HTTPException(status_code=404, detail="分组成员不存在")
    
    db.delete(member)
    db.commit()
    return {"message": "分组成员删除成功"}

# 从CMDB获取设备列表
@router.get("/cmdb-devices")
async def get_cmdb_devices(
    name: Optional[str] = None,
    ip_address: Optional[str] = None,
    device_type_id: Optional[int] = None,
    location_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Asset)
    
    if name:
        query = query.filter(Asset.name.ilike(f"%{name}%"))
    if ip_address:
        query = query.filter(Asset.ip_address.ilike(f"%{ip_address}%"))
    if device_type_id:
        query = query.filter(Asset.device_type_id == device_type_id)
    if location_id:
        query = query.filter(Asset.location_id == location_id)
    
    devices = query.all()
    return devices 