"""微信公众号后台自动上传 — Playwright persistent context。"""
import asyncio
import os

MP_HOME = "https://mp.weixin.qq.com"
PROFILE_DIR = "data/browser-profile"
_context = None
_page = None


async def _get_page():
    global _context, _page
    if _page is not None and not _page.is_closed():
        return _page

    from playwright.async_api import async_playwright

    os.makedirs(PROFILE_DIR, exist_ok=True)
    pw = await async_playwright().start()
    _context = await pw.chromium.launch_persistent_context(
        PROFILE_DIR, headless=False, viewport={"width": 1280, "height": 900},
    )
    _page = _context.pages[0] if _context.pages else await _context.new_page()
    await _page.goto(f"{MP_HOME}/cgi-bin/home?t=home/index&lang=zh_CN",
                     wait_until="networkidle", timeout=30000)
    await asyncio.sleep(3)
    body = (await _page.text_content("body")) or ""

    if "立即注册" in body:
        print("  ┌─────────────────────────────────────────┐")
        print("  │  首次使用，请在浏览器中扫码登录         │")
        print("  │  登录成功后程序自动继续（仅此一次）     │")
        print("  └─────────────────────────────────────────┘")
        try:
            await _page.wait_for_url("**/cgi-bin/home*token=*", timeout=600000)
        except Exception:
            return None
        print("  [微信后台] ✅ 登录已持久化")
    return _page


async def _open_editor(page):
    """从管理后台打开新建图文编辑器，返回 editor page。"""
    # 方式 1: 点击「新的创作」→「写新图文」
    try:
        btn = page.locator('text=新的创作').first
        if await btn.count() > 0:
            await btn.click()
            await asyncio.sleep(2)
            link = page.locator('text=写新图文').first
            if await link.count() > 0 and await link.is_visible():
                async with page.context.expect_page(timeout=10000) as popup:
                    await link.click()
                editor = await popup.value
                print("    通过「新的创作 → 写新图文」打开")
                return editor
    except Exception:
        pass

    # 方式 2: 侧边栏导航
    for menu in ["素材管理", "内容管理"]:
        try:
            el = page.locator(f'text={menu}').first
            if await el.count() > 0:
                await el.click()
                await asyncio.sleep(3)
                break
        except Exception:
            continue
    for label in ["新建图文", "写新图文", "新建"]:
        try:
            btn = page.locator(f'text={label}').first
            if await btn.count() > 0 and await btn.is_visible():
                async with page.context.expect_page(timeout=10000) as popup:
                    await btn.click()
                editor = await popup.value
                print(f"    通过「{label}」打开")
                return editor
        except Exception:
            continue

    # 方式 3: 直链（带 referer）
    editor = await page.context.new_page()
    await editor.goto(
        f"{MP_HOME}/cgi-bin/appmsg?t=media/appmsg_edit&action=edit&type=77&isMul=1&lang=zh_CN",
        wait_until="networkidle", timeout=30000,
        referer=f"{MP_HOME}/cgi-bin/home",
    )
    print("    直链打开")
    return editor


async def upload_node(state: dict, client=None) -> dict:
    title = state.get("title", "")
    formatted = state.get("formatted", "")
    if not title or not formatted:
        return {"draft_media_id": "", "error": "title or formatted empty"}

    try:
        page = await _get_page()
        if page is None:
            return {"draft_media_id": "", "error": "登录超时"}
        os.makedirs("data", exist_ok=True)

        # 打开编辑器
        print("  → 打开编辑器...")
        editor = await _open_editor(page)
        await asyncio.sleep(5)
        await editor.wait_for_load_state("networkidle", timeout=30000)
        await asyncio.sleep(5)
        await editor.screenshot(path="data/debug_editor.png")
        print(f"    编辑器 URL: {editor.url[:80]}")

        # 检查是否跳回登录
        body = (await editor.text_content("body")) or ""
        if "login" in editor.url.lower() or "立即注册" in body:
            print("    ⚠ 需要登录，请扫码...")
            try:
                await editor.wait_for_url("**/cgi-bin/appmsg*", timeout=600000)
            except Exception:
                return {"draft_media_id": "", "error": "编辑器登录超时"}
            await editor.wait_for_load_state("networkidle")
            await asyncio.sleep(5)

        # 等 React 渲染
        try:
            await editor.wait_for_selector(
                '#title, #ueditor_0, iframe, [contenteditable="true"]',
                timeout=30000)
        except Exception:
            pass
        await asyncio.sleep(3)

        # 填标题
        print("  → 填标题...")
        ok = False
        for sel in ['#title', '#appmsg_title',
                     'input[placeholder*="标题"]', 'input[placeholder*="输入"]', 'textarea']:
            try:
                el = editor.locator(sel).first
                if await el.count() > 0 and await el.is_visible():
                    await el.click()
                    await asyncio.sleep(0.2)
                    await el.fill("")
                    await el.fill(title)
                    await asyncio.sleep(0.3)
                    ok = True
                    print(f"    标题 ✓ ({sel})")
                    break
            except Exception:
                continue
        if not ok:
            print("    ⚠ 标题未自动填入")

        # 填正文
        print("  → 填正文...")
        ok = False
        for sel in ['#ueditor_0', 'iframe[id*="ueditor"]', 'iframe[id*="editor"]', "iframe"]:
            try:
                frame = editor.frame_locator(sel)
                body = frame.locator("body")
                if await body.count() > 0:
                    await body.first.evaluate("el => el.innerHTML = arguments[0]", formatted)
                    await body.first.press("End")
                    await body.first.press("Enter")
                    ok = True
                    print(f"    正文 ✓ (iframe {sel})")
                    break
            except Exception:
                continue
        if not ok:
            for sel in ['div[contenteditable="true"]', '[role="textbox"]']:
                try:
                    el = editor.locator(sel).first
                    if await el.count() > 0:
                        await el.evaluate("el => el.innerHTML = arguments[0]", formatted)
                        ok = True
                        print(f"    正文 ✓ ({sel})")
                        break
                except Exception:
                    continue
        if not ok:
            try:
                await editor.evaluate(f"""
                    document.querySelectorAll('iframe').forEach(f=>{{
                        try{{f.contentDocument.body.innerHTML={repr(formatted)}}}catch(e){{}}
                    }});
                    const ce=document.querySelector('[contenteditable="true"]');
                    if(ce)ce.innerHTML={repr(formatted)};
                """)
                ok = True
                print("    正文 ✓ (JS)")
            except Exception:
                pass
        if not ok:
            print("    ⚠ 正文未自动填入")

        # 保存
        print("  → 保存草稿...")
        saved = False
        for sel in ["#js_submit",
                     'button:has-text("保存为草稿")', 'button:has-text("保存")',
                     'a:has-text("保存为草稿")', 'a:has-text("保存")']:
            try:
                btn = editor.locator(sel).first
                if await btn.count() > 0 and await btn.is_visible():
                    await btn.click()
                    await asyncio.sleep(3)
                    saved = True
                    print(f"    保存 ✓ ({sel})")
                    break
            except Exception:
                continue
        if not saved:
            print("    ⚠ 请手动点击保存（20 秒窗口）")
            await asyncio.sleep(20)

        await editor.screenshot(path="data/debug_saved.png")
        return {"draft_media_id": "saved"}

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"draft_media_id": "", "error": str(e)}
