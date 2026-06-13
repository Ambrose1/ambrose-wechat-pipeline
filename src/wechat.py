import time
from typing import Optional

import httpx

WECHAT_API_BASE = "https://api.weixin.qq.com"


class WeChatClient:
    def __init__(self, app_id: str, app_secret: str):
        if not app_id:
            raise ValueError("WECHAT_APP_ID is required")
        if not app_secret:
            raise ValueError("WECHAT_APP_SECRET is required")
        self.app_id = app_id
        self.app_secret = app_secret
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0.0

    async def get_access_token(self) -> str:
        now = time.time()
        if self._access_token and now < self._token_expires_at - 60:
            return self._access_token

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{WECHAT_API_BASE}/cgi-bin/token",
                params={
                    "grant_type": "client_credential",
                    "appid": self.app_id,
                    "secret": self.app_secret,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            self._access_token = data["access_token"]
            self._token_expires_at = now + data.get("expires_in", 7200)
            return self._access_token

    def invalidate_token(self) -> None:
        self._access_token = None
        self._token_expires_at = 0.0

    async def add_draft(self, title: str, content: str) -> str:
        token = await self.get_access_token()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{WECHAT_API_BASE}/cgi-bin/draft/add",
                params={"access_token": token},
                json={
                    "articles": [{"title": title, "content": content}],
                },
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("errcode") == 40001:  # token 过期
                self.invalidate_token()
                token = await self.get_access_token()
                resp = await client.post(
                    f"{WECHAT_API_BASE}/cgi-bin/draft/add",
                    params={"access_token": token},
                    json={"articles": [{"title": title, "content": content}]},
                )
                resp.raise_for_status()
                data = resp.json()

            if data.get("errcode", 0) != 0:
                raise RuntimeError(
                    f"微信 API 错误: {data.get('errmsg', 'unknown')} (errcode={data.get('errcode')})"
                )

            return data["media_id"]
