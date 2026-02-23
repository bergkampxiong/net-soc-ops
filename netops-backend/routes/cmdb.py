from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel
import json

from database.cmdb_session import get_cmdb_db, CMDBBase, cmdb_engine
from database.cmdb_models import (
    DeviceType, Vendor, Location, Department, AssetStatus, 
    Asset, NetworkDevice, Server, VirtualMachine, K8sCluster
)

# 创建数据库表
CMDBBase.metadata.create_all(bind=cmdb_engine)

router = APIRouter(
    prefix="/cmdb",
    tags=["cmdb"],
    responses={404: {"description": "Not found"}},
)

# 初始化基础数据
def init_base_data(db: Session):
    # 检查是否已有数据
    if db.query(DeviceType).count() == 0:
        # 添加设备类型
        device_types = [
            {"name": "Router", "description": "Network router device"},
            {"name": "Switch", "description": "Network switch device"},
            {"name": "Firewall", "description": "Network security device"},
            {"name": "Server", "description": "Physical server"},
            {"name": "Virtual Machine", "description": "Virtual server"},
            {"name": "K8s Cluster", "description": "Kubernetes cluster"}
        ]
        for dt in device_types:
            now = datetime.utcnow().isoformat()
            db.add(DeviceType(
                name=dt["name"], 
                description=dt["description"],
                created_at=now,
                updated_at=now
            ))
        
        # 添加厂商
        vendors = [
            {"name": "Huawei", "description": "Huawei Technologies"},
            {"name": "H3C", "description": "H3C Technologies"},
            {"name": "Ruijie", "description": "Ruijie Networks"},
            {"name": "Cisco", "description": "Cisco Systems"},
            {"name": "Fortinet", "description": "Fortinet Security"},
            {"name": "Palo Alto", "description": "Palo Alto Networks"},
            {"name": "Dell", "description": "Dell Technologies"},
            {"name": "HPE", "description": "Hewlett Packard Enterprise"},
            {"name": "Lenovo", "description": "Lenovo Group Limited"}
        ]
        for v in vendors:
            now = datetime.utcnow().isoformat()
            db.add(Vendor(
                name=v["name"], 
                description=v["description"],
                created_at=now,
                updated_at=now
            ))
        
        # 添加位置
        locations = [
            {"name": "Beijing DC", "address": "Beijing, China", "description": "Beijing Data Center"},
            {"name": "Shanghai DC", "address": "Shanghai, China", "description": "Shanghai Data Center"},
            {"name": "Guangzhou DC", "address": "Guangzhou, China", "description": "Guangzhou Data Center"}
        ]
        for loc in locations:
            now = datetime.utcnow().isoformat()
            db.add(Location(
                name=loc["name"], 
                address=loc["address"],
                description=loc["description"],
                created_at=now,
                updated_at=now
            ))
        
        # 添加部门
        departments = [
            {"name": "IT", "description": "IT Department"},
            {"name": "Finance", "description": "Finance Department"},
            {"name": "HR", "description": "Human Resources"},
            {"name": "R&D", "description": "Research and Development"}
        ]
        for dept in departments:
            now = datetime.utcnow().isoformat()
            db.add(Department(
                name=dept["name"], 
                description=dept["description"],
                created_at=now,
                updated_at=now
            ))
        
        # 添加资产状态
        statuses = [
            {"name": "In Use", "description": "Asset is currently in use"},
            {"name": "In Stock", "description": "Asset is in stock"},
            {"name": "Under Maintenance", "description": "Asset is under maintenance"},
            {"name": "Retired", "description": "Asset is retired"}
        ]
        for status in statuses:
            now = datetime.utcnow().isoformat()
            db.add(AssetStatus(
                name=status["name"], 
                description=status["description"],
                created_at=now,
                updated_at=now
            ))
        
        db.commit()

# 设备类型API
@router.get("/device-types", response_model=List[dict])
def get_device_types(db: Session = Depends(get_cmdb_db)):
    # 初始化基础数据
    init_base_data(db)
    
    device_types = db.query(DeviceType).all()
    return [{"id": dt.id, "name": dt.name, "description": dt.description} for dt in device_types]

# 厂商API
@router.get("/vendors", response_model=List[dict])
def get_vendors(db: Session = Depends(get_cmdb_db)):
    vendors = db.query(Vendor).all()
    return [{"id": v.id, "name": v.name, "description": v.description} for v in vendors]

# 位置API
@router.get("/locations", response_model=List[dict])
def get_locations(db: Session = Depends(get_cmdb_db)):
    locations = db.query(Location).all()
    return [{"id": l.id, "name": l.name, "address": l.address, "description": l.description} for l in locations]

