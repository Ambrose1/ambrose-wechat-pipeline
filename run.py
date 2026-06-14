"""本地运行微信公众号文章流水线。

用法：
    python run.py --file article.docx
    python run.py --title "标题" --content "正文"
    python run.py --file article.md
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
    p.add_argument("--content", "-c", help="文章正文（直接输入）")
    p.add_argument("--file", "-f", help="从文件读取（支持 .md/.txt/.docx）")
    p.add_argument("--style", "-s", default=None, help="风格：深度/轻松/干货")
    return p.parse_args()


def read_input(args):
    title = args.title
    content = args.content

    if args.file:
        filepath = args.file.lower()
        if filepath.endswith(".docx"):
            from docx import Document
            doc = Document(args.file)
            paragraphs = [p.text for p in doc.paragraphs]
            text = "\n".join(paragraphs).strip()
        else:
            with open(args.file, "r", encoding="utf-8") as f:
                text = f.read().strip()

        lines = text.split("\n", 1)
        if not title:
            first_line = lines[0].strip()
            if first_line.startswith("#"):
                title = first_line.lstrip("#").strip()
                content = lines[1].strip() if len(lines) > 1 else ""
            else:
                title = first_line
                content = lines[1].strip() if len(lines) > 1 else ""
        else:
            content = text

    if not title:
        print("错误: 请提供 --title 或文件第一行作为标题")
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

    print(f"LLM: {provider}/{model}  风格: {style}")
    print(f"标题: {title}")
    print(f"正文: {len(content)} 字符")
    print("—" * 40)

    llm = create_llm(LLMConfig(
        provider=provider, model=model, api_key=api_key, base_url=base_url,
    ))

    state = {
        "title": title,
        "content": content,
        "polished": "",
        "enhanced": "",
        "formatted": "",
        "draft_media_id": "",
        "metadata": {"source": "local"},
    }

    # Step 1: 润色
    print("[1/4] 风格润色中...")
    state.update(polish_node(state, llm, style=style))
    if state.get("error"):
        print(f"❌ 润色失败: {state['error']}")
        sys.exit(1)
    print(f"      ✅ 完成 ({len(state['polished'])} 字符)")

    # Step 2: 补充
    print("[2/4] 补充板块中...")
    state.update(enhance_node(state, llm))
    if state.get("error"):
        print(f"❌ 补充失败: {state['error']}")
        sys.exit(1)
    print(f"      ✅ 完成 ({len(state['enhanced'])} 字符)")

    # Step 3: 排版
    print("[3/4] 排版格式化...")
    state.update(format_node(state))
    print(f"      ✅ 完成 ({len(state['formatted'])} 字符)")

    # Step 4: 记录
    log_node(state)
    print("[4/4] 准备上传")
    print()

    # 保存文件
    os.makedirs("data", exist_ok=True)

    html_path = "data/latest_article.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(state["formatted"])

    md_path = "data/latest_article.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n{state['enhanced']}")

    print("—" * 40)
    print(f"✅ 文章生成完成")
    print(f"   HTML:      {html_path}")
    print(f"   Markdown:  {md_path}")

    # 复制到剪贴板
    try:
        import pyperclip
        pyperclip.copy(state["formatted"])
        print("   📋 已复制到剪贴板")
    except Exception:
        pass

    # 打开微信编辑器
    editor_url = "https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_edit&action=edit&type=77&isMul=1&lang=zh_CN"
    print(f"   🌐 打开微信编辑器...")
    webbrowser.open(editor_url)

    print()
    print("请在浏览器中：")
    print("  1. 扫码登录（如需要）")
    print("  2. 标题栏粘贴标题")
    print("  3. 正文区 Cmd+V 粘贴（已复制 HTML）")
    print("  4. 点击「保存为草稿」")


if __name__ == "__main__":
    main()
