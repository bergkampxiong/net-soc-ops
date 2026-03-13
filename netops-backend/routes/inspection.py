# 日常巡检：巡检清单 CRUD API
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from database.session import get_db
from database.inspection_models import InspectionChecklist, InspectionChecklistItem
from auth.authentication import get_current_user

router = APIRouter(prefix="/inspection", tags=["日常巡检"])


class ChecklistItemCreate(BaseModel):
    """清单项创建/更新结构"""
    item_type: str  # 'device' | 'service'
    name: str
    target: str


class ChecklistItemResponse(BaseModel):
    id: int
    item_type: str
    name: str
    target: str
    sort_order: int

    class Config:
        from_attributes = True


class ChecklistCreate(BaseModel):
    name: str
    description: Optional[str] = None
    items: List[ChecklistItemCreate] = []


class ChecklistUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    items: Optional[List[ChecklistItemCreate]] = None


class ChecklistResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]
    created_by: Optional[str]
    items: List[ChecklistItemResponse] = []
    item_count: int = 0

    class Config:
        from_attributes = True


class ChecklistListItem(BaseModel):
    """列表项（不含 items 明细）"""
    id: int
    name: str
    description: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]
    created_by: Optional[str]
    item_count: int = 0

    class Config:
        from_attributes = True


def _checklist_to_response(c: InspectionChecklist, include_items: bool = True) -> dict:
    """将清单转为响应字典"""
    items = []
    if include_items and c.items:
        items = [
            {"id": i.id, "item_type": i.item_type, "name": i.name, "target": i.target, "sort_order": i.sort_order or 0}
            for i in sorted(c.items, key=lambda x: (x.sort_order or 0, x.id))
        ]
    return {
        "id": c.id,
        "name": c.name,
        "description": c.description,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        "created_by": c.created_by,
        "items": items,
        "item_count": len(c.items) if c.items else 0,
    }


@router.get("/checklists", response_model=List[dict])
def list_checklists(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """巡检清单列表（分页，不含 items）"""
    query = db.query(InspectionChecklist).order_by(InspectionChecklist.updated_at.desc())
    total = query.count()
    rows = query.offset(skip).limit(limit).all()
    result = []
    for c in rows:
        d = _checklist_to_response(c, include_items=False)
        d["item_count"] = db.query(InspectionChecklistItem).filter(InspectionChecklistItem.checklist_id == c.id).count()
        result.append(d)
    return result


@router.post("/checklists", response_model=dict)
def create_checklist(
    body: ChecklistCreate,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """创建巡检清单（含清单项）"""
    checklist = InspectionChecklist(
        name=body.name,
        description=body.description or "",
        created_by=getattr(_current_user, "username", None) or "unknown",
    )
    db.add(checklist)
    db.flush()
    for idx, it in enumerate(body.items):
        if it.item_type not in ("device", "service"):
            raise HTTPException(status_code=400, detail="item_type 必须为 device 或 service")
        item = InspectionChecklistItem(
            checklist_id=checklist.id,
            item_type=it.item_type,
            name=it.name.strip(),
            target=it.target.strip(),
            sort_order=idx,
        )
        db.add(item)
    db.commit()
    db.refresh(checklist)
    checklist.items = db.query(InspectionChecklistItem).filter(InspectionChecklistItem.checklist_id == checklist.id).order_by(InspectionChecklistItem.sort_order, InspectionChecklistItem.id).all()
    return _checklist_to_response(checklist)


@router.get("/checklists/{checklist_id}", response_model=dict)
def get_checklist(
    checklist_id: int,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """巡检清单详情（含 items）"""
    c = db.query(InspectionChecklist).filter(InspectionChecklist.id == checklist_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="巡检清单不存在")
    c.items = db.query(InspectionChecklistItem).filter(InspectionChecklistItem.checklist_id == c.id).order_by(InspectionChecklistItem.sort_order, InspectionChecklistItem.id).all()
    return _checklist_to_response(c)


@router.put("/checklists/{checklist_id}", response_model=dict)
def update_checklist(
    checklist_id: int,
    body: ChecklistUpdate,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """更新巡检清单（可选更新 items，传则全量替换）"""
    c = db.query(InspectionChecklist).filter(InspectionChecklist.id == checklist_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="巡检清单不存在")
    if body.name is not None:
        c.name = body.name
    if body.description is not None:
        c.description = body.description
    if body.items is not None:
        db.query(InspectionChecklistItem).filter(InspectionChecklistItem.checklist_id == checklist_id).delete()
        for idx, it in enumerate(body.items):
            if it.item_type not in ("device", "service"):
                raise HTTPException(status_code=400, detail="item_type 必须为 device 或 service")
            item = InspectionChecklistItem(
                checklist_id=checklist_id,
                item_type=it.item_type,
                name=it.name.strip(),
                target=it.target.strip(),
                sort_order=idx,
            )
            db.add(item)
    db.commit()
    db.refresh(c)
    c.items = db.query(InspectionChecklistItem).filter(InspectionChecklistItem.checklist_id == c.id).order_by(InspectionChecklistItem.sort_order, InspectionChecklistItem.id).all()
    return _checklist_to_response(c)


@router.delete("/checklists/{checklist_id}")
def delete_checklist(
    checklist_id: int,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """删除巡检清单（级联删除清单项）"""
    c = db.query(InspectionChecklist).filter(InspectionChecklist.id == checklist_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="巡检清单不存在")
    db.delete(c)
    db.commit()
    return {"message": "已删除"}
