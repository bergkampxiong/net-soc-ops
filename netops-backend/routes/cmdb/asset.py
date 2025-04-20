from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from datetime import datetime
import csv
import io
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel

from database.cmdb_session import get_cmdb_db
from database.cmdb_models import Asset as AssetModel
from database.cmdb_models import DeviceType as DeviceTypeModel
from database.cmdb_models import Vendor as VendorModel
from database.cmdb_models import Department as DepartmentModel
from database.cmdb_models import Location as LocationModel
from database.cmdb_models import AssetStatus as AssetStatusModel
from database.cmdb_models import SystemType as SystemTypeModel

from schemas.cmdb_asset import (
    Asset, AssetCreate, AssetUpdate, AssetQueryParams, AssetStatistics, ImportResponse
)

router = APIRouter()

# 资产API
@router.get("/assets", response_model=List[Asset], tags=["CMDB资产"])
def get_assets(
    skip: int = 0,
    limit: int = 100,
    name: Optional[str] = None,
    asset_tag: Optional[str] = None,
    ip_address: Optional[str] = None,
    device_type_id: Optional[int] = None,
    vendor_id: Optional[int] = None,
    department_id: Optional[int] = None,
    location_id: Optional[int] = None,
    status_id: Optional[int] = None,
    system_type_id: Optional[int] = None,
    db: Session = Depends(get_cmdb_db),
):
    """获取资产列表，支持多种过滤条件"""
    query = db.query(AssetModel)
    
    # 应用过滤条件
    if name:
        query = query.filter(AssetModel.name.ilike(f"%{name}%"))
    if asset_tag:
        query = query.filter(AssetModel.asset_tag.ilike(f"%{asset_tag}%"))
    if ip_address:
        query = query.filter(AssetModel.ip_address.ilike(f"%{ip_address}%"))
    if device_type_id:
        query = query.filter(AssetModel.device_type_id == device_type_id)
    if vendor_id:
        query = query.filter(AssetModel.vendor_id == vendor_id)
    if department_id:
        query = query.filter(AssetModel.department_id == department_id)
    if location_id:
        query = query.filter(AssetModel.location_id == location_id)
    if status_id:
        query = query.filter(AssetModel.status_id == status_id)
    if system_type_id:
        query = query.filter(AssetModel.system_type_id == system_type_id)
    
    # 执行查询
    assets = query.offset(skip).limit(limit).all()
    return assets

@router.post("/assets", response_model=Asset, tags=["CMDB资产"])
def create_asset(
    asset: AssetCreate,
    db: Session = Depends(get_cmdb_db),
):
    """创建新资产"""
    db_asset = AssetModel(
        name=asset.name,
        asset_tag=asset.asset_tag,
        ip_address=asset.ip_address,
        serial_number=asset.serial_number,
        device_type_id=asset.device_type_id,
        vendor_id=asset.vendor_id,
        department_id=asset.department_id,
        location_id=asset.location_id,
        status_id=asset.status_id,
        system_type_id=asset.system_type_id,
        owner=asset.owner,
        purchase_date=asset.purchase_date,
        purchase_cost=asset.purchase_cost,
        current_value=asset.current_value,
        online_date=asset.online_date,
        warranty_expiry=asset.warranty_expiry,
        notes=asset.notes,
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat()
    )
    db.add(db_asset)
    db.commit()
    db.refresh(db_asset)
    return db_asset

@router.get("/assets/{asset_id}", response_model=Asset, tags=["CMDB资产"])
def get_asset(
    asset_id: int,
    db: Session = Depends(get_cmdb_db),
):
    """获取特定资产详情"""
    db_asset = db.query(AssetModel).filter(AssetModel.id == asset_id).first()
    if db_asset is None:
        raise HTTPException(status_code=404, detail="资产不存在")
    return db_asset

@router.put("/assets/{asset_id}", response_model=Asset, tags=["CMDB资产"])
def update_asset(
    asset_id: int,
    asset: AssetUpdate,
    db: Session = Depends(get_cmdb_db),
):
    """更新资产信息"""
    db_asset = db.query(AssetModel).filter(AssetModel.id == asset_id).first()
    if db_asset is None:
        raise HTTPException(status_code=404, detail="资产不存在")
    
    update_data = asset.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_asset, key, value)
    
    db_asset.updated_at = datetime.now().isoformat()
    db.commit()
    db.refresh(db_asset)
    return db_asset

