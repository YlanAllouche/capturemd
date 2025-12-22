#!/usr/bin/env python3
# capture_youtube_videos.py

import subprocess
import json
from datetime import datetime

def get_video_info(video_id):
    """Get information about a YouTube video using yt-dlp."""
    try:
        # Run yt-dlp as a subprocess to get video information
        cmd = [
            'yt-dlp',
            f'https://www.youtube.com/watch?v={video_id}',
            '--dump-json',
            '--no-playlist'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        video_info = json.loads(result.stdout)
        
        return video_info
    except subprocess.CalledProcessError as e:
        print(f"Error running yt-dlp: {e}")
        print(f"stderr: {e.stderr}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing yt-dlp output: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

def parse_note(frontmatter):
    """Parse a YouTube video note and update its frontmatter."""
    video_id = frontmatter.get('locator')
    if not video_id:
        print("No video ID found in frontmatter.")
        return None
    
    video_info = get_video_info(video_id)
    if not video_info:
        print(f"Failed to get information for video {video_id}")
        return None
    
    # Get the best thumbnail
    thumbnail = video_info.get('thumbnail', '')
    
    # Extract channel information
    channel_name = video_info.get('channel', video_info.get('uploader', ''))
    channel_id = video_info.get('channel_id', '')
    channel_url = f"https://www.youtube.com/channel/{channel_id}" if channel_id else ''
    
    # Create RSS feed URL for the channel
    channel_feed = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}" if channel_id else ''
    date_str = video_info.get('upload_date', '') 
    date_obj = datetime.strptime(date_str, "%Y%m%d")
    upload_date = date_obj.strftime("%Y-%m-%d")
    
    # Preserve the cache flag if it's already set to true
    cache_value = frontmatter.get('cache', True)
    
    # Preserve the published_date if it exists
    published_date = frontmatter.get('published_date')
    
    # Update frontmatter with video information
    updated_frontmatter = frontmatter.copy()
    updated_frontmatter.update({
        'title': video_info.get('title', ''),
        'duration': int(video_info.get('duration', 0)),  # Keep as integer seconds
        'date': datetime.now().date(),  # Date type without quotes
        'upload_date': upload_date,
        'watched_on_date': None,
        'scope': 'youtube',
        'watched': False,
        'cache': cache_value,  # Preserve existing cache value
        'tags': ['inbox'],
        'class': ['video', 'youtube', 'content', 'resource'],
        'type': 'video',
        'topics': [],
        'url': f"https://www.youtube.com/watch?v={video_id}",
        'thumbnail': thumbnail,
        'channel': channel_name,
        'channel_id': channel_id,
        'channel_url': channel_url,
        'channel_feed': channel_feed
    })
    
    # Add published_date if it exists
    if published_date:
        updated_frontmatter['published_date'] = published_date
    
    return updated_frontmatter, f"\n![thumbnail]({thumbnail})\n"
