from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.database import get_db
from app import models, security, crud

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/auth/login')


async def get_current_user(db: AsyncSession = Depends(get_db), token: str = Depends(oauth2_scheme)) -> models.User:

    crendentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail='无效的认证凭证', headers={'WWW-Authenticate': 'Bearer'})

    # 1. 解码 token
    payload = security.decode_access_token(token)
    if payload is None:
        raise crendentials_exception

    # 2. 提取 sub
    username: str | None = payload.get('sub')
    if username is None:
        raise crendentials_exception

    # 3. 查用户（确保用户仍然存在）
    user = await crud.get_user_by_username(db, username)
    if user is None:
        raise crendentials_exception

    return user


async def get_current_active_user(current_user: models.User = Depends(get_current_user)) -> models.User:
    """额外检查 is_active"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail='账号已被禁用')
    return current_user


def require_role(*allow_roles):
    """
    依赖工厂：生成一个检查角色的依赖。
   用法:Depends(require_role(UserRole.ADMIN))
   """
    async def check_role(current_user: models.User = Depends(get_current_active_user)) -> models.User:
        if current_user.role not in allow_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=f'权限不足，需要 {','.join(allow_roles)}')
        return current_user

    return check_role
