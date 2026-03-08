from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Article:
    title: str
    summary: str
    link: str
    published: datetime
    source: str


@dataclass
class Theme:
    title: str
    summary: str
    key_articles: list[str] = field(default_factory=list)
    relevance_score: int = 0


@dataclass
class TweetDraft:
    format_name: str
    text: str
    char_count: int


@dataclass
class ThemeTweets:
    theme: Theme
    drafts: list[TweetDraft] = field(default_factory=list)
