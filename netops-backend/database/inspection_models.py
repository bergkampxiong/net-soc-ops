# 日常巡检：巡检清单与清单项，表通过 int_all_db.py 初始化
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database.base import Base
import datetime


class InspectionChecklist(Base):
    """巡检清单主表"""
    __tablename__ = "inspection_checklists"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, comment="清单名称")
    description = Column(Text, comment="清单描述")
    created_at = Column(DateTime, default=datetime.datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, comment="更新时间")
    created_by = Column(String(255), comment="创建人")

    items = relationship("InspectionChecklistItem", back_populates="checklist", cascade="all, delete-orphan")


class InspectionChecklistItem(Base):
    """巡检清单项：设备（来自 CMDB）或服务（名称+URL）"""
    __tablename__ = "inspection_checklist_items"

    id = Column(Integer, primary_key=True, index=True)
    checklist_id = Column(Integer, ForeignKey("inspection_checklists.id", ondelete="CASCADE"), nullable=False, comment="所属清单ID")
    item_type = Column(String(20), nullable=False, comment="device=设备, service=服务")
    name = Column(String(255), nullable=False, comment="显示名称（设备名或服务名）")
    target = Column(String(512), nullable=False, comment="IP 或 URL")
    sort_order = Column(Integer, default=0, comment="排序序号")

    checklist = relationship("InspectionChecklist", back_populates="items")
