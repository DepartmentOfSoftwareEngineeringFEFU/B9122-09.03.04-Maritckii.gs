from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .database import engine, Base, SessionLocal
from . import models
from .auth import get_password_hash
from .routers import auth, orders, scans, routes
from .services.history_loader import load_history_to_db
import os

Base.metadata.create_all(bind=engine)
app = FastAPI(title="Warehouse Automation API", description="Система автоматизации склада (ВКР Марицкий Г.С.)", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(auth.router, prefix="/api/auth", tags=["Авторизация"])
app.include_router(orders.router, prefix="/api/orders", tags=["Заказы"])
app.include_router(scans.router, prefix="/api/scans", tags=["Сканирование"])
app.include_router(routes.router, prefix="/api/routes", tags=["Маршрутизация"])

static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.on_event("startup")
def startup_event():
    db = SessionLocal()
    if not db.query(models.User).filter(models.User.login == "admin").first():
        admin = models.User(login="admin", hashed_password=get_password_hash("admin123"), full_name="Администратор Склада", role=models.UserRole.ADMIN)
        picker = models.User(login="picker1", hashed_password=get_password_hash("picker123"), full_name="Иванов Иван (Сборщик)", role=models.UserRole.PICKER)
        db.add_all([admin, picker])
        db.commit()
    load_history_to_db(db)
    db.close()

@app.get("/")
def root():
    return {"message": "Warehouse Automation API is running. Docs: /docs"}