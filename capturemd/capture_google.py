#!/usr/bin/env python3
# capture_google.py - Handle Google search queries

import os
import re
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Optional

# Define the notes file
BROWSER_NOTES_FILE = Path.home() / "share" / "notes" / "browser_notes.md"

def is_google_search(url: str) -> bool:
    """
    Check if the URL is a Google search query.
    
    Args:
        url (str): The URL to check
        
    Returns:
        bool: True if it's a Google search query, False otherwise
    """
    pattern = r'^https?://(www\.)?google\.[a-z.]+/search'
    return bool(re.match(pattern, url))

def extract_google_query(url: str) -> Optional[str]:
    """
    Extract the search query from a Google search URL.
    
    Args:
        url (str): The Google search URL
        
    Returns:
        Optional[str]: The decoded search query, or None if no query found
    """
    if not is_google_search(url):
        return None
    
    # Parse the URL and get the query parameters
    parsed_url = urllib.parse.urlparse(url)
    query_params = urllib.parse.parse_qs(parsed_url.query)
    
    # Get the 'q' parameter (search query)
    if 'q' in query_params:
        return urllib.parse.unquote_plus(query_params['q'][0])
    
    return None

def capture_google_search(url: str) -> bool:
    """
    Capture a Google search query and append it to the browser notes file.
    
    Args:
        url (str): The Google search URL
        
    Returns:
        bool: True if successfully captured, False otherwise
    """
    query = extract_google_query(url)
    if not query:
        print(f"No query found in URL: {url}")
        return False
    
    # Get today's date
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Format the note entry
    note_entry = f"- [*] {query} [tag:: inbox] [date:: {today}]\n"
    
    # Ensure the directory exists
    BROWSER_NOTES_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # Append to the browser notes file
    try:
        # Create the file if it doesn't exist
        if not BROWSER_NOTES_FILE.exists():
            with open(BROWSER_NOTES_FILE, 'w', encoding='utf-8') as f:
                f.write("# Browser Notes\n\n")
        
        # Append the entry
        with open(BROWSER_NOTES_FILE, 'a', encoding='utf-8') as f:
            f.write(note_entry)
        
        print(f"Added Google search query to {BROWSER_NOTES_FILE}")
        return True
    except Exception as e:
        print(f"Error capturing Google search query: {e}")
        return False