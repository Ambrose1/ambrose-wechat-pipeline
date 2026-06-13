import pytest
from src.wechat import WeChatClient


def test_client_requires_app_id():
    with pytest.raises(ValueError, match="WECHAT_APP_ID"):
        WeChatClient(app_id="", app_secret="secret")


def test_client_requires_app_secret():
    with pytest.raises(ValueError, match="WECHAT_APP_SECRET"):
        WeChatClient(app_id="wx123", app_secret="")


@pytest.mark.asyncio
async def test_get_access_token_success(httpx_mock):
    httpx_mock.add_response(
        url="https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=wx123&secret=secret",
        json={"access_token": "test_token_abc", "expires_in": 7200},
    )
    client = WeChatClient(app_id="wx123", app_secret="secret")
    token = await client.get_access_token()
    assert token == "test_token_abc"


@pytest.mark.asyncio
async def test_get_access_token_caches(httpx_mock):
    httpx_mock.add_response(
        url="https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=wx123&secret=secret",
        json={"access_token": "test_token_abc", "expires_in": 7200},
    )
    client = WeChatClient(app_id="wx123", app_secret="secret")
    token1 = await client.get_access_token()
    token2 = await client.get_access_token()
    assert token1 == token2
    # 只请求了一次（第二次走缓存）
    assert len(httpx_mock.get_requests()) == 1


@pytest.mark.asyncio
async def test_add_draft(httpx_mock):
    # access_token 请求
    httpx_mock.add_response(
        url="https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=wx123&secret=secret",
        json={"access_token": "tok", "expires_in": 7200},
    )
    # add_draft 请求
    httpx_mock.add_response(
        url="https://api.weixin.qq.com/cgi-bin/draft/add?access_token=tok",
        json={"media_id": "draft_media_001", "errcode": 0},
    )
    client = WeChatClient(app_id="wx123", app_secret="secret")
    media_id = await client.add_draft(title="测试标题", content="<p>内容</p>")
    assert media_id == "draft_media_001"


@pytest.mark.asyncio
async def test_add_draft_token_expired_retry(httpx_mock):
    # access_token 请求（第一次）
    httpx_mock.add_response(
        url="https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=wx123&secret=secret",
        json={"access_token": "old_tok", "expires_in": 7200},
    )
    # add_draft 返回 token 过期
    httpx_mock.add_response(
        url="https://api.weixin.qq.com/cgi-bin/draft/add?access_token=old_tok",
        json={"errcode": 40001, "errmsg": "access_token expired"},
    )
    # access_token 请求（刷新）
    httpx_mock.add_response(
        url="https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=wx123&secret=secret",
        json={"access_token": "new_tok", "expires_in": 7200},
    )
    # add_draft 成功
    httpx_mock.add_response(
        url="https://api.weixin.qq.com/cgi-bin/draft/add?access_token=new_tok",
        json={"media_id": "draft_002", "errcode": 0},
    )
    client = WeChatClient(app_id="wx123", app_secret="secret")
    media_id = await client.add_draft(title="标题", content="<p>内容</p>")
    assert media_id == "draft_002"
