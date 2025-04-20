from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

# 创建CMDB专用的Base类
CMDBBase = declarative_base()

# 基础数据模型
class DeviceType(CMDBBase):
    """设备类型模型"""
    __tablename__ = "cmdb_device_types"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True)  # 设备类型名称
    description = Column(String(200), nullable=True)  # 描述
    created_at = Column(String(50))
    updated_at = Column(String(50))
    
    # 关联关系
    assets = relationship("Asset", back_populates="device_type")

class Vendor(CMDBBase):
    """厂商模型"""
    __tablename__ = "cmdb_vendors"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True)  # 厂商名称
    description = Column(String(200), nullable=True)  # 描述
    contact = Column(String(100), nullable=True)  # 联系方式
    website = Column(String(100), nullable=True)  # 网站
    created_at = Column(String(50))
    updated_at = Column(String(50))
    
    # 关联关系
    assets = relationship("Asset", back_populates="vendor")

class Location(CMDBBase):
    """位置模型"""
    __tablename__ = "cmdb_locations"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True)  # 位置名称
    address = Column(String(200), nullable=True)  # 地址
    description = Column(String(200), nullable=True)  # 描述
    created_at = Column(String(50))
    updated_at = Column(String(50))
    
    # 关联关系
    assets = relationship("Asset", back_populates="location")

class Department(CMDBBase):
    """部门模型"""
    __tablename__ = "cmdb_departments"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True)  # 部门名称
    description = Column(String(200), nullable=True)  # 描述
    created_at = Column(String(50))
    updated_at = Column(String(50))
    
    # 关联关系
    assets = relationship("Asset", back_populates="department")

class AssetStatus(CMDBBase):
    """资产状态模型"""
    __tablename__ = "cmdb_asset_statuses"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True)  # 状态名称
    description = Column(String(200), nullable=True)  # 描述
    created_at = Column(String(50))
    updated_at = Column(String(50))
    
    # 关联关系
    assets = relationship("Asset", back_populates="status")

# 系统类型模型
class SystemType(CMDBBase):
    """系统类型模型"""
    __tablename__ = "cmdb_system_types"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True)  # 系统类型名称
    description = Column(String(200), nullable=True)  # 描述
    created_at = Column(String(50))
    updated_at = Column(String(50))
    
    # 关联关系
    assets = relationship("Asset", back_populates="system_type")

# 资产模型
class Asset(CMDBBase):
    """资产模型"""
    __tablename__ = "cmdb_assets"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True)  # 资产名称
    asset_tag = Column(String(50), unique=True, index=True)  # 资产标签
    ip_address = Column(String(50), nullable=True, index=True)  # IP地址
    serial_number = Column(String(50), nullable=True, index=True)  # SN码
    device_type_id = Column(Integer, ForeignKey("cmdb_device_types.id"), nullable=True)
    vendor_id = Column(Integer, ForeignKey("cmdb_vendors.id"), nullable=True)
    department_id = Column(Integer, ForeignKey("cmdb_departments.id"), nullable=True)
    location_id = Column(Integer, ForeignKey("cmdb_locations.id"), nullable=True)
    status_id = Column(Integer, ForeignKey("cmdb_asset_statuses.id"), nullable=True)
    system_type_id = Column(Integer, ForeignKey("cmdb_system_types.id"), nullable=True)  # 新增系统类型ID
    owner = Column(String(50), nullable=True)  # 资产所有者
    purchase_date = Column(String(50), nullable=True)  # 购买日期
    purchase_cost = Column(Float, nullable=True)  # 购买成本
    current_value = Column(Float, nullable=True)  # 当前价值
    online_date = Column(String(50), nullable=True)  # 上线时间
    warranty_expiry = Column(String(50), nullable=True)  # 保修到期
    notes = Column(Text, nullable=True)  # 备注
    created_at = Column(String(50))
    updated_at = Column(String(50))
    
    # 关联关系
    device_type = relationship("DeviceType", back_populates="assets")
    vendor = relationship("Vendor", back_populates="assets")
    department = relationship("Department", back_populates="assets")
    location = relationship("Location", back_populates="assets")
    status = relationship("AssetStatus", back_populates="assets")
    system_type = relationship("SystemType", back_populates="assets")  # 新增系统类型关系
    
    # 多态关联
    network_device = relationship("NetworkDevice", back_populates="asset", uselist=False)
    server = relationship("Server", back_populates="asset", uselist=False)
    virtual_machine = relationship("VirtualMachine", back_populates="asset", uselist=False)
    k8s_cluster = relationship("K8sCluster", back_populates="asset", uselist=False)

