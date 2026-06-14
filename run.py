"""本地运行微信公众号文章流水线。

用法：
    python run.py --file article.docx
    python run.py --title "标题" --content "正文"
"""

import argparse
import asyncio
import os
import sys

from dotenv import load_dotenv
load_dotenv()

from src.llm import create_llm, LLMConfig
from src.graph import build_graph
from src.state import PipelineState


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
            if first.startswith("#"):
                title = first.lstrip("#").strip()
                content = lines[1].strip() if len(lines) > 1 else ""
            else:
                title = first
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


async def main():
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
    print(f"标题: {title}  ({len(content)} 字符)")
    print("—" * 40)

    llm = create_llm(LLMConfig(provider=provider, model=model, api_key=api_key, base_url=base_url))
    graph = build_graph(llm, style=style).compile()

    state = PipelineState(title="", content="", polished="", enhanced="",
                          formatted="", draft_media_id="", metadata={})
    config = {"configurable": {"payload": {"title": title, "content": content}}}

    print("[1/6] 接收解析 → [2/6] 润色 → [3/6] 补充 → [4/6] 排版 → [5/6] 上传 → [6/6] 记录")
    print()

    result = await graph.ainvoke(state, config)

    print("—" * 40)
    if result.get("error"):
        print(f"❌ 失败: {result['error']}")
    else:
        print(f"✅ 完成！草稿已保存到微信公众号")
        print(f"   标题: {result.get('title', '')}")

    formatted = result.get("formatted", "")
    if formatted:
        os.makedirs("data", exist_ok=True)
        with open("data/latest_article.html", "w") as f:
            f.write(formatted)


if __name__ == "__main__":
    asyncio.run(main())
