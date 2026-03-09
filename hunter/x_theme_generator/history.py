"""過去に生成したツイートの履歴を管理し、重複回避に使用する。"""

import logging
import re
from datetime import datetime, timedelta
from pathlib import Path

from hunter.x_theme_generator.config import OUTPUT_DIR

logger = logging.getLogger(__name__)


def load_recent_tweets(days: int = 7) -> list[str]:
    """output/ディレクトリから直近N日分のツイートテキストを読み込む。

    ファイル名 xtheme_YYYYMMDD_HHMMSS.md から日付を判定し、
    ```で囲まれたツイート本文を抽出して返す。
    """
    if not OUTPUT_DIR.exists():
        return []

    cutoff = datetime.now() - timedelta(days=days)
    tweets: list[str] = []

    for filepath in sorted(OUTPUT_DIR.glob("xtheme_*.md")):
        # ファイル名から日時を取得
        match = re.search(r"xtheme_(\d{8})_(\d{6})\.md", filepath.name)
        if not match:
            continue

        try:
            file_date = datetime.strptime(
                f"{match.group(1)}_{match.group(2)}", "%Y%m%d_%H%M%S"
            )
        except ValueError:
            continue

        if file_date < cutoff:
            continue

        # ```で囲まれたツイート本文を抽出
        content = filepath.read_text(encoding="utf-8")
        code_blocks = re.findall(r"```\n(.*?)\n```", content, re.DOTALL)
        tweets.extend(code_blocks)

    logger.info("過去%d日間のツイート履歴: %d件", days, len(tweets))
    return tweets


def format_history_for_prompt(tweets: list[str], max_items: int = 12) -> str:
    """過去ツイートをプロンプト注入用のテキストに整形する。"""
    if not tweets:
        return ""

    recent = tweets[-max_items:]
    lines = ["## 過去に生成した投稿（これらと内容・構造が被らないようにすること）"]
    for i, tweet in enumerate(recent, 1):
        # 各ツイートの最初の1行だけをサマリーとして使う（トークン節約）
        first_line = tweet.strip().split("\n")[0]
        lines.append(f"{i}. {first_line}")

    return "\n".join(lines)
