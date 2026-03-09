import json
import logging
import random

import anthropic

from hunter.x_theme_generator.config import CLAUDE_MODEL, PROMPTS_DIR
from hunter.x_theme_generator.models import Theme, TweetDraft, ThemeTweets

logger = logging.getLogger(__name__)

BUZZ_FORMATS = [
    "shocking_number",
    "empathy_reversal",
    "fomo",
    "list_summary",
    "honest_confession",
    "story",
    "office_aruaru",
    "gap_humor",
]

FORMAT_LABELS = {
    "shocking_number": "衝撃の数字型",
    "empathy_reversal": "共感→反転型",
    "fomo": "知らないと損型",
    "list_summary": "まとめ・リスト型",
    "honest_confession": "ぶっちゃけ告白型",
    "story": "ストーリー型",
    "office_aruaru": "あるある型",
    "gap_humor": "期待と現実型",
}

TONES = ["皮肉", "自虐", "ドヤ顔", "脱力", "真面目", "ユーモア"]


def _load_prompt() -> str:
    return (PROMPTS_DIR / "tweet_generation.md").read_text(encoding="utf-8")


def _parse_json_response(raw_text: str) -> list[dict] | None:
    """APIレスポンスからJSONを抽出してパースする。"""
    text = raw_text.strip()
    if "```" in text:
        start = text.index("```") + 3
        if text[start:].startswith("json"):
            start += 4
        end = text.index("```", start)
        text = text[start:end].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def generate_tweets(
    themes: list[Theme],
    client: anthropic.Anthropic,
    past_tweets_hint: str = "",
) -> list[ThemeTweets]:
    if not themes:
        return []

    system_prompt = _load_prompt()
    results: list[ThemeTweets] = []

    # テーマ間でフォーマットが被らないようにシャッフルして順番に割り当て
    shuffled_formats = random.sample(BUZZ_FORMATS, len(BUZZ_FORMATS))
    format_index = 0

    for theme in themes:
        # 2つのフォーマットを順番に取得（ラウンドロビン）
        selected_formats = []
        for _ in range(2):
            selected_formats.append(shuffled_formats[format_index % len(shuffled_formats)])
            format_index += 1

        format_names = [FORMAT_LABELS[f] for f in selected_formats]

        # トーンも2つランダムに選ぶ（重複なし）
        selected_tones = random.sample(TONES, 2)

        articles_hint = ""
        if theme.key_articles:
            articles_hint = f"参考記事URL: {', '.join(theme.key_articles)}\n\n"

        history_section = ""
        if past_tweets_hint:
            history_section = f"\n{past_tweets_hint}\n\n"

        user_message = (
            f"以下のテーマでバズる投稿を2本書け。\n\n"
            f"テーマ: {theme.title}\n"
            f"切り口: {theme.summary}\n"
            f"{articles_hint}"
            f"使用するスタイル:\n"
            f"1. {format_names[0]}（format名: {selected_formats[0]}）— トーン: {selected_tones[0]}\n"
            f"2. {format_names[1]}（format名: {selected_formats[1]}）— トーン: {selected_tones[1]}\n\n"
            f"バズらせるための必須条件:\n"
            f"- 1行目は15文字以内で「え？」「マジ？」と思わせるフックにしろ\n"
            f"- 2本の投稿で書き出し・構造・口調を変えろ。同じパターンの繰り返しはNG\n"
            f"- 具体的な数字（時間、コスト、精度）を最低1つ入れろ\n"
            f"- 最後の1行で余韻を残せ。「いいね」ではなく「保存」される投稿を書け\n"
            f"- 普通の会社員（事務職・営業・企画・管理職）が「自分のことだ」と感じるリアルさを入れろ\n"
            f"- 製造業・工場・生産管理の話は禁止。一般のオフィスワーカーに響く内容にしろ\n"
            f"- 2本のうち少なくとも1本は、失敗談・予想外の結末・皮肉を含めろ\n"
            f"- 各投稿は140〜280文字\n"
            f"{history_section}"
        )

        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )

        raw_text = response.content[0].text.strip()
        drafts_data = _parse_json_response(raw_text)

        if drafts_data is None:
            logger.warning("JSON解析失敗、再試行中: %s", theme.title)
            response = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=2048,
                system=system_prompt + "\n\n必ず有効なJSONのみを出力してください。説明文は不要です。",
                messages=[{"role": "user", "content": user_message}],
            )
            raw_text = response.content[0].text.strip()
            drafts_data = _parse_json_response(raw_text)

            if drafts_data is None:
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
