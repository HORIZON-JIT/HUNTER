import argparse
import logging
import logging.handlers
import signal
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

import anthropic
import schedule

from hunter.x_theme_generator.config import ANTHROPIC_API_KEY, NOTIFICATION_METHOD
from hunter.x_theme_generator.rss_collector import collect_articles
from hunter.x_theme_generator.theme_analyzer import extract_themes
from hunter.x_theme_generator.tweet_generator import generate_tweets, FORMAT_LABELS
from hunter.x_theme_generator.notifier import notify
from hunter.x_theme_generator.history import load_recent_tweets, format_history_for_prompt

logger = logging.getLogger(__name__)

LOG_DIR = Path("logs")


def _setup_logging(to_file: bool = False) -> None:
    """ロギングを設定する。to_file=True でファイル出力も追加。"""
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # コンソール出力
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)

    if to_file:
        LOG_DIR.mkdir(exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            LOG_DIR / "scheduler.log",
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setFormatter(fmt)
        root.addHandler(file_handler)


def _safe_run_pipeline(notify_method: str, dry_run: bool = False, output_only: bool = False) -> None:
    """_run_pipeline を例外安全にラップする。スケジューラーモード用。"""
    start = datetime.now()
    logger.info("===== パイプライン実行開始 =====")
    try:
        _run_pipeline(notify_method, dry_run=dry_run, output_only=output_only)
        elapsed = (datetime.now() - start).total_seconds()
        logger.info("===== パイプライン実行完了（%.1f秒） =====", elapsed)
    except Exception:
        elapsed = (datetime.now() - start).total_seconds()
        logger.error(
            "===== パイプライン実行失敗（%.1f秒） =====\n%s",
            elapsed,
            traceback.format_exc(),
        )


def _run_pipeline(notify_method: str, dry_run: bool = False, output_only: bool = False) -> None:
    """テーマ生成パイプラインを1回実行する。"""
    print(f"\n{'=' * 60}")
    print(f"⏰ 実行開始")
    print(f"{'=' * 60}")

    if not ANTHROPIC_API_KEY:
        print("エラー: ANTHROPIC_API_KEYが設定されていません。")
        return

    # Step 1: RSS収集
    print("📡 RSSフィードからAIニュースを収集中...")
    articles = collect_articles()
    print(f"   {len(articles)}件の記事を取得\n")

    if not articles:
        print("記事が見つかりませんでした。フィードを確認してください。")
        return

    # Step 2: Claude APIでテーマ分析
    print("🤖 Claude APIでトレンド分析中...")
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    themes = extract_themes(articles, client)
    print(f"   {len(themes)}件のテーマを抽出\n")

    if not themes:
        print("テーマを抽出できませんでした。")
        return

    # Step 3: 過去履歴を読み込み＆投稿下書き生成
    print("✍️  投稿下書きを生成中...")
    past_tweets = load_recent_tweets(days=7)
    past_tweets_hint = format_history_for_prompt(past_tweets)
    results = generate_tweets(themes, client, past_tweets_hint=past_tweets_hint)
    total_drafts = sum(len(r.drafts) for r in results)
    print(f"   {total_drafts}本の投稿案を生成\n")

    # Step 4: 出力
    if dry_run:
        print("=" * 60)
        print("【ドライラン】生成結果プレビュー")
        print("=" * 60)
        for i, item in enumerate(results, 1):
            print(f"\n--- テーマ{i}: {item.theme.title} ---")
            print(f"概要: {item.theme.summary}")
            print(f"関連度: {item.theme.relevance_score}/100\n")
            for j, draft in enumerate(item.drafts, 1):
                label = FORMAT_LABELS.get(draft.format_name, draft.format_name)
                print(f"  投稿案{j} [{label}] ({draft.char_count}文字)")
                print(f"  {draft.text}\n")
    else:
        method = notify_method
        if output_only:
            from hunter.x_theme_generator.notifier import _save_to_file
            filepath = _save_to_file(results)
            print(f"💾 ファイル保存完了: {filepath}")
        else:
            print(f"📤 通知送信中（{method}）...")
            filepath = notify(results, method)
            print(f"✅ 完了! 結果を保存・送信しました: {filepath}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="X（Twitter）投稿テーマ自動生成ツール",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="通知を送信せず、標準出力に表示のみ",
    )
    parser.add_argument(
        "--notify",
        choices=["discord", "gmail"],
        default=None,
        help="通知方法を指定（デフォルト: .envのNOTIFICATION_METHOD）",
    )
    parser.add_argument(
        "--output-only",
        action="store_true",
        help="ファイル保存のみ（通知なし）",
    )
    parser.add_argument(
        "--schedule",
        metavar="HH:MM",
        nargs="+",
        help="指定時刻に定期実行（例: --schedule 07:00 20:00）",
    )
    args = parser.parse_args()

    if not ANTHROPIC_API_KEY:
        print("エラー: ANTHROPIC_API_KEYが設定されていません。")
        print(".envファイルまたは環境変数で設定してください。")
        sys.exit(1)

    notify_method = args.notify or NOTIFICATION_METHOD

    if args.schedule:
        # スケジュールモード: ファイルログ有効化
        _setup_logging(to_file=True)
        logger.info("スケジューラー起動")

        # スケジュール登録（例外安全ラッパー経由）
        for t in args.schedule:
            schedule.every().day.at(t).do(
                _safe_run_pipeline, notify_method=notify_method,
                dry_run=args.dry_run, output_only=args.output_only,
            )
            logger.info("毎日 %s に実行予定を登録", t)

        print(f"\n🟢 スケジューラー起動中（Ctrl+C で停止）")
        print(f"   ログ出力先: {LOG_DIR / 'scheduler.log'}")
        next_run = schedule.next_run()
        if next_run:
            print(f"   次回実行: {next_run.strftime('%Y-%m-%d %H:%M')}")

        # Ctrl+C でグレースフルに停止
        def _handle_signal(signum, frame):
            logger.info("スケジューラー停止（シグナル: %s）", signum)
            print("\n\n🔴 スケジューラーを停止しました")
            sys.exit(0)

        signal.signal(signal.SIGINT, _handle_signal)
        signal.signal(signal.SIGTERM, _handle_signal)

        # ハートビート用カウンタ（30秒sleep × 60回 = 30分）
        heartbeat_counter = 0
        HEARTBEAT_INTERVAL = 60  # 30秒 × 60 = 30分

        while True:
            schedule.run_pending()
            time.sleep(30)
            heartbeat_counter += 1
            if heartbeat_counter >= HEARTBEAT_INTERVAL:
                heartbeat_counter = 0
                next_run = schedule.next_run()
                next_str = next_run.strftime('%Y-%m-%d %H:%M') if next_run else "なし"
                logger.info("ハートビート: スケジューラー稼働中 | 次回実行: %s", next_str)
    else:
        # 即時実行モード（従来動作）
        _setup_logging(to_file=False)
        _run_pipeline(notify_method, dry_run=args.dry_run, output_only=args.output_only)


if __name__ == "__main__":
    main()
