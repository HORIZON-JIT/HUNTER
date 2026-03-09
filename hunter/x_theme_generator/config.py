import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")

NOTIFICATION_METHOD = os.environ.get("NOTIFICATION_METHOD", "discord")
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")
GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
GMAIL_TO = os.environ.get("GMAIL_TO", "")

RSS_FEEDS = {
    "TechCrunch AI": "https://techcrunch.com/category/artificial-intelligence/feed/",
    "MIT Technology Review": "https://www.technologyreview.com/feed/",
    "Gigazine": "https://gigazine.net/news/rss_2.0/",
    "OpenAI Blog": "https://openai.com/blog/rss.xml",
    "The Verge AI": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
    "CNET Japan": "https://feeds.japan.cnet.com/rss/cnet/all.rdf",
}

ARTICLES_MAX_AGE_HOURS = int(os.environ.get("ARTICLES_MAX_AGE_HOURS", "48"))

OUTPUT_DIR = Path("output")
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
