#!/usr/bin/env python3
# capture_reddit.py

import requests
import json
from datetime import datetime

def get_reddit_thread_info(thread_id, subreddit):
    """Get information about a Reddit thread using the Reddit API."""
    try:
        url = f"https://www.reddit.com/r/{subreddit}/comments/{thread_id}.json"
        headers = {
            'User-Agent': 'capturemd/0.1.0 (by /u/anonymous)'
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        thread_data = response.json()
        
        # The API returns an array with the thread data and comments
        if len(thread_data) > 0 and 'data' in thread_data[0] and 'children' in thread_data[0]['data']:
            thread_info = thread_data[0]['data']['children'][0]['data']
            return thread_info
        
        return None
    except requests.RequestException as e:
        print(f"Error fetching Reddit thread: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing Reddit API response: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

def parse_note(frontmatter):
    """Parse a Reddit thread note and update its frontmatter."""
    thread_id = frontmatter.get('locator')
    subreddit = frontmatter.get('subreddit')
    
    if not thread_id or not subreddit:
        print("Missing thread ID or subreddit in frontmatter.")
        return None
    
    thread_info = get_reddit_thread_info(thread_id, subreddit)
    if not thread_info:
        print(f"Failed to get information for Reddit thread {thread_id}")
        return None
    
    # Convert Unix timestamp to date
    created_utc = thread_info.get('created_utc', 0)
    created_date = datetime.fromtimestamp(created_utc).date()
    
    # Update frontmatter with thread information
    updated_frontmatter = frontmatter.copy()
    updated_frontmatter.update({
        'title': thread_info.get('title', ''),
        'date': datetime.now().date(),
        'created_date': created_date,
        'scope': 'reddit',
        'tags': ['inbox'],
        'class': ['thread', 'resource'],
        'type': 'thread',
        'topics': [],
        'url': f"https://www.reddit.com/r/{subreddit}/comments/{thread_id}/",
        # TODO: Look at thumbnail if one
        # TODO: Look at that `url_overridden_by_dest` field
        # TODO: Look at that `preview` array field
        # TODO: Look into images with the text itself
        # TODO: Look into what happens when sharing just a link
        # TODO: look into media embed thing?
        # TODO: look into media_metadata
        'author': thread_info.get('author', ''),
        'score': thread_info.get('score', 0),
        'num_comments': thread_info.get('num_comments', 0),
        'permalink': thread_info.get('permalink', ''),
        'subreddit': subreddit,
        'selftext': thread_info.get('selftext', '') != ''
    })
    
    # Add thumbnail if available and not a self post
    thumbnail = thread_info.get('thumbnail', '')
    if thumbnail and thumbnail not in ['self', 'default', 'nsfw']:
        return updated_frontmatter, f"\n![thumbnail]({thumbnail})\n"
    
    return updated_frontmatter, ""
