"""本地运行微信公众号文章流水线。

用法：
    python run.py --title "文章标题" --content "文章内容"
    python run.py --title "文章标题" --file article.md
    python run.py --file article.md          # 标题从文件第一行提取（# 开头）
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
    p.add_argument("--content", "-c", help="文章正文（直接输入）")
    p.add_argument("--file", "-f", help="从文件读取文章内容（Markdown/TXT）")
    p.add_argument("--style", "-s", default=None, help="文章风格：深度/轻松/干货（默认从 .env 读取）")
    return p.parse_args()


def read_input(args):
    title = args.title
    content = args.content

    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            text = f.read().strip()
        lines = text.split("\n", 1)
        # 如果文件第一行是 # 标题，提取标题
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
        print("错误: 请提供文章标题 (--title 或文件第一行)")
        sys.exit(1)
    if not content:
        print("错误: 请提供文章内容 (--content 或 --file)")
        sys.exit(1)

    return title.strip(), content.strip()


async def main():
    args = parse_args()
    title, content = read_input(args)

    provider = os.getenv("LLM_PROVIDER", "openai")
    model = os.getenv("LLM_MODEL", "gpt-4o")
    api_key = os.getenv("LLM_API_KEY", "")
    base_url = os.getenv("LLM_BASE_URL") or None
    style = args.style or os.getenv("ARTICLE_STYLE", "深度")

    if not api_key:
        print("错误: 请设置 LLM_API_KEY 环境变量 (.env 文件)")
        sys.exit(1)

    print(f"LLM: {provider}/{model}  风格: {style}")
    print(f"标题: {title}")
    print(f"正文字符数: {len(content)}")
    print("—" * 40)

    llm = create_llm(LLMConfig(
        provider=provider, model=model, api_key=api_key, base_url=base_url,
    ))
    graph = build_graph(llm, style=style).compile()

    initial_state = PipelineState(
        title="",
        content="",
        polished="",
        enhanced="",
        formatted="",
        draft_media_id="",
        metadata={},
    )
    config = {"configurable": {"payload": {"title": title, "content": content}}}

    print("[1/6] 接收解析...")
    print("[2/6] 风格润色中...")
    print("[3/6] 补充板块中...")
    print("[4/6] 排版格式化...")
    print("[5/6] 上传公众号草稿...")
    print("      ⚠️  浏览器将打开，首次需扫码登录公众号后台")
    print()

    result = await graph.ainvoke(initial_state, config)

    print("—" * 40)
    if result.get("error"):
        print(f"❌ 失败: {result['error']}")
    else:
        print(f"✅ 完成 — 草稿已保存到微信公众号")
        print(f"   标题: {result.get('title', '')}")

    # 保存排版后的 HTML 到本地
    formatted = result.get("formatted", "")
    if formatted:
        out_path = "data/latest_article.html"
        os.makedirs("data", exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(formatted)
        print(f"   HTML 已保存: {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
