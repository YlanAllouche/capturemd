#!/usr/bin/env python3
# cli.py - Command-line interface for capturemd

import argparse
import sys
from pathlib import Path

from capturemd import __version__
from capturemd.url_processor import parse_unparsed_notes, process_url


def create_parser():
    parser = argparse.ArgumentParser(
        description="Capture web content into markdown files.", prog="capturemd"
    )

    parser.add_argument(
        "--version", action="version", version=f"capturemd {__version__}"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # URL parser
    url_parser = subparsers.add_parser("url", help="Process a URL and create a note")
    url_parser.add_argument(
        "url",
        nargs="?",
        help="URL to process. If not provided, will try to use clipboard.",
    )
    url_parser.add_argument(
        "--parse", action="store_true", help="Parse the note immediately after creation"
    )

    # YouTube parser
    youtube_parser = subparsers.add_parser(
        "youtube", help="Process a YouTube video URL"
    )
    youtube_parser.add_argument("url", help="YouTube video URL")
    youtube_parser.add_argument(
        "--parse", action="store_true", help="Parse the note immediately after creation"
    )

    # GitHub parser
    github_parser = subparsers.add_parser(
        "github", help="Process a GitHub repository URL"
    )
    github_parser.add_argument("url", help="GitHub repository URL")
    github_parser.add_argument(
        "--parse", action="store_true", help="Parse the note immediately after creation"
    )

    # Reddit parser
    reddit_parser = subparsers.add_parser("reddit", help="Process a Reddit thread URL")
    reddit_parser.add_argument("url", help="Reddit thread URL")
    reddit_parser.add_argument(
        "--parse", action="store_true", help="Parse the note immediately after creation"
    )

    # Steam parser
    steam_parser = subparsers.add_parser("steam", help="Process a Steam game URL")
    steam_parser.add_argument("url", help="Steam game URL")
    steam_parser.add_argument(
        "--parse", action="store_true", help="Parse the note immediately after creation"
    )

    # Hacker News parser
    hackernews_parser = subparsers.add_parser(
        "hackernews", help="Process a Hacker News item URL"
    )
    hackernews_parser.add_argument("url", help="Hacker News item URL")
    hackernews_parser.add_argument(
        "--parse", action="store_true", help="Parse the note immediately after creation"
    )

    # Google search parser
    google_parser = subparsers.add_parser(
        "google", help="Process a Google search query"
    )
    google_parser.add_argument("query", help="Google search query or URL")

    # Podcast parser
    podcast_parser = subparsers.add_parser("podcast", help="Process a podcast episode")
    podcast_parser.add_argument("url", help="Podcast episode URL")
    podcast_parser.add_argument(
        "--title", required=True, help="Title of the podcast episode"
    )
    podcast_parser.add_argument(
        "--channel", required=True, help="Channel/show name of the podcast"
    )
    podcast_parser.add_argument(
        "--description", default="", help="Description of the podcast episode"
    )
    podcast_parser.add_argument(
        "--published-date",
        default="",
        help="Publication date of the episode (YYYY-MM-DD)",
    )
    podcast_parser.add_argument(
        "--tags", default="inbox", help="Comma-separated list of tags"
    )

    # Wallabag parser
    wallabag_parser = subparsers.add_parser(
        "parse-wallabag", help="Process entries from Wallabag"
    )

    # FreshRSS parser
    freshrss_parser = subparsers.add_parser(
        "parse-rss", help="Process starred items from FreshRSS"
    )

    # Parse command
    parse_parser = subparsers.add_parser("parse", help="Parse unparsed notes")

    # Cache command
    cache_parser = subparsers.add_parser("cache", help="Manage cached content")
    cache_subparsers = cache_parser.add_subparsers(
        dest="cache_type", help="Type of content to cache"
    )

    # YouTube cache subcommand
    youtube_cache_parser = cache_subparsers.add_parser(
        "youtube", help="Manage YouTube video cache"
    )
    youtube_cache_parser.add_argument(
        "--regen",
        action="store_true",
        help="Regenerate NFO files for all cached videos",
    )
    youtube_cache_parser.add_argument(
        "--convert-flat-structure",
        action="store_true",
        help="Convert videos from flat structure to show/season folder structure",
    )

    # Podcast cache subcommand
    podcast_cache_parser = cache_subparsers.add_parser(
        "podcast", help="Manage podcast cache"
    )

    # Play command
    play_parser = subparsers.add_parser("play", help="Play a media file by ID")
    play_parser.add_argument("id", help="ID of the media to play")

    return parser


def play_media(media_id):
    """
    Play media (YouTube video or podcast) by ID.
    - Finds the note with matching ID in appropriate resource directory
    - Gets the media file path
    - Plays the media file using mpv
    - Uses a unique named pipe to ensure only capturemd's mpv instance is used
    """
    import glob
    import os
    import re
    import signal
    import subprocess
    import time
    from pathlib import Path

    import yaml

    # Use a unique named pipe specific to capturemd
    pipe_path = "/tmp/capturemd-mpv-pipe"
    pid_file = "/tmp/capturemd-mpv.pid"

    # Try to find the media in different resource directories
    resource_types = [
        {
            "name": "youtube",
            "notes_dir": Path.home() / "share" / "notes" / "resource" / "youtube",
            "media_dir": Path.home() / "Media" / "videos" / "yt",
            "id_field": "id",
            "locator_field": "locator",
        },
        {
            "name": "podcast",
            "notes_dir": Path.home() / "share" / "notes" / "resource" / "podcast",
            "media_dir": Path.home() / "Media" / "podcasts",
            "id_field": "id",
            "locator_field": "id",  # For podcasts, the ID itself is the locator
            "url_field": "audio_url",  # URL for the audio source - not a local path
        },
    ]

    media_path = None
    media_type = None
    locator = None

    # Try to find the media in each resource type
    for resource in resource_types:
        if not resource["notes_dir"].exists():
            continue

        # Read all markdown files in the resource directory
        for md_file in resource["notes_dir"].glob("*.md"):
            try:
                with open(md_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # Extract YAML frontmatter
                match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
                if match:
                    frontmatter = yaml.safe_load(match.group(1))

                    # Check if this is the media we're looking for
                    if frontmatter.get(resource["id_field"]) == media_id:
                        # Found the matching note
                        media_type = resource["name"]

                        # For podcasts, first look for cached files based on ID
                        if media_type == "podcast":
                            podcast_id = frontmatter.get(resource["id_field"])
                            # Search for cached podcast files
                            cached_files = list(
                                resource["media_dir"].glob(f"{podcast_id}.*")
                            )
                            media_files = [
                                f
                                for f in cached_files
                                if f.suffix.lower()
                                in [
                                    ".mp3",
                                    ".mp4",
                                    ".m4a",
                                    ".opus",
                                    ".webm",
                                    ".mkv",
                                    ".wav",
                                ]
                            ]

                            if media_files:
                                media_path = str(media_files[0])
                                print(f"Found cached podcast: {media_path}")
                                break

                            # If no cached file found but has audio_url, offer to download it
                            if "url_field" in resource and frontmatter.get(
                                resource["url_field"]
                            ):
                                print(
                                    f"Podcast not cached. Run 'capturemd cache podcast' to download it first."
                                )
                                return False

                        # Otherwise, use the locator to find the file
                        locator = frontmatter.get(resource["locator_field"])
                        if locator:
                            # First look for media files in the new folder structure (show/season/locator.*)
                            channel_name = (
                                frontmatter.get("channel", "")
                                .replace("/", "_")
                                .replace("\\", "_")
                            )
                            upload_date = frontmatter.get("upload_date", "")

                            # Handle different types of upload_date (string or datetime.date)
                            if (
                                isinstance(upload_date, str)
                                and upload_date
                                and len(upload_date) >= 4
                            ):
                                year = upload_date[:4]
                            elif hasattr(upload_date, "year"):  # datetime.date object
                                year = str(upload_date.year)
                            else:
                                year = ""

                            media_files = []
                            print(f"Looking for media with locator: {locator}")

                            # Do a comprehensive search for the video file
                            media_extensions = [
                                ".mp4",
                                ".mkv",
                                ".webm",
                                ".mp3",
                                ".m4a",
                                ".opus",
                                ".ogg",
                                ".wav",
                            ]

                            # First try specific locations if we have channel/year info
                            if channel_name and year:
                                print(
                                    f"  Checking in channel: {channel_name}, year: {year}"
                                )
                                # Look in the exact folder structure (channel/year/locator.ext)
                                for ext in media_extensions:
                                    path = (
                                        resource["media_dir"]
                                        / channel_name
                                        / year
                                        / f"{locator}{ext}"
                                    )
                                    if path.exists() and path.is_file():
                                        print(
                                            f"  Found in channel/year directory: {path}"
                                        )
                                        media_files.append(path)

                            # If not found or no channel/year info, do a recursive search
                            if not media_files:
                                print(f"  Searching recursively for {locator}")
                                for ext in media_extensions:
                                    # Search recursively (takes longer but more thorough)
                                    for path in resource["media_dir"].glob(
                                        f"**/{locator}{ext}"
                                    ):
                                        if path.exists() and path.is_file():
                                            print(
                                                f"  Found in directory: {path.parent}"
                                            )
                                            media_files.append(path)

                            # Finally check the root directory as a fallback
                            if not media_files:
                                print(f"  Checking root directory")
                                for ext in media_extensions:
                                    path = resource["media_dir"] / f"{locator}{ext}"
                                    if path.exists() and path.is_file():
                                        print(f"  Found in root directory: {path}")
                                        media_files.append(path)

                            if media_files:
                                # Verify the file actually exists before returning it
                                for file_path in media_files:
                                    if Path(file_path).exists():
                                        media_path = str(file_path)
                                        print(f"Found media file: {media_path}")
                                        break
                                if media_path:
                                    break
            except Exception as e:
                print(f"Error reading {md_file}: {e}")
                continue

        if media_path:
            break

    if not media_path:
        print(f"No media found for ID: {media_id}")
        return False

    # Ensure the file exists before trying to play it
    if not os.path.exists(media_path):
        print(f"ERROR: The file {media_path} does not exist.")
        return False

    # Make sure it's a file, not a directory
    if not os.path.isfile(media_path):
        print(f"ERROR: The path {media_path} is not a file.")
        return False

    print(f"Found {media_type}: {media_path}")

    # Create the named pipe if it doesn't exist
    if not os.path.exists(pipe_path):
        try:
            os.mkfifo(pipe_path)
        except OSError as e:
            print(f"Failed to create named pipe: {e}")
            return False

    # Check if our capturemd mpv instance is already running
    capturemd_mpv_running = False
    mpv_pid = None

    if os.path.exists(pid_file):
        try:
            with open(pid_file, "r") as f:
                mpv_pid = int(f.read().strip())

            # Check if process with this PID exists and is mpv
            try:
                os.kill(mpv_pid, 0)  # Just checking if process exists
                ps_result = subprocess.run(
                    ["ps", "-p", str(mpv_pid), "-o", "comm="],
                    capture_output=True,
                    text=True,
                )
                if "mpv" in ps_result.stdout:
                    capturemd_mpv_running = True
            except OSError:
                # Process doesn't exist
                pass
        except (ValueError, FileNotFoundError):
            pass

    # Set up mpv options based on media type
    mpv_options = [
        f"--input-ipc-server={pipe_path}",
    ]

    if media_type == "youtube":
        mpv_options.append("--force-window=yes")  # Ensure video window opens
    elif media_type == "podcast":
        # For podcasts, we want different default options
        mpv_options.extend(
            [
                "--audio-display=no",  # Don't show video window for audio
                "--save-position-on-quit",  # Remember playback position
                "--speed=1.5",  # Default faster playback for podcasts
            ]
        )

    try:
        if capturemd_mpv_running:
            # Our MPV is running, send command to the pipe
            print(f"Sending to existing mpv (PID: {mpv_pid})")
            try:
                with open(pipe_path, "w") as pipe:
                    # Use replace instead of append-play to ensure it starts playing
                    pipe.write(f"loadfile {media_path} replace\n")

                # Verify mpv received the command by checking if it's still running
                time.sleep(0.5)  # Give it a moment to process
                try:
                    os.kill(mpv_pid, 0)  # Just check if process still exists
                    print(f"Playing {media_type}: {locator or media_path}")
                except OSError:
                    print("MPV process died, starting a new one")
                    capturemd_mpv_running = False
            except Exception as e:
                print(f"Failed to communicate with pipe: {e}")
                capturemd_mpv_running = False

        if not capturemd_mpv_running:
            # Start a new mpv instance with our IPC pipe
            print("Starting new mpv instance...")
            cmd = ["mpv", media_path] + mpv_options
            process = subprocess.Popen(cmd)

            # Save the PID
            with open(pid_file, "w") as f:
                f.write(str(process.pid))

            print(f"Playing {media_type}: {locator or media_path} (PID: {process.pid})")

        return True
    except Exception as e:
        print(f"Error playing media: {e}")
        return False


def play_youtube_video(video_id):
    """
    Play a YouTube video by ID.
    Wrapper for play_media for backwards compatibility.
    """
    return play_media(video_id)


def main():
    parser = create_parser()
    args = parser.parse_args()

    if not args.command or args.command is None:
        parser.print_help()
        return 1

    if args.command == "parse":
        parse_unparsed_notes()
        return 0

    # For URL processing commands
    if args.command in ["url", "youtube", "github", "reddit", "steam", "hackernews"]:
        # Add command arguments to sys.argv for compatibility with the old script
        if args.parse:
            sys.argv.append("--parse")

        note_path = process_url(args.url)
        if note_path and args.parse:
            parse_unparsed_notes()

        return 0 if note_path else 1

    # Handle Google command
    if args.command == "google":
        from capturemd.capture_google import capture_google_search

        # Check if the input is a URL or a query
        query = args.query
        if query.startswith("http"):
            # It's a URL, process directly
            success = capture_google_search(query)
        else:
            # It's a query, construct a Google search URL
            search_url = f"https://www.google.com/search?q={query}"
            success = capture_google_search(search_url)

        return 0 if success else 1

    # Handle podcast command
    if args.command == "podcast":
        from capturemd.capture_podcast import process_podcast

        # Process tags (convert comma-separated list to array)
        tags = [tag.strip() for tag in args.tags.split(",") if tag.strip()]

        note_path = process_podcast(
            url=args.url,
            title=args.title,
            channel=args.channel,
            description=args.description,
            published_date=args.published_date,
            tags=tags,
        )

        return 0 if note_path else 1

    # Handle wallabag processing
    if args.command == "parse-wallabag":
        from capturemd.capture_wallabag import process_wallabag

        return process_wallabag()

    # Handle FreshRSS processing
    if args.command == "parse-rss":
        from capturemd.capture_freshrss import process_freshrss

        return process_freshrss()

    # Handle cache command
    if args.command == "cache":
        if args.cache_type == "youtube":
            from capturemd.cache_manager import (
                convert_flat_structure_to_hierarchical,
                manage_youtube_cache,
                regenerate_youtube_nfo_files,
            )

            if args.regen:
                regenerate_youtube_nfo_files()
            elif args.convert_flat_structure:
                convert_flat_structure_to_hierarchical()
            else:
                manage_youtube_cache()
            return 0
        elif args.cache_type == "podcast":
            from capturemd.cache_manager import manage_podcast_cache

            manage_podcast_cache()
            return 0
        else:
            print("Please specify a valid cache type (youtube, podcast)")
            return 1

    # Handle play command
    if args.command == "play":
        success = play_media(args.id)
        return 0 if success else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
