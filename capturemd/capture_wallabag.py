import json
import os
import re
import requests
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from capturemd.url_processor import (
    is_youtube_video, is_github_repo, is_reddit_thread,
    is_steam_game, is_hackernews_item, is_google_search,
    get_youtube_video_id, get_github_repo_info, get_reddit_thread_info,
    get_steam_game_info, get_hackernews_item_info,
    process_url
)
from capturemd.paths import BOOKMARK_NOTES_DIR

# Wallabag API constants - loaded from environment variables
WALLABAG_HOST = os.getenv("WALLABAG_HOST", "")
WALLABAG_CLIENT_ID = os.getenv("WALLABAG_CLIENT_ID", "")
WALLABAG_CLIENT_SECRET = os.getenv("WALLABAG_CLIENT_SECRET", "")
WALLABAG_USERNAME = os.getenv("WALLABAG_USERNAME", "")
WALLABAG_PASSWORD = os.getenv("WALLABAG_PASSWORD", "")
WALLABAG_PARSED_TAG = "parsed"


class WallabagAPI:
    """Client for interacting with the Wallabag API."""
    
    def __init__(self):
        self.host = WALLABAG_HOST
        self.client_id = WALLABAG_CLIENT_ID
        self.client_secret = WALLABAG_CLIENT_SECRET
        self.username = WALLABAG_USERNAME
        self.password = WALLABAG_PASSWORD
        self.token = None
    
    def authenticate(self) -> bool:
        """Authenticate with the Wallabag API and get an access token."""
        auth_url = f"{self.host}/oauth/v2/token"
        payload = {
            "grant_type": "password",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "username": self.username,
            "password": self.password
        }
        
        try:
            response = requests.post(auth_url, data=payload)
            response.raise_for_status()
            self.token = response.json().get("access_token")
            return bool(self.token)
        except requests.exceptions.RequestException as e:
            print(f"Authentication error: {e}")
            return False
    
    def get_headers(self) -> Dict[str, str]:
        """Get headers with authentication token."""
        if not self.token and not self.authenticate():
            raise Exception("Failed to authenticate with Wallabag API")
        
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def get_entries(self, page: int = 1, tags: List[str] = None) -> Dict:
        """Get entries from Wallabag, optionally filtered by tags."""
        entries_url = f"{self.host}/api/entries"
        params = {"page": page, "perPage": 30}
        
        # Filter by tags (exclusion)
        if tags:
            params["tags"] = ",".join(tags)
        
        try:
            response = requests.get(
                entries_url, 
                params=params, 
                headers=self.get_headers()
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error getting entries: {e}")
            return {"_embedded": {"items": []}}
    
    def get_entries_without_tag(self, tag: str) -> List[Dict]:
        """Get all entries that do not have a specific tag."""
        all_entries = []
        page = 1
        
        while True:
            result = self.get_entries(page=page)
            items = result.get("_embedded", {}).get("items", [])
            
            if not items:
                break
                
            # Filter out entries that have the tag
            filtered_entries = [
                entry for entry in items 
                if not any(t.get("label") == tag for t in entry.get("tags", []))
            ]
            
            all_entries.extend(filtered_entries)
            page += 1
            
            # Check if we've reached the last page
            if not result.get("_links", {}).get("next"):
                break
                
        return all_entries
    
    def delete_entry(self, entry_id: int) -> bool:
        """Delete an entry from Wallabag."""
        delete_url = f"{self.host}/api/entries/{entry_id}"
        
        try:
            response = requests.delete(delete_url, headers=self.get_headers())
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            print(f"Error deleting entry {entry_id}: {e}")
            return False
    
    def add_tags_to_entry(self, entry_id: int, tags: List[str]) -> bool:
        """Add tags to an entry."""
        tags_url = f"{self.host}/api/entries/{entry_id}/tags"
        payload = {"tags": ",".join(tags)}
        
        try:
            response = requests.post(
                tags_url, 
                json=payload, 
                headers=self.get_headers()
            )
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            print(f"Error adding tags to entry {entry_id}: {e}")
            return False
    
    def check_url_exists(self, url: str) -> Tuple[bool, Optional[int]]:
        """Check if a URL exists in Wallabag and return its ID if it does."""
        exists_url = f"{self.host}/api/entries/exists"
        params = {"url": url, "return_id": 1}
        
        try:
            response = requests.get(
                exists_url, 
                params=params, 
                headers=self.get_headers()
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get("exists"):
                return True, result.get("id")
            return False, None
        except requests.exceptions.RequestException as e:
            print(f"Error checking if URL exists: {e}")
            return False, None
    
    def add_url(self, url: str, tags: List[str] = None) -> Tuple[bool, Optional[int]]:
        """Add a URL to Wallabag."""
        add_url = f"{self.host}/api/entries"
        payload = {"url": url}
        
        if tags:
            payload["tags"] = ",".join(tags)
        
        try:
            response = requests.post(
                add_url, 
                json=payload, 
                headers=self.get_headers()
            )
            response.raise_for_status()
            result = response.json()
            return True, result.get("id")
        except requests.exceptions.RequestException as e:
            print(f"Error adding URL: {e}")
            return False, None


def identify_url_type(url: str) -> str:
    """Identify the type of URL based on existing patterns."""
    if is_youtube_video(url):
        return "youtube"
    elif is_github_repo(url):
        return "github"
    elif is_reddit_thread(url):
        return "reddit"
    elif is_steam_game(url):
        return "steam"
    elif is_hackernews_item(url):
        return "hackernews"
    elif is_google_search(url):
        return "google"
    else:
        return "default"


def process_wallabag_entry(wallabag: WallabagAPI, entry: Dict) -> None:
    """Process a single Wallabag entry."""
    entry_id = entry.get("id")
    url = entry.get("url")
    title = entry.get("title", "")
    
    if not url:
        print(f"Entry {entry_id} has no URL, skipping")
        return
    
    print(f"Processing entry: {title} ({url})")
    
    # Identify URL type
    url_type = identify_url_type(url)
    print(f"URL type: {url_type}")
    
    # Process the URL through capturemd
    note_path = process_url(url)
    
    if not note_path:
        print(f"Failed to process URL: {url}")
        return
    
    # If it's a default bookmark, update the note with Wallabag information
    # (but only if it's a newly created note, not an existing one)
    if url_type == "default" and note_path != "google_search_processed":
        update_note_with_wallabag_info(note_path, entry)
    
    # Mark as processed in Wallabag by adding the "parsed" tag
    # This happens even for duplicates - we still want to mark it as processed
    success = wallabag.add_tags_to_entry(entry_id, [WALLABAG_PARSED_TAG])
    
    if success:
        print(f"Added 'parsed' tag to entry {entry_id}")
    else:
        print(f"Failed to add 'parsed' tag to entry {entry_id}")
    
    # Delete entry from Wallabag if it's specialized content
    if url_type != "default":
        success = wallabag.delete_entry(entry_id)
        if success:
            print(f"Deleted entry {entry_id} from Wallabag")
        else:
            print(f"Failed to delete entry {entry_id} from Wallabag")


def update_note_with_wallabag_info(note_path: str, entry: Dict) -> None:
    """Update a markdown note with Wallabag information."""
    if not os.path.exists(note_path):
        print(f"Note file does not exist: {note_path}")
        return
    
    # Extract frontmatter and content
    with open(note_path, "r", encoding="utf-8") as f:
        note_content = f.read()
    
    # Extract YAML frontmatter between --- delimiters
    frontmatter_match = re.search(r'^---\n(.*?)\n---', note_content, re.DOTALL)
    if not frontmatter_match:
        print(f"No frontmatter found in {note_path}")
        return
        
    yaml_text = frontmatter_match.group(1)
    frontmatter = yaml.safe_load(yaml_text)
    content = note_content[frontmatter_match.end():].strip()
    
    # Add Wallabag information
    frontmatter["wallabag_id"] = entry.get("id")
    frontmatter["title"] = entry.get("title", "")
    frontmatter["date"] = entry.get("created_at", "")
    frontmatter["tags"] = ["inbox"]
    frontmatter["class"] = ["webpage", "bookmark", "resource"]
    frontmatter["parsed"] = True
    frontmatter["scope"] = ""
    frontmatter["type"] = "bookmark"
    
    # Reconstruct the note
    yaml_frontmatter = yaml.dump(frontmatter, default_flow_style=False)
    updated_note = f"---\n{yaml_frontmatter}---\n\n{content}"
    
    # Write the updated note
    with open(note_path, "w", encoding="utf-8") as f:
        f.write(updated_note)
    
    print(f"Updated note with Wallabag info: {note_path}")


def find_unparsed_bookmark_notes() -> List[str]:
    """Find all default bookmark markdown notes that don't have a wallabag_id."""
    notes_dir = str(BOOKMARK_NOTES_DIR)
    note_paths = []
    
    if not os.path.exists(notes_dir):
        return note_paths
    
    for file_name in os.listdir(notes_dir):
        if file_name.endswith(".md"):
            file_path = os.path.join(notes_dir, file_name)
            
            # Read the note and check if it has a wallabag_id
            with open(file_path, "r", encoding="utf-8") as f:
                note_content = f.read()
            
            # Extract YAML frontmatter between --- delimiters
            frontmatter_match = re.search(r'^---\n(.*?)\n---', note_content, re.DOTALL)
            if not frontmatter_match:
                continue
                
            yaml_text = frontmatter_match.group(1)
            try:
                frontmatter = yaml.safe_load(yaml_text)
                
                if frontmatter and "wallabag_id" not in frontmatter and "url" in frontmatter:
                    note_paths.append(file_path)
            except yaml.YAMLError:
                print(f"Error parsing YAML in {file_path}")
                continue
    
    return note_paths


def process_existing_bookmark_notes(wallabag: WallabagAPI) -> None:
    """Process existing bookmark notes that don't have Wallabag IDs."""
    note_paths = find_unparsed_bookmark_notes()
    
    for note_path in note_paths:
        # Read the note and extract URL
        with open(note_path, "r", encoding="utf-8") as f:
            note_content = f.read()
        
        # Extract YAML frontmatter between --- delimiters
        frontmatter_match = re.search(r'^---\n(.*?)\n---', note_content, re.DOTALL)
        if not frontmatter_match:
            print(f"No frontmatter found in {note_path}")
            continue
            
        yaml_text = frontmatter_match.group(1)
        frontmatter = yaml.safe_load(yaml_text)
        content = note_content[frontmatter_match.end():].strip()
        
        url = frontmatter.get("url")
        
        if not url:
            print(f"Note has no URL: {note_path}")
            continue
        
        print(f"Processing bookmark note: {note_path}")
        
        # Check if URL exists in Wallabag
        exists, entry_id = wallabag.check_url_exists(url)
        
        if exists and entry_id:
            print(f"URL already exists in Wallabag with ID {entry_id}")
            
            # Update note with Wallabag ID
            frontmatter["wallabag_id"] = entry_id
            
            # Ensure the entry has the "parsed" tag
            wallabag.add_tags_to_entry(entry_id, [WALLABAG_PARSED_TAG])
        else:
            print(f"Adding URL to Wallabag: {url}")
            success, entry_id = wallabag.add_url(url, tags=[WALLABAG_PARSED_TAG])
            
            if success and entry_id:
                print(f"Added URL to Wallabag with ID {entry_id}")
                frontmatter["wallabag_id"] = entry_id
            else:
                print(f"Failed to add URL to Wallabag: {url}")
                continue
        
        # Update the note
        yaml_frontmatter = yaml.dump(frontmatter, default_flow_style=False)
        updated_note = f"---\n{yaml_frontmatter}---\n\n{content}"
        
        with open(note_path, "w", encoding="utf-8") as f:
            f.write(updated_note)
        
        print(f"Updated note with Wallabag ID: {note_path}")


def process_wallabag() -> int:
    """
    Main function to process Wallabag entries.
    
    This function:
    1. Lists all items that do not have the "parsed" tag in Wallabag
    2. For each item, checks if the URL matches a specific handler or is a default bookmark
    3. Processes the URL through capturemd
    4. For default bookmarks, adds Wallabag info to the note
    5. For all items, adds a "parsed" tag in Wallabag
    6. For non-default items, deletes the entry from Wallabag
    7. Processes existing bookmark notes that don't have Wallabag IDs
    
    Returns:
        int: 0 for success, 1 for failure
    """
    # Initialize Wallabag API client
    wallabag = WallabagAPI()
    
    if not wallabag.authenticate():
        print("Failed to authenticate with Wallabag API")
        return 1
    
    print("Authenticated with Wallabag API")
    
    # Get all entries without the "parsed" tag
    print(f"Fetching entries without the '{WALLABAG_PARSED_TAG}' tag")
    entries = wallabag.get_entries_without_tag(WALLABAG_PARSED_TAG)
    
    if not entries:
        print("No unparsed entries found in Wallabag")
    else:
        print(f"Found {len(entries)} unparsed entries")
        
        # Process each entry
        for entry in entries:
            process_wallabag_entry(wallabag, entry)
    
    # Process existing bookmark notes
    print("Processing existing bookmark notes")
    process_existing_bookmark_notes(wallabag)
    
    print("Wallabag processing complete")
    return 0
