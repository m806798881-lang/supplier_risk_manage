from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, func, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# ---------- Supplier ----------


class Supplier(Base):
    __tablename__ = 'suppliers'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200))
    credit_code: Mapped[str] = mapped_column(
        String(50), unique=True, index=True)
    address: Mapped[str | None] = mapped_column(String(500))
    cooperation_years: Mapped[int] = mapped_column(default=0)
    contact_person: Mapped[str | None] = mapped_column(String(50))
    contact_phone: Mapped[str | None] = mapped_column(String(20))
    create_at: Mapped[datetime] = mapped_column(server_default=func.now())
    create_by: Mapped[int | None] = mapped_column(
        ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)

    risk_assessments: Mapped[list["RiskAssessment"]] = relationship(
        back_populates="supplier",
        cascade="all,delete-orphan",
        order_by='RiskAssessment.assessed_at.desc(),RiskAssessment.id.desc()'
    )
    creator: Mapped['User | None'] = relationship(foreign_keys=[create_by])

# ---------- RiskAssessment ----------


class RiskAssessment(Base):
    __tablename__ = 'riskassessments'

    id: Mapped[int] = mapped_column(autoincrement=True, primary_key=True)
    supplier_id: Mapped[int] = mapped_column(
        ForeignKey("suppliers.id", ondelete="CASCADE"), index=True)
    score: Mapped[int] = mapped_column(Integer)
    level: Mapped[str] = mapped_column(String(10), index=True)
    assessor: Mapped[str] = mapped_column(String(50))
    assessed_at: Mapped[datetime] = mapped_column(server_default=func.now())
    remark: Mapped[str | None] = mapped_column(String(500))

    supplier: Mapped["Supplier"] = relationship(
        back_populates='risk_assessments')

    __table_args__ = (CheckConstraint(
        'score >= 0 AND score <= 100', name='ck_score_range'),)

    @staticmethod
    def cal_level(score: int) -> str:
        if score < 40:
            return 'low'
        if score < 70:
            return 'medium'
        return 'high'

# ---------- User ----------


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(autoincrement=True, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), index=True, unique=True)
    hashed_password: Mapped[str] = mapped_column(String(225))
    is_active: Mapped[bool] = mapped_column(default=True)
    role: Mapped[str] = mapped_column(String(20), default='analyst')
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "role IN ('analyst','admin','audit')",
            name='ck_user_role',
        ),
    )


# ---------- Role ----------
class UserRole(StrEnum):
    ADMIN = 'admin'
    ANALYST = 'analyst'
    AUDITOR = 'auditor'
