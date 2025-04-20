from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from .cmdb_kubernetes import K8sCluster

# Kubernetes节点Schema
class K8sNodeBase(BaseModel):
    node_name: str
    node_role: Optional[str] = None
    node_ip: Optional[str] = None
    kubelet_version: Optional[str] = None
    os_type: Optional[str] = None
    os_version: Optional[str] = None
    cpu_cores: Optional[int] = None
    memory_size: Optional[float] = None
    disk_size: Optional[float] = None
    status: Optional[str] = None

class K8sNodeCreate(K8sNodeBase):
    cluster_id: int
    server_id: Optional[int] = None

class K8sNodeUpdate(BaseModel):
    node_name: Optional[str] = None
    node_role: Optional[str] = None
    node_ip: Optional[str] = None
    kubelet_version: Optional[str] = None
    os_type: Optional[str] = None
    os_version: Optional[str] = None
    cpu_cores: Optional[int] = None
    memory_size: Optional[float] = None
    disk_size: Optional[float] = None
    status: Optional[str] = None

class K8sNodeInDB(K8sNodeBase):
    id: int
    cluster_id: int
    server_id: Optional[int] = None
    created_at: str
    updated_at: str

    class Config:
        orm_mode = True

class K8sNode(K8sNodeInDB):
    pass

# 集群详情（包含节点）
class K8sClusterWithNodes(K8sCluster):
    nodes: Optional[List[K8sNode]] = None 