from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from database.cmdb_session import get_cmdb_db
from database.cmdb_models import DeviceType as DeviceTypeModel
from database.cmdb_models import Vendor as VendorModel
from database.cmdb_models import Location as LocationModel
from database.cmdb_models import Department as DepartmentModel
from database.cmdb_models import AssetStatus as AssetStatusModel
from database.cmdb_models import SystemType as SystemTypeModel

from schemas.cmdb_base import (
    DeviceType, DeviceTypeCreate, DeviceTypeUpdate,
    Vendor, VendorCreate, VendorUpdate,
    Location, LocationCreate, LocationUpdate,
    Department, DepartmentCreate, DepartmentUpdate,
    AssetStatus, AssetStatusCreate, AssetStatusUpdate,
    SystemType
)

router = APIRouter()

# 设备类型API
@router.get("/device-types", response_model=List[DeviceType], tags=["CMDB基础数据"])
def get_device_types(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_cmdb_db),
):
    """获取所有设备类型"""
    device_types = db.query(DeviceTypeModel).offset(skip).limit(limit).all()
    return device_types

@router.post("/device-types", response_model=DeviceType, tags=["CMDB基础数据"])
def create_device_type(
    device_type: DeviceTypeCreate,
    db: Session = Depends(get_cmdb_db),
):
    """创建新设备类型"""
    db_device_type = DeviceTypeModel(
        name=device_type.name,
        description=device_type.description,
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat()
    )
    db.add(db_device_type)
    db.commit()
    db.refresh(db_device_type)
    return db_device_type

@router.get("/device-types/{device_type_id}", response_model=DeviceType, tags=["CMDB基础数据"])
def get_device_type(
    device_type_id: int,
    db: Session = Depends(get_cmdb_db),
):
    """获取特定设备类型"""
    db_device_type = db.query(DeviceTypeModel).filter(DeviceTypeModel.id == device_type_id).first()
    if db_device_type is None:
        raise HTTPException(status_code=404, detail="设备类型不存在")
    return db_device_type

@router.put("/device-types/{device_type_id}", response_model=DeviceType, tags=["CMDB基础数据"])
def update_device_type(
    device_type_id: int,
    device_type: DeviceTypeUpdate,
    db: Session = Depends(get_cmdb_db),
):
    """更新设备类型"""
    db_device_type = db.query(DeviceTypeModel).filter(DeviceTypeModel.id == device_type_id).first()
    if db_device_type is None:
        raise HTTPException(status_code=404, detail="设备类型不存在")
    
    update_data = device_type.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_device_type, key, value)
    
    db_device_type.updated_at = datetime.now().isoformat()
    db.commit()
    db.refresh(db_device_type)
    return db_device_type

@router.delete("/device-types/{device_type_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["CMDB基础数据"])
def delete_device_type(
    device_type_id: int,
    db: Session = Depends(get_cmdb_db),
):
    """删除设备类型"""
    db_device_type = db.query(DeviceTypeModel).filter(DeviceTypeModel.id == device_type_id).first()
    if db_device_type is None:
        raise HTTPException(status_code=404, detail="设备类型不存在")
    
    db.delete(db_device_type)
    db.commit()
    return None

# 厂商API
@router.get("/vendors", response_model=List[Vendor], tags=["CMDB基础数据"])
def get_vendors(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_cmdb_db),
):
    """获取所有厂商"""
    vendors = db.query(VendorModel).offset(skip).limit(limit).all()
    return vendors

@router.post("/vendors", response_model=Vendor, tags=["CMDB基础数据"])
def create_vendor(
    vendor: VendorCreate,
    db: Session = Depends(get_cmdb_db),
):
    """创建新厂商"""
    db_vendor = VendorModel(
        name=vendor.name,
        description=vendor.description,
        contact=vendor.contact,
        website=vendor.website,
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat()
    )
    db.add(db_vendor)
    db.commit()
    db.refresh(db_vendor)
    return db_vendor

@router.get("/vendors/{vendor_id}", response_model=Vendor, tags=["CMDB基础数据"])
def get_vendor(
    vendor_id: int,
    db: Session = Depends(get_cmdb_db),
):
    """获取特定厂商"""
    db_vendor = db.query(VendorModel).filter(VendorModel.id == vendor_id).first()
    if db_vendor is None:
        raise HTTPException(status_code=404, detail="厂商不存在")
    return db_vendor

@router.put("/vendors/{vendor_id}", response_model=Vendor, tags=["CMDB基础数据"])
def update_vendor(
    vendor_id: int,
    vendor: VendorUpdate,
    db: Session = Depends(get_cmdb_db),
):
    """更新厂商"""
    db_vendor = db.query(VendorModel).filter(VendorModel.id == vendor_id).first()
    if db_vendor is None:
        raise HTTPException(status_code=404, detail="厂商不存在")
    
    update_data = vendor.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_vendor, key, value)
    
    db_vendor.updated_at = datetime.now().isoformat()
    db.commit()
    db.refresh(db_vendor)
    return db_vendor