# 部门API
@router.get("/departments", response_model=List[dict])
def get_departments(db: Session = Depends(get_cmdb_db)):
    departments = db.query(Department).all()
    return [{"id": d.id, "name": d.name, "description": d.description} for d in departments]

# 资产状态API
@router.get("/asset-statuses", response_model=List[dict])
def get_asset_statuses(db: Session = Depends(get_cmdb_db)):
    statuses = db.query(AssetStatus).all()
    return [{"id": s.id, "name": s.name, "description": s.description} for s in statuses]

# 资产API
@router.get("/assets", response_model=List[dict])
def get_assets(
    skip: int = 0, 
    limit: int = 100,
    device_type_id: Optional[int] = None,
    vendor_id: Optional[int] = None,
    department_id: Optional[int] = None,
    location_id: Optional[int] = None,
    status_id: Optional[int] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_cmdb_db)
):
    query = db.query(Asset)
    
    # 应用过滤条件
    if device_type_id:
        query = query.filter(Asset.device_type_id == device_type_id)
    if vendor_id:
        query = query.filter(Asset.vendor_id == vendor_id)
    if department_id:
        query = query.filter(Asset.department_id == department_id)
    if location_id:
        query = query.filter(Asset.location_id == location_id)
    if status_id:
        query = query.filter(Asset.status_id == status_id)
    if search:
        query = query.filter(
            (Asset.name.ilike(f"%{search}%")) | 
            (Asset.asset_tag.ilike(f"%{search}%")) |
            (Asset.ip_address.ilike(f"%{search}%")) |
            (Asset.serial_number.ilike(f"%{search}%"))
        )

    query = query.options(joinedload(Asset.network_device))
    assets = query.offset(skip).limit(limit).all()

    result = []
    for asset in assets:
        model = None
        version_from_device = None
        if asset.network_device:
            model = asset.network_device.device_model
            version_from_device = asset.network_device.os_version
        asset_dict = {
            "id": asset.id,
            "name": asset.name,
            "asset_tag": asset.asset_tag,
            "ip_address": asset.ip_address,
            "serial_number": asset.serial_number,
            "device_type": {"name": asset.device_type.name} if asset.device_type else None,
            "vendor": {"name": asset.vendor.name} if asset.vendor else None,
            "department": {"name": asset.department.name} if asset.department else None,
            "location": {"name": asset.location.name} if asset.location else None,
            "status": {"name": asset.status.name} if asset.status else None,
            "owner": asset.owner,
            "model": model,
            "version": asset.version or version_from_device,
            "purchase_date": asset.purchase_date,
            "purchase_cost": asset.purchase_cost,
            "current_value": asset.current_value,
            "online_date": asset.online_date,
            "warranty_expiry": asset.warranty_expiry,
            "notes": asset.notes,
            "created_at": asset.created_at,
            "updated_at": asset.updated_at
        }
        result.append(asset_dict)

    return result

# 资产查询API
@router.post("/assets/query", response_model=List[dict])
def query_assets(
    query_params: dict,
    db: Session = Depends(get_cmdb_db)
):
    query = db.query(Asset)
    
    # 应用过滤条件
    if "device_type_id" in query_params and query_params["device_type_id"]:
        query = query.filter(Asset.device_type_id == query_params["device_type_id"])
    if "vendor_id" in query_params and query_params["vendor_id"]:
        query = query.filter(Asset.vendor_id == query_params["vendor_id"])
    if "department_id" in query_params and query_params["department_id"]:
        query = query.filter(Asset.department_id == query_params["department_id"])
    if "location_id" in query_params and query_params["location_id"]:
        query = query.filter(Asset.location_id == query_params["location_id"])
    if "status_id" in query_params and query_params["status_id"]:
        query = query.filter(Asset.status_id == query_params["status_id"])
    if "name" in query_params and query_params["name"]:
        query = query.filter(Asset.name.ilike(f"%{query_params['name']}%"))
    if "asset_tag" in query_params and query_params["asset_tag"]:
        query = query.filter(Asset.asset_tag.ilike(f"%{query_params['asset_tag']}%"))
    if "ip_address" in query_params and query_params["ip_address"]:
        query = query.filter(Asset.ip_address.ilike(f"%{query_params['ip_address']}%"))
    if "serial_number" in query_params and query_params["serial_number"]:
        query = query.filter(Asset.serial_number.ilike(f"%{query_params['serial_number']}%"))
    if "owner" in query_params and query_params["owner"]:
        query = query.filter(Asset.owner.ilike(f"%{query_params['owner']}%"))

    query = query.options(joinedload(Asset.network_device))
    assets = query.all()

    result = []
    for asset in assets:
        # 型号来自关联的 NetworkDevice.device_model（Asset 表无 model 字段）
        model = None
        version_from_device = None
        if asset.network_device:
            model = asset.network_device.device_model
            version_from_device = asset.network_device.os_version
        asset_dict = {
            "id": asset.id,
            "name": asset.name,
            "asset_tag": asset.asset_tag,
            "ip_address": asset.ip_address,
            "serial_number": asset.serial_number,
            "device_type": {"name": asset.device_type.name} if asset.device_type else None,
            "vendor": {"name": asset.vendor.name} if asset.vendor else None,
            "department": {"name": asset.department.name} if asset.department else None,
            "location": {"name": asset.location.name} if asset.location else None,
            "status": {"name": asset.status.name} if asset.status else None,
            "system_type": {"name": asset.system_type.name} if asset.system_type else None,
            "owner": asset.owner,
            "model": model,
            "version": asset.version or version_from_device,
            "cpu_count": asset.cpu_count,
            "memory_capacity": asset.memory_capacity,
            "storage_capacity": asset.storage_capacity,
            "purchase_date": asset.purchase_date,
            "purchase_cost": asset.purchase_cost,
            "current_value": asset.current_value,
            "online_date": asset.online_date,
            "warranty_expiry": asset.warranty_expiry,
            "notes": asset.notes,
            "created_at": asset.created_at,
            "updated_at": asset.updated_at
        }
        result.append(asset_dict)

    return result


