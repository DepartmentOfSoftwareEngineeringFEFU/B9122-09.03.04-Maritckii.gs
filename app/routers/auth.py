from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from .. import models, schemas, database, auth

router = APIRouter()

@router.post("/login", response_model=schemas.Token)
def login(credentials: schemas.LoginRequest, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.login == credentials.login).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Пользователь не найден")
    if not auth.verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный пароль")
    access_token = auth.create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/token", response_model=schemas.Token)
def login_form(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.login == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверные учетные данные", headers={"WWW-Authenticate": "Bearer"})
    access_token = auth.create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/register")
def register(user_data: schemas.LoginRequest, db: Session = Depends(database.get_db)):
    existing_user = db.query(models.User).filter(models.User.login == user_data.login).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Пользователь уже существует")
    new_user = models.User(
        login=user_data.login,
        hashed_password=auth.get_password_hash(user_data.password),
        full_name=f"Сборщик {user_data.login}",
        role=models.UserRole.PICKER
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": f"Пользователь {user_data.login} создан", "id": new_user.id}