import json
import logging

import anthropic

from hunter.x_theme_generator.config import CLAUDE_MODEL, PROMPTS_DIR
from hunter.x_theme_generator.models import Article, Theme

logger = logging.getLogger(__name__)


def _load_prompt() -> str:
    return (PROMPTS_DIR / "theme_extraction.md").read_text(encoding="utf-8")


def _build_articles_text(articles: list[Article]) -> str:
    lines = []
    for i, a in enumerate(articles, 1):
        lines.append(
            f"{i}. [{a.source}] {a.title}\n"
            f"   URL: {a.link}\n"
            f"   概要: {a.summary}\n"
        )
    return "\n".join(lines)


def extract_themes(
    articles: list[Article],
    client: anthropic.Anthropic,
) -> list[Theme]:
    if not articles:
        logger.warning("記事が0件のためテーマ抽出をスキップ")
        return []

    system_prompt = _load_prompt()
    articles_text = _build_articles_text(articles)

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2048,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": f"以下の記事一覧からトレンドTop3を抽出してください。\n\n{articles_text}",
            }
        ],
    )

    raw_text = response.content[0].text.strip()

    # JSON部分を抽出（```json ... ``` で囲まれている場合に対応）
    if "```" in raw_text:
        start = raw_text.index("```") + 3
        if raw_text[start:].startswith("json"):
            start += 4
        end = raw_text.index("```", start)
        raw_text = raw_text[start:end].strip()

    themes_data = json.loads(raw_text)

    themes = []
    for item in themes_data[:3]:
        themes.append(Theme(
            title=item["title"],
            summary=item["summary"],
            key_articles=item.get("key_articles", []),
            relevance_score=item.get("relevance_score", 0),
        ))

    return themes