# 网络设备模型
class NetworkDevice(CMDBBase):
    """网络设备模型"""
    __tablename__ = "cmdb_network_devices"
    
    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("cmdb_assets.id"), unique=True)
    device_model = Column(String(100), nullable=True)  # 设备型号
    os_version = Column(String(50), nullable=True)  # 操作系统版本
    management_ip = Column(String(50), nullable=True)  # 管理IP
    console_port = Column(String(50), nullable=True)  # 控制台端口
    device_role = Column(String(50), nullable=True)  # 设备角色（核心、汇聚、接入）
    created_at = Column(String(50))
    updated_at = Column(String(50))
    
    # 关联关系
    asset = relationship("Asset", back_populates="network_device")
    interfaces = relationship("NetworkInterface", back_populates="device")

class NetworkInterface(CMDBBase):
    """网络接口模型"""
    __tablename__ = "cmdb_network_interfaces"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("cmdb_network_devices.id"))
    name = Column(String(50))  # 接口名称
    type = Column(String(50), nullable=True)  # 接口类型
    mac_address = Column(String(50), nullable=True)  # MAC地址
    ip_address = Column(String(50), nullable=True)  # IP地址
    subnet_mask = Column(String(50), nullable=True)  # 子网掩码
    status = Column(String(50), nullable=True)  # 状态
    speed = Column(String(50), nullable=True)  # 速率
    description = Column(String(200), nullable=True)  # 描述
    created_at = Column(String(50))
    updated_at = Column(String(50))
    
    # 关联关系
    device = relationship("NetworkDevice", back_populates="interfaces")

# 服务器模型
class Server(CMDBBase):
    """服务器模型"""
    __tablename__ = "cmdb_servers"
    
    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("cmdb_assets.id"), unique=True)
    server_type = Column(String(50), nullable=True)  # 服务器类型（物理、虚拟）
    cpu_model = Column(String(100), nullable=True)  # CPU型号
    cpu_cores = Column(Integer, nullable=True)  # CPU核心数
    memory_size = Column(Float, nullable=True)  # 内存大小(GB)
    disk_size = Column(Float, nullable=True)  # 磁盘大小(GB)
    os_type = Column(String(50), nullable=True)  # 操作系统类型
    os_version = Column(String(50), nullable=True)  # 操作系统版本
    management_ip = Column(String(50), nullable=True)  # 管理IP
    created_at = Column(String(50))
    updated_at = Column(String(50))
    
    # 关联关系
    asset = relationship("Asset", back_populates="server")
    virtual_machines = relationship("VirtualMachine", back_populates="host_server")

class VirtualMachine(CMDBBase):
    """虚拟机模型"""
    __tablename__ = "cmdb_virtual_machines"
    
    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("cmdb_assets.id"), unique=True)
    host_server_id = Column(Integer, ForeignKey("cmdb_servers.id"), nullable=True)
    vm_type = Column(String(50), nullable=True)  # 虚拟机类型（VMware、KVM等）
    vcpu_count = Column(Integer, nullable=True)  # vCPU数量
    memory_size = Column(Float, nullable=True)  # 内存大小(GB)
    disk_size = Column(Float, nullable=True)  # 磁盘大小(GB)
    os_type = Column(String(50), nullable=True)  # 操作系统类型
    os_version = Column(String(50), nullable=True)  # 操作系统版本
    created_at = Column(String(50))
    updated_at = Column(String(50))
    
    # 关联关系
    asset = relationship("Asset", back_populates="virtual_machine", uselist=False)
    host_server = relationship("Server", back_populates="virtual_machines")

