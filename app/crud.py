from app import models, schemas
from app.security import get_password_hash

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload


# ---------- Supplier ----------


async def create_supplier(data: schemas.SupplierCreate, db: AsyncSession, created_by: int | None = None) -> models.Supplier:
    supplier = models.Supplier(**data.model_dump(), create_by=created_by)
    db.add(supplier)
    await db.commit()
    await db.refresh(supplier)
    return supplier

# 管理员/审计员看全部，其他人只看自己创建的


async def list_suppliers(db: AsyncSession, skip: int = 0, limit: int = 100, search: str | None = None) -> list[models.Supplier]:
    stmt = select(models.Supplier)
    if search:
        stmt = stmt.where(
            models.Supplier.name.ilike(f'%{search}%'))
    stmt = stmt.offset(skip).limit(
        limit).order_by(models.Supplier.id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


# async def search_suppliers(db: AsyncSession, keyword: str, skip: int = 0, limit: int = 100) -> list[models.Supplier]:
#     stmt = select(models.Supplier).where(models.Supplier.name.ilike(
#         f'%{keyword}%')).offset(skip).limit(limit).order_by(models.Supplier.id)
#     result = await db.execute(stmt)
#     return list(result.scalars().all())


async def list_suppliers_by_creator(db: AsyncSession, creator_id: int, skip: int = 0, limit: int = 100) -> list[models.Supplier]:
    stmt = select(models.Supplier).where(models.Supplier.create_by == creator_id).offset(skip).limit(
        limit).order_by(models.Supplier.id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_supplier(db: AsyncSession, supplier_id: int) -> models.Supplier | None:
    stmt = select(models.Supplier).options(
        selectinload(models.Supplier.risk_assessments)).where(models.Supplier.id == supplier_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def update_supplier(db: AsyncSession, supplier_id: int, data: schemas.SupplierUpdate) -> models.Supplier | None:
    supplier = await get_supplier(db, supplier_id)

    if supplier is None:
        return None

    # 只更新传入的字段
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(supplier, key, value)

    await db.commit()
    await db.refresh(supplier)
    return supplier


async def delete_supplier(db: AsyncSession, supplier_id: int) -> bool:
    supplier = await get_supplier(db, supplier_id)
    if supplier is None:
        return False

    await db.delete(supplier)
    await db.commit()
    return True

# ---------- Risk Assessments ----------


async def create_risk(data: schemas.RiskCreate, assessor: str, supplier_id: int, db: AsyncSession) -> models.RiskAssessment:
    risk = models.RiskAssessment(**data.model_dump(),
                                 level=models.RiskAssessment.cal_level(
                                     data.score),
                                 assessor=assessor,
                                 supplier_id=supplier_id)
    db.add(risk)
    await db.commit()
    await db.refresh(risk)
    return risk


async def list_risks_by_supplier(db: AsyncSession, supplier_id: int) -> list[models.RiskAssessment]:
    stmt = select(models.RiskAssessment).where(
        models.RiskAssessment.supplier_id == supplier_id).order_by(models.RiskAssessment.assessed_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_risk(db: AsyncSession, risk_id: int, supplier_id: int) -> models.RiskAssessment | None:
    stmt = select(models.RiskAssessment).where(
        models.RiskAssessment.id == risk_id, models.RiskAssessment.supplier_id == supplier_id,)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def delete_risk(db: AsyncSession, risk_id: int, supplier_id: int) -> bool:
    risk = await get_risk(db, risk_id, supplier_id)
    if risk is None:
        return False
    await db.delete(risk)
    await db.commit()
    return True

# ---------- User ----------


async def create_user(db: AsyncSession, username: str, password: str, role: str = 'analyst') -> models.User:

    user = models.User(username=username,
                       hashed_password=get_password_hash(password),
                       role=role)
    db.add(user)
    await db.commit()
    await db.refresh(user)  # 返回的是None
    return user


async def get_user_by_username(db: AsyncSession, username: str) -> models.User | None:
    stmt = select(models.User).where(models.User.username == username)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
