![banner](banner.webp)
# capturemd

A personal productivity tool for capturing web content into structured markdown notes with support for video downloads through `yt-dlp`.
Connects to self hosted services like Wallabag and FreshRSS.

## Features

- **Smart URL Capture**: Convert web pages, YouTube videos, GitHub repos, Reddit threads, Hacker News posts, Steam pages, Google searches, and podcasts into markdown
- **Obsidian & Dataview Compatible**: Notes include frontmatter with metadata for querying and organization
- **Jellyfin Integration**: YouTube videos cached as media files with NFO metadata (year as season, video as episode)
- **Episode Reindexing**: Automatically renumbers episodes chronologically after caching for Kodi compatibility
- **Wallabag Integration**: Share content from mobile to Wallabag, sync as markdown notes, visible in Dataview queries
- **Google Search Workflows**: Share search links to Wallabag, process on desktop into markdown inbox
- **Browser Integration**: Map Tridactyl or qutebrowser to capture bookmarks directly
- **FreshRSS Support**: Convert feed items to markdown notes
- **Local Caching**: Cache videos and content for offline access

## Installation

```bash
pip install . # --break-system-packages 
```

## Usage

```bash
# Capture from clipboard
capturemd url

# Capture specific URL
capturemd url "https://example.com"

# Parse all notes
capturemd parse

# Play cached video
capturemd play "video_id"
```
