#!/usr/bin/env python3
# capture_steam.py

import requests
import json
from datetime import datetime

def get_steam_game_info(app_id):
    """Get information about a Steam game using the Steam API."""
    try:
        # Use the Steam API to get game details
        url = f"https://store.steampowered.com/api/appdetails/?appids={app_id}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36"
        }
        
        print(f"Fetching Steam API data from: {url}")
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            print(f"Steam API request failed with status code: {response.status_code}")
            print(f"Response content: {response.text[:200]}...")
            return None
        
        try:
            data = response.json()
            print(f"Raw API response: {data.keys()}")
            
            # Check if request was successful
            if not data:
                print("Empty response from Steam API")
                return None
                
            # Convert app_id to string for comparison since API uses string keys
            app_id_str = str(app_id)
            if app_id_str not in data:
                print(f"App ID {app_id} not found in response")
                print(f"Available keys: {data.keys()}")
                return None
                
            if not data[app_id_str].get('success'):
                print(f"API returned success=false for app ID {app_id}")
                return None
            
            # Extract the game data
            game_data = data[app_id_str]['data']
            return game_data
            
        except json.JSONDecodeError as e:
            print(f"Error parsing Steam API response: {e}")
            print(f"Response content: {response.text[:200]}...")
            return None
        
    except requests.RequestException as e:
        print(f"Request error fetching Steam game data: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error in get_steam_game_info: {e}")
        import traceback
        traceback.print_exc()
        return None

def parse_note(frontmatter):
    """Parse a Steam game note and update its frontmatter."""
    app_id = frontmatter.get('locator')
    if not app_id:
        print("No Steam app ID found in frontmatter.")
        return None
    
    game_info = get_steam_game_info(app_id)
    if not game_info:
        print(f"Failed to get information for Steam game {app_id}")
        return None
    
    # Get the header image
    header_image = game_info.get('header_image', '')
    
    # Extract developer and publisher information 
    developers = game_info.get('developers', [])
    publishers = game_info.get('publishers', [])
    
    # Extract release date
    release_date = None
    if 'release_date' in game_info and 'date' in game_info['release_date']:
        date_str = game_info['release_date']['date']
        try:
            # Try to parse the date in multiple formats
            for fmt in ["%d %b, %Y", "%b %d, %Y", "%B %d, %Y"]:
                try:
                    release_date = datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
                    break
                except ValueError:
                    continue
        except Exception as e:
            print(f"Error parsing release date '{date_str}': {e}")
    
    updated_frontmatter = frontmatter.copy()
    updated_frontmatter.update({
        'title': game_info.get('name', ''),
        'date': datetime.now().date(),  # Date type without quotes
        'news': f"https://steamcommunity.com/app/{app_id}/allnews/",
        'steamdb': f"https://steamdb.info/app/{app_id}/",
        'release_date': release_date,
        'scope': 'steam',
        'playing': False,
        'tags': ['inbox'],
        'class': ['game', 'resource'],
        'type': 'game',
        'topics': [],
        'url': f"https://store.steampowered.com/app/{app_id}",
        'thumbnail': header_image,
        'developers': developers,
        'publishers': publishers,
        'metacritic_score': game_info.get('metacritic', {}).get('score') if 'metacritic' in game_info else None,
        'description': game_info.get('short_description', '')
    })
    
    # Create the additional markdown content with the header image and description
    additional_content = f"\n![banner]({header_image})\n\n"
    
    return updated_frontmatter, additional_content