class AssetUpdateBody(BaseModel):
    """资产更新请求体（用于 PUT /assets/{asset_id}）"""
    name: Optional[str] = None
    asset_tag: Optional[str] = None
    ip_address: Optional[str] = None
    serial_number: Optional[str] = None
    device_type_id: Optional[int] = None
    vendor_id: Optional[int] = None
    department_id: Optional[int] = None
    location_id: Optional[int] = None
    status_id: Optional[int] = None
    system_type_id: Optional[int] = None
    owner: Optional[str] = None
    model: Optional[str] = None  # 写入 NetworkDevice.device_model
    version: Optional[str] = None  # 写入 Asset.version 与 NetworkDevice.os_version
    cpu_count: Optional[int] = None
    memory_capacity: Optional[float] = None
    storage_capacity: Optional[float] = None
    purchase_date: Optional[str] = None
    purchase_cost: Optional[float] = None
    current_value: Optional[float] = None
    online_date: Optional[str] = None
    warranty_expiry: Optional[str] = None
    notes: Optional[str] = None


@router.put("/assets/{asset_id}", response_model=dict)
def update_asset(
    asset_id: int,
    body: AssetUpdateBody,
    db: Session = Depends(get_cmdb_db),
):
    """更新资产信息；model 写入 NetworkDevice.device_model，version 写入 Asset.version 与 NetworkDevice.os_version。"""
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="资产不存在")
    update_data = body.dict(exclude_unset=True)
    now = datetime.utcnow().isoformat()
    asset_fields = {k: v for k, v in update_data.items() if k not in ("model",)}
    for key, value in asset_fields.items():
        if hasattr(asset, key):
            setattr(asset, key, value)
    asset.updated_at = now
    if "version" in update_data and update_data["version"] is not None:
        asset.version = (update_data["version"] or "")[:50]
    if "model" in update_data:
        nd = db.query(NetworkDevice).filter(NetworkDevice.asset_id == asset_id).first()
        if nd:
            nd.device_model = (update_data["model"] or "")[:100] if update_data["model"] else None
            if "version" in update_data and update_data["version"] is not None:
                nd.os_version = (update_data["version"] or "")[:50]
            nd.updated_at = now
        else:
            nd = NetworkDevice(
                asset_id=asset_id,
                device_model=(update_data["model"] or "")[:100] if update_data.get("model") else None,
                os_version=(update_data.get("version") or "")[:50] if update_data.get("version") else None,
                management_ip=asset.ip_address,
                created_at=now,
                updated_at=now,
            )
            db.add(nd)
    db.commit()
    db.refresh(asset)
    model = None
    version_from_device = None
    if asset.network_device:
        model = asset.network_device.device_model
        version_from_device = asset.network_device.os_version
    return {
        "id": asset.id,
        "name": asset.name,
        "asset_tag": asset.asset_tag,
        "ip_address": asset.ip_address,
        "serial_number": asset.serial_number,
        "device_type": {"name": asset.device_type.name} if asset.device_type else None,
        "vendor": {"name": asset.vendor.name} if asset.vendor else None,
        "model": model,
        "version": asset.version or version_from_device,
        "cpu_count": asset.cpu_count,
        "memory_capacity": asset.memory_capacity,
        "storage_capacity": asset.storage_capacity,
        "updated_at": asset.updated_at,
    }


