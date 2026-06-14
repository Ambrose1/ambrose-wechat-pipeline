"""微信公众号文章流水线 — 全自动生成 + 一键粘贴上传。

用法：
    python run.py --file article.docx
    python run.py --title "标题" --content "正文"
"""

import argparse
import asyncio
import os
import sys
import webbrowser

from dotenv import load_dotenv

load_dotenv()

from src.llm import create_llm, LLMConfig
from src.nodes.polish import polish_node
from src.nodes.enhance import enhance_node
from src.nodes.format import format_node
from src.nodes.log import log_node


def parse_args():
    p = argparse.ArgumentParser(description="微信公众号文章自动生成流水线")
    p.add_argument("--title", "-t", help="文章标题")
    p.add_argument("--content", "-c", help="文章正文")
    p.add_argument("--file", "-f", help="从文件读取（.md/.txt/.docx）")
    p.add_argument("--style", "-s", default=None, help="风格：深度/轻松/干货")
    return p.parse_args()


def read_input(args):
    title = args.title
    content = args.content
    if args.file:
        if args.file.lower().endswith(".docx"):
            from docx import Document
            doc = Document(args.file)
            text = "\n".join(p.text for p in doc.paragraphs).strip()
        else:
            with open(args.file, "r", encoding="utf-8") as f:
                text = f.read().strip()
        lines = text.split("\n", 1)
        if not title:
            first = lines[0].strip()
            title = first.lstrip("#").strip() if first.startswith("#") else first
            content = lines[1].strip() if len(lines) > 1 else ""
        else:
            content = text
    if not title:
        print("错误: 请提供 --title 或文件第一行")
        sys.exit(1)
    if not content:
        print("错误: 请提供 --content 或 --file")
        sys.exit(1)
    return title.strip(), content.strip()


def main():
    args = parse_args()
    title, content = read_input(args)
    style = args.style or os.getenv("ARTICLE_STYLE", "深度")

    provider = os.getenv("LLM_PROVIDER", "openai")
    model = os.getenv("LLM_MODEL", "gpt-4o")
    api_key = os.getenv("LLM_API_KEY", "")
    base_url = os.getenv("LLM_BASE_URL") or None
    if not api_key:
        print("错误: 请设置 LLM_API_KEY (.env 文件)")
        sys.exit(1)

    print(f"✨ {provider}/{model}  |  {style}风格")
    print(f"📄 {title}  ({len(content)} 字符)")
    print("—" * 40)

    llm = create_llm(LLMConfig(provider=provider, model=model, api_key=api_key, base_url=base_url))

    state = {"title": title, "content": content, "polished": "", "enhanced": "",
             "formatted": "", "draft_media_id": "", "metadata": {"source": "local"}}

    print("[1/4] 风格润色...")
    state.update(polish_node(state, llm, style=style))
    if state.get("error"):
        print(f"❌ {state['error']}"); sys.exit(1)
    print(f"      ✅ {len(state['polished'])} 字符")

    print("[2/4] 补充板块...")
    state.update(enhance_node(state, llm))
    if state.get("error"):
        print(f"❌ {state['error']}"); sys.exit(1)
    print(f"      ✅ {len(state['enhanced'])} 字符")

    print("[3/4] 排版格式化...")
    state.update(format_node(state))
    print(f"      ✅ {len(state['formatted'])} 字符")

    print("[4/4] 写入剪贴板 & 打开编辑器")
    log_node(state)

    os.makedirs("data", exist_ok=True)
    html_path = "data/latest_article.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(state["formatted"])

    # 复制标题到剪贴板
    try:
        import pyperclip
        pyperclip.copy(title)
    except Exception:
        pass

    # 打开微信编辑器
    editor_url = "https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_edit&action=edit&type=77&isMul=1&lang=zh_CN"
    webbrowser.open(editor_url)

    # 提示（标题已在剪贴板）
    print()
    print("—" * 40)
    print("📋 标题已复制到剪贴板（Cmd+V 粘贴到标题栏）")
    print("📋 正文 HTML 已复制，在正文区 Cmd+V 粘贴")
    print(f"📁 HTML 已保存: {html_path}")
    print()
    print("请在浏览器中：")
    print("  1. 登录（如需要）")
    print("  2. 标题栏 → Cmd+V")
    print("  3. 正文区 → Cmd+V")
    print("  4. 保存为草稿")

    # 复制正文到剪贴板（后复制，这样 Cmd+V 默认粘贴正文）
    try:
        import pyperclip
        pyperclip.copy(state["formatted"])
    except Exception:
        pass

    print()
    print("✅ 正文已写入剪贴板，切换到浏览器 Cmd+V 粘贴即可")


if __name__ == "__main__":
    main()
