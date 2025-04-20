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
    db_group = DeviceGroup(**group.dict())
    db.add(db_group)
    db.commit()
    db.refresh(db_group)
    # 确保返回的对象包含所需的字段
    return {
        "id": db_group.id,
        "name": db_group.name,
        "description": db_group.description,
        "created_at": db_group.created_at
    }

# 删除设备分组
@router.delete("/groups/{group_id}")
def delete_device_group(
    group_id: int,
    db: Session = Depends(get_db)
):
    db_group = db.query(DeviceGroup).filter(DeviceGroup.id == group_id).first()
    if not db_group:
        raise HTTPException(status_code=404, detail="设备分组不存在")
    
    db.delete(db_group)
    db.commit()
    return {"message": "设备分组已删除"}

# 获取分组成员
@router.get("/groups/{group_id}/members")
async def get_group_members(
    group_id: int,
    db: Session = Depends(get_db)
):
    # 检查分组是否存在
    group = db.query(DeviceGroup).filter(DeviceGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="设备分组不存在")
        
    members = db.query(DeviceGroupMember).filter(
        DeviceGroupMember.group_id == group_id
    ).all()
    
    if not members:
        return []
    
    # 收集所有设备ID
    device_ids = [member.device_id for member in members]
    
    # 创建设备ID到成员对象的映射
    member_map = {member.device_id: member for member in members}
    
    # 批量获取设备信息
    result = []
    async with httpx.AsyncClient() as client:
        # 并行请求所有设备信息
        tasks = []
        for device_id in device_ids:
            tasks.append(client.get(f"http://localhost:3000/api/cmdb/assets/{device_id}", timeout=5.0))
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理响应
        for i, response in enumerate(responses):
            device_id = device_ids[i]
            member = member_map[device_id]
            
            if isinstance(response, Exception):
                # 处理请求异常
                print(f"获取设备信息异常: {str(response)}")
                result.append({
                    "id": member.id,
                    "group_id": member.group_id,
                    "device_id": device_id,
                    "device_name": f"Device {device_id}",
                    "ip_address": "",
                    "location": ""
                })
                continue
                
            if response.status_code == 200:
                device_data = response.json()
                result.append({
                    "id": member.id,
                    "group_id": member.group_id,
                    "device_id": device_id,
                    "device_name": device_data.get("name", ""),
                    "ip_address": device_data.get("ip_address", ""),
                    "location": device_data.get("location", "")
                })
            else:
                # 如果无法获取设备信息，返回基本信息
                result.append({
                    "id": member.id,
                    "group_id": member.group_id,
                    "device_id": device_id,
                    "device_name": f"Device {device_id}",
                    "ip_address": "",
                    "location": ""
                })
    
    return result

# 获取设备类型列表
@router.get("/device-types")
async def get_device_types():
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:3000/api/cmdb/device-types")
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="获取设备类型失败")
        return response.json()

# 获取位置列表
@router.get("/locations")
async def get_locations():
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:3000/api/cmdb/locations")
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="获取位置列表失败")
        return response.json()

# 获取所有CMDB设备（支持筛选）
@router.get("/cmdb-devices")
async def get_cmdb_devices(
    name: Optional[str] = None,
    ip_address: Optional[str] = None,
    device_type_id: Optional[int] = None,
    location_id: Optional[int] = None
):
    # 至少需要一个筛选条件
    if not any([name, ip_address, device_type_id, location_id]):
        return []

    # 构建查询参数
    params = {}
    if name:
        params["name"] = name
    if ip_address:
        params["ip_address"] = ip_address
    if device_type_id:
        params["device_type_id"] = device_type_id
    if location_id:
        params["location_id"] = location_id

    # 调用 CMDB 查询 API
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://localhost:3000/api/cmdb/assets",
            params=params
        )
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="CMDB查询失败")
        
        devices = response.json()
        
        # 格式化响应数据
        return [
            {
                "id": device["id"],
                "name": device["name"],
                "ip_address": device.get("ip_address", ""),
                "device_type": device.get("device_type"),
                "location": device.get("location")
            }
            for device in devices
        ]

