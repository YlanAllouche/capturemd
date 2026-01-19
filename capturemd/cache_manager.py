#!/usr/bin/env python3

import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

import yaml

from .episode_indexer import (force_reindex_season_episodes,
                              reindex_season_episodes)
from .paths import (PODCAST_CACHE_DIR, PODCAST_NOTES_DIR, YOUTUBE_CACHE_DIR,
                    YOUTUBE_NOTES_DIR)

try:
    from capturemd.error_logger import log_error, log_subprocess_error
except ImportError:
    from error_logger import log_error, log_subprocess_error


def create_show_nfo(channel_name, channel_id=None):
    """Create an NFO file for a YouTube channel (show) in the Kodi NFO format."""
    try:
        # Create the show directory if it doesn't exist
        show_dir = YOUTUBE_CACHE_DIR / channel_name
        show_dir.mkdir(parents=True, exist_ok=True)

        nfo_path = show_dir / "tvshow.nfo"

        # Skip if the file already exists
        if nfo_path.exists():
            print(f"Show NFO already exists for {channel_name}")
            return True

        # Create basic show NFO
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


        # Write the NFO file
        with open(nfo_path, "w", encoding="utf-8") as f:
            f.write(nfo_content)

        print(f"Created show NFO file: {nfo_path}")
        return True
    except Exception as e:
        print(f"Error creating show NFO file for {channel_name}: {e}")
        return False


def create_nfo_file(video_id, video_info, create_new_structure=True):
    """Create an NFO file for a YouTube video in the Kodi NFO format.

    If create_new_structure is True, creates the file in a show/season folder structure.
    Otherwise, creates it in the root cache directory.
    """
    try:
        # Extract relevant information from video_info
        title = video_info.get("title", "")
        channel = video_info.get("channel", video_info.get("uploader", ""))
        channel_id = video_info.get("channel_id", "")
        description = video_info.get("description", "")
        thumbnail = video_info.get("thumbnail", "")

        # Format the date
        upload_date_str = video_info.get("upload_date", "")
        if isinstance(upload_date_str, str) and upload_date_str:
            try:
                date_obj = datetime.strptime(upload_date_str, "%Y%m%d")
                date_formatted = date_obj.strftime("%Y-%m-%d")
                year = date_formatted[:4]
            except ValueError:
                date_formatted = ""
                year = str(
                    datetime.now().year
                )  # Default to current year if we can't parse
        elif hasattr(upload_date_str, "strftime"):  # datetime.date object
            date_formatted = upload_date_str.strftime("%Y-%m-%d")
            year = str(upload_date_str.year)
        else:
            date_formatted = ""
            year = str(datetime.now().year)  # Default to current year

        # Format the duration in seconds
        duration = int(video_info.get("duration", 0))

        # Sanitize channel name for folder structure
        safe_channel = (
            channel.replace("/", "_")
            .replace("\\", "_")
            .replace("?", "_")
            .replace("*", "_")
        )
        safe_channel = (
            safe_channel.replace(":", "_")
            .replace('"', "_")
            .replace("<", "_")
            .replace(">", "_")
        )

        if create_new_structure and safe_channel and year:
            # Create show and season directories
            show_dir = YOUTUBE_CACHE_DIR / safe_channel
            season_dir = show_dir / year

            # Make sure the directories exist
            season_dir.mkdir(parents=True, exist_ok=True)

            # Create show NFO if it doesn't exist
            create_show_nfo(safe_channel, channel_id)

            # Set the episode NFO path
            nfo_path = season_dir / f"{video_id}.nfo"

            # Create the NFO content in TV show episode format
            nfo_content = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>