@router.delete("/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["CMDB资产"])
def delete_asset(
    asset_id: int,
    db: Session = Depends(get_cmdb_db),
):
    """删除资产"""
    db_asset = db.query(AssetModel).filter(AssetModel.id == asset_id).first()
    if db_asset is None:
        raise HTTPException(status_code=404, detail="资产不存在")
    
    db.delete(db_asset)
    db.commit()
    return None

@router.post("/assets/query", response_model=List[Asset], tags=["CMDB资产"])
def query_assets(
    query_params: AssetQueryParams,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_cmdb_db),
):
    """高级查询资产"""
    query = db.query(AssetModel)
    
    # 从查询参数中提取非空字段
    filter_params = query_params.dict(exclude_unset=True, exclude_none=True)
    
    # 应用过滤条件
    for key, value in filter_params.items():
        if key == 'name' or key == 'asset_tag' or key == 'ip_address' or key == 'serial_number' or key == 'owner':
            # 对字符串字段使用模糊匹配
            query = query.filter(getattr(AssetModel, key).ilike(f"%{value}%"))
        else:
            # 对其他字段使用精确匹配
            query = query.filter(getattr(AssetModel, key) == value)
    
    # 执行查询
    assets = query.offset(skip).limit(limit).all()
    return assets

@router.get("/assets/statistics", response_model=AssetStatistics, tags=["CMDB资产"])
def get_asset_statistics(
    db: Session = Depends(get_cmdb_db),
):
    """获取资产统计信息"""
    # 计算总资产数
    total_assets = db.query(AssetModel).count()
    
    # 按设备类型统计
    device_type_stats = {}
    device_types = db.query(DeviceTypeModel).all()
    for dt in device_types:
        count = db.query(AssetModel).filter(AssetModel.device_type_id == dt.id).count()
        device_type_stats[dt.name] = count
    
    # 按厂商统计
    vendor_stats = {}
    vendors = db.query(VendorModel).all()
    for v in vendors:
        count = db.query(AssetModel).filter(AssetModel.vendor_id == v.id).count()
        vendor_stats[v.name] = count
    
    # 按部门统计
    department_stats = {}
    departments = db.query(DepartmentModel).all()
    for d in departments:
        count = db.query(AssetModel).filter(AssetModel.department_id == d.id).count()
        department_stats[d.name] = count
    
    # 按位置统计
    location_stats = {}
    locations = db.query(LocationModel).all()
    for l in locations:
        count = db.query(AssetModel).filter(AssetModel.location_id == l.id).count()
        location_stats[l.name] = count
    
    # 按状态统计
    status_stats = {}
    statuses = db.query(AssetStatusModel).all()
    for s in statuses:
        count = db.query(AssetModel).filter(AssetModel.status_id == s.id).count()
        status_stats[s.name] = count
    
    return {
        "total_assets": total_assets,
        "by_device_type": device_type_stats,
        "by_vendor": vendor_stats,
        "by_department": department_stats,
        "by_location": location_stats,
        "by_status": status_stats
    }

