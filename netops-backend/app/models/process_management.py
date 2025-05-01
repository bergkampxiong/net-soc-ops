from typing import Dict, List, Any, Optional
from pydantic import BaseModel
from datetime import datetime

class ProcessDefinition(BaseModel):
    """流程定义模型"""
    id: str
    name: str
    description: Optional[str] = None
    version: int
    status: str  # 'draft' | 'published' | 'disabled'
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    variables: Dict[str, Any] = {}
    created_by: str
    created_at: str
    updated_by: str
    updated_at: str
    deleted_at: Optional[str] = None

class ProcessDefinitionVersion(BaseModel):
    """流程定义版本模型"""
    id: str
    process_id: str
    version: int
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    variables: Dict[str, Any] = {}
    created_by: str
    created_at: str 