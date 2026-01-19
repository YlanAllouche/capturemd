#!/usr/bin/env python3
# url_processor.py

import sys
import os
import re
import uuid
import pyperclip
from urllib.parse import urlparse, parse_qs
import yaml
from pathlib import Path
import subprocess
import json
from datetime import datetime

from .paths import (
    MARKDOWN_DIR, YOUTUBE_DIR, GITHUB_DIR, REDDIT_DIR,
    STEAM_DIR, HN_DIR, DEFAULT_DIR
)

# Templates directory (still local to this file)
TEMPLATES_DIR = Path(__file__).parent / "templates"

# Ensure directories exist
for directory in [YOUTUBE_DIR, GITHUB_DIR, REDDIT_DIR, STEAM_DIR, HN_DIR, DEFAULT_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Ensure directories exist
for directory in [YOUTUBE_DIR, GITHUB_DIR, REDDIT_DIR, STEAM_DIR, HN_DIR, DEFAULT_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

def extract_url_from_share_param(url):
    """
    Extract the actual URL from a share/redirect URL's 'url' parameter.
    
    Args:
        url (str): The share/redirect URL
        
    Returns:
        str or None: The extracted URL if found and valid, None otherwise
    """
    try:
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        
        if 'url' in query_params:
            extracted_url = query_params['url'][0]
            # Validate that we got a proper URL
            result = urlparse(extracted_url)
            if all([result.scheme, result.netloc]):
                return extracted_url
    except (ValueError, IndexError, KeyError):
        pass
    
    return None


def is_youtube_share_url(url):
    """
    Check if URL is a YouTube share/redirect URL.
    
    YouTube mobile share URLs have formats like:
    - https://youtube.com/redirect?url=<actual_youtube_url>
    - https://www.youtube.com/oembed?format=xml&url=<actual_youtube_url>
    
    These URLs contain the actual video URL in the 'url' query parameter,
    which may be URL-encoded.
    """
    try:
        parsed_url = urlparse(url)
        
        # Check if it's a YouTube redirect or oEmbed domain
        if parsed_url.netloc in ['youtube.com', 'www.youtube.com']:
            # Check for both /redirect and /oembed paths
            if parsed_url.path in ['/redirect', '/oembed']:
                # Extract the URL from the 'url' parameter
                extracted_url = extract_url_from_share_param(url)
                if extracted_url:
                    # Recursively check if the extracted URL is a YouTube video
                    return is_youtube_video(extracted_url)
    except (ValueError, TypeError):
        pass
    
    return False


def is_youtube_video(url):
    """Check if URL is a YouTube video."""
    # First check if it's a share/redirect URL
    if is_youtube_share_url(url):
        return True
    
    parsed_url = urlparse(url)
    youtube_domains = ['youtube.com', 'www.youtube.com', 'm.youtube.com', 'youtu.be']
    
    if parsed_url.netloc in youtube_domains:
        if parsed_url.netloc == 'youtu.be':
            # Short URL format
            return parsed_url.path.strip('/') != ''
        else:
            # Standard URL format with /watch path
            if parsed_url.path == '/watch' and 'v' in parse_qs(parsed_url.query):
                return True
            # YouTube shorts format
            elif parsed_url.path.startswith('/shorts/') and parsed_url.path.strip('/shorts/') != '':
                return True
    return False

def is_github_repo(url):
    """Check if URL is a GitHub repository."""
    parsed_url = urlparse(url)
    if parsed_url.netloc in ['github.com', 'www.github.com']:
        path_parts = parsed_url.path.strip('/').split('/')
        # Check if path has format: username/repository
        return len(path_parts) >= 2 and not path_parts[0].startswith('.') and not path_parts[1].startswith('.')
    return False
    
def is_reddit_thread(url):
    """Check if URL is a Reddit thread."""
    parsed_url = urlparse(url)
    if parsed_url.netloc in ['reddit.com', 'www.reddit.com', 'old.reddit.com']:
        path_parts = parsed_url.path.strip('/').split('/')
        # Check if path has format: r/subreddit/comments/id/...
        return (len(path_parts) >= 4 and 
                path_parts[0] == 'r' and 
                path_parts[2] == 'comments' and 
                path_parts[3] != '')
    return False

def is_steam_game(url):
    """Check if URL is a Steam game."""
    parsed_url = urlparse(url)
    if parsed_url.netloc in ['store.steampowered.com', 'www.store.steampowered.com']:
        path_parts = parsed_url.path.strip('/').split('/')
        # Check if path has format: app/appid/...
        return (len(path_parts) >= 2 and 
                path_parts[0] == 'app' and 
                path_parts[1].isdigit())
    return False

def is_hackernews_item(url):
    """Check if URL is a Hacker News item."""
    parsed_url = urlparse(url)
    if parsed_url.netloc in ['news.ycombinator.com', 'www.news.ycombinator.com']:
        # Check if path has format: item?id=...
        return parsed_url.path == '/item' and 'id' in parse_qs(parsed_url.query)
    return False

def is_google_search(url):
    """Check if URL is a Google search query."""
    parsed_url = urlparse(url)
    if parsed_url.netloc in ['google.com', 'www.google.com']:
        # Check if path is /search and query has q parameter
        return parsed_url.path == '/search' and 'q' in parse_qs(parsed_url.query)
    return False

def get_youtube_video_id(url):
    """Extract YouTube video ID from URL, including share/redirect URLs."""
    # First check if it's a share/redirect URL and extract the actual URL
    extracted_url = extract_url_from_share_param(url)
    if extracted_url:
        url = extracted_url
    
    parsed_url = urlparse(url)
    if parsed_url.netloc == 'youtu.be':
        return parsed_url.path.strip('/')
    elif parsed_url.path.startswith('/shorts/'):
        # Handle YouTube shorts format - remove /shorts/ prefix and trailing slash
        return parsed_url.path[8:].strip('/')
    else:
        return parse_qs(parsed_url.query)['v'][0]

def get_github_repo_info(url):
    """Extract GitHub repository info from URL."""
    parsed_url = urlparse(url)
    path_parts = parsed_url.path.strip('/').split('/')
    return {
        'owner': path_parts[0],
        'repo': path_parts[1]
    }
    
def get_reddit_thread_info(url):
    """Extract Reddit thread info from URL."""
    parsed_url = urlparse(url)
    path_parts = parsed_url.path.strip('/').split('/')
    return {
        'subreddit': path_parts[1],
        'thread_id': path_parts[3]
    }

def get_steam_game_info(url):
    """Extract Steam game info from URL."""
    parsed_url = urlparse(url)
    path_parts = parsed_url.path.strip('/').split('/')
    return {
        'app_id': path_parts[1],
        'name': path_parts[2] if len(path_parts) > 2 else ''
    }

def get_hackernews_item_info(url):
    """Extract Hacker News item info from URL."""
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    return {
        'item_id': query_params['id'][0]
    }

def check_existing_note(locator, directory):
    """
    Check if a note with the given locator already exists.
    
    Returns:
        tuple: (exists: bool, file_path: str or None) where file_path is the path
               to the existing note if it exists, None otherwise.
    """
    for file_path in directory.glob("*.md"):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if f"locator: {locator}" in content:
                return True, str(file_path)
    return False, None

def create_initial_note(url, note_type, tags=None):
    """
    Create an initial markdown note based on URL type.
    
    Args:
        url (str): URL to process
        note_type (str): Type of note to create
        tags (List[str], optional): List of tags to add to the note
    
    Returns:
        str: Path to the created note, or path to existing note if duplicate found
    """
    note_id = str(uuid.uuid4())
    
    # Default tags if none provided
    if tags is None:
        tags = ["inbox"]
    
    # Format tags as YAML list
    tags_yaml = yaml.dump({"tags": tags}, default_flow_style=False).strip()
    tags_yaml = tags_yaml.replace("tags:", "tags:")
    
    if note_type == "youtube":
        video_id = get_youtube_video_id(url)
        
        # Check if a note with this video ID already exists
        exists, existing_file = check_existing_note(video_id, YOUTUBE_DIR)
        if exists:
            print(f"Note for YouTube video {video_id} already exists at: {existing_file}")
            return existing_file
        
        # Create initial note
        note_path = YOUTUBE_DIR / f"{note_id}.md"
        content = f"""---
id: {note_id}
locator: {video_id}
parsed: false
scope: youtube
{tags_yaml}
---
"""
        with open(note_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return note_path
    
    elif note_type == "github":
        repo_info = get_github_repo_info(url)
        repo_id = f"{repo_info['owner']}/{repo_info['repo']}"
        
        # Check if a note with this repo ID already exists
        exists, existing_file = check_existing_note(repo_id, GITHUB_DIR)
        if exists:
            print(f"Note for GitHub repo {repo_id} already exists at: {existing_file}")
            return existing_file
        
        # Create initial note
        note_path = GITHUB_DIR / f"{note_id}.md"
        content = f"""---
id: {note_id}
locator: {repo_id}
parsed: false
scope: github
{tags_yaml}
---
"""
        with open(note_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return note_path
    
    elif note_type == "reddit":
        thread_info = get_reddit_thread_info(url)
        thread_id = thread_info['thread_id']
        subreddit = thread_info['subreddit']
        
        # Check if a note with this thread ID already exists
        exists, existing_file = check_existing_note(thread_id, REDDIT_DIR)
        if exists:
            print(f"Note for Reddit thread {thread_id} already exists at: {existing_file}")
            return existing_file
        
        # Create initial note
        note_path = REDDIT_DIR / f"{note_id}.md"
        content = f"""---
id: {note_id}
locator: {thread_id}
subreddit: {subreddit}
parsed: false
scope: reddit
{tags_yaml}
---
"""
        with open(note_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return note_path
    
    elif note_type == "steam":
        game_info = get_steam_game_info(url)
        app_id = game_info['app_id']
        
        # Check if a note with this app ID already exists
        exists, existing_file = check_existing_note(app_id, STEAM_DIR)
        if exists:
            print(f"Note for Steam game {app_id} already exists at: {existing_file}")
            return existing_file
        
        # Create initial note
        note_path = STEAM_DIR / f"{note_id}.md"
        content = f"""---
id: {note_id}
locator: {app_id}
parsed: false
scope: steam
{tags_yaml}
---
"""
        with open(note_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return note_path
    
    elif note_type == "hackernews":
        item_info = get_hackernews_item_info(url)
        item_id = item_info['item_id']
        
        # Check if a note with this item ID already exists
        exists, existing_file = check_existing_note(item_id, HN_DIR)
        if exists:
            print(f"Note for Hacker News item {item_id} already exists at: {existing_file}")
            return existing_file
        
        # Create initial note
        note_path = HN_DIR / f"{note_id}.md"
        content = f"""---
id: {note_id}
locator: {item_id}
parsed: false
scope: hackernews
{tags_yaml}
---
"""
        with open(note_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return note_path
    
    else:  # default
        note_path = DEFAULT_DIR / f"{note_id}.md"
        content = f"""---
id: {note_id}
url: {url}
parsed: false
scope: default
{tags_yaml}
---
"""
        with open(note_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return note_path

def process_url(url, tags=None):
    """
    Process a URL and create appropriate markdown note.
    
    Args:
        url (str): URL to process
        tags (List[str], optional): List of tags to add to the note
        
    Returns:
        str: Path to the created note (or existing note if duplicate), 
             special string "google_search_processed" for Google searches,
             or None if failed
    """
    if not url:
        try:
            url = pyperclip.paste()
            print(f"Using URL from clipboard: {url}")
        except:
            print("Failed to get URL from clipboard.")
            return
        
        if not url:
            print("No URL provided and clipboard is empty.")
            return
    
    # Validate URL
    try:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            print(f"Invalid URL: {url}")
            return
    except:
        print(f"Invalid URL: {url}")
        return
    
    # Check for Google search query
    if is_google_search(url):
        print(f"Processing Google search query: {url}")
        from capturemd.capture_google import capture_google_search
        success = capture_google_search(url)
        if success:
            # Return a special indicator for Google search queries
            # This isn't a real path but a signal that processing succeeded
            return "google_search_processed"
        return None
    
    # Determine URL type and create note
    if is_youtube_video(url):
        print(f"Processing YouTube video: {url}")
        note_path = create_initial_note(url, "youtube", tags)
    elif is_github_repo(url):
        print(f"Processing GitHub repository: {url}")
        note_path = create_initial_note(url, "github", tags)
    elif is_reddit_thread(url):
        print(f"Processing Reddit thread: {url}")
        note_path = create_initial_note(url, "reddit", tags)
    elif is_steam_game(url):
        print(f"Processing Steam game: {url}")
        note_path = create_initial_note(url, "steam", tags)
    elif is_hackernews_item(url):
        print(f"Processing Hacker News item: {url}")
        note_path = create_initial_note(url, "hackernews", tags)
    else:
        print(f"Processing generic URL: {url}")
        note_path = create_initial_note(url, "default", tags)
    
    if note_path:
        print(f"Created note: {note_path}")
        return str(note_path)  # Convert Path to str for consistency
    return None

def main():
    # Get URL from arguments or clipboard
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        try:
            url = pyperclip.paste()
        except:
            print("Failed to get URL from clipboard.")
            return
    
    note_path = process_url(url)
    
    # Optionally run the parser for the newly created note
    if note_path and "--parse" in sys.argv:
        parse_unparsed_notes()

def parse_unparsed_notes():
    """Parse all notes with parsed=false."""
    print("Parsing unparsed notes...")
    # This will be implemented in the second script
    # For now, we'll just call it as a subprocess
    parser_script = Path(__file__).parent / "parse_notes.py"
    if parser_script.exists():
        subprocess.run([sys.executable, str(parser_script)])
    else:
        print(f"Parser script not found: {parser_script}")

if __name__ == "__main__":
    main()