"""
微信公众号后台自动化上传 — 基于 Playwright persistent context。
复用浏览器数据目录 data/browser-profile，一次扫码永久有效。
"""
import asyncio
import os

MP_HOME = "https://mp.weixin.qq.com"
PROFILE_DIR = "data/browser-profile"
_browser = None
_context = None
_page = None


async def _get_page():
    """获取或创建浏览器 page。使用 persistent context 保持登录态。"""
    global _browser, _context, _page

    if _page is not None and not _page.is_closed():
        return _page

    from playwright.async_api import async_playwright

    os.makedirs(PROFILE_DIR, exist_ok=True)
    pw = await async_playwright().start()

    _context = await pw.chromium.launch_persistent_context(
        PROFILE_DIR,
        headless=False,
        viewport={"width": 1280, "height": 900},
        locale="zh-CN",
        channel=None,
    )
    _page = _context.pages[0] if _context.pages else await _context.new_page()

    # 检查登录态
    await _page.goto(f"{MP_HOME}/cgi-bin/home?t=home/index&lang=zh_CN", wait_until="networkidle", timeout=30000)
    await asyncio.sleep(3)

    body = (await _page.text_content("body")) or ""

    if "立即注册" in body or "password" in body.lower():
        print("  [微信后台] 请扫码登录（仅此一次）...")
        # 点「登录」
        try:
            login_link = _page.locator('a:has-text("登录"), button:has-text("登录")').first
            if await login_link.count() > 0 and await login_link.is_visible():
                await login_link.click()
                await asyncio.sleep(3)
        except Exception:
            pass
        # 等跳到管理后台
        try:
            await _page.wait_for_url("**/cgi-bin/home*token=*", timeout=300000)
        except Exception:
            return None
        print("  [微信后台] 登录成功（已持久化，下次无需再扫）")

    return _page


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

        # ==== 打开编辑器 ====
        print("  → 打开编辑器...")
        await page.goto(
            f"{MP_HOME}/cgi-bin/appmsg?t=media/appmsg_edit&action=edit&type=77&isMul=1&lang=zh_CN",
            wait_until="networkidle", timeout=30000,
        )
        await asyncio.sleep(5)

        # 如果被踢回登录页，等用户扫码
        if "login" in page.url.lower() or "password" in ((await page.text_content("body")) or "").lower():
            print("  [微信后台] 会话过期，请扫码...")
            try:
                await page.wait_for_url("**/cgi-bin/appmsg*", timeout=300000)
            except Exception:
                return {"draft_media_id": "", "error": "编辑器登录超时"}
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(5)

        await page.screenshot(path="data/debug_editor.png")
        print(f"    编辑器: {page.url[:80]}")

        # ==== 填标题 ====
        print("  → 填标题...")
        ok = False
        for sel in ['#title', 'input[placeholder*="标题"]', '#appmsg_title']:
            try:
                el = page.locator(sel).first
                if await el.count() > 0:
                    await el.wait_for(state="visible", timeout=10000)
                    await el.click()
                    await asyncio.sleep(0.3)
                    await el.fill("")
                    await el.fill(title)
                    await asyncio.sleep(0.3)
                    try:
                        v = await el.input_value()
                    except Exception:
                        v = title
                    if v == title:
                        ok = True
                        print(f"    标题 ✓ ({sel})")
                        break
            except Exception:
                continue
        if not ok:
            print("    ⚠ 标题未自动填入，请手动填写")

        # ==== 填正文 ====
        print("  → 填正文...")
        ok = False
        # 尝试 iframe
        for sel in ['#ueditor_0', 'iframe[id*="ueditor"]', 'iframe[id*="editor"]', "iframe"]:
            try:
                frame = page.frame_locator(sel)
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
        # 尝试 contenteditable
        if not ok:
            for sel in ['div[contenteditable="true"]', '[role="textbox"]']:
                try:
                    el = page.locator(sel).first
                    if await el.count() > 0:
                        await el.evaluate("el => el.innerHTML = arguments[0]", formatted)
                        ok = True
                        print(f"    正文 ✓ ({sel})")
                        break
                except Exception:
                    continue
        # JS 兜底
        if not ok:
            try:
                await page.evaluate(f"""
                    document.querySelectorAll('iframe').forEach(f => {{
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

        # ==== 保存 ====
        print("  → 保存草稿...")
        saved = False
        for sel in [
            "#js_submit",
            'button:has-text("保存为草稿")',
            'button:has-text("保存")',
            'a:has-text("保存为草稿")',
            'button:has-text("发表")',  # 有时按钮叫发表
        ]:
            try:
                btn = page.locator(sel).first
                if await btn.count() > 0 and await btn.is_visible():
                    await btn.click()
                    await asyncio.sleep(3)
                    saved = True
                    print(f"    保存 ✓ ({sel})")
                    break
            except Exception:
                continue
        if not saved:
            print("    ⚠ 未找到保存按钮，请手动点击")
            await asyncio.sleep(15)

        await page.screenshot(path="data/debug_saved.png")
        return {"draft_media_id": "saved"}

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"draft_media_id": "", "error": str(e)}
