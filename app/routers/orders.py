from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from .. import models, schemas, database, auth
import os
import json
from datetime import datetime

EXCHANGE_FOLDER = r"C:\Users\mar_grisha\Desktop\DIPLOM_2\data\status"

def save_status_to_file(order_id: str, status_value: str, progress: Optional[float] = None):
    try:
        os.makedirs(EXCHANGE_FOLDER, exist_ok=True)
        filename = f"status_{order_id}.json"
        filepath = os.path.join(EXCHANGE_FOLDER, filename)
        data = {
            "order_id": order_id,
            "status": status_value,
            "timestamp": datetime.now().isoformat(),
            "type": "order_status"
        }
        if progress is not None:
            data["progress"] = progress
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        pass

router = APIRouter()

@router.post("/", status_code=status.HTTP_201_CREATED)
def receive_order_from_1c(payload: schemas.OrderCreatePayload, db: Session = Depends(database.get_db)):
    picker = db.query(models.User).filter(models.User.login == payload.picker.login).first()
    if not picker:
        picker = models.User(
            login=payload.picker.login,
            hashed_password=auth.get_password_hash(payload.picker.password),
            full_name=payload.picker.full_name,
            role=models.UserRole.PICKER
        )
        db.add(picker)
        db.flush()
    else:
        picker.full_name = payload.picker.full_name
    for mid, mat_data in payload.materials.items():
        mat = db.query(models.Material).filter(models.Material.id == mid).first()
        if not mat:
            mat = models.Material(id=mid, barcode=mid)
            db.add(mat)
        mat.name = mat_data.name
        mat.rack = mat_data.rack
        mat.weight = float(mat_data.weight.replace(',', '.'))
        mat.height = float(mat_data.height.replace(',', '.'))
        mat.width = float(mat_data.width.replace(',', '.'))
        mat.depth = float(mat_data.depth.replace(',', '.'))
        if mat_data.barcode:
            mat.barcode = mat_data.barcode
    order = db.query(models.Order).filter(models.Order.id == payload.order.order_id).first()
    if not order:
        order = models.Order(id=payload.order.order_id, assigned_to_id=picker.id)
        db.add(order)
    else:
        if order.status in [models.OrderStatus.COMPLETED, models.OrderStatus.IN_PROGRESS]:
            order.assigned_to_id = picker.id
        else:
            order.assigned_to_id = picker.id
            order.status = models.OrderStatus.NEW
    db.query(models.OrderItem).filter(models.OrderItem.order_id == order.id).delete()
    for item in payload.order.items:
        db.add(models.OrderItem(order_id=order.id, material_id=item.material_id, required_qty=item.qty))
    db.commit()
    return {"status": "ok", "order_id": order.id, "picker": payload.picker.login}

@router.get("/", response_model=List[schemas.OrderSummaryOut])
def get_orders(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(database.get_db)):
    query = db.query(models.Order)
    if current_user.role == models.UserRole.PICKER:
        query = query.filter(models.Order.assigned_to_id == current_user.id)
    orders = query.all()
    return [{"order_id": o.id, "status": o.status.value} for o in orders]

@router.get("/{order_id}")
def get_order_details(order_id: str, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(database.get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    if current_user.role == models.UserRole.PICKER and order.assigned_to_id != current_user.id:
        raise HTTPException(status_code=403, detail="Нет доступа к этому заказу")
    items = []
    scanned_materials = []
    for item in order.items:
        mat = db.query(models.Material).filter(models.Material.id == item.material_id).first()
        if mat:
            items.append({
                "material_id": mat.id,
                "name": mat.name,
                "rack": mat.rack,
                "warehouse": "Основной",
                "weight": str(mat.weight).replace('.', ','),
                "height": str(mat.height).replace('.', ','),
                "width": str(mat.width).replace('.', ','),
                "depth": str(mat.depth).replace('.', ','),
                "qty": item.required_qty
            })
            scanned_qty = db.query(models.ScanEvent).filter(
                models.ScanEvent.order_id == order.id,
                models.ScanEvent.barcode == mat.barcode,
                models.ScanEvent.is_valid == True
            ).count()
            if scanned_qty >= item.required_qty:
                scanned_materials.append(mat.id)
    return {
        "order_id": order.id,
        "status": order.status.value,
        "progress": float(order.progress) if order.progress is not None else 0.0,
        "items": items,
        "scanned_materials": scanned_materials
    }

@router.post("/{order_id}/status")
def update_order_status(order_id: str, body: schemas.OrderStatusUpdate, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(database.get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    if current_user.role == models.UserRole.PICKER and order.assigned_to_id != current_user.id:
        raise HTTPException(status_code=403, detail="Нет доступа к этому заказу")
    valid_statuses = [s.value for s in models.OrderStatus]
    if body.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Недопустимый статус. Допустимые: {valid_statuses}")
    order.status = models.OrderStatus(body.status)
    if body.progress is not None:
        order.progress = body.progress
    db.commit()
    save_status_to_file(order_id, body.status, body.progress)
    return {"order_id": order.id, "status": order.status.value, "progress": float(order.progress)}