# Kubernetes模型
class K8sCluster(CMDBBase):
    """Kubernetes集群模型"""
    __tablename__ = "cmdb_k8s_clusters"
    
    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("cmdb_assets.id"), unique=True)
    cluster_version = Column(String(50), nullable=True)  # Kubernetes版本
    control_plane_count = Column(Integer, nullable=True)
    worker_node_count = Column(Integer, nullable=True)
    pod_cidr = Column(String(50), nullable=True)
    service_cidr = Column(String(50), nullable=True)
    ingress_domain = Column(String(100), nullable=True)
    api_endpoint = Column(String(100), nullable=True)
    dashboard_url = Column(String(100), nullable=True)
    created_at = Column(String(50))
    updated_at = Column(String(50))
    
    # 关联关系
    asset = relationship("Asset", back_populates="k8s_cluster")
    nodes = relationship("K8sNode", back_populates="cluster")

class K8sNode(CMDBBase):
    """Kubernetes节点模型"""
    __tablename__ = "cmdb_k8s_nodes"
    
    id = Column(Integer, primary_key=True, index=True)
    cluster_id = Column(Integer, ForeignKey("cmdb_k8s_clusters.id"))
    server_id = Column(Integer, ForeignKey("cmdb_servers.id"), nullable=True)
    node_name = Column(String(100))
    node_role = Column(String(50), nullable=True)  # control-plane/worker
    node_ip = Column(String(50), nullable=True)
    kubelet_version = Column(String(50), nullable=True)
    os_type = Column(String(50), nullable=True)
    os_version = Column(String(50), nullable=True)
    cpu_cores = Column(Integer, nullable=True)
    memory_size = Column(Float, nullable=True)  # GB
    disk_size = Column(Float, nullable=True)  # GB
    status = Column(String(50), nullable=True)
    created_at = Column(String(50))
    updated_at = Column(String(50))
    
    # 关联关系
    cluster = relationship("K8sCluster", back_populates="nodes")
    pods = relationship("K8sPod", back_populates="node")

class K8sPod(CMDBBase):
    """Kubernetes Pod模型"""
    __tablename__ = "cmdb_k8s_pods"
    
    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(Integer, ForeignKey("cmdb_k8s_nodes.id"))
    name = Column(String(100), index=True)  # Pod名称
    namespace = Column(String(100), nullable=True)  # 命名空间
    status = Column(String(50), nullable=True)  # 状态
    ip_address = Column(String(50), nullable=True)  # IP地址
    created_at = Column(String(50))
    updated_at = Column(String(50))
    
    # 关联关系
    node = relationship("K8sNode", back_populates="pods")

# 资产盘点模型
class InventoryTask(CMDBBase):
    """资产盘点任务模型"""
    __tablename__ = "cmdb_inventory_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    description = Column(String(200), nullable=True)
    task_type = Column(String(50))  # discovery/audit
    status = Column(String(50))  # pending/running/completed/failed
    start_time = Column(String(50), nullable=True)
    end_time = Column(String(50), nullable=True)
    result = Column(Text, nullable=True)
    created_by = Column(String(50))
    created_at = Column(String(50))
    updated_at = Column(String(50))
    
    # 添加外键
    location_id = Column(Integer, ForeignKey("cmdb_locations.id"), nullable=True)
    department_id = Column(Integer, ForeignKey("cmdb_departments.id"), nullable=True)
    
    # 关联关系
    location = relationship("Location")
    department = relationship("Department")
    items = relationship("InventoryItem", back_populates="task")

class InventoryItem(CMDBBase):
    """资产盘点项模型"""
    __tablename__ = "cmdb_inventory_items"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("cmdb_inventory_tasks.id"))
    asset_id = Column(Integer, ForeignKey("cmdb_assets.id"))
    status = Column(String(50), nullable=True)  # 状态（待盘点、已盘点、丢失、位置不符）
    notes = Column(String(200), nullable=True)  # 备注
    checked_by = Column(String(100), nullable=True)  # 盘点人
    checked_at = Column(String(50), nullable=True)  # 盘点时间
    created_at = Column(String(50))
    updated_at = Column(String(50))
    
    # 关联关系
    task = relationship("InventoryTask", back_populates="items")
    asset = relationship("Asset")

# 添加Asset与VirtualMachine的关系
Asset.virtual_machine = relationship("VirtualMachine", back_populates="asset", uselist=False) 