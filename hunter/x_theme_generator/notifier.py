import logging
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path

import requests

from hunter.x_theme_generator.config import (
    LINE_NOTIFY_TOKEN,
    GMAIL_ADDRESS,
    GMAIL_APP_PASSWORD,
    GMAIL_TO,
    OUTPUT_DIR,
)
from hunter.x_theme_generator.models import ThemeTweets
from hunter.x_theme_generator.tweet_generator import FORMAT_LABELS

logger = logging.getLogger(__name__)


def _format_results(results: list[ThemeTweets]) -> str:
    lines = []
    lines.append(f"=== X投稿テーマ生成結果 ({datetime.now().strftime('%Y/%m/%d %H:%M')}) ===\n")

    for i, item in enumerate(results, 1):
        theme = item.theme
        lines.append(f"--- テーマ{i}: {theme.title} (関連度: {theme.relevance_score}/100) ---")
        lines.append(f"概要: {theme.summary}\n")

        for j, draft in enumerate(item.drafts, 1):
            label = FORMAT_LABELS.get(draft.format_name, draft.format_name)
            lines.append(f"  投稿案{j} [{label}] ({draft.char_count}文字)")
            lines.append(f"  {draft.text}\n")

    return "\n".join(lines)


def _save_to_file(results: list[ThemeTweets]) -> Path:
    OUTPUT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = OUTPUT_DIR / f"xtheme_{timestamp}.md"

    lines = [f"# X投稿テーマ生成結果\n", f"生成日時: {datetime.now().strftime('%Y/%m/%d %H:%M')}\n"]

    for i, item in enumerate(results, 1):
        theme = item.theme
        lines.append(f"## テーマ{i}: {theme.title}\n")
        lines.append(f"- 関連度スコア: {theme.relevance_score}/100")
        lines.append(f"- 概要: {theme.summary}")
        if theme.key_articles:
            lines.append("- 参考記事:")
            for url in theme.key_articles:
                lines.append(f"  - {url}")
        lines.append("")

        for j, draft in enumerate(item.drafts, 1):
            label = FORMAT_LABELS.get(draft.format_name, draft.format_name)
            lines.append(f"### 投稿案{j} [{label}] ({draft.char_count}文字)\n")
            lines.append(f"```\n{draft.text}\n```\n")

    filepath.write_text("\n".join(lines), encoding="utf-8")
    return filepath


def notify_line(results: list[ThemeTweets]) -> None:
    token = LINE_NOTIFY_TOKEN
    if not token:
        raise ValueError("LINE_NOTIFY_TOKENが設定されていません")

    message = "\n" + _format_results(results)
    # LINE Notifyは1000文字制限があるため分割送信
    chunks = [message[i:i + 999] for i in range(0, len(message), 999)]

    for chunk in chunks:
        resp = requests.post(
            "https://notify-api.line.me/api/notify",
            headers={"Authorization": f"Bearer {token}"},
            data={"message": chunk},
            timeout=30,
        )
        resp.raise_for_status()

    logger.info("LINE Notify送信完了")


def notify_gmail(results: list[ThemeTweets]) -> None:
    if not all([GMAIL_ADDRESS, GMAIL_APP_PASSWORD, GMAIL_TO]):
        raise ValueError("Gmail設定（GMAIL_ADDRESS, GMAIL_APP_PASSWORD, GMAIL_TO）が不足しています")

    body = _format_results(results)
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = f"[HUNTER] X投稿テーマ生成結果 - {datetime.now().strftime('%Y/%m/%d')}"
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = GMAIL_TO

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.send_message(msg)

    logger.info("Gmail送信完了")


def notify(results: list[ThemeTweets], method: str) -> Path:
    filepath = _save_to_file(results)
    logger.info("ファイル保存: %s", filepath)

    if method == "line":
        notify_line(results)
    elif method == "gmail":
        notify_gmail(results)
    else:
        logger.warning("不明な通知方法: %s（ファイル保存のみ実行）", method)

    return filepath
