import json
import logging
import random

import anthropic

from hunter.x_theme_generator.config import CLAUDE_MODEL, PROMPTS_DIR
from hunter.x_theme_generator.models import Theme, TweetDraft, ThemeTweets

logger = logging.getLogger(__name__)

BUZZ_FORMATS = [
    "before_after",
    "empathy_betrayal",
    "provoke_rescue",
    "number_list",
    "contrarian_slash",
    "story",
]

FORMAT_LABELS = {
    "before_after": "Before→After型",
    "empathy_betrayal": "共感→裏切り型",
    "provoke_rescue": "煽り→救済型",
    "number_list": "数字の羅列型",
    "contrarian_slash": "逆張り一刀両断型",
    "story": "ストーリー型",
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
            f"以下のテーマでバズる投稿を2本書け。\n\n"
            f"テーマ: {theme.title}\n"
            f"切り口: {theme.summary}\n"
            f"{articles_hint}"
            f"使用するスタイル:\n"
            f"1. {format_names[0]}（format名: {selected_formats[0]}）\n"
            f"2. {format_names[1]}（format名: {selected_formats[1]}）\n\n"
            f"バズらせるための必須条件:\n"
            f"- 1行目は15文字以内で「え？」「マジ？」と思わせるフックにしろ\n"
            f"- 2本の投稿で書き出し・構造・口調を変えろ。同じパターンの繰り返しはNG\n"
            f"- 具体的な数字（時間、コスト、精度）を最低1つ入れろ\n"
            f"- 最後の1行で余韻を残せ。「いいね」ではなく「保存」される投稿を書け\n"
            f"- 製造業の現場を知ってる人間にしか書けないリアルさを入れろ\n"
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
