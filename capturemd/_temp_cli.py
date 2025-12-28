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
        if args.parse:
            sys.argv.append("--parse")

        note_path = process_url(args.url)
        if note_path and args.parse:
            parse_unparsed_notes()

        return 0 if note_path else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