<episodedetails>
    <title>{title}</title>
    <showtitle>{channel}</showtitle>
    <season>{year}</season>
    <aired>{date_formatted}</aired>
    <premiered>{date_formatted}</premiered>
    <plot>{description}</plot>
    <runtime>{duration // 60}</runtime>
    <thumb>{thumbnail}</thumb>
    <id>{video_id}</id>
    <uniqueid type="youtube">{video_id}</uniqueid>
    <director>{channel}</director>
    <genre>YouTube</genre>
    <source>YouTube</source>
    <studio>{channel}</studio>
    <dateadded>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</dateadded>
    <url>https://www.youtube.com/watch?v={video_id}</url>
</episodedetails>
"""
        else:
            # Use the old structure (flat directory)
            nfo_path = YOUTUBE_CACHE_DIR / f"{video_id}.nfo"

            # Create the NFO content in movie format for backward compatibility
            nfo_content = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>
<movie>
    <title>{title}</title>
    <originaltitle>{title}</originaltitle>
    <userrating>{video_info.get('average_rating', 0)}</userrating>
    <year>{year}</year>
    <director>{channel}</director>
    <premiered>{date_formatted}</premiered>
    <dateadded>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</dateadded>
    <plot>{description}</plot>
    <runtime>{duration // 60}</runtime>
    <thumb>{thumbnail}</thumb>
    <source>YouTube</source>
    <id>{video_id}</id>
    <genre>YouTube</genre>
    <tag>{video_info.get('categories', ['YouTube'])[0] if video_info.get('categories') else 'YouTube'}</tag>
    <studio>{channel}</studio>
    <trailer>plugin://plugin.video.youtube/play/?video_id={video_id}</trailer>
    <url>https://www.youtube.com/watch?v={video_id}</url>
</movie>
"""

        # Write the NFO file
        with open(nfo_path, "w", encoding="utf-8") as f:
            f.write(nfo_content)

        print(f"Created NFO file: {nfo_path}")
        return True, nfo_path
    except Exception as e:
        print(f"Error creating NFO file for {video_id}: {e}")
        log_error(
            context={
                "operation": "create_nfo_file",
                "entry_id": video_id,
                "file": str(nfo_path) if 'nfo_path' in locals() else "unknown"
            },
            error=e,
            error_type="file_io_error"
        )
        return False, None


def extract_frontmatter(file_path):
    """Extract the YAML frontmatter from a markdown file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Extract YAML frontmatter between --- delimiters
        frontmatter_match = re.search(r"^---\n(.*?)\n---", content, re.DOTALL)
        if frontmatter_match:
            yaml_text = frontmatter_match.group(1)
            frontmatter = yaml.safe_load(yaml_text)
            return frontmatter
        return None
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None


def get_youtube_cached_ids():
    """Get a list of YouTube video IDs from cached files."""
    if not YOUTUBE_CACHE_DIR.exists():
        print(f"YouTube cache directory {YOUTUBE_CACHE_DIR} does not exist.")
        return []

    video_ids = set()
    # Look for videos recursively in all subdirectories
    for ext in [".mp4", ".mkv", ".webm"]:
        # Look in root directory first
        for file_path in YOUTUBE_CACHE_DIR.glob(f"*{ext}"):
            if file_path.is_file():
                # Extract the video ID from the filename (remove extension)
                video_id = file_path.stem
                video_ids.add(video_id)

        # Then look in all subdirectories
        for file_path in YOUTUBE_CACHE_DIR.glob(f"**/*{ext}"):
            if file_path.is_file() and file_path.parent != YOUTUBE_CACHE_DIR:
                # Extract the video ID from the filename (remove extension)
                video_id = file_path.stem
                video_ids.add(video_id)

    return video_ids


def download_youtube_video(video_id, use_tv_structure=True):
    """
    Download a YouTube video using yt-dlp with metadata, chapters, and subtitles.

    Args:
        video_id (str): YouTube video ID
        use_tv_structure (bool): Whether to use TV show folder structure (channel/year)
    """
    try:
        print(f"Downloading YouTube video: {video_id}")

        # Make sure the cache directory exists
        YOUTUBE_CACHE_DIR.mkdir(parents=True, exist_ok=True)

        # First get the video information as JSON
        json_cmd = [
            "yt-dlp",
            f"https://www.youtube.com/watch?v={video_id}",
            "--dump-json",
            "--no-playlist",
        ]

        print("Getting video metadata...")
        json_result = subprocess.run(
            json_cmd, capture_output=True, text=True, check=True
        )
        video_info = json.loads(json_result.stdout)

        # Extract channel and date information
        channel = video_info.get("channel", video_info.get("uploader", ""))
        upload_date_data = video_info.get("upload_date", "")

        # Handle different types of upload_date (string or datetime.date)
        if isinstance(upload_date_data, str) and upload_date_data:
            year = upload_date_data[:4]
        elif hasattr(upload_date_data, "year"):  # datetime.date object
            year = str(upload_date_data.year)
        else:
            year = str(datetime.now().year)

        # Sanitize channel name for folder structure
        safe_channel = (
            channel.replace("/", "_")
            .replace("\\", "_")
            .replace("?", "_")
            .replace("*", "_")
        )
        safe_channel = (
            safe_channel.replace(":", "_")
            .replace('"', "_")
            .replace("<", "_")
            .replace(">", "_")
        )

        if use_tv_structure and safe_channel and year:
            # Create show and season directories
            show_dir = YOUTUBE_CACHE_DIR / safe_channel
            season_dir = show_dir / year

            # Make sure the directories exist
            season_dir.mkdir(parents=True, exist_ok=True)

            # Write the NFO file using the TV show structure
            success, nfo_path = create_nfo_file(
                video_id, video_info, create_new_structure=True
            )

            # Define output path for TV structure
            output_template = f"{season_dir}/%(id)s.%(ext)s"
        else:
            # Use the flat structure
            success, nfo_path = create_nfo_file(
                video_id, video_info, create_new_structure=False
            )
            output_template = f"{YOUTUBE_CACHE_DIR}/%(id)s.%(ext)s"

        # Construct the yt-dlp command with additional features
        # Try with subtitles first
        cmd = [
            "yt-dlp",
            f"https://www.youtube.com/watch?v={video_id}",
            "-o",
            output_template,
            "--format",
            "bestvideo[height<=720]+bestaudio/best[height<=720]",
            "--merge-output-format",
            "mp4",
            "--add-metadata",  # Add metadata to the video file
            "--write-auto-subs",  # Download auto-generated subtitles if available
            "--write-subs",  # Download subtitles if available
            "--sub-langs",
            "en.*",  # Prefer English subtitles
            "--embed-subs",  # Embed subtitles in the video file
            "--embed-chapters",  # Embed chapters in the video file
            "--convert-subs",
            "srt",  # Convert subtitles to SRT format
        ]

        # Run yt-dlp as a subprocess
        print("Attempting to download video with subtitles...")
        print(cmd)
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"Successfully downloaded video with subtitles: {video_id}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Download with subtitles failed: {e}")
            print("Retrying without subtitles...")

            # Fall back to downloading without subtitles
            cmd_fallback = [
                "yt-dlp",
                f"https://www.youtube.com/watch?v={video_id}",
                "-o",
                output_template,
                "--format",
                "bestvideo[height<=720]+bestaudio/best[height<=720]",
                "--merge-output-format",
                "mp4",
                "--add-metadata",  # Add metadata to the video file
                "--embed-chapters",  # Embed chapters in the video file
            ]

            print("Retrying with fallback command (no subtitles)...")
            print(cmd_fallback)
            try:
                result = subprocess.run(cmd_fallback, capture_output=True, text=True, check=True)
                print(f"Successfully downloaded video (without subtitles): {video_id}")
                return True
            except subprocess.CalledProcessError as fallback_error:
                print(
                    f"Error downloading video {video_id} (fallback also failed): {fallback_error}"
                )
                log_subprocess_error(
                    context={
                        "operation": "cache_download",
                        "entry_id": video_id,
                        "video_url": f"https://www.youtube.com/watch?v={video_id}"
                    },
                    command=cmd_fallback,
                    exit_code=fallback_error.returncode,
                    stdout=fallback_error.stdout if fallback_error.stdout else "",
                    stderr=fallback_error.stderr if fallback_error.stderr else ""
                )
                return False
    except subprocess.CalledProcessError as e:
        print(f"Error downloading video {video_id}: {e}")
        log_subprocess_error(
            context={
                "operation": "cache_download",
                "entry_id": video_id,
                "video_url": f"https://www.youtube.com/watch?v={video_id}",
                "stage": "metadata_fetch"
            },
            command=json_cmd if 'json_cmd' in locals() else [],
            exit_code=e.returncode,
            stdout=e.stdout if hasattr(e, 'stdout') and e.stdout else "",
            stderr=e.stderr if hasattr(e, 'stderr') and e.stderr else ""
        )
        return False
    except Exception as e:
        print(f"Unexpected error while downloading {video_id}: {e}")
        log_error(
            context={
                "operation": "cache_download",
                "entry_id": video_id,
                "video_url": f"https://www.youtube.com/watch?v={video_id}"
            },
            error=e,
            error_type="unexpected_error"
        )
        return False


def delete_cached_file(file_id, cache_dir):
    """Delete a cached file (YouTube video or podcast) and its associated auxiliary files."""
    try:
        deleted_any = False

        # First, check if the video is in the hierarchical structure
        # It could be in a subfolder like CHANNEL_NAME/YEAR/ID.mp4
        all_media_files = []

        # First, search recursively for the file in all subdirectories
        for extension in [".mp4", ".mkv", ".webm", ".mp3", ".m4a", ".opus"]:
            # Search both direct files and in subdirectories
            direct_path = cache_dir / f"{file_id}{extension}"
            if direct_path.exists():
                all_media_files.append(direct_path)

            # Search in subdirectories
            for file_path in cache_dir.glob(f"**/{file_id}{extension}"):
                all_media_files.append(file_path)

        if not all_media_files:
            print(f"No media files found for {file_id}")
            return False

        # Delete each found media file and its associated auxiliary files
        for media_file in all_media_files:
            # Get the parent directory (could be root or a subfolder)
            parent_dir = media_file.parent

            # Delete the main media file
            print(f"Deleting media file: {media_file}")
            media_file.unlink()
            deleted_any = True

            # Delete associated auxiliary files in the same directory
            for aux_path in parent_dir.glob(f"{file_id}.*"):
                # Skip actual media files (already deleted the main one)
                if aux_path.suffix.lower() in [
                    ".mp4",
                    ".mkv",
                    ".webm",
                    ".mp3",
                    ".m4a",
                    ".opus",
                ]:
                    continue

                # Only delete specific auxiliary file types
                if aux_path.suffix.lower() in [
                    ".srt",
                    ".nfo",
                    ".description",
                    ".json",
                    ".info.json",
                    ".en.srt",
                    ".en.vtt",
                ]:
                    print(f"Deleting auxiliary file: {aux_path}")
                    aux_path.unlink()
                    deleted_any = True

        return deleted_any
    except Exception as e:
        print(f"Error deleting file {file_id}: {e}")
        return False


def delete_youtube_video(video_id):
    """Delete a cached YouTube video."""
    return delete_cached_file(video_id, YOUTUBE_CACHE_DIR)


def delete_podcast(podcast_id):
    """Delete a cached podcast."""
    return delete_cached_file(podcast_id, PODCAST_CACHE_DIR)


def get_podcast_cached_ids():
    """Get a list of podcast IDs from cached files."""
    if not PODCAST_CACHE_DIR.exists():
        print(f"Podcast cache directory {PODCAST_CACHE_DIR} does not exist.")
        return []

    podcast_ids = set()
    for file_path in PODCAST_CACHE_DIR.iterdir():
        if file_path.is_file():
            # Extract the podcast ID from the filename (remove extension)
            podcast_id = file_path.stem
            podcast_ids.add(podcast_id)

    return podcast_ids


def download_podcast_from_note(note_id, url):
    """Download a podcast from a note."""
    from capturemd.capture_podcast import download_podcast

    return download_podcast(url, note_id)


# PERF: Jellyfin seems to be able to keep track of media watch status even when the episode counts shifts.
# Ideally this will become more robust once the watch status is stored in markdown as well
def _reindex_season_episodes():
    """Wrapper for reindex_season_episodes from episode_indexer module."""
    reindex_season_episodes(YOUTUBE_CACHE_DIR)


def manage_youtube_cache(video_id=None):
    """Manage YouTube video cache based on notes, optionally only for a specific video."""
    print("Managing YouTube video cache...")

    # Get all cached video IDs
    cached_ids = get_youtube_cached_ids()
    print(f"Found {len(cached_ids)} videos in cache directory")

    # Get all notes and track which videos should be cached
    should_cache = {}  # video_id -> cache (True/False)
    note_count = 0

    if not YOUTUBE_NOTES_DIR.exists():
        print(f"YouTube notes directory {YOUTUBE_NOTES_DIR} does not exist.")
        return

    for file_path in YOUTUBE_NOTES_DIR.glob("*.md"):
        note_count += 1
        frontmatter = extract_frontmatter(file_path)
        if frontmatter and "locator" in frontmatter:
            current_video_id = frontmatter["locator"]
            if video_id is not None and current_video_id != video_id:
                continue
            cache_value = frontmatter.get("cache", False)
            should_cache[current_video_id] = cache_value

    print(f"Processed {note_count} notes")

    if video_id is not None:
        print(f"Processing only video: {video_id}")

    # Delete videos that shouldn't be cached
    for vid in cached_ids:
        if video_id is not None and vid != video_id:
            continue
        if vid not in should_cache or not should_cache[vid]:
            print(f"Deleting {vid} - not marked for caching")
            delete_youtube_video(vid)

    # Download videos that should be cached but aren't
    for vid, cache in should_cache.items():
        if cache and vid not in cached_ids:
            print(f"Downloading {vid} - marked for caching but not found in cache")
            download_youtube_video(vid)
        elif cache and vid in cached_ids:
            # Video exists and should be cached, check if NFO exists
            found_nfo = False

            # Look in all possible locations for an NFO file
            for potential_nfo in YOUTUBE_CACHE_DIR.glob(f"**/{vid}.nfo"):
                found_nfo = True
                break

            if not found_nfo:
                print(f"Creating NFO file for existing video: {vid}")
                try:
                    json_cmd = [
                        "yt-dlp",
                        f"https://www.youtube.com/watch?v={vid}",
                        "--dump-json",
                        "--no-playlist",
                    ]
                    json_result = subprocess.run(
                        json_cmd, capture_output=True, text=True, check=True
                    )
                    video_info = json.loads(json_result.stdout)
                    create_nfo_file(vid, video_info)
                except subprocess.CalledProcessError as e:
                    print(f"Error fetching metadata for NFO file for {vid}: {e}")
                    log_subprocess_error(
                        context={
                            "operation": "cache_nfo_create",
                            "entry_id": vid,
                            "video_url": f"https://www.youtube.com/watch?v={vid}"
                        },
                        command=json_cmd,
                        exit_code=e.returncode,
                        stdout=e.stdout if e.stdout else "",
                        stderr=e.stderr if e.stderr else ""
                    )
                except Exception as e:
                    print(f"Error creating NFO file for {vid}: {e}")
                    log_error(
                        context={
                            "operation": "cache_nfo_create",
                            "entry_id": vid,
                            "video_url": f"https://www.youtube.com/watch?v={vid}"
                        },
                        error=e,
                        error_type="nfo_creation_error"
                    )

    if video_id is None:
        _reindex_season_episodes()

    print("YouTube cache management complete")


def convert_flat_structure_to_hierarchical():
    """Convert videos from flat directory structure to channel/year hierarchy."""
    print("Converting flat directory structure to channel/year hierarchy...")

    # Get all cached video IDs
    if not YOUTUBE_CACHE_DIR.exists():
        print(f"YouTube cache directory {YOUTUBE_CACHE_DIR} does not exist.")
        return

    # Get all video files in root directory (.mp4, .mkv, etc.)
    video_files = []
    print(f"Searching for videos in: {YOUTUBE_CACHE_DIR}")

    # First check if the directory exists
    if not YOUTUBE_CACHE_DIR.exists():
        print(f"ERROR: YouTube cache directory {YOUTUBE_CACHE_DIR} does not exist!")
        return

    # List all files in the root directory
    all_files = list(YOUTUBE_CACHE_DIR.iterdir())
    print(f"Total files in directory: {len(all_files)}")

    # Find media files with specific extensions
    for ext in [".mp4", ".mkv", ".webm"]:
        matching_files = list(YOUTUBE_CACHE_DIR.glob(f"*{ext}"))
        print(f"Found {len(matching_files)} files with extension {ext}")
        video_files.extend(matching_files)

    # Only process files directly in the root directory, not in subdirectories
    root_video_files = [f for f in video_files if f.parent == YOUTUBE_CACHE_DIR]
    print(f"Found {len(root_video_files)} video files in root cache directory")

    if not root_video_files:
        print("No videos to convert. Root directory is already empty.")
        return

    # Map from video ID to note data for cross-referencing
    video_metadata = {}
    if YOUTUBE_NOTES_DIR.exists():
        for file_path in YOUTUBE_NOTES_DIR.glob("*.md"):
            frontmatter = extract_frontmatter(file_path)
            if frontmatter and "locator" in frontmatter:
                video_id = frontmatter["locator"]
                video_metadata[video_id] = frontmatter

    # Process each video file
    for video_file in root_video_files:
        if not video_file.is_file():
            continue

        video_id = video_file.stem
        print(f"\nProcessing video: {video_file} (ID: {video_id})")

        # Check if we have a note for this video
        if video_id in video_metadata:
            print(f"Processing video file: {video_file.name}")

            # Get metadata from note
            frontmatter = video_metadata[video_id]
            channel = frontmatter.get("channel", "")
            upload_date = frontmatter.get("upload_date", "")

            # Handle different types of upload_date (string or datetime.date)
            if isinstance(upload_date, str) and upload_date:
                year = upload_date[:4]
            elif hasattr(upload_date, "year"):  # datetime.date object
                year = str(upload_date.year)
            else:
                year = ""

            # If we have channel and year info from the note
            if channel and year:
                # Sanitize channel name for folder structure
                safe_channel = (
                    channel.replace("/", "_")
                    .replace("\\", "_")
                    .replace("?", "_")
                    .replace("*", "_")
                )
                safe_channel = (
                    safe_channel.replace(":", "_")
                    .replace('"', "_")
                    .replace("<", "_")
                    .replace(">", "_")
                )

                # Create the show and season directories
                show_dir = YOUTUBE_CACHE_DIR / safe_channel
                season_dir = show_dir / year

                # Make sure the directories exist
                season_dir.mkdir(parents=True, exist_ok=True)

                # Create show NFO if it doesn't exist
                create_show_nfo(safe_channel, frontmatter.get("channel_id", ""))

                # Move the video file
                new_video_path = season_dir / video_file.name
                print(f"Moving {video_file} -> {new_video_path}")
                video_file.rename(new_video_path)

                # Check for and move NFO file
                nfo_path = YOUTUBE_CACHE_DIR / f"{video_id}.nfo"
                if nfo_path.exists():
                    new_nfo_path = season_dir / f"{video_id}.nfo"
                    print(f"Moving {nfo_path} -> {new_nfo_path}")
                    nfo_path.rename(new_nfo_path)
                else:
                    # Create new NFO file in the new location if it doesn't exist
                    print(f"NFO file not found, retrieving video info...")
                    try:
                        json_cmd = [
                            "yt-dlp",
                            f"https://www.youtube.com/watch?v={video_id}",
                            "--dump-json",
                            "--no-playlist",
                        ]

                        json_result = subprocess.run(
                            json_cmd, capture_output=True, text=True, check=True
                        )
                        video_info = json.loads(json_result.stdout)

                        # Create NFO file in the new location
                        create_nfo_file(video_id, video_info)
                    except Exception as e:
                        print(f"Error creating NFO file for {video_id}: {e}")

                # Move any subtitle files
                for srt_file in YOUTUBE_CACHE_DIR.glob(f"{video_id}.*.srt"):
                    new_srt_path = season_dir / srt_file.name
                    print(f"Moving {srt_file} -> {new_srt_path}")
                    srt_file.rename(new_srt_path)
            else:
                # If we don't have sufficient information from the notes
                print(
                    f"Cannot move {video_file.name} - missing channel or year information in metadata"
                )
                print(f"Retrieving information from YouTube...")

                try:
                    json_cmd = [
                        "yt-dlp",
                        f"https://www.youtube.com/watch?v={video_id}",
                        "--dump-json",
                        "--no-playlist",
                    ]

                    json_result = subprocess.run(
                        json_cmd, capture_output=True, text=True, check=True
                    )
                    video_info = json.loads(json_result.stdout)

                    # Extract channel and date information
                    channel = video_info.get("channel", video_info.get("uploader", ""))
                    upload_date_data = video_info.get("upload_date", "")

                    # Handle different types of upload_date (string or datetime.date)
                    if isinstance(upload_date_data, str) and upload_date_data:
                        year = upload_date_data[:4]
                    elif hasattr(upload_date_data, "year"):  # datetime.date object
                        year = str(upload_date_data.year)
                    else:
                        year = str(datetime.now().year)

                    if channel and year:
                        # Sanitize channel name for folder structure
                        safe_channel = (
                            channel.replace("/", "_")
                            .replace("\\", "_")
                            .replace("?", "_")
                            .replace("*", "_")
                        )
                        safe_channel = (
                            safe_channel.replace(":", "_")
                            .replace('"', "_")
                            .replace("<", "_")
                            .replace(">", "_")
                        )

                        # Create the show and season directories
                        show_dir = YOUTUBE_CACHE_DIR / safe_channel
                        season_dir = show_dir / year

                        # Make sure the directories exist
                        season_dir.mkdir(parents=True, exist_ok=True)

                        # Create show NFO
                        create_show_nfo(safe_channel, video_info.get("channel_id", ""))

                        # Move the video file
                        new_video_path = season_dir / video_file.name
                        print(f"Moving {video_file} -> {new_video_path}")
                        video_file.rename(new_video_path)

                        # Create a new NFO file in the new location
                        create_nfo_file(video_id, video_info)

                        # Move any subtitle files
                        for srt_file in YOUTUBE_CACHE_DIR.glob(f"{video_id}.*.srt"):
                            new_srt_path = season_dir / srt_file.name
                            print(f"Moving {srt_file} -> {new_srt_path}")
                            srt_file.rename(new_srt_path)
                    else:
                        print(
                            f"Cannot move {video_file.name} - unable to retrieve channel or year information"
                        )
                except Exception as e:
                    print(f"Error processing {video_id}: {e}")
        else:
            print(
                f"No metadata found for {video_id}, retrieving information from YouTube..."
            )

            try:
                json_cmd = [
                    "yt-dlp",
                    f"https://www.youtube.com/watch?v={video_id}",
                    "--dump-json",
                    "--no-playlist",
                ]

                json_result = subprocess.run(
                    json_cmd, capture_output=True, text=True, check=True
                )
                video_info = json.loads(json_result.stdout)

                # Extract channel and date information
                channel = video_info.get("channel", video_info.get("uploader", ""))
                upload_date_data = video_info.get("upload_date", "")

                # Handle different types of upload_date (string or datetime.date)
                if isinstance(upload_date_data, str) and upload_date_data:
                    year = upload_date_data[:4]
                elif hasattr(upload_date_data, "year"):  # datetime.date object
                    year = str(upload_date_data.year)
                else:
                    year = str(datetime.now().year)

                if channel and year:
                    # Sanitize channel name for folder structure
                    safe_channel = (
                        channel.replace("/", "_")
                        .replace("\\", "_")
                        .replace("?", "_")
                        .replace("*", "_")
                    )
                    safe_channel = (
                        safe_channel.replace(":", "_")
                        .replace('"', "_")
                        .replace("<", "_")
                        .replace(">", "_")
                    )

                    # Create the show and season directories
                    show_dir = YOUTUBE_CACHE_DIR / safe_channel
                    season_dir = show_dir / year

                    # Make sure the directories exist
                    season_dir.mkdir(parents=True, exist_ok=True)

                    # Create show NFO
                    create_show_nfo(safe_channel, video_info.get("channel_id", ""))

                    # Move the video file
                    new_video_path = season_dir / video_file.name
                    print(f"Moving {video_file} -> {new_video_path}")
                    video_file.rename(new_video_path)

                    # Create a new NFO file in the new location
                    create_nfo_file(video_id, video_info)

                    # Move any subtitle files
                    for srt_file in YOUTUBE_CACHE_DIR.glob(f"{video_id}.*.srt"):
                        new_srt_path = season_dir / srt_file.name
                        print(f"Moving {srt_file} -> {new_srt_path}")
                        srt_file.rename(new_srt_path)
                else:
                    print(
                        f"Cannot move {video_file.name} - unable to retrieve channel or year information"
                    )
            except Exception as e:
                print(f"Error processing {video_id}: {e}")

    print("Conversion complete")


def regenerate_youtube_nfo_files():
    """Regenerate NFO files for all cached YouTube videos."""
    print("Regenerating NFO files for cached YouTube videos...")

    # Get all cached video IDs
    if not YOUTUBE_CACHE_DIR.exists():
        print(f"YouTube cache directory {YOUTUBE_CACHE_DIR} does not exist.")
        return

    # Get all video files recursively (.mp4, .mkv, etc.)
    video_files = []
    for ext in [".mp4", ".mkv", ".webm"]:
        video_files.extend(list(YOUTUBE_CACHE_DIR.glob(f"**/*{ext}")))

    print(f"Found {len(video_files)} video files in cache directory")

    # Map from video ID to note ID/UUID for cross-referencing
    video_id_to_note_id = {}
    if YOUTUBE_NOTES_DIR.exists():
        for file_path in YOUTUBE_NOTES_DIR.glob("*.md"):
            frontmatter = extract_frontmatter(file_path)
            if frontmatter and "locator" in frontmatter and "id" in frontmatter:
                video_id = frontmatter["locator"]
                note_id = frontmatter["id"]
                video_id_to_note_id[video_id] = note_id

    # Process each video file
    for video_file in video_files:
        video_id = video_file.stem

        # Determine if this is in the new folder structure
        is_hierarchical = str(video_file.parent) != str(YOUTUBE_CACHE_DIR)

        # Check if NFO file exists
        if is_hierarchical:
            nfo_path = video_file.parent / f"{video_id}.nfo"
        else:
            nfo_path = YOUTUBE_CACHE_DIR / f"{video_id}.nfo"

        # Skip if NFO file already exists
        if nfo_path.exists():
            print(f"NFO file already exists for {video_id}")
            continue

        print(f"Regenerating NFO file for {video_id}")

        # Get video info using yt-dlp
        try:
            json_cmd = [
                "yt-dlp",
                f"https://www.youtube.com/watch?v={video_id}",
                "--dump-json",
                "--no-playlist",
            ]

            json_result = subprocess.run(
                json_cmd, capture_output=True, text=True, check=True
            )
            video_info = json.loads(json_result.stdout)

            # Create NFO file - use hierarchical structure if the video is in a subfolder
            create_nfo_file(video_id, video_info, create_new_structure=is_hierarchical)
            print(f"Successfully created NFO file for {video_id}")

            # If the video has a note, print the cross-reference
            if video_id in video_id_to_note_id:
                note_id = video_id_to_note_id[video_id]
                print(f"Video {video_id} corresponds to note with ID {note_id}")
        except subprocess.CalledProcessError as e:
            print(f"Error fetching metadata for {video_id}: {e}")
            log_subprocess_error(
                context={
                    "operation": "cache_nfo_regenerate",
                    "entry_id": video_id,
                    "video_url": f"https://www.youtube.com/watch?v={video_id}",
                    "file": str(video_file)
                },
                command=json_cmd if 'json_cmd' in locals() else [],
                exit_code=e.returncode,
                stdout=e.stdout if e.stdout else "",
                stderr=e.stderr if e.stderr else ""
            )
        except Exception as e:
            print(f"Error regenerating NFO file for {video_id}: {e}")
            log_error(
                context={
                    "operation": "cache_nfo_regenerate",
                    "entry_id": video_id,
                    "video_url": f"https://www.youtube.com/watch?v={video_id}",
                    "file": str(video_file)
                },
                error=e,
                error_type="nfo_regeneration_error"
            )

    print("NFO regeneration complete")


def manage_podcast_cache():
    """Manage podcast cache based on notes."""
    print("Managing podcast cache...")

    # Get all cached podcast IDs
    cached_ids = get_podcast_cached_ids()
    print(f"Found {len(cached_ids)} podcasts in cache directory")

    # Get all notes and track which podcasts should be cached
    should_cache = {}  # podcast_id -> (cache (True/False), url)
    note_count = 0

    if not PODCAST_NOTES_DIR.exists():
        print(f"Podcast notes directory {PODCAST_NOTES_DIR} does not exist.")
        return

    # Ensure cache directory exists
    PODCAST_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    for file_path in PODCAST_NOTES_DIR.glob("*.md"):
        note_count += 1
        frontmatter = extract_frontmatter(file_path)
        if frontmatter and "id" in frontmatter and "url" in frontmatter:
            podcast_id = frontmatter["id"]
            url = frontmatter["url"]
            cache_value = frontmatter.get("cache", True)  # Default to True for podcasts
            should_cache[podcast_id] = (cache_value, url)

            # Check if the podcast audio is already downloaded
            downloaded = False
            for cached_file in PODCAST_CACHE_DIR.glob(f"{podcast_id}.*"):
                if cached_file.suffix.lower() not in [
                    ".srt",
                    ".txt",
                    ".json",
                    ".description",
                ]:
                    downloaded = True
                    break

    print(f"Processed {note_count} notes")

    # Delete podcasts that shouldn't be cached
    for podcast_id in cached_ids:
        if podcast_id not in should_cache or not should_cache[podcast_id][0]:
            print(f"Deleting {podcast_id} - not marked for caching")
            delete_podcast(podcast_id)

    # Download podcasts that should be cached but aren't
    for podcast_id, (cache, url) in should_cache.items():
        if cache and podcast_id not in cached_ids:
            print(
                f"Downloading {podcast_id} - marked for caching but not found in cache"
            )
            audio_file = download_podcast_from_note(podcast_id, url)

            if audio_file:
                print(f"Successfully downloaded podcast: {podcast_id}")

    print("Podcast cache management complete")


if __name__ == "__main__":
    manage_youtube_cache()