@router.post("/assets/import", response_model=ImportResponse, tags=["CMDB资产"])
async def import_assets_from_csv(
    request: dict,
    db: Session = Depends(get_cmdb_db),
):
    """从CSV内容导入资产数据"""
    if 'content' not in request:
        raise HTTPException(status_code=400, detail="缺少CSV内容")
    
    # 处理CSV数据
    imported_count = 0
    failed_count = 0
    errors = []
    
    try:
        # 解析CSV内容
        csv_reader = csv.DictReader(io.StringIO(request['content']))
        
        # 获取设备类型、厂商、状态和系统类型的映射
        device_types = {dt.name: dt.id for dt in db.query(DeviceTypeModel).all()}
        vendors = {v.name: v.id for v in db.query(VendorModel).all()}
        statuses = {s.name: s.id for s in db.query(AssetStatusModel).all()}
        locations = {l.name: l.id for l in db.query(LocationModel).all()}
        system_types = {st.name: st.id for st in db.query(SystemTypeModel).all()}
        departments = {d.name: d.id for d in db.query(DepartmentModel).all()}
        
        for row_idx, row in enumerate(csv_reader, start=1):
            try:
                # 检查必填字段
                required_fields = ['设备名称', '资产标签', '设备类型', 'IP地址', '系统类型']
                missing_fields = [field for field in required_fields if not row.get(field)]
                if missing_fields:
                    raise ValueError(f"缺少必填字段: {', '.join(missing_fields)}")
                
                # 获取或创建设备类型
                device_type_name = row['设备类型']
                device_type_id = device_types.get(device_type_name)
                if not device_type_id:
                    new_device_type = DeviceTypeModel(
                        name=device_type_name,
                        description=f"从CSV导入创建的设备类型: {device_type_name}",
                        created_at=datetime.now().isoformat(),
                        updated_at=datetime.now().isoformat()
                    )
                    db.add(new_device_type)
                    db.flush()
                    device_type_id = new_device_type.id
                    device_types[device_type_name] = device_type_id
                
                # 获取或创建厂商
                vendor_name = row.get('厂商')
                vendor_id = None
                if vendor_name:
                    vendor_id = vendors.get(vendor_name)
                    if not vendor_id:
                        new_vendor = VendorModel(
                            name=vendor_name,
                            description=f"从CSV导入创建的厂商: {vendor_name}",
                            created_at=datetime.now().isoformat(),
                            updated_at=datetime.now().isoformat()
                        )
                        db.add(new_vendor)
                        db.flush()
                        vendor_id = new_vendor.id
                        vendors[vendor_name] = vendor_id
                
                # 获取或创建状态
                status_name = row.get('状态', '在线')  # 默认为"在线"
                status_id = statuses.get(status_name)
                if not status_id:
                    new_status = AssetStatusModel(
                        name=status_name,
                        description=f"从CSV导入创建的状态: {status_name}",
                        created_at=datetime.now().isoformat(),
                        updated_at=datetime.now().isoformat()
                    )
                    db.add(new_status)
                    db.flush()
                    status_id = new_status.id
                    statuses[status_name] = status_id
                
                # 获取或创建系统类型
                system_type_name = row['系统类型']
                system_type_id = system_types.get(system_type_name)
                if not system_type_id:
                    new_system_type = SystemTypeModel(
                        name=system_type_name,
                        description=f"从CSV导入创建的系统类型: {system_type_name}",
                        created_at=datetime.now().isoformat(),
                        updated_at=datetime.now().isoformat()
                    )
                    db.add(new_system_type)
                    db.flush()
                    system_type_id = new_system_type.id
                    system_types[system_type_name] = system_type_id
                
                # 获取或创建位置
                location_name = row.get('位置')
                location_id = None
                if location_name:
                    location_id = locations.get(location_name)
                    if not location_id:
                        new_location = LocationModel(
                            name=location_name,
                            description=f"从CSV导入创建的位置: {location_name}",
                            created_at=datetime.now().isoformat(),
                            updated_at=datetime.now().isoformat()
                        )
                        db.add(new_location)
                        db.flush()
                        location_id = new_location.id
                        locations[location_name] = location_id
                
                # 获取或创建部门
                department_name = row.get('所属部门')
                department_id = None
                if department_name:
                    department_id = departments.get(department_name)
                    if not department_id:
                        new_department = DepartmentModel(
                            name=department_name,
                            description=f"从CSV导入创建的部门: {department_name}",
                            created_at=datetime.now().isoformat(),
                            updated_at=datetime.now().isoformat()
                        )
                        db.add(new_department)
                        db.flush()
                        department_id = new_department.id
                        departments[department_name] = department_id
                
                # 检查是否已存在相同的资产标签
                asset_tag = row['资产标签']
                existing_asset = db.query(AssetModel).filter(AssetModel.asset_tag == asset_tag).first()
                
                # 处理日期字段
                purchase_date = None
                if row.get('购买日期'):
                    try:
                        purchase_date = datetime.strptime(row['购买日期'], '%Y-%m-%d').date().isoformat()
                    except ValueError:
                        errors.append(f"第{row_idx}行: 购买日期格式错误，应为YYYY-MM-DD")
                
                online_date = None
                if row.get('上线时间'):
                    try:
                        online_date = datetime.strptime(row['上线时间'], '%Y-%m-%d').date().isoformat()
                    except ValueError:
                        errors.append(f"第{row_idx}行: 上线时间格式错误，应为YYYY-MM-DD")
                
                warranty_expiry = None
                if row.get('保修到期'):
                    try:
                        warranty_expiry = datetime.strptime(row['保修到期'], '%Y-%m-%d').date().isoformat()
                    except ValueError:
                        errors.append(f"第{row_idx}行: 保修到期格式错误，应为YYYY-MM-DD")
                
                # 处理金额字段
                try:
                    purchase_cost = float(row['购买成本']) if row.get('购买成本') else None
                except ValueError:
                    purchase_cost = None
                    errors.append(f"第{row_idx}行: 购买成本格式错误，应为数字")
                
                try:
                    current_value = float(row['当前价值']) if row.get('当前价值') else None
                except ValueError:
                    current_value = None
                    errors.append(f"第{row_idx}行: 当前价值格式错误，应为数字")
                
                asset_data = {
                    'name': row['设备名称'],
                    'asset_tag': asset_tag,
                    'ip_address': row['IP地址'],
                    'serial_number': row.get('SN码'),
                    'device_type_id': device_type_id,
                    'vendor_id': vendor_id,
                    'department_id': department_id,
                    'location_id': location_id,
                    'status_id': status_id,
                    'system_type_id': system_type_id,
                    'owner': row.get('所有者'),
                    'purchase_date': purchase_date,
                    'purchase_cost': purchase_cost,
                    'current_value': current_value,
                    'online_date': online_date,
                    'warranty_expiry': warranty_expiry,
                    'notes': row.get('备注'),
                    'updated_at': datetime.now().isoformat()
                }
                
                if existing_asset:
                    # 更新现有资产
                    for key, value in asset_data.items():
                        setattr(existing_asset, key, value)
                else:
                    # 创建新资产
                    asset_data['created_at'] = datetime.now().isoformat()
                    new_asset = AssetModel(**asset_data)
                    db.add(new_asset)
                
                db.flush()
                imported_count += 1
                
            except IntegrityError as e:
                db.rollback()
                errors.append(f"第{row_idx}行: 数据完整性错误 - {str(e)}")
                failed_count += 1
            except Exception as e:
                errors.append(f"第{row_idx}行: 处理错误 - {str(e)}")
                failed_count += 1
        
        # 提交事务
        db.commit()
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"导入过程中发生错误: {str(e)}")
    
    return {
        "success": True,
        "imported": imported_count,
        "failed": failed_count,
        "errors": errors if errors else None
    }

