from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models
from app import database, auth, schemas

router = APIRouter()

@router.post("/verify/{order_id}", response_model=schemas.ScanResponse)
def verify_scan(order_id: str, req: schemas.ScanRequest, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(database.get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Заказ не найден")
    material = db.query(models.Material).filter(models.Material.barcode == req.barcode).first()
    if not material:
        return schemas.ScanResponse(status="error", message="Товар не найден в справочнике", progress=0.0)
    order_item = db.query(models.OrderItem).filter(
        models.OrderItem.order_id == order_id,
        models.OrderItem.material_id == material.id
    ).first()
    if not order_item:
        return schemas.ScanResponse(status="error", message="Этот товар не нужен в этом заказе!", progress=0.0)
    scanned_qty = db.query(models.ScanEvent).filter(
        models.ScanEvent.order_id == order_id,
        models.ScanEvent.barcode == req.barcode,
        models.ScanEvent.is_valid == True
    ).count()
    if scanned_qty >= order_item.required_qty:
        return schemas.ScanResponse(status="error", message="Превышено требуемое количество!", progress=0.0)
    db.add(models.ScanEvent(order_id=order_id, worker_id=current_user.id, barcode=req.barcode, is_valid=True))
    db.add(models.MovementLog(worker_id=current_user.id, from_loc="PREV_LOC", to_loc=material.rack, duration_sec=10.0))
    db.commit()
    if order.status in [models.OrderStatus.ACCEPTED, models.OrderStatus.NEW]:
        order.status = models.OrderStatus.IN_PROGRESS
        db.commit()
    total_required = sum(i.required_qty for i in order.items)
    total_scanned = db.query(models.ScanEvent).filter(
        models.ScanEvent.order_id == order_id,
        models.ScanEvent.is_valid == True
    ).count()
    progress = total_scanned / total_required if total_required > 0 else 0.0
    status_msg = "completed" if progress == 1.0 else "success"
    if progress == 1.0:
        order.status = models.OrderStatus.COMPLETED
        order.progress = 1.0
        db.commit()
        from .orders import save_status_to_file
        save_status_to_file(order_id, "completed", 1.0)
    else:
        order.progress = progress
        db.commit()
        from .orders import save_status_to_file
        save_status_to_file(order_id, order.status.value, progress)
    return schemas.ScanResponse(status=status_msg, message=f"Верно! {material.name}", progress=progress, material_name=material.name)