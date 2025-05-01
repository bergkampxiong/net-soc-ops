from fastapi import APIRouter, HTTPException
from app.process_designer.code_generator import CodeGenerator
from app.models.process_designer import ProcessDefinition
from app.schemas.process_designer import ProcessDefinitionCreate, ProcessDefinitionUpdate

router = APIRouter(prefix="/api/process-definitions", tags=["process-designer"])

@router.post("/{process_id}/validate")
async def validate_process(process_id: str):
    """验证流程定义的有效性"""
    try:
        process = await ProcessDefinition.get(id=process_id)
        generator = CodeGenerator(process.dict())
        result = generator.validate()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{process_id}/generate-code")
async def generate_code(process_id: str):
    """生成流程代码"""
    try:
        process = await ProcessDefinition.get(id=process_id)
        generator = CodeGenerator(process.dict())
        code = generator.generate_code()
        return code
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 