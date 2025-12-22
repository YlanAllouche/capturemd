#!/usr/bin/env python3
# Temporary NFO creation module

import os
import re
from datetime import datetime
from pathlib import Path

import yaml


def extract_frontmatter(file_path):
    """Extract YAML frontmatter from a markdown file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        match = re.search(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
        if match:
            frontmatter = yaml.safe_load(match.group(1))
            return frontmatter
        return None
    except Exception as e:
        print(f"Error extracting frontmatter from {file_path}: {e}")
        return None


def create_show_nfo(channel_name, channel_id=None):
    """Create an NFO file for a YouTube channel (show) in the Kodi NFO format."""
    try:
        show_dir = Path.home() / "Media" / "videos" / "yt" / channel_name
        show_dir.mkdir(parents=True, exist_ok=True)

        nfo_path = show_dir / "tvshow.nfo"

        if nfo_path.exists():
            print(f"Show NFO already exists for {channel_name}")
            return True

        channel_url = (
            f"https://www.youtube.com/channel/{channel_id}" if channel_id else ""
        )

        nfo_content = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>
<tvshow>
    <title>{channel_name}</title>
    <showtitle>{channel_name}</showtitle>
    <year>{datetime.now().year}</year>
    <premiered>{datetime.now().strftime("%Y-%m-%d")}</premiered>
    <plot>YouTube channel: {channel_name}</plot>
    <genre>YouTube</genre>
    <studio>YouTube</studio>
    <id>{channel_id}</id>
    <uniqueid type="youtube">{channel_id}</uniqueid>
</tvshow>
"""

        with open(nfo_path, "w", encoding="utf-8") as f:
            f.write(nfo_content)

        print(f"Created show NFO file: {nfo_path}")
        return True
    except Exception as e:
        print(f"Error creating show NFO file for {channel_name}: {e}")
        return False


def create_nfo_file(video_id, video_info, create_new_structure=True):
    """Create an NFO file for a YouTube video in the Kodi NFO format."""
    try:
        title = video_info.get("title", "")
        channel = video_info.get("channel", video_info.get("uploader", ""))
        channel_id = video_info.get("channel_id", "")
        description = video_info.get("description", "")
        thumbnail = video_info.get("thumbnail", "")

        upload_date_str = video_info.get("upload_date", "")
        if isinstance(upload_date_str, str) and upload_date_str:
            try:
                date_obj = datetime.strptime(upload_date_str, "%Y%m%d")
                date_formatted = date_obj.strftime("%Y-%m-%d")
                year = date_formatted[:4]
            except ValueError:
                date_formatted = ""
                year = str(datetime.now().year)
        elif hasattr(upload_date_str, "strftime"):
            date_formatted = upload_date_str.strftime("%Y-%m-%d")
            year = str(upload_date_str.year)
        else:
            date_formatted = ""
            year = str(datetime.now().year)

        if create_new_structure:
            nfo_dir = (
                Path.home() / "Media" / "videos" / "yt" 
                / channel.replace("/", "_").replace("\\", "_") 
                / year
            )
            nfo_dir.mkdir(parents=True, exist_ok=True)
            nfo_path = nfo_dir / f"{video_id}.nfo"
        else:
            nfo_path = Path.home() / "Media" / "videos" / "yt" / f"{video_id}.nfo"

        nfo_content = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>
<episodedetails>
    <title>{title}</title>
    <showtitle>{channel}</showtitle>
    <season>{year}</season>
    <aired>{date_formatted}</aired>
    <plot>{description[:500] if description else ''}</plot>
    <studio>YouTube</studio>
    <director>{channel}</director>
    <genre>YouTube</genre>
    <id>{video_id}</id>
    <uniqueid type="youtube">{video_id}</uniqueid>
</episodedetails>
"""

        with open(nfo_path, "w", encoding="utf-8") as f:
            f.write(nfo_content)

        print(f"Created NFO file: {nfo_path}")
        return str(nfo_path)
    except Exception as e:
        print(f"Error creating NFO file for {video_id}: {e}")
        return None
