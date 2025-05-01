from typing import Dict, List, Any, Optional
from pydantic import BaseModel

class ProcessDefinitionBase(BaseModel):
    """流程定义基础模型"""
    name: str
    description: Optional[str] = None
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    variables: Dict[str, Any] = {}

class ProcessDefinitionCreate(ProcessDefinitionBase):
    """创建流程定义模型"""
    pass

class ProcessDefinitionUpdate(ProcessDefinitionBase):
    """更新流程定义模型"""
    name: Optional[str] = None
    description: Optional[str] = None 