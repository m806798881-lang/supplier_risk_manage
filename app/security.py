from passlib.context import CryptContext
from datetime import timedelta, timezone, datetime
from jose import jwt, JWTError

from app.config import settings

# ---------- user password hash ----------

# 全局密码上下文，统一配置算法
pwd_context = CryptContext(
    schemes=['bcrypt'],
    deprecated="auto",
    bcrypt__rounds=12    # cost factor
)


def get_password_hash(password: str) -> str:
    """把明文密码哈希成 bcrypt 字符串"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hash_password: str) -> bool:
    """校验明文密码是否匹配哈希值"""
    return pwd_context.verify(plain_password, hash_password)


# 测试上述函数
if __name__ == "__main__":
    hash_pwd = get_password_hash('123456')
    print(hash_pwd)
    print(verify_password('123456', hash_pwd))
    print(verify_password('123555', hash_pwd))


# ---------- JWT token ----------
def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """生成 access token"""
    to_encode = data.copy()

    # 过期时间：默认 30 分钟
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.access_token_expire_minutes)

    expire = datetime.now(timezone.utc)+expires_delta
    to_encode.update({'exp': expire, 'iat': datetime.now(timezone.utc)})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict | None:
    """解码并验证 token,失败返回 None"""
    try:
        pyload = jwt.decode(token, settings.secret_key,
                            algorithms=[settings.algorithm])
        return pyload
    except JWTError:
        return None
