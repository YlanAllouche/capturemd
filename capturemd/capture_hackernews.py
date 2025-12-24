#!/usr/bin/env python3


import requests
import json
from datetime import datetime

def get_hackernews_item_info(item_id):
    """Get information about a Hacker News item using the Algolia API."""
    try:
        url = f"https://hn.algolia.com/api/v1/items/{item_id}"
        headers = {
            'User-Agent': 'capturemd/0.1.0'
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        item_data = response.json()
        return item_data
    except requests.RequestException as e:
        print(f"Error fetching Hacker News item: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing Hacker News API response: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

def parse_note(frontmatter):
    """Parse a Hacker News item note and update its frontmatter."""
    item_id = frontmatter.get('locator')
    
    if not item_id:
        print("Missing item ID in frontmatter.")
        return None
    
    item_info = get_hackernews_item_info(item_id)
    if not item_info:
        print(f"Failed to get information for Hacker News item {item_id}")
        return None
    
    # Convert Unix timestamp to date
    created_at = item_info.get('created_at')
    if created_at:
        try:
            created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00')).date()
        except ValueError:
            created_date = ''
    else:
        created_date = ''
    
    # Update frontmatter with item information
    updated_frontmatter = frontmatter.copy()
    updated_frontmatter.update({
        'title': item_info.get('title', ''),
        'date': datetime.now().date(),
        'created_date': created_date, 
        'scope': 'hackernews',
        'tags': ['inbox'],
        'class': ['thread', 'resource'],
        'type': 'thread',
        'topics': [],
        'url': f"https://news.ycombinator.com/item?id={item_id}",
        'target': item_info.get('url', ''),
        'author': item_info.get('author', ''),
        'points': item_info.get('points', 0),
        'num_comments': len(item_info.get('children', [])),
    })
    
    return updated_frontmatter, ""