# 添加示例资产数据
@router.post("/seed-data")
def seed_data(db: Session = Depends(get_cmdb_db)):
    # 检查是否已有资产数据
    if db.query(Asset).count() > 0:
        return {"message": "Data already seeded"}
    
    # 获取基础数据ID
    device_types = {dt.name: dt.id for dt in db.query(DeviceType).all()}
    vendors = {v.name: v.id for v in db.query(Vendor).all()}
    locations = {l.name: l.id for l in db.query(Location).all()}
    departments = {d.name: d.id for d in db.query(Department).all()}
    statuses = {s.name: s.id for s in db.query(AssetStatus).all()}
    
    # 添加示例资产
    assets = [
        {
            "name": "Core-Router-01",
            "asset_tag": "NET-RTR-001",
            "ip_address": "10.0.0.1",
            "serial_number": "HUAWEI123456",
            "device_type": "Router",
            "vendor": "Huawei",
            "department": "IT",
            "location": "Beijing DC",
            "status": "In Use",
            "owner": "Network Team",
            "purchase_date": "2023-01-15",
            "purchase_cost": 15000.00,
            "current_value": 12000.00,
            "online_date": "2023-02-01",
            "warranty_expiry": "2026-01-15",
            "notes": "Core router for Beijing DC"
        },
        {
            "name": "Core-Switch-01",
            "asset_tag": "NET-SWT-001",
            "ip_address": "10.0.0.2",
            "serial_number": "H3C789012",
            "device_type": "Switch",
            "vendor": "H3C",
            "department": "IT",
            "location": "Beijing DC",
            "status": "In Use",
            "owner": "Network Team",
            "purchase_date": "2023-01-20",
            "purchase_cost": 8000.00,
            "current_value": 6500.00,
            "online_date": "2023-02-05",
            "warranty_expiry": "2026-01-20",
            "notes": "Core switch for Beijing DC"
        },
        {
            "name": "Firewall-01",
            "asset_tag": "NET-FW-001",
            "ip_address": "10.0.0.3",
            "serial_number": "FTNT345678",
            "device_type": "Firewall",
            "vendor": "Fortinet",
            "department": "IT",
            "location": "Beijing DC",
            "status": "In Use",
            "owner": "Security Team",
            "purchase_date": "2023-01-25",
            "purchase_cost": 12000.00,
            "current_value": 10000.00,
            "online_date": "2023-02-10",
            "warranty_expiry": "2026-01-25",
            "notes": "Main firewall for Beijing DC"
        },
        {
            "name": "App-Server-01",
            "asset_tag": "SRV-APP-001",
            "ip_address": "10.0.1.1",
            "serial_number": "DELL901234",
            "device_type": "Server",
            "vendor": "Dell",
            "department": "IT",
            "location": "Beijing DC",
            "status": "In Use",
            "owner": "Server Team",
            "purchase_date": "2023-02-01",
            "purchase_cost": 25000.00,
            "current_value": 22000.00,
            "online_date": "2023-02-15",
            "warranty_expiry": "2026-02-01",
            "notes": "Application server"
        },
        {
            "name": "DB-Server-01",
            "asset_tag": "SRV-DB-001",
            "ip_address": "10.0.1.2",
            "serial_number": "HPE567890",
            "device_type": "Server",
            "vendor": "HPE",
            "department": "IT",
            "location": "Beijing DC",
            "status": "In Use",
            "owner": "Database Team",
            "purchase_date": "2023-02-05",
            "purchase_cost": 30000.00,
            "current_value": 27000.00,
            "online_date": "2023-02-20",
            "warranty_expiry": "2026-02-05",
            "notes": "Database server"
        }
    ]
    
    for asset_data in assets:
        now = datetime.utcnow().isoformat()
        asset = Asset(
            name=asset_data["name"],
            asset_tag=asset_data["asset_tag"],
            ip_address=asset_data["ip_address"],
            serial_number=asset_data["serial_number"],
            device_type_id=device_types.get(asset_data["device_type"]),
            vendor_id=vendors.get(asset_data["vendor"]),
            department_id=departments.get(asset_data["department"]),
            location_id=locations.get(asset_data["location"]),
            status_id=statuses.get(asset_data["status"]),
            owner=asset_data["owner"],
            purchase_date=asset_data["purchase_date"],
            purchase_cost=asset_data["purchase_cost"],
            current_value=asset_data["current_value"],
            online_date=asset_data["online_date"],
            warranty_expiry=asset_data["warranty_expiry"],
            notes=asset_data["notes"],
            created_at=now,
            updated_at=now
        )
        db.add(asset)
    
    db.commit()
    return {"message": "Sample data seeded successfully"} 