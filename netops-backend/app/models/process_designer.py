from typing import Dict, List, Any
from pydantic import BaseModel

class ProcessDefinition(BaseModel):
    """流程定义模型"""
    id: str
    name: str
    description: str
    version: int
    status: str  # 'draft' | 'published' | 'disabled'
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    variables: Dict[str, Any] = {}
    created_by: str
    created_at: str
    updated_by: str
    updated_at: str
    deleted_at: str = None

    @classmethod
    async def get(cls, id: str) -> 'ProcessDefinition':
        """获取流程定义"""
        # TODO: 从数据库获取流程定义
        # 这里暂时返回一个模拟数据
        return cls(
            id=id,
            name="测试流程",
            description="这是一个测试流程",
            version=1,
            status="draft",
            nodes=[],
            edges=[],
            created_by="admin",
            created_at="2024-04-30T00:00:00Z",
            updated_by="admin",
            updated_at="2024-04-30T00:00:00Z"
        ) 