# 添加设备到分组
@router.post("/groups/{group_id}/members")
async def add_group_members(
    group_id: int,
    request: BatchAddDevices,
    db: Session = Depends(get_db)
):
    try:
        # 检查分组是否存在
        group = db.query(DeviceGroup).filter(DeviceGroup.id == group_id).first()
        if not group:
            raise HTTPException(status_code=404, detail="设备分组不存在")
        
        # 检查设备是否已在分组中
        existing_members = db.query(DeviceGroupMember).filter(
            DeviceGroupMember.group_id == group_id,
            DeviceGroupMember.device_id.in_(request.device_ids)
        ).all()
        
        existing_device_ids = {member.device_id for member in existing_members}
        new_device_ids = [device_id for device_id in request.device_ids if device_id not in existing_device_ids]
        
        if not new_device_ids:
            raise HTTPException(status_code=400, detail="所选设备已在分组中")
        
        # 批量创建新成员
        new_members = []
        for device_id in new_device_ids:
            member = DeviceGroupMember(
                group_id=group_id,
                device_id=device_id
            )
            db.add(member)
            new_members.append(member)
        
        # 一次性提交所有更改
        db.commit()
        
        # 批量刷新所有新成员
        for member in new_members:
            db.refresh(member)
        
        # 创建设备ID到成员对象的映射
        member_map = {member.device_id: member for member in new_members}
        
        # 批量获取设备信息
        result = []
        async with httpx.AsyncClient() as client:
            # 并行请求所有设备信息
            tasks = []
            for device_id in new_device_ids:
                tasks.append(client.get(f"http://localhost:3000/api/cmdb/assets/{device_id}", timeout=5.0))
            
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理响应
            for i, response in enumerate(responses):
                device_id = new_device_ids[i]
                member = member_map[device_id]
                
                if isinstance(response, Exception):
                    # 处理请求异常
                    print(f"获取设备信息异常: {str(response)}")
                    result.append({
                        "id": member.id,
                        "group_id": member.group_id,
                        "device_id": device_id,
                        "device_name": f"Device {device_id}",
                        "ip_address": "",
                        "location": ""
                    })
                    continue
                    
                if response.status_code == 200:
                    device_data = response.json()
                    result.append({
                        "id": member.id,
                        "group_id": member.group_id,
                        "device_id": device_id,
                        "device_name": device_data.get("name", ""),
                        "ip_address": device_data.get("ip_address", ""),
                        "location": device_data.get("location", "")
                    })
                else:
                    # 如果无法获取设备信息，返回基本信息
                    result.append({
                        "id": member.id,
                        "group_id": member.group_id,
                        "device_id": device_id,
                        "device_name": f"Device {device_id}",
                        "ip_address": "",
                        "location": ""
                    })
        
        return result
    except HTTPException:
        # 重新抛出 HTTP 异常
        raise
    except Exception as e:
        db.rollback()
        # 打印详细的错误信息
        import traceback
        error_details = traceback.format_exc()
        print(f"添加设备到分组失败: {str(e)}\n{error_details}")
        raise HTTPException(status_code=500, detail=f"添加设备到分组失败: {str(e)}")

# 从分组中移除设备
@router.delete("/groups/{group_id}/members/{member_id}")
def remove_group_member(
    group_id: int,
    member_id: int,
    db: Session = Depends(get_db)
):
    # 检查分组是否存在
    group = db.query(DeviceGroup).filter(DeviceGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="设备分组不存在")
    
    # 查找成员
    member = db.query(DeviceGroupMember).filter(
        DeviceGroupMember.id == member_id,
        DeviceGroupMember.group_id == group_id
    ).first()
    
    if not member:
        raise HTTPException(status_code=404, detail="设备成员不存在")
    
    try:
        # 删除成员
        db.delete(member)
        db.commit()
        return {"message": "设备已从分组中移除", "member_id": member_id, "group_id": group_id}
    except Exception as e:
        db.rollback()
        # 打印详细的错误信息
        import traceback
        error_details = traceback.format_exc()
        print(f"从分组中移除设备失败: {str(e)}\n{error_details}")
        raise HTTPException(status_code=500, detail=f"从分组中移除设备失败: {str(e)}")

# 批量从分组中移除设备
@router.delete("/groups/{group_id}/members")
def remove_group_members_batch(
    group_id: int,
    request: BatchAddDevices,
    db: Session = Depends(get_db)
):
    # 检查分组是否存在
    group = db.query(DeviceGroup).filter(DeviceGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="设备分组不存在")
    
    if not request.device_ids:
        raise HTTPException(status_code=400, detail="请提供要删除的设备ID列表")
    
    try:
        # 查找成员
        members = db.query(DeviceGroupMember).filter(
            DeviceGroupMember.group_id == group_id,
            DeviceGroupMember.device_id.in_(request.device_ids)
        ).all()
        
        if not members:
            raise HTTPException(status_code=404, detail="未找到指定的设备成员")
        
        # 批量删除成员
        for member in members:
            db.delete(member)
        
        # 一次性提交所有更改
        db.commit()
        
        return {
            "message": "设备已从分组中批量移除", 
            "group_id": group_id, 
            "removed_count": len(members),
            "device_ids": [member.device_id for member in members]
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        # 打印详细的错误信息
        import traceback
        error_details = traceback.format_exc()
        print(f"批量从分组中移除设备失败: {str(e)}\n{error_details}")
        raise HTTPException(status_code=500, detail=f"批量从分组中移除设备失败: {str(e)}") 