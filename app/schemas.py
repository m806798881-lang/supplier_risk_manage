from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

# ---------- Supplier ----------


class SupplierBase(BaseModel):
    """公共字段，供 Create /res复用"""
    name: str = Field(..., max_length=200, description='公司名称')
    address: str | None = Field(None, max_length=500, description='地址')
    cooperation_years: int = Field(0, ge=0, description='合作年限')
    contact_person: str | None = Field(
        None, max_length=50, description='联系人')
    contact_phone: str | None = Field(
        None, max_length=20, description='联系电话')


class SupplierCreate(SupplierBase):
    """创建时必须填写credit_code"""
    credit_code: str = Field(..., max_length=50, description='统一社会信用代码')


class SupplierOut(SupplierBase):
    """响应体：包含数据库生成的字段"""
    id: int
    credit_code: str
    create_at: datetime
    create_by: int

    model_config = ConfigDict(from_attributes=True)


class SupplierUpdate(BaseModel):
    """除了社会信用代码剩下都可以更改，更新：所有字段可选，只更新传入的字段"""
    name: str | None = Field(None, max_length=200)
    address: str | None = Field(None, max_length=500,)
    cooperation_years: int | None = Field(None, ge=0)
    contact_person: str | None = Field(
        None, max_length=50)
    contact_phone: str | None = Field(
        None, max_length=20)

# ---------- User ----------


class UserRegister(BaseModel):
    """注册请求体"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=128)


class UserOut(BaseModel):
    """用户响应体（绝不包含 hashed_password!)"""
    id: int
    username: str
    is_active: bool
    role: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------- Token ----------
class Token(BaseModel):
    """登录响应"""
    access_token: str
    token_type: str = 'bearer'


class TokenPayload(BaseModel):
    """JWT payload 的结构（用于类型提示，非必需）"""
    sub: str | None = None
    role: str | None = None
    exp: int | None = None

# ---------- risk assessments ----------


class RiskCreate(BaseModel):
    score: int = Field(..., ge=0, le=100)
    remark: str | None

# class RiskCreate(BaseModel):
#     score: int = Field(..., ge=0, le=100)
#     assessor: str = Field(..., max_length=50)
#     remark: str | None = Field(None, max_length=500)


class RiskOut(BaseModel):
    id: int
    supplier_id: int
    score: int
    level: str
    assessor: str
    assessed_at: datetime
    remark: str | None

    model_config = ConfigDict(from_attributes=True)
