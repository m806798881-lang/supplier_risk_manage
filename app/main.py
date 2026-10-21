from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.database import engine, Base, get_db
from app import crud, schemas, models, deps
from app.security import verify_password, create_access_token
from app.models import UserRole


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时建表（生产环境应改用 Alembic 迁移）
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    # 关闭时释放连接池
    await engine.dispose()

app = FastAPI(title='供应商风险评估', version='0.1.0', lifespan=lifespan,
              description="供应商主数据 + 风险记录 + JWT 鉴权 + RBAC 权限控制")

# ============================================================
# 健康检查（无鉴权，Docker 健康检查用）
# ============================================================


@app.get('/health', tags=['系统'])
async def health():
    return {'status': 'ok'}

# ---------- user auth----------
# 公开


@app.post('/auth/register', response_model=schemas.UserOut, status_code=201, tags=['认证'])
async def register(data: schemas.UserRegister, db: AsyncSession = Depends(get_db)):
    existing = await crud.get_user_by_username(db, data.username)
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, detail='用户名已被占用')

    try:
        user = await crud.create_user(db, data.username, data.password)
    except IntegrityError:
        # 并发情况下两个请求同时通过了 exists 检查，兜底
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, detail='用户名已被占用')
    return user


@app.post('/auth/login', response_model=schemas.Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db), tags=['认证']):
    # 1. 查用户
    user = await crud.get_user_by_username(db, form_data.username)

    # 2. 校验用户名和密码（统一错误信息，防止用户名枚举）
    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='用户名或密码错误',
            headers={'WWW-Authenticate': 'Bearer'}
        )

    # 3.验证用户是否被软禁用
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail='账号已被禁用')

    # 4.生成token
    access_token = create_access_token(
        {'sub': user.username, 'role': user.role})

    return {'access_token': access_token, 'token_type': 'bearer'}  # rfc 6749 响应标准


@app.get('/auth/me', response_model=schemas.UserOut)
async def get_current_user(current_user: models.User = Depends(deps.get_current_user), tags=['认证']):
    return current_user


# ---------- supplier ----------
# ---------- 列表 ----------
@app.get('/suppliers/', response_model=list[schemas.SupplierOut], tags=["供应商"])
async def list_suppliers(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db), current_user: models.User = Depends(deps.get_current_active_user)):
    return await crud.list_suppliers(db, skip, limit)


@app.get('/suppliers/me', response_model=list[schemas.SupplierOut], tags=["供应商"])
async def list_my_suppliers(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db), current_user: models.User = Depends(deps.get_current_active_user)):

    if current_user.role in (UserRole.ADMIN, UserRole.AUDITOR):
        return await crud.list_suppliers(db, skip, limit)
    return await crud.list_suppliers_by_creator(db, current_user.id, skip, limit)

# ---------- 单个 ----------
# 所有登录用户


@app.get('/suppliers/{supplier_id}', response_model=schemas.SupplierOut, tags=["供应商"])
async def get_supplier(supplier_id: int, db: AsyncSession = Depends(get_db), current_user: models.User = Depends(deps.get_current_active_user)):
    supplier = await crud.get_supplier(db, supplier_id)
    if supplier is None:
        raise HTTPException(status_code=404, detail=f'供应商{supplier_id}不存在')

    return supplier

# ---------- 创建 ----------
# analyst，admin


@app.post('/suppliers/', response_model=schemas.SupplierOut, status_code=201, tags=["供应商"])
async def create_supplier(data: schemas.SupplierCreate, db: AsyncSession = Depends(get_db), current_user: models.User = Depends(deps.require_role(UserRole.ANALYST, UserRole.ADMIN))):
    try:
        return await crud.create_supplier(data, db, current_user.id)
    except IntegrityError:
        await db.rollback()
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail='统一社会信用代码已存在')

# ---------- 更新 ----------


@app.patch('/suppliers/{supplier_id}', response_model=schemas.SupplierOut, tags=["供应商"])
async def update_supplier(supplier_id: int, data: schemas.SupplierUpdate, db: AsyncSession = Depends(get_db), current_user: models.User = Depends(deps.require_role(UserRole.ANALYST, UserRole.ADMIN))):
    supplier = await crud.update_supplier(db, supplier_id, data)
    if supplier is None:
        raise HTTPException(status_code=404, detail=f'供应商{supplier_id}不存在')
    return supplier

# ---------- 删除 ----------
# 仅admin


@app.delete('/suppliers/{supplier_id}', status_code=204, tags=["供应商"])
async def delete_supplier(supplier_id: int, db: AsyncSession = Depends(get_db), current_user: models.User = Depends(deps.require_role(UserRole.ADMIN))):
    ok = await crud.delete_supplier(db, supplier_id)
    if not ok:
        return HTTPException(status_code=404, detail=f'供应商{supplier_id}不存在')

 # 204 不返回 body
# ============================================================
# 风险记录（挂在供应商下，RESTful 子资源）
# ============================================================


@app.post('/suppliers/{supplier_id}/risks/', response_model=schemas.RiskOut, status_code=201, tags=['风险记录'])
async def create_risk(supplier_id: int, data: schemas.RiskCreate, db: AsyncSession = Depends(get_db), current_user: models.User = Depends(deps.require_role(UserRole.ADMIN, UserRole.ANALYST))):
    supplier = await crud.get_supplier(db, supplier_id)
    if supplier is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"供应商 {supplier_id} 不存在")
    return await crud.create_risk(data, current_user.username, supplier_id, db)


@app.get('/suppliers/{supplier_id}/risks/', response_model=list[schemas.RiskOut], tags=['风险记录'])
async def list_risks(supplier_id: int, db: AsyncSession = Depends(get_db), current_user: models.User = Depends(deps.get_current_active_user)):
    supplier = await crud.get_supplier(db, supplier_id)
    if supplier is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"供应商 {supplier_id} 不存在")
    await crud.list_risks_by_supplier(db, supplier_id)


@app.get("/suppliers/{supplier_id}/risks/{risk_id}", response_model=schemas.RiskOut, tags=['风险记录'])
async def get_risk(supplier_id: int, risk_id: int, db: AsyncSession = Depends(get_db), current_user: models.User = Depends(deps.get_current_active_user)):
    risk = await crud.get_risk(db, risk_id, supplier_id)
    if risk is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail='风险记录不存在')
    return risk


@app.delete('/suppliers/{supplier_id}/risks/{risk_id}', status_code=status.HTTP_204_NO_CONTENT, tags=['风险记录'])
async def delete_risk(supplier_id: int, risk_id: int, db: AsyncSession = Depends(get_db), current_user: models.User = Depends(deps.require_role(UserRole.ADMIN))):
    ok = await crud.delete_risk(db, risk_id, supplier_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail='风险记录不存在')
