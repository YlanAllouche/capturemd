#!/usr/bin/env python3

import os
from pathlib import Path

CAPTUREMD_SHARE_BASE = os.getenv("CAPTUREMD_SHARE_BASE", str(Path.home() / "share"))
CAPTUREMD_MEDIA_BASE = os.getenv("CAPTUREMD_MEDIA_BASE", str(Path.home() / "Media"))

SHARE_PATH = Path(CAPTUREMD_SHARE_BASE)
MEDIA_PATH = Path(CAPTUREMD_MEDIA_BASE)

MARKDOWN_DIR = SHARE_PATH / "notes" / "resource"

NOTES_RESOURCE_DIR = MARKDOWN_DIR
YOUTUBE_DIR = MARKDOWN_DIR / "youtube"
YOUTUBE_NOTES_DIR = MARKDOWN_DIR / "youtube"
GITHUB_DIR = MARKDOWN_DIR / "github"
REDDIT_DIR = MARKDOWN_DIR / "reddit"
STEAM_DIR = MARKDOWN_DIR / "steam"
HN_DIR = MARKDOWN_DIR / "hn"
DEFAULT_DIR = MARKDOWN_DIR / "bookmark"
BOOKMARK_NOTES_DIR = MARKDOWN_DIR / "bookmark"
PODCAST_DIR = MARKDOWN_DIR / "podcast"
PODCAST_NOTES_DIR = MARKDOWN_DIR / "podcast"

TOPIC_LANG_DIR = SHARE_PATH / "notes" / "topic" / "lang"

YOUTUBE_CACHE_DIR = MEDIA_PATH / "videos" / "yt"
PODCAST_CACHE_DIR = MEDIA_PATH / "podcasts"

BROWSER_NOTES_FILE = SHARE_PATH / "notes" / "browser_notes.md"


def ensure_directories():
    """Create all required directories if they don't exist."""
    directories = [
        MARKDOWN_DIR,
        YOUTUBE_DIR,
        YOUTUBE_NOTES_DIR,
        GITHUB_DIR,
        REDDIT_DIR,
        STEAM_DIR,
        HN_DIR,
        DEFAULT_DIR,
        BOOKMARK_NOTES_DIR,
        PODCAST_DIR,
        PODCAST_NOTES_DIR,
        TOPIC_LANG_DIR,
        YOUTUBE_CACHE_DIR,
        PODCAST_CACHE_DIR,
    ]
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
