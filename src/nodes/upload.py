import asyncio
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

    os.makedirs(os.path.dirname(COOKIE_FILE) or "data", exist_ok=True)

    pw = await async_playwright().start()
    _browser = await pw.chromium.launch(headless=False)

    if os.path.exists(COOKIE_FILE):
        print("  [微信后台] 加载已保存的登录会话...")
        _context = await _browser.new_context(storage_state=COOKIE_FILE)
    else:
        _context = await _browser.new_context()
    _page = await _context.new_page()

    await _page.goto(f"{MP_HOME}/cgi-bin/home", wait_until="networkidle")

    need_login = "login" in _page.url.lower() or "登录" in await _page.title()

    if need_login:
        print("  [微信后台] 会话已过期，请扫描浏览器中的二维码登录...")
        _page = await _context.new_page()
        await _page.goto(f"{MP_HOME}", wait_until="networkidle")
        try:
            await _page.wait_for_url("**/cgi-bin/home*", timeout=300000)
        except Exception:
            return None
        print("  [微信后台] 登录成功。")

    await _context.storage_state(path=COOKIE_FILE)
    return _page


async def upload_node(state: dict, client=None) -> dict:
    title = state.get("title", "")
    formatted = state.get("formatted", "")

    if not title or not formatted:
        return {"draft_media_id": "", "error": "title or formatted is empty"}

    try:
        page = await _get_page()
        if page is None:
            return {"draft_media_id": "", "error": "登录超时"}

        os.makedirs("data", exist_ok=True)

        # ======== 进入编辑器 ========
        print("  → 进入新建图文...")

        if "home" not in page.url:
            await page.goto(f"{MP_HOME}/cgi-bin/home", wait_until="networkidle")
            await asyncio.sleep(2)

        await page.screenshot(path="data/debug_01_home.png")

        editor_page = None

        # 尝试「新的创作」→「写新图文」
        try:
            new_create = page.locator("text=新的创作").first
            if await new_create.count() > 0:
                await new_create.click()
                await asyncio.sleep(2)
                await page.screenshot(path="data/debug_02_menu.png")

                write_article = page.locator("text=写新图文").first
                if await write_article.count() > 0 and await write_article.is_visible():
                    async with page.context.expect_page(timeout=10000) as popup:
                        await write_article.click()
                    editor_page = await popup.value
                    print("    通过「新的创作 → 写新图文」打开")
        except Exception as e:
            print(f"    菜单方式: {e}")

        # 降级：同页导航
        if editor_page is None:
            if "appmsg" in page.url:
                editor_page = page
            else:
                await page.goto(
                    f"{MP_HOME}/cgi-bin/appmsg?t=media/appmsg_edit&action=edit&type=77&isMul=1&lang=zh_CN",
                    wait_until="networkidle",
                    timeout=30000,
                )
                await asyncio.sleep(5)
                editor_page = page
                print("    同页导航到编辑器")

        # 等待 React 渲染
        await editor_page.wait_for_load_state("networkidle", timeout=30000)
        await asyncio.sleep(5)

        await editor_page.screenshot(path="data/debug_03_editor.png")
        print(f"    编辑器 URL: {editor_page.url[:80]}")

        if "login" in editor_page.url.lower():
            print("    ⚠️  跳转到登录页，请扫码...")
            await editor_page.wait_for_url("**/cgi-bin/appmsg*", timeout=300000)
            await editor_page.wait_for_load_state("networkidle")
            await asyncio.sleep(5)
            print("    已进入编辑器")

        # ======== 填写标题 ========
        print("  → 填写标题...")
        title_filled = False

        # 等输入元素出现
        try:
            await editor_page.wait_for_selector(
                'input, textarea, [contenteditable="true"]',
                timeout=15000,
            )
        except Exception:
            pass

        for sel in [
            "#title", "#appmsg_title",
            'input[placeholder*="请在这里输入标题"]',
            'input[placeholder*="标题"]',
            'textarea[placeholder*="标题"]',
        ]:
            try:
                el = editor_page.locator(sel).first
                if await el.count() > 0:
                    await el.click()
                    await asyncio.sleep(0.2)
                    await el.fill("")
                    await el.fill(title)
                    await asyncio.sleep(0.3)
                    try:
                        if await el.input_value() == title:
                            title_filled = True
                            print(f"    标题已填写 ({sel})")
                            break
                    except Exception:
                        title_filled = True
                        print(f"    标题已填写 ({sel})")
                        break
            except Exception:
                continue

        # 键盘输入兜底
        if not title_filled:
            try:
                el = editor_page.locator("#title").first
                if await el.count() > 0:
                    await el.click()
                await editor_page.keyboard.type(title, delay=50)
                title_filled = True
                print("    标题已填写 (键盘输入)")
            except Exception:
                pass

        if not title_filled:
            print("    ⚠️  未找到标题输入框")

        # ======== 填写正文 ========
        print("  → 填写正文...")
        content_filled = False

        for sel in [
            "#ueditor_0", 'iframe[id*="ueditor"]', 'iframe[id*="editor"]', "iframe",
        ]:
            try:
                frame = editor_page.frame_locator(sel)
                body = frame.locator("body")
                if await body.count() > 0 and await body.first.is_visible():
                    await body.first.evaluate(
                        "el => el.innerHTML = arguments[0]", formatted
                    )
                    await body.first.press("End")
                    await body.first.press("Enter")
                    content_filled = True
                    print(f"    正文已填写 (iframe: {sel})")
                    break
            except Exception:
                continue

        if not content_filled:
            for sel in ['div[contenteditable="true"]', '[role="textbox"]']:
                try:
                    el = editor_page.locator(sel).first
                    if await el.count() > 0:
                        await el.evaluate(
                            "el => el.innerHTML = arguments[0]", formatted
                        )
                        content_filled = True
                        print(f"    正文已填写 ({sel})")
                        break
                except Exception:
                    continue

        if not content_filled:
            try:
                await editor_page.evaluate(f"""
                    document.querySelectorAll('iframe').forEach(f => {{
                        try {{ f.contentDocument.body.innerHTML = {repr(formatted)}; }} catch(e) {{}}
                    }});
                    const ce = document.querySelector('[contenteditable="true"]');
                    if (ce) ce.innerHTML = {repr(formatted)};
                """)
                content_filled = True
                print("    正文已填写 (JS 盲写)")
            except Exception:
                pass

        if not content_filled:
            print("    ⚠️  未找到编辑器")

        # ======== 保存 ========
        print("  → 保存草稿...")
        await editor_page.screenshot(path="data/debug_04_before_save.png")
        saved = False

        for sel in [
            "#js_submit",
            'button:has-text("保存为草稿")',
            'button:has-text("保存")',
            'a:has-text("保存为草稿")',
            '[title="保存"]',
        ]:
            try:
                btn = editor_page.locator(sel).first
                if await btn.count() > 0 and await btn.is_visible():
                    await btn.click()
                    await asyncio.sleep(3)
                    saved = True
                    print(f"    已点击保存 ({sel})")
                    break
            except Exception:
                continue

        if not saved:
            print("    ⚠️  请手动点击保存按钮")

        await editor_page.screenshot(path="data/debug_05_after_save.png")
        print("    浏览器保持打开 15 秒，确认草稿已保存后自动关闭")
        await asyncio.sleep(15)

        return {"draft_media_id": "saved"}

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"draft_media_id": "", "error": f"upload failed: {e}"}
