![banner](banner.webp)
# capturemd

A personal and very idiosyncratic productivity tool for capturing web content into structured markdown notes with support for video downloads through `yt-dlp`.
Connects to self hosted services like Wallabag and FreshRSS.
Meant to be a replacement to org-capture living outside of Obsidan.

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

### From CLI

```bash
# Capture from clipboard
capturemd url

# Capture specific URL
capturemd url "https://example.com"
```

## From browser

Similar as from the CLi, this can be called from Qutebrowser/Tridactyl withsomething like:

### Tridactyl

Add to `~/.tridactylrc`:

``` bash
# Capture current page
bind ,b composite get_current_url | js -p tri.excmds.shellescape(JS_ARG).then(url => tri.excmds.exclaim_quiet('notify-send Captured && ~/.local/bin/capturemd url ' + url))
# Capture "hinted" link 
bind ,B hint -qW js -p tri.excmds.shellescape(JS_ARG).then(url => tri.excmds.exclaim('notify-send "Captured target link" && ~/.local/bin/capturemd url ' + url))
```


### Qutebrowser

Add to `~/.config/qutebrowser/config.py`:

``` python
# Capture current page
c.bind(',b', 'spawn capturemd url {url}')
# Capture "hinted" link
c.bind(',B', 'spawn capturemd url {hint-url}')
```

## From Android

- wallabag is the main way I get data out of my Android phone (although it should work on iOS)
- sharing a link to wallabag will eventually have `capturemd` process it on a cron
- one off notes are entered as google search in a new tab and added into the "$SHARE/notes/browser_notes.md" file

## Parsing

Parse from external services into markdown

```bash
capturemd parse-rss # parses the starred items
capturemd parse-wallabag # parses new entries from wallabag and tag them as parsed if meant to stay there, otherwise removes the entry
```

when parsed from external sources or manually from a URL, notes are initially bare and only specifiy a url/platform-specific UUID (like the ID of a youtube video).
Then when runnin `parse` the script contacts the appropriate server and writes down the information.


```bash
# Parse all notes
capturemd parse
```
