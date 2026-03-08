import argparse
import logging
import sys

import anthropic

from hunter.x_theme_generator.config import ANTHROPIC_API_KEY, NOTIFICATION_METHOD
from hunter.x_theme_generator.rss_collector import collect_articles
from hunter.x_theme_generator.theme_analyzer import extract_themes
from hunter.x_theme_generator.tweet_generator import generate_tweets, FORMAT_LABELS
from hunter.x_theme_generator.notifier import notify

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


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
    args = parser.parse_args()

    if not ANTHROPIC_API_KEY:
        print("エラー: ANTHROPIC_API_KEYが設定されていません。")
        print(".envファイルまたは環境変数で設定してください。")
        sys.exit(1)

    # Step 1: RSS収集
    print("📡 RSSフィードからAIニュースを収集中...")
    articles = collect_articles()
    print(f"   {len(articles)}件の記事を取得\n")

    if not articles:
        print("記事が見つかりませんでした。フィードを確認してください。")
        sys.exit(0)

    # Step 2: Claude APIでテーマ分析
    print("🤖 Claude APIでトレンド分析中...")
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    themes = extract_themes(articles, client)
    print(f"   {len(themes)}件のテーマを抽出\n")

    if not themes:
        print("テーマを抽出できませんでした。")
        sys.exit(0)

    # Step 3: 投稿下書き生成
    print("✍️  投稿下書きを生成中...")
    results = generate_tweets(themes, client)
    total_drafts = sum(len(r.drafts) for r in results)
    print(f"   {total_drafts}本の投稿案を生成\n")

    # Step 4: 出力
    if args.dry_run:
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
        method = args.notify or NOTIFICATION_METHOD
        if args.output_only:
            from hunter.x_theme_generator.notifier import _save_to_file
            filepath = _save_to_file(results)
            print(f"💾 ファイル保存完了: {filepath}")
        else:
            print(f"📤 通知送信中（{method}）...")
            filepath = notify(results, method)
            print(f"✅ 完了! 結果を保存・送信しました: {filepath}")


if __name__ == "__main__":
    main()
