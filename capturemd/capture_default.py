#!/usr/bin/env python3
# capture_default.py

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import shlex

def get_page_info(url):
    """Get basic information about a web page."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract title
        title = soup.title.string.strip() if soup.title else url
        
        # Extract description
        description = ""
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            description = meta_desc['content']
        
        return {
            'title': title,
            'description': description,
            'url': url
        }
    except Exception as e:
        print(f"Error fetching page info: {e}")
        return {
            'title': url,
            'description': '',
            'url': url
        }
def shellscape(input_string, max_length=100):
    # Convert to string (in case of non-string input)
    input_string = str(input_string)
    
    # Remove newlines, tabs, and multiple whitespaces
    input_string = re.sub(r'[\n\r\t]+', ' ', input_string)
    input_string = re.sub(r'\s+', ' ', input_string)
    
    # Trim leading and trailing whitespace
    input_string = input_string.strip()
    
    # Escape shell special characters
    escaped_string = shlex.quote(input_string)
    
    # Additional sanitization
    sanitized_string = re.sub(r'[^\w\s.-]', '', escaped_string)
    
    # Truncate to max_length
    truncated_string = sanitized_string[:max_length]
    
    return truncated_string

def parse_note(frontmatter):
    """Parse a default URL note and update its frontmatter."""
    url = frontmatter.get('url')
    if not url:
        print("No URL found in frontmatter.")
        return None
    
    page_info = get_page_info(url)
    
    # Update frontmatter with page information
    updated_frontmatter = frontmatter.copy()
    updated_frontmatter.update({
        'title': shellscape(page_info.get('title', '')),
        'description': page_info.get('description', ''),
        'date': datetime.now().date(),
        'scope': None,
        'class': ['webpage', 'bookmark','resource'],
        'type': 'bookmark',
        'tags': ['inbox'],
        'topics': []
    })
    
    # Return just the frontmatter since we don't have additional content for default URLs
    return updated_frontmatter
