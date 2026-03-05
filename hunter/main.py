import asyncio
import sys
from datetime import datetime
from pathlib import Path

from claude_agent_sdk import query, ClaudeAgentOptions

from hunter.agents import AGENTS
from hunter.config import OUTPUT_DIR

DIRECTOR_PROMPT = """\
あなたはリサーチディレクターです。ユーザーから与えられたトピックについて、
チームの専門エージェントを指揮して包括的なリサーチレポートを作成してください。

ワークフロー:
1. まず researcher エージェントに情報収集を依頼する
2. 次に analyst エージェントに収集情報の分析を依頼する
3. 最後に writer エージェントにレポート作成を依頼する

各エージェントの成果物を確認し、必要に応じて追加調査を指示してください。
最終レポートは output/ ディレクトリにMarkdownファイルとして保存してください。"""


async def run(topic: str) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = OUTPUT_DIR / f"report_{timestamp}.md"

    prompt = f"""\
以下のトピックについてリサーチ・分析レポートを作成してください。

トピック: {topic}

最終レポートは {output_file} に保存してください。"""

    print(f"🔍 リサーチ開始: {topic}")
    print(f"📄 出力先: {output_file}\n")

    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            allowed_tools=[
                "Read", "Write", "Edit",
                "WebSearch", "WebFetch",
                "Grep", "Glob", "Task",
            ],
            agents=AGENTS,
            system_prompt=DIRECTOR_PROMPT,
        ),
    ):
        if hasattr(message, "content"):
            for block in message.content:
                if getattr(block, "type", None) == "tool_use" and block.name == "Task":
                    agent_name = block.input.get("subagent_type", "unknown")
                    print(f"  → エージェント起動: {agent_name}")
                elif getattr(block, "type", None) == "text" and block.text.strip():
                    print(f"  {block.text[:120]}")

        if hasattr(message, "result"):
            print(f"\n✅ 完了! レポート: {output_file}")


def cli() -> None:
    if len(sys.argv) < 2:
        print("使い方: hunter <トピック>")
        print('例: hunter "AIエージェントの最新トレンド"')
        sys.exit(1)

    topic = " ".join(sys.argv[1:])
    asyncio.run(run(topic))


if __name__ == "__main__":
    cli()
