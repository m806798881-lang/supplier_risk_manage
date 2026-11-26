import httpx
import os
from dotenv import load_dotenv
from fastapi import status

load_dotenv()

API_BASE = os.getenv('AGENT_API_BASE', "http://127.0.0.1:8000")
USERNAME = os.getenv('AGENT_API_USERNAME', '')
PASSWORD = os.getenv('AGENT_API_PASSWORD', '')


class APIError(Exception):
    """
    API 调用失败，携带可读信息供 Tool 转成自然语言
    API 调用在预期内的失败——连不上、认证失败、返回了错误状态码。
    """
    pass


async def login() -> str:
    """登录 FastAPI,返回 access_token"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(url=f'{API_BASE}/auth/login',
                                     # OAuth2PasswordRequestForm,用 data= 而不是 json=
                                     data={'username': USERNAME, 'password': PASSWORD})

        except httpx.ConnectError as e:
            raise APIError(f'无法连接后端服务（{API_BASE}），请确认 FastAPI 已启动') from e

        if resp.status_code == status.HTTP_401_UNAUTHORIZED:
            raise APIError("后端认证失败，请检查 AGENT_API_USERNAME/PASSWORD")

        resp.raise_for_status()
        return resp.json()['access_token']


async def search_suppliers_api(keyword: str) -> list[dict]:
    token = await login()
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f'{API_BASE}/suppliers/', params={'search': keyword, "limit": 50}, headers={'Authorization': f'Bearer {token}'})
        resp.raise_for_status()
        return resp.json()


async def list_all_suppliers_api() -> list[dict]:
    token = await login()
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f'{API_BASE}/suppliers/', params={"limit": 200}, headers={'Authorization': f'Bearer {token}'})
        resp.raise_for_status()
        return resp.json()


async def list_risks_api(supplier_id: int) -> list[dict]:
    token = await login()
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{API_BASE}/suppliers/{supplier_id}/risks/",
                                headers={"Authorization": f"Bearer {token}"},)
        resp.raise_for_status()
        return resp.json()

    # async def fetch_supplier_risk(supplier_name: str) -> dict:
    #     """先登录,再根据名字查找可能对应的供应商"""
    #     token = await login()
    #     headers = {'Authorization': f'Bearer {token}'}

    #     async with httpx.AsyncClient(timeout=10) as client:
    #         resp = await client.get(url=f'{API_BASE}/suppliers/', headers=headers,
    #                                 params={'search': supplier_name})
    #         resp.raise_for_status()
    #         suppliers = resp.json()

    #     if not suppliers:
    #         raise ValueError(f'未找到供应商{supplier_name}')

    #      # 精确匹配优先，没有才退化为模糊匹配的第一个
    #     exact = [s for s in suppliers if s['name'] == supplier_name]
    #     return exact[0] if exact else suppliers[0]
