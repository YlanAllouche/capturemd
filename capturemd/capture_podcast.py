#!/usr/bin/env python3
# capture_podcast.py - Handle podcast URLs

import os
import uuid
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

# Define the podcast directory
PODCAST_DIR = Path.home() / "share" / "notes" / "resource" / "podcast"
# Define the podcast cache directory
PODCAST_CACHE_DIR = Path.home() / "Media" / "podcasts"

# Ensure directories exist
PODCAST_DIR.mkdir(parents=True, exist_ok=True)
PODCAST_CACHE_DIR.mkdir(parents=True, exist_ok=True)

def create_podcast_note(
    url: str,
    title: str,
    channel: str,
    description: str = "",
    published_date: str = "",
    tags: List[str] = None,
    duration: str = "",
    audio_file: str = ""
) -> Optional[str]:
    """
    Create a podcast note with the provided metadata.
    
    Args:
        url (str): URL of the podcast episode
        title (str): Title of the podcast episode
        channel (str): Name of the podcast channel
        description (str): Description of the podcast episode
        published_date (str): Publication date of the episode (ISO format preferred)
        tags (List[str]): List of tags for categorization
        duration (str): Duration of the podcast episode (e.g., "1:30:45")
        audio_file (str): Path to the cached audio file
        
    Returns:
        Optional[str]: Path to the created note file, or None if failed
    """
    if not url or not title or not channel:
        print("URL, title, and channel are required.")
        return None
    
    # Generate a unique ID
    note_id = str(uuid.uuid4())
    
    # Create the note path
    note_path = PODCAST_DIR / f"{note_id}.md"
    
    # Prepare tags if provided
    if not tags:
        tags = ["inbox"]
    
    # Current date
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    # Prepare the frontmatter
    frontmatter = {
        "id": note_id,
        "url": url,
        "title": title,
        "channel": channel,
        "description": description,
        "parsed": True,  # Always set to true as we're providing all metadata
        "scope": "podcast",
        "class": ["resource", "bookmark", "podcast"],
        "date": current_date,
        "tags": tags,
        "cache": True,  # Default to caching podcasts
    }
    
    # Add published_date only if provided
    if published_date:
        frontmatter["published_date"] = published_date
    
    # Add duration if provided
    if duration:
        frontmatter["duration"] = duration
    
    # Add audio_url if provided (this is the original source URL for the audio)
    if audio_file:
        frontmatter["audio_url"] = audio_file
    
    # Create the content
    yaml_frontmatter = yaml.dump(frontmatter, default_flow_style=False)
    content = f"---\n{yaml_frontmatter}---\n\n{description}"
    
    # Write to file
    try:
        with open(note_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Created podcast note: {note_path}")
        return str(note_path)
    except Exception as e:
        print(f"Error creating podcast note: {e}")
        return None

def process_podcast(
    url: str,
    title: str,
    channel: str,
    description: str = "",
    published_date: str = "",
    tags: List[str] = None,
    duration: str = "",
    audio_file: str = ""
) -> str:
    """
    Process a podcast URL and create a note.
    
    Args:
        url (str): URL of the podcast episode
        title (str): Title of the podcast episode
        channel (str): Name of the podcast channel
        description (str): Description of the podcast episode
        published_date (str): Publication date of the episode (ISO format preferred)
        tags (List[str]): List of tags for categorization
        duration (str): Duration of the podcast episode (e.g., "1:30:45")
        audio_file (str): Path to the cached audio file
        
    Returns:
        str: Path to the created note, or empty string if failed
    """
    print(f"Processing podcast: {title} ({channel})")
    
    # Create the podcast note
    note_path = create_podcast_note(
        url=url,
        title=title,
        channel=channel,
        description=description,
        published_date=published_date,
        tags=tags,
        duration=duration,
        audio_file=audio_file
    )
    
    if note_path:
        return note_path
    return ""


def download_podcast(url: str, note_id: str) -> Optional[str]:
    """
    Download a podcast episode and save it to the cache directory.
    
    Args:
        url (str): URL of the podcast episode
        note_id (str): Unique ID for the podcast note
        
    Returns:
        Optional[str]: Path to the downloaded file, or None if failed
    """
    try:
        # Ensure the cache directory exists
        PODCAST_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        
        # Output file path based on note ID
        output_path = PODCAST_CACHE_DIR / f"{note_id}.%(ext)s"
        
        # Use yt-dlp to download the podcast
        import subprocess
        
        cmd = [
            'yt-dlp',
            url,
            '-o', str(output_path),
            '--extract-audio',  # Extract audio
            '--audio-format', 'mp3',  # Convert to mp3
            '--add-metadata',  # Add metadata
            '--embed-thumbnail',  # Embed thumbnail in audio file if available
            '--no-playlist',  # Don't download playlists
        ]
        
        print(f"Downloading podcast from {url}")
        subprocess.run(cmd, check=True)
        
        # Find the downloaded file
        for file_path in PODCAST_CACHE_DIR.glob(f"{note_id}.*"):
            print(f"Downloaded podcast to {file_path}")
            return str(file_path)
        
        return None
    except Exception as e:
        print(f"Error downloading podcast {url}: {e}")
        return None