@router.delete("/vendors/{vendor_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["CMDB基础数据"])
def delete_vendor(
    vendor_id: int,
    db: Session = Depends(get_cmdb_db),
):
    """删除厂商"""
    db_vendor = db.query(VendorModel).filter(VendorModel.id == vendor_id).first()
    if db_vendor is None:
        raise HTTPException(status_code=404, detail="厂商不存在")
    
    db.delete(db_vendor)
    db.commit()
    return None

# 位置API
@router.get("/locations", response_model=List[Location], tags=["CMDB基础数据"])
def get_locations(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_cmdb_db),
):
    """获取所有位置"""
    locations = db.query(LocationModel).offset(skip).limit(limit).all()
    return locations

@router.post("/locations", response_model=Location, tags=["CMDB基础数据"])
def create_location(
    location: LocationCreate,
    db: Session = Depends(get_cmdb_db),
):
    """创建新位置"""
    db_location = LocationModel(
        name=location.name,
        address=location.address,
        description=location.description,
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat()
    )
    db.add(db_location)
    db.commit()
    db.refresh(db_location)
    return db_location

@router.get("/locations/{location_id}", response_model=Location, tags=["CMDB基础数据"])
def get_location(
    location_id: int,
    db: Session = Depends(get_cmdb_db),
):
    """获取特定位置"""
    db_location = db.query(LocationModel).filter(LocationModel.id == location_id).first()
    if db_location is None:
        raise HTTPException(status_code=404, detail="位置不存在")
    return db_location

@router.put("/locations/{location_id}", response_model=Location, tags=["CMDB基础数据"])
def update_location(
    location_id: int,
    location: LocationUpdate,
    db: Session = Depends(get_cmdb_db),
):
    """更新位置"""
    db_location = db.query(LocationModel).filter(LocationModel.id == location_id).first()
    if db_location is None:
        raise HTTPException(status_code=404, detail="位置不存在")
    
    update_data = location.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_location, key, value)
    
    db_location.updated_at = datetime.now().isoformat()
    db.commit()
    db.refresh(db_location)
    return db_location

@router.delete("/locations/{location_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["CMDB基础数据"])
def delete_location(
    location_id: int,
    db: Session = Depends(get_cmdb_db),
):
    """删除位置"""
    db_location = db.query(LocationModel).filter(LocationModel.id == location_id).first()
    if db_location is None:
        raise HTTPException(status_code=404, detail="位置不存在")
    
    db.delete(db_location)
    db.commit()
    return None

# 部门API
@router.get("/departments", response_model=List[Department], tags=["CMDB基础数据"])
def get_departments(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_cmdb_db),
):
    """获取所有部门"""
    departments = db.query(DepartmentModel).offset(skip).limit(limit).all()
    return departments

@router.post("/departments", response_model=Department, tags=["CMDB基础数据"])
def create_department(
    department: DepartmentCreate,
    db: Session = Depends(get_cmdb_db),
):
    """创建新部门"""
    db_department = DepartmentModel(
        name=department.name,
        description=department.description,
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat()
    )
    db.add(db_department)
    db.commit()
    db.refresh(db_department)
    return db_department

@router.get("/departments/{department_id}", response_model=Department, tags=["CMDB基础数据"])
def get_department(
    department_id: int,
    db: Session = Depends(get_cmdb_db),
):
    """获取特定部门"""
    db_department = db.query(DepartmentModel).filter(DepartmentModel.id == department_id).first()
    if db_department is None:
        raise HTTPException(status_code=404, detail="部门不存在")
    return db_department

@router.put("/departments/{department_id}", response_model=Department, tags=["CMDB基础数据"])
def update_department(
    department_id: int,
    department: DepartmentUpdate,
    db: Session = Depends(get_cmdb_db),
):
    """更新部门"""
    db_department = db.query(DepartmentModel).filter(DepartmentModel.id == department_id).first()
    if db_department is None:
        raise HTTPException(status_code=404, detail="部门不存在")
    
    update_data = department.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_department, key, value)
    
    db_department.updated_at = datetime.now().isoformat()
    db.commit()
    db.refresh(db_department)
    return db_department

@router.delete("/departments/{department_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["CMDB基础数据"])
def delete_department(
    department_id: int,
    db: Session = Depends(get_cmdb_db),
):
    """删除部门"""
    db_department = db.query(DepartmentModel).filter(DepartmentModel.id == department_id).first()
    if db_department is None:
        raise HTTPException(status_code=404, detail="部门不存在")
    
    db.delete(db_department)
    db.commit()
    return None

# 资产状态API
@router.get("/asset-statuses", response_model=List[AssetStatus], tags=["CMDB基础数据"])
def get_asset_statuses(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_cmdb_db),
):
    """获取所有资产状态"""
    asset_statuses = db.query(AssetStatusModel).offset(skip).limit(limit).all()
    return asset_statuses

