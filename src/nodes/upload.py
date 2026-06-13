import asyncio
import json
import os
from pathlib import Path

COOKIE_FILE = "data/wechat_cookies.json"
_browser = None
_context = None
_page = None

MP_HOME = "https://mp.weixin.qq.com"


async def _get_page():
    """获取或创建浏览器 page，自动处理登录/会话恢复。"""
    global _browser, _context, _page

    if _page is not None and not _page.is_closed():
        return _page

    from playwright.async_api import async_playwright

    pw = await async_playwright().start()
    _browser = await pw.chromium.launch(headless=False)

    # 尝试恢复已有登录态
    if os.path.exists(COOKIE_FILE):
        _context = await _browser.new_context(storage_state=COOKIE_FILE)
    else:
        _context = await _browser.new_context()
    _page = await _context.new_page()

    await _page.goto(f"{MP_HOME}/cgi-bin/home", wait_until="networkidle")

    # 检查是否需要登录
    if "登录" in await _page.title():
        print("\n[微信后台] 请扫描浏览器中的二维码登录...")
        # 等待跳转到首页（最多等 5 分钟）
        try:
            await _page.wait_for_url("**/cgi-bin/home*", timeout=300000)
        except Exception:
            return None
        # 保存登录态，下次不用扫
        await _context.storage_state(path=COOKIE_FILE)
        os.makedirs(os.path.dirname(COOKIE_FILE), exist_ok=True)
        print("[微信后台] 登录成功，会话已保存。")

    return _page


async def upload_node(state: dict, client=None) -> dict:
    """通过 Playwright 浏览器自动化上传文章到微信公众号草稿箱。

    从 state 取 title 和 formatted（HTML），模拟浏览器操作：
    1. 打开/恢复微信公众号后台
    2. 进入新建图文
    3. 填写标题和正文
    4. 保存草稿
    """
    title = state.get("title", "")
    formatted = state.get("formatted", "")

    if not title or not formatted:
        return {"draft_media_id": "", "error": "upload failed: title or formatted is empty"}

    try:
        page = await _get_page()
        if page is None:
            return {"draft_media_id": "", "error": "upload failed: 登录超时"}

        # 开新页面：新建图文
        new_page = await page.context.new_page()
        try:
            await new_page.goto(
                f"{MP_HOME}/cgi-bin/appmsg?t=media/appmsg_edit&action=edit&type=77&isMul=1&lang=zh_CN",
                wait_until="networkidle",
                timeout=30000,
            )
        except Exception:
            pass
        await asyncio.sleep(2)

        # 填写标题
        try:
            title_input = new_page.locator("#title")
            await title_input.wait_for(state="visible", timeout=10000)
            await title_input.fill(title)
        except Exception:
            # 尝试 textarea
            try:
                title_input = new_page.locator('textarea[name="title"]')
                await title_input.wait_for(state="visible", timeout=5000)
                await title_input.fill(title)
            except Exception:
                pass

        # 填写正文（在 iframe 中）
        # 微信后台编辑器正文是一个 iframe (about:blank 或类似)
        try:
            content_frame = new_page.frame_locator("#ueditor_0")
            # 点击正文区域获取焦点
            body = content_frame.locator("body")
            await body.wait_for(state="visible", timeout=10000)
            await body.click()
            await asyncio.sleep(0.5)

            # 通过 JS 设置 HTML 内容
            await body.evaluate("el => el.innerHTML = arguments[0]", formatted)
            await asyncio.sleep(0.5)

            # 触发输入事件，让编辑器感知内容变化
            await body.press("Enter")
            await body.press("Backspace")
        except Exception:
            pass

        # 点击「保存为草稿」或「保存」
        try:
            # 优先找「保存为草稿」
            save_btn = new_page.locator("button:has-text('保存为草稿')")
            if await save_btn.count() == 0:
                save_btn = new_page.locator("button:has-text('保存')")
            if await save_btn.count() == 0:
                save_btn = new_page.locator("text=保存")
            await save_btn.first.click(timeout=5000)
            await asyncio.sleep(3)
        except Exception:
            # 最后尝试点击底部保存按钮
            try:
                save_btn = new_page.locator("#js_submit")
                await save_btn.click(timeout=3000)
                await asyncio.sleep(3)
            except Exception:
                pass

        await new_page.close()
        return {"draft_media_id": "saved"}

    except Exception as e:
        return {"draft_media_id": "", "error": f"upload failed: {e}"}
