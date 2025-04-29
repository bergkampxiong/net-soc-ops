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
    BatchAddDevices,
    BatchDeleteDevices
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
    # 检查分组是否存在
    group = db.query(DeviceGroup).filter(DeviceGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="分组不存在")
    
    # 获取分组成员
    members = db.query(DeviceGroupMember).filter(DeviceGroupMember.group_id == group_id).all()
    
    # 从CMDB获取设备信息
    device_ids = [member.device_id for member in members]
    devices = db.query(Asset).filter(Asset.id.in_(device_ids)).all()
    device_map = {device.id: device for device in devices}
    
    # 获取所有位置信息
    location_ids = [device.location_id for device in devices if device.location_id]
    locations = db.query(Location).filter(Location.id.in_(location_ids)).all()
    location_map = {location.id: location.name for location in locations}
    
    # 构建返回数据
    result = []
    for member in members:
        device = device_map.get(member.device_id)
        if device:
            result.append({
                "id": member.id,
                "group_id": member.group_id,
                "device_id": member.device_id,
                "device_name": device.name,
                "ip_address": device.ip_address or "",
                "device_type": device.device_type_id,
                "location": location_map.get(device.location_id, "")
            })
    
    return result

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
@router.post("/groups/{group_id}/members/batch", response_model=List[DeviceMemberSchema])
async def batch_add_group_members(
    group_id: int,
    batch: BatchAddDevices,
    db: Session = Depends(get_db)
):
    try:
        # 检查分组是否存在
        group = db.query(DeviceGroup).filter(DeviceGroup.id == group_id).first()
        if not group:
            raise HTTPException(status_code=404, detail="分组不存在")
        
        # 获取现有成员
        existing_members = db.query(DeviceGroupMember).filter(DeviceGroupMember.group_id == group_id).all()
        existing_device_ids = {member.device_id for member in existing_members}
        
        # 过滤掉已存在的设备
        new_device_ids = [device_id for device_id in batch.device_ids if device_id not in existing_device_ids]
        
        if not new_device_ids:
            return []
        
        # 添加新成员
        new_members = []
        for device_id in new_device_ids:
            try:
                member = DeviceGroupMember(
                    group_id=group_id,
                    device_id=device_id
                )
                db.add(member)
                new_members.append(member)
            except Exception as e:
                print(f"添加设备 {device_id} 到分组时出错: {str(e)}")
                continue
        
        db.commit()
        
        # 从CMDB获取设备信息
        devices = db.query(Asset).filter(Asset.id.in_([m.device_id for m in new_members])).all()
        device_map = {device.id: device for device in devices}
        
        # 获取所有位置信息
        location_ids = [device.location_id for device in devices if device.location_id]
        locations = db.query(Location).filter(Location.id.in_(location_ids)).all()
        location_map = {location.id: location.name for location in locations}
        
        # 构建返回数据
        result = []
        for member in new_members:
            device = device_map.get(member.device_id)
            if device:
                result.append({
                    "id": member.id,
                    "group_id": member.group_id,
                    "device_id": member.device_id,
                    "device_name": device.name,
                    "ip_address": device.ip_address or "",
                    "device_type": device.device_type_id,
                    "location": location_map.get(device.location_id, "")
                })
        
        return result
        
    except Exception as e:
        db.rollback()
        print(f"批量添加分组成员时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

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

# 批量删除分组成员
@router.delete("/groups/{group_id}/members")
def batch_delete_group_members(
    group_id: int,
    batch: BatchDeleteDevices,
    db: Session = Depends(get_db)
):
    try:
        # 检查分组是否存在
        group = db.query(DeviceGroup).filter(DeviceGroup.id == group_id).first()
        if not group:
            raise HTTPException(status_code=404, detail="分组不存在")
        
        # 检查要删除的成员是否存在
        existing_members = db.query(DeviceGroupMember).filter(
            DeviceGroupMember.group_id == group_id,
            DeviceGroupMember.device_id.in_(batch.device_ids)
        ).all()
        
        if not existing_members:
            return {"message": "没有找到要删除的成员"}
        
        # 删除成员
        for member in existing_members:
            db.delete(member)
        
        db.commit()
        return {"message": "批量删除成员成功"}
        
    except Exception as e:
        db.rollback()
        print(f"批量删除分组成员时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

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