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
    parse_parser.add_argument(
        "id",
        nargs="?",
        default=None,
        help="Optional locator ID to parse a specific note",
    )

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
        "id",
        nargs="?",
        default=None,
        help="Optional locator ID to cache a specific video",
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

    return parser


def main():
    parser = create_parser()
    args = parser.parse_args()

    if not args.command or args.command is None:
        parser.print_help()
        return 1

    if args.command == "parse":
        from capturemd.parse_notes import parse_notes

        parse_notes(args.id)
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
                manage_youtube_cache(args.id)
            return 0
        elif args.cache_type == "podcast":
            from capturemd.cache_manager import manage_podcast_cache

            manage_podcast_cache()
            return 0
        else:
            print("Please specify a valid cache type (youtube, podcast)")
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