# 批量删除资产请求模型
class DeleteAssetsRequest(BaseModel):
    ids: List[int]

@router.post("/assets/delete", status_code=status.HTTP_204_NO_CONTENT, tags=["CMDB资产"])
def delete_assets(
    request: DeleteAssetsRequest,
    db: Session = Depends(get_cmdb_db),
):
    """批量删除资产"""
    if not request.ids:
        raise HTTPException(status_code=400, detail="未提供要删除的资产ID")
    
    # 查询所有要删除的资产
    assets_to_delete = db.query(AssetModel).filter(AssetModel.id.in_(request.ids)).all()
    
    # 检查是否所有ID都存在
    found_ids = [asset.id for asset in assets_to_delete]
    missing_ids = [id for id in request.ids if id not in found_ids]
    
    if missing_ids:
        raise HTTPException(
            status_code=404, 
            detail=f"以下资产ID不存在: {', '.join(map(str, missing_ids))}"
        )
    
    # 删除资产
    for asset in assets_to_delete:
        db.delete(asset)
    
    db.commit()
    return None

# 获取设备类型列表
@router.get("/device-types", response_model=List[Dict], tags=["CMDB资产"])
def get_device_types(
    db: Session = Depends(get_cmdb_db),
):
    """获取所有设备类型"""
    device_types = db.query(DeviceTypeModel).all()
    return [{"id": dt.id, "name": dt.name, "description": dt.description} for dt in device_types]

# 获取厂商列表
@router.get("/vendors", response_model=List[Dict], tags=["CMDB资产"])
def get_vendors(
    db: Session = Depends(get_cmdb_db),
):
    """获取所有厂商"""
    vendors = db.query(VendorModel).all()
    return [{"id": v.id, "name": v.name, "description": v.description} for v in vendors]

# 获取状态列表
@router.get("/statuses", response_model=List[Dict], tags=["CMDB资产"])
def get_statuses(
    db: Session = Depends(get_cmdb_db),
):
    """获取所有资产状态"""
    statuses = db.query(AssetStatusModel).all()
    return [{"id": s.id, "name": s.name, "description": s.description} for s in statuses]

# 获取位置列表
@router.get("/locations", response_model=List[Dict], tags=["CMDB资产"])
def get_locations(
    db: Session = Depends(get_cmdb_db),
):
    """获取所有位置"""
    locations = db.query(LocationModel).all()
    return [{"id": l.id, "name": l.name, "description": l.description} for l in locations]

# 获取系统类型列表
@router.get("/system-types", response_model=List[Dict], tags=["CMDB资产"])
def get_system_types(
    db: Session = Depends(get_cmdb_db),
):
    """获取所有系统类型"""
    system_types = db.query(SystemTypeModel).all()
    return [{"id": st.id, "name": st.name, "description": st.description} for st in system_types]