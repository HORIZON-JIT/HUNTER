import json
import logging
import random

import anthropic

from hunter.x_theme_generator.config import CLAUDE_MODEL, PROMPTS_DIR
from hunter.x_theme_generator.models import Theme, TweetDraft, ThemeTweets

logger = logging.getLogger(__name__)

BUZZ_FORMATS = [
    "field_report",
    "surprising_fact",
    "contrarian",
    "quick_tip",
    "news_insight",
]

FORMAT_LABELS = {
    "field_report": "現場の実験レポート型",
    "surprising_fact": "意外な発見型",
    "contrarian": "逆張り・本音型",
    "quick_tip": "即使えるTips型",
    "news_insight": "ニュース深掘り型",
}


def _load_prompt() -> str:
    return (PROMPTS_DIR / "tweet_generation.md").read_text(encoding="utf-8")


def generate_tweets(
    themes: list[Theme],
    client: anthropic.Anthropic,
) -> list[ThemeTweets]:
    if not themes:
        return []

    system_prompt = _load_prompt()
    results: list[ThemeTweets] = []

    for theme in themes:
        selected_formats = random.sample(BUZZ_FORMATS, 2)
        format_names = [FORMAT_LABELS[f] for f in selected_formats]

        articles_hint = ""
        if theme.key_articles:
            articles_hint = f"参考記事URL: {', '.join(theme.key_articles)}\n\n"

        user_message = (
            f"以下のテーマで投稿を2本書いてください。\n\n"
            f"テーマ: {theme.title}\n"
            f"面白いポイント: {theme.summary}\n"
            f"{articles_hint}"
            f"使用するスタイル:\n"
            f"1. {format_names[0]}（format名: {selected_formats[0]}）\n"
            f"2. {format_names[1]}（format名: {selected_formats[1]}）\n\n"
            f"重要:\n"
            f"- テンプレをなぞるのではなく、読んだ人が「へぇ」と思う内容にすること\n"
            f"- 製造業の現場で働く人間のリアルな目線で書くこと\n"
            f"- 具体的な数字・ツール名・手順を入れること\n"
            f"- 各投稿は140〜280文字\n"
        )

        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )

        raw_text = response.content[0].text.strip()
        if "```" in raw_text:
            start = raw_text.index("```") + 3
            if raw_text[start:].startswith("json"):
                start += 4
            end = raw_text.index("```", start)
            raw_text = raw_text[start:end].strip()

        try:
            drafts_data = json.loads(raw_text)
        except json.JSONDecodeError:
            logger.warning("JSON解析失敗、再試行中: %s", theme.title)
            response = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=2048,
                system=system_prompt + "\n\n必ず有効なJSONのみを出力してください。説明文は不要です。",
                messages=[{"role": "user", "content": user_message}],
            )
            raw_text = response.content[0].text.strip()
            if "```" in raw_text:
                start = raw_text.index("```") + 3
                if raw_text[start:].startswith("json"):
                    start += 4
                end = raw_text.index("```", start)
                raw_text = raw_text[start:end].strip()
            try:
                drafts_data = json.loads(raw_text)
            except json.JSONDecodeError:
                logger.error("再試行でもJSON解析失敗、スキップ: %s", theme.title)
                continue

        drafts = []
        for item in drafts_data:
            text = item["tweet"]
            drafts.append(TweetDraft(
                format_name=item["format"],
                text=text,
                char_count=len(text),
            ))

        results.append(ThemeTweets(theme=theme, drafts=drafts))

    return results
