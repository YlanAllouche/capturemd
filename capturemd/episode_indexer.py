#!/usr/bin/env python3
# episode_indexer.py - Handle episode re-indexing for YouTube seasons

import re
from datetime import datetime
from pathlib import Path


def _extract_episode_info_from_nfo(nfo_path):
    """Extract aired date and current episode number from NFO file.
    
    Returns:
        dict: Contains 'nfo_path', 'aired_date' (datetime), 'aired_str' (str), 
              'content' (str), and 'current_episode' (int or None)
    """
    try:
        with open(nfo_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Extract aired date from NFO
        aired_match = re.search(r"<aired>(.*?)</aired>", content)
        aired_date = aired_match.group(1) if aired_match else None

        # Extract current episode number if it exists
        episode_match = re.search(r"<episode>(\d+)</episode>", content)
        current_episode = int(episode_match.group(1)) if episode_match else None

        # Parse the date string
        if aired_date:
            try:
                date_obj = datetime.strptime(aired_date, "%Y-%m-%d")
            except ValueError:
                print(
                    f"  Warning: Could not parse date '{aired_date}' in {nfo_path.name}"
                )
                # Use a far future date for unparseable dates
                date_obj = datetime.max
        else:
            print(f"  Warning: No aired date found in {nfo_path.name}")
            # Use a far future date for files without aired date
            date_obj = datetime.max

        return {
            "nfo_path": nfo_path,
            "aired_date": date_obj,
            "aired_str": aired_date,
            "content": content,
            "current_episode": current_episode,
        }
    except Exception as e:
        print(f"Error processing {nfo_path}: {e}")
        return None


def _remove_episode_tag(content):
    """Remove the existing episode tag from NFO content.
    
    Returns:
        str: Content with episode tag removed
    """
    return re.sub(r"\n    <episode>\d+</episode>", "", content)


def _add_episode_tag(content, episode_num):
    """Add or update episode tag in NFO content.
    
    Inserts the episode tag right after the season tag for logical grouping.
    
    Returns:
        str: Updated content with new episode tag
    """
    # First remove any existing episode tag
    content = _remove_episode_tag(content)
    
    # Then add the new episode tag after the season tag
    updated_content = re.sub(
        r"(<season>.*?</season>)",
        rf"\1\n    <episode>{episode_num}</episode>",
        content,
    )
    return updated_content


def _reindex_season(season_dir, force=False):
    """Re-index a single season directory by aired date.
    
    Args:
        season_dir: Path object to the season directory
        force: If True, reindex all episodes. If False, only reindex if 
               any episode is missing a number.
    
    Returns:
        bool: True if reindexing was performed, False otherwise
    """
    # Skip tvshow.nfo files, only process episode NFO files
    nfo_files = [f for f in season_dir.glob("*.nfo") if f.name != "tvshow.nfo"]

    if not nfo_files:
        return False

    # Check if any NFO files are missing episode numbers (unless forcing)
    if not force:
        needs_reindexing = False
        for nfo_file in nfo_files:
            try:
                with open(nfo_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    if "<episode>" not in content:
                        needs_reindexing = True
                        break
            except Exception as e:
                print(f"Error reading {nfo_file}: {e}")
                continue

        if not needs_reindexing:
            return False

    # Parse all NFO files to get aired dates
    episode_data = []
    for nfo_file in nfo_files:
        episode_info = _extract_episode_info_from_nfo(nfo_file)
        if episode_info:
            episode_data.append(episode_info)

    if not episode_data:
        return False

    # Sort by aired date
    episode_data.sort(key=lambda x: x["aired_date"])

    # Assign episode numbers and update NFO files
    for episode_num, episode_info in enumerate(episode_data, start=1):
        try:
            content = episode_info["content"]
            nfo_path = episode_info["nfo_path"]

            # Update episode number (removes old if exists, adds new)
            updated_content = _add_episode_tag(content, episode_num)

            # Write updated content back to NFO file
            with open(nfo_path, "w", encoding="utf-8") as f:
                f.write(updated_content)

            video_id = nfo_path.stem
            old_ep = episode_info["current_episode"]
            if old_ep and old_ep != episode_num:
                print(
                    f"  Episode {episode_num}: {video_id} ({episode_info['aired_str']}) "
                    f"[was {old_ep}]"
                )
            else:
                print(
                    f"  Episode {episode_num}: {video_id} ({episode_info['aired_str']})"
                )

        except Exception as e:
            print(f"Error updating {nfo_path}: {e}")
            continue

    return True


def reindex_season_episodes(youtube_cache_dir):
    """Re-index episodes in all seasons by aired date.

    Scans all show/season directories and for any season that has NFO files
    without episode numbers, assigns sequential episode numbers based on
    the aired date (earliest = episode 1).
    
    Args:
        youtube_cache_dir: Path object to the YouTube cache directory
    """
    if not youtube_cache_dir.exists():
        print(f"YouTube cache directory {youtube_cache_dir} does not exist.")
        return

    print("Re-indexing episode numbers by aired date...")

    # Iterate through all channel directories
    for channel_dir in youtube_cache_dir.iterdir():
        if not channel_dir.is_dir() or channel_dir.name.startswith("."):
            continue

        # Iterate through all season (year) directories
        for season_dir in channel_dir.iterdir():
            if not season_dir.is_dir() or season_dir.name.startswith("."):
                continue

            if _reindex_season(season_dir, force=False):
                print(
                    f"\nReindexing season: {channel_dir.name}/{season_dir.name}"
                )

    print("Episode re-indexing complete")


def force_reindex_season_episodes(youtube_cache_dir):
    """Force re-index ALL episodes in all seasons by aired date.

    This function completely rewrites episode numbers for all videos in all seasons,
    useful for correcting previous indexing mistakes (like duplicate episode numbers).
    It ignores whether files already have episode numbers.
    
    Args:
        youtube_cache_dir: Path object to the YouTube cache directory
    """
    if not youtube_cache_dir.exists():
        print(f"YouTube cache directory {youtube_cache_dir} does not exist.")
        return

    print("Force re-indexing ALL episode numbers by aired date...")
    print("WARNING: This will rewrite all existing episode numbers!")

    reindexed_count = 0

    # Iterate through all channel directories
    for channel_dir in youtube_cache_dir.iterdir():
        if not channel_dir.is_dir() or channel_dir.name.startswith("."):
            continue

        # Iterate through all season (year) directories
        for season_dir in channel_dir.iterdir():
            if not season_dir.is_dir() or season_dir.name.startswith("."):
                continue

            if _reindex_season(season_dir, force=True):
                print(
                    f"\nForce reindexing season: {channel_dir.name}/{season_dir.name}"
                )
                reindexed_count += 1

    print(
        f"Force re-indexing complete. Updated {reindexed_count} season(s)."
    )
