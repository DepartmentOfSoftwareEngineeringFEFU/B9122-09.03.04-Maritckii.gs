from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from .database import Base
import enum
import datetime

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    PICKER = "picker"

class OrderStatus(str, enum.Enum):
    NEW = "new"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    login = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(SAEnum(UserRole), default=UserRole.PICKER, nullable=False)
    orders = relationship("Order", back_populates="assignee")

class Material(Base):
    __tablename__ = "materials"
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    barcode = Column(String, unique=True, index=True, nullable=False)
    rack = Column(String, nullable=False)
    weight = Column(Float, default=0.0)
    height = Column(Float, default=0.0)
    width = Column(Float, default=0.0)
    depth = Column(Float, default=0.0)
    min_stock = Column(Integer, default=0)

class Order(Base):
    __tablename__ = "orders"
    id = Column(String, primary_key=True, index=True)
    status = Column(SAEnum(OrderStatus), default=OrderStatus.NEW)
    progress = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    assigned_to_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    assignee = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    scan_events = relationship("ScanEvent", back_populates="order")

class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String, ForeignKey("orders.id"), nullable=False)
    material_id = Column(String, ForeignKey("materials.id"), nullable=False)
    required_qty = Column(Integer, nullable=False)
    order = relationship("Order", back_populates="items")
    material = relationship("Material")

class ScanEvent(Base):
    __tablename__ = "scan_events"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String, ForeignKey("orders.id"), nullable=False)
    worker_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    barcode = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    is_valid = Column(Boolean, default=False)
    order = relationship("Order", back_populates="scan_events")

class MovementLog(Base):
    __tablename__ = "movement_logs"
    id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(Integer, ForeignKey("users.id"))
    from_loc = Column(String, nullable=False)
    to_loc = Column(String, nullable=False)
    duration_sec = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)