@router.post("/asset-statuses", response_model=AssetStatus, tags=["CMDB基础数据"])
def create_asset_status(
    asset_status: AssetStatusCreate,
    db: Session = Depends(get_cmdb_db),
):
    """创建新资产状态"""
    db_asset_status = AssetStatusModel(
        name=asset_status.name,
        description=asset_status.description,
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat()
    )
    db.add(db_asset_status)
    db.commit()
    db.refresh(db_asset_status)
    return db_asset_status

@router.get("/asset-statuses/{asset_status_id}", response_model=AssetStatus, tags=["CMDB基础数据"])
def get_asset_status(
    asset_status_id: int,
    db: Session = Depends(get_cmdb_db),
):
    """获取特定资产状态"""
    db_asset_status = db.query(AssetStatusModel).filter(AssetStatusModel.id == asset_status_id).first()
    if db_asset_status is None:
        raise HTTPException(status_code=404, detail="资产状态不存在")
    return db_asset_status

@router.put("/asset-statuses/{asset_status_id}", response_model=AssetStatus, tags=["CMDB基础数据"])
def update_asset_status(
    asset_status_id: int,
    asset_status: AssetStatusUpdate,
    db: Session = Depends(get_cmdb_db),
):
    """更新资产状态"""
    db_asset_status = db.query(AssetStatusModel).filter(AssetStatusModel.id == asset_status_id).first()
    if db_asset_status is None:
        raise HTTPException(status_code=404, detail="资产状态不存在")
    
    update_data = asset_status.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_asset_status, key, value)
    
    db_asset_status.updated_at = datetime.now().isoformat()
    db.commit()
    db.refresh(db_asset_status)
    return db_asset_status

@router.delete("/asset-statuses/{asset_status_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["CMDB基础数据"])
def delete_asset_status(
    asset_status_id: int,
    db: Session = Depends(get_cmdb_db),
):
    """删除资产状态"""
    db_asset_status = db.query(AssetStatusModel).filter(AssetStatusModel.id == asset_status_id).first()
    if db_asset_status is None:
        raise HTTPException(status_code=404, detail="资产状态不存在")
    
    db.delete(db_asset_status)
    db.commit()
    return None

# 系统类型API
@router.get("/system-types", response_model=List[SystemType], tags=["CMDB基础数据"])
def get_system_types(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_cmdb_db),
):
    """获取系统类型列表"""
    system_types = db.query(SystemTypeModel).offset(skip).limit(limit).all()
    return system_types

@router.get("/system-types/{system_type_id}", response_model=SystemType, tags=["CMDB基础数据"])
def get_system_type(
    system_type_id: int,
    db: Session = Depends(get_cmdb_db),
):
    """获取特定系统类型详情"""
    system_type = db.query(SystemTypeModel).filter(SystemTypeModel.id == system_type_id).first()
    if system_type is None:
        raise HTTPException(status_code=404, detail="系统类型不存在")
    return system_type

@router.post("/system-types", response_model=SystemType, tags=["CMDB基础数据"])
def create_system_type(
    name: str,
    description: Optional[str] = None,
    db: Session = Depends(get_cmdb_db),
):
    """创建新系统类型"""
    db_system_type = db.query(SystemTypeModel).filter(SystemTypeModel.name == name).first()
    if db_system_type:
        raise HTTPException(status_code=400, detail="系统类型已存在")
    
    db_system_type = SystemTypeModel(
        name=name,
        description=description,
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat()
    )
    db.add(db_system_type)
    db.commit()
    db.refresh(db_system_type)
    return db_system_type

@router.put("/system-types/{system_type_id}", response_model=SystemType, tags=["CMDB基础数据"])
def update_system_type(
    system_type_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    db: Session = Depends(get_cmdb_db),
):
    """更新系统类型"""
    db_system_type = db.query(SystemTypeModel).filter(SystemTypeModel.id == system_type_id).first()
    if db_system_type is None:
        raise HTTPException(status_code=404, detail="系统类型不存在")
    
    if name is not None:
        db_system_type.name = name
    if description is not None:
        db_system_type.description = description
    
    db_system_type.updated_at = datetime.now().isoformat()
    db.commit()
    db.refresh(db_system_type)
    return db_system_type

@router.delete("/system-types/{system_type_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["CMDB基础数据"])
def delete_system_type(
    system_type_id: int,
    db: Session = Depends(get_cmdb_db),
):
    """删除系统类型"""
    db_system_type = db.query(SystemTypeModel).filter(SystemTypeModel.id == system_type_id).first()
    if db_system_type is None:
        raise HTTPException(status_code=404, detail="系统类型不存在")
    
    db.delete(db_system_type)
    db.commit()
    return None 