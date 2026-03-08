import json
import logging
import random

import anthropic

from hunter.x_theme_generator.config import CLAUDE_MODEL, PROMPTS_DIR
from hunter.x_theme_generator.models import Theme, TweetDraft, ThemeTweets

logger = logging.getLogger(__name__)

BUZZ_FORMATS = [
    "speed_alert",
    "comparison",
    "secret_reveal",
    "before_after",
    "list_thread",
    "problem_solution",
    "question_claim_evidence",
]

FORMAT_LABELS = {
    "speed_alert": "速報アラート型",
    "comparison": "比較煽り型",
    "secret_reveal": "秘密公開型",
    "before_after": "ビフォーアフター数字型",
    "list_thread": "リスト×スレッド型",
    "problem_solution": "問題→解決型",
    "question_claim_evidence": "質問→主張→証拠型",
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

        user_message = (
            f"以下のテーマについて、指定されたフォーマットで投稿下書きを2本生成してください。\n\n"
            f"テーマ: {theme.title}\n"
            f"概要: {theme.summary}\n\n"
            f"使用するフォーマット:\n"
            f"1. {format_names[0]}（format名: {selected_formats[0]}）\n"
            f"2. {format_names[1]}（format名: {selected_formats[1]}）\n\n"
            f"各投稿は140〜280文字で生成してください。"
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
