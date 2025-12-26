#!/usr/bin/env python3
# capture_freshrss.py - Handle FreshRSS starred items

import json
import os
import re
import requests
import yaml
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import urllib.parse

from capturemd.url_processor import (
    is_youtube_video, is_github_repo, is_reddit_thread, 
    is_steam_game, is_hackernews_item, is_google_search,
    process_url
)

# FreshRSS API constants - loaded from environment variables
FRESHRSS_URL = os.getenv("FRESHRSS_URL", "")
FRESHRSS_USERNAME = os.getenv("FRESHRSS_USERNAME", "")
FRESHRSS_PASSWORD = os.getenv("FRESHRSS_PASSWORD", "")

class FreshRSSAPI:
    """Client for interacting with the FreshRSS API using Google Reader API compatibility."""
    
    def __init__(self):
        self.url = FRESHRSS_URL
        self.username = FRESHRSS_USERNAME
        self.password = FRESHRSS_PASSWORD
        self.auth_token = None
    
    def authenticate(self) -> bool:
        """
        Authenticate with the FreshRSS API and get an auth token.
        
        Returns:
            bool: True if authentication was successful, False otherwise.
        """
        auth_url = f"{self.url}/accounts/ClientLogin"
        payload = {
            "Email": self.username,
            "Passwd": self.password
        }
        
        try:
            response = requests.post(auth_url, data=payload)
            response.raise_for_status()
            
            # Extract the Auth token from the response
            for line in response.text.splitlines():
                if line.startswith("Auth="):
                    self.auth_token = line.split("=", 1)[1]
                    return True
            
            return False
        except requests.exceptions.RequestException as e:
            print(f"Authentication error: {e}")
            return False
    
    def get_headers(self, content_type="application/json") -> Dict[str, str]:
        """
        Get headers with authentication token.
        
        Args:
            content_type (str): Content type header value. Defaults to "application/json".
            
        Returns:
            Dict[str, str]: Headers for API requests.
        """
        if not self.auth_token and not self.authenticate():
            raise Exception("Failed to authenticate with FreshRSS API")
        
        return {
            "Authorization": f"GoogleLogin auth={self.auth_token}",
            "Content-Type": content_type
        }
    
    def get_starred_items(self, continuation: Optional[str] = None) -> Dict[str, Any]:
        """
        Get starred items from FreshRSS.
        
        Args:
            continuation (Optional[str]): Continuation token for pagination.
            
        Returns:
            Dict[str, Any]: Response containing starred items.
        """
        starred_url = f"{self.url}/reader/api/0/stream/contents/user/-/state/com.google/starred"
        params = {"n": 100}  # Number of items to fetch
        
        if continuation:
            params["c"] = continuation
        
        try:
            response = requests.get(
                starred_url,
                params=params,
                headers=self.get_headers()
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error getting starred items: {e}")
            return {"items": []}
    
    def get_all_starred_items(self) -> List[Dict[str, Any]]:
        """
        Get all starred items from FreshRSS with pagination.
        
        Returns:
            List[Dict[str, Any]]: All starred items.
        """
        all_items = []
        continuation = None
        
        while True:
            result = self.get_starred_items(continuation)
            items = result.get("items", [])
            
            if not items:
                break
                
            all_items.extend(items)
            
            # Get continuation token for next page
            continuation = result.get("continuation")
            if not continuation:
                break
        
        return all_items
    
    def unstar_item(self, item_id: str) -> bool:
        """
        Remove star from an item.
        
        Args:
            item_id (str): ID of the item to unstar.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        edit_tag_url = f"{self.url}/reader/api/0/edit-tag"
        form_data = {
            "i": item_id,
            "r": "user/-/state/com.google/starred"  # 'r' means remove tag
        }
        
        try:
            # Use form data and appropriate content type for edit-tag endpoint
            response = requests.post(
                edit_tag_url,
                data=form_data,
                headers=self.get_headers("application/x-www-form-urlencoded")
            )
            response.raise_for_status()
            return "OK" in response.text
        except requests.exceptions.RequestException as e:
            print(f"Error unstarring item {item_id}: {e}")
            return False


def extract_tags_from_categories(categories: List[str]) -> List[str]:
    """
    Extract tags from FreshRSS categories.
    
    Args:
        categories (List[str]): List of category strings.
        
    Returns:
        List[str]: Extracted tags.
    """
    tags = []
    
    for category in categories:
        # Look for user-defined labels
        if 'user/-/label/' in category:
            # Extract the part after 'user/-/label/'
            label = category.split('user/-/label/', 1)[1]
            # Split by underscore and add each part as a tag
            tags.extend(label.split('_'))
    
    # Always add 'inbox' tag
    if 'inbox' not in tags:
        tags.append('inbox')
    
    return tags


def identify_url_type(url: str) -> str:
    """
    Identify the type of URL based on existing patterns.
    
    Args:
        url (str): URL to identify.
        
    Returns:
        str: URL type or "default" if no specific type.
    """
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


def extract_hn_comments_url(item: Dict[str, Any]) -> Optional[str]:
    """
    Extract Hacker News comments URL from a FreshRSS item.
    
    Args:
        item (Dict[str, Any]): The FreshRSS item to check
        
    Returns:
        Optional[str]: The HN comments URL if found, None otherwise
    """
    # Check if this is from Hacker News
    origin = item.get("origin", {})
    is_hn = False
    
    # Check if the origin htmlUrl is Hacker News
    if origin.get("htmlUrl", "").startswith("https://news.ycombinator.com"):
        is_hn = True
    
    # Or check if the origin title is Hacker News
    elif origin.get("title", "") == "Hacker News":
        is_hn = True
    
    if not is_hn:
        return None
    
    # Look for comments URL in summary content
    summary = item.get("summary", {}).get("content", "")
    
    # Try to extract a Hacker News item URL using regex
    match = re.search(r'href="(https://news\.ycombinator\.com/item\?id=\d+)"', summary)
    if match:
        return match.group(1)
    
    return None


def get_published_date(item: Dict[str, Any]) -> Optional[str]:
    """
    Extract the published date from a FreshRSS item.
    
    Args:
        item (Dict[str, Any]): The FreshRSS item
        
    Returns:
        Optional[str]: The published date in YYYY-MM-DD format, or None if not available
    """
    published_timestamp = item.get("published")
    if published_timestamp:
        try:
            # Convert Unix timestamp to datetime object
            published_date = datetime.fromtimestamp(published_timestamp)
            # Format as YYYY-MM-DD
            return published_date.strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            pass
    return None


def should_cache_youtube(tags: List[str]) -> bool:
    """
    Determine if a YouTube video should be cached based on tags.
    
    Args:
        tags (List[str]): List of tags
        
    Returns:
        bool: True if the video should be cached, False otherwise
    """
    return "news" in tags or "feed" in tags


def is_podcast(tags: List[str]) -> bool:
    """
    Determine if an item is a podcast based on tags.
    
    Args:
        tags (List[str]): List of tags
        
    Returns:
        bool: True if the item is a podcast, False otherwise
    """
    return "podcast" in tags


def extract_podcast_description(item: Dict[str, Any]) -> str:
    """
    Extract a description from a FreshRSS item for podcast use.
    
    Args:
        item (Dict[str, Any]): The FreshRSS item
        
    Returns:
        str: The extracted description or an empty string
    """
    # Try to get content from summary
    if "summary" in item and "content" in item["summary"]:
        # Remove HTML tags from content for clean description
        import re
        content = item["summary"]["content"]
        description = re.sub(r'<[^>]*>', ' ', content)
        description = re.sub(r'\s+', ' ', description).strip()
        return description[:500]  # Limit length
    
    # Try to get content from other fields
    if "content" in item and "content" in item["content"]:
        content = item["content"]["content"]
        import re
        description = re.sub(r'<[^>]*>', ' ', content)
        description = re.sub(r'\s+', ' ', description).strip()
        return description[:500]  # Limit length
    
    return ""

def extract_channel_from_item(item: Dict[str, Any], tags: List[str]) -> str:
    """
    Extract the channel name from a FreshRSS item.
    
    Args:
        item (Dict[str, Any]): The FreshRSS item
        tags (List[str]): List of tags
        
    Returns:
        str: The extracted channel name or "Unknown"
    """
    # First try to get it from the feed origin
    if "origin" in item and "title" in item["origin"]:
        return item["origin"]["title"]
    
    # Then try from tags
    for tag in tags:
        if tag != "podcast" and len(tag) > 3:  # Avoid short tags
            return tag.capitalize()
    
    return "Unknown"

def process_podcast_item(item: Dict[str, Any], url: str, title: str, 
                         published_date: Optional[str], tags: List[str]) -> Optional[str]:
    """
    Process a podcast item.
    
    Args:
        item (Dict[str, Any]): The original FreshRSS item for additional metadata
        url (str): Podcast URL
        title (str): Podcast title
        published_date (Optional[str]): Published date
        tags (List[str]): List of tags
        
    Returns:
        Optional[str]: Path to the created note, or None if failed
    """
    from capturemd.capture_podcast import process_podcast
    
    # Get description from item content if available
    description = extract_podcast_description(item)
    
    # Get the channel name
    channel = extract_channel_from_item(item, tags)
    
    # Create a copy of tags without the "podcast" tag
    processed_tags = [tag for tag in tags if tag != "podcast"]
    
    # Make sure we have at least the inbox tag
    if not processed_tags:
        processed_tags = ["inbox"]
    
    print(f"Processing podcast: {title} from {channel}")
    print(f"Description: {description[:100]}...")  # Show part of description
    print(f"Tags: {processed_tags}")
    
    return process_podcast(
        url=url,
        title=title,
        channel=channel,
        description=description,
        published_date=published_date or "",
        tags=processed_tags
    )


def process_freshrss_item(item: Dict[str, Any]) -> Optional[str]:
    """
    Process a single FreshRSS starred item.
    
    Args:
        item (Dict[str, Any]): The FreshRSS item to process.
        
    Returns:
        Optional[str]: Path to the created/existing note, special string for Google searches,
                       or None if skipped or failed.
    """
    item_id = item.get("id", "")
    title = item.get("title", "")
    url = item.get("alternate", [{}])[0].get("href", "") if item.get("alternate") else ""
    categories = item.get("categories", [])
    
    if not url:
        print(f"Item {item_id} has no URL, skipping")
        return None
    
    # Extract the published date
    published_date = get_published_date(item)
    if published_date:
        print(f"Published date: {published_date}")
    
    # Check if this is a Hacker News item and extract the comments URL
    hn_comments_url = extract_hn_comments_url(item)
    if hn_comments_url:
        print(f"Found Hacker News comments URL: {hn_comments_url}")
        # Use the HN comments URL instead of the target URL
        url = hn_comments_url
    
    print(f"Processing FreshRSS item: {title} ({url})")
    
    # Extract tags from categories
    tags = extract_tags_from_categories(categories)
    print(f"Extracted tags: {tags}")
    
    # Check if item is a podcast
    if is_podcast(tags):
        print(f"Processing as podcast: {title}")
        note_path = process_podcast_item(item, url, title, published_date, tags)
        return note_path
    
    # Identify URL type
    url_type = identify_url_type(url)
    print(f"URL type: {url_type}")
    
    # Process the URL through capturemd, passing tags
    note_path = process_url(url, tags=tags)
    
    if not note_path:
        print(f"Failed to process URL: {url}")
        return None
    
    if note_path == "google_search_processed":
        # Google search processing is special case, already completed
        return note_path
    
    # The tags are now added during initial note creation,
    # and will be preserved during parsing
    
    # If it's a YouTube video and has 'news' or 'feed' tag, set cache to true
    if url_type == "youtube" and should_cache_youtube(tags):
        try:
            with open(note_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Extract YAML frontmatter
            frontmatter_match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
            if frontmatter_match:
                yaml_text = frontmatter_match.group(1)
                frontmatter = yaml.safe_load(yaml_text)
                rest_content = content[frontmatter_match.end():]
                
                # Set cache to true
                frontmatter["cache"] = True
                
                # Add published_date if available
                if published_date:
                    frontmatter["published_date"] = published_date
                
                # Write back to file
                yaml_text = yaml.dump(frontmatter, default_flow_style=False)
                with open(note_path, "w", encoding="utf-8") as f:
                    f.write(f"---\n{yaml_text}---{rest_content}")
                
                print(f"Set cache=true for YouTube video: {note_path}")
        except Exception as e:
            print(f"Error setting cache=true: {e}")
    
    # Add published_date to frontmatter if available
    elif published_date:
        try:
            with open(note_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Extract YAML frontmatter
            frontmatter_match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
            if frontmatter_match:
                yaml_text = frontmatter_match.group(1)
                frontmatter = yaml.safe_load(yaml_text)
                rest_content = content[frontmatter_match.end():]
                
                # Add published_date
                frontmatter["published_date"] = published_date
                
                # Write back to file
                yaml_text = yaml.dump(frontmatter, default_flow_style=False)
                with open(note_path, "w", encoding="utf-8") as f:
                    f.write(f"---\n{yaml_text}---{rest_content}")
                
                print(f"Added published_date to frontmatter: {note_path}")
        except Exception as e:
            print(f"Error adding published_date: {e}")
    
    return note_path


def process_freshrss() -> int:
    """
    Process FreshRSS starred items.
    
    This function:
    1. Authenticates with the FreshRSS API
    2. Gets all starred items
    3. Processes each item based on URL type
    4. Unstars successfully processed items
    
    Returns:
        int: 0 for success, 1 for failure
    """
    # Initialize FreshRSS API client
    freshrss = FreshRSSAPI()
    
    if not freshrss.authenticate():
        print("Failed to authenticate with FreshRSS API")
        return 1
    
    print("Authenticated with FreshRSS API")
    
    # Get all starred items
    print("Fetching starred items from FreshRSS")
    items = freshrss.get_all_starred_items()
    
    if not items:
        print("No starred items found in FreshRSS")
        return 0
    
    print(f"Found {len(items)} starred items")
    
    # Process each item
    for item in items:
        item_id = item.get("id", "")
        
        # Process the item
        note_path = process_freshrss_item(item)
        
        # If successfully processed, unstar the item
        if note_path:
            # Only unstar if it's not a default bookmark (which we're skipping)
            success = freshrss.unstar_item(item_id)
            if success:
                print(f"Unstarred item {item_id} from FreshRSS")
            else:
                print(f"Failed to unstar item {item_id} from FreshRSS")
    
    print("FreshRSS processing complete")
    return 0