#!/usr/bin/env python3
# capture_github_repos.py

import requests
from datetime import datetime
import os
import yaml
import uuid
from pathlib import Path

def get_repo_info(repo_id):
    """Get information about a GitHub repository."""
    owner, repo = repo_id.split('/')
    
    try:
        # Use GitHub API to get repository information
        url = f"https://api.github.com/repos/{owner}/{repo}"
        response = requests.get(url)
        response.raise_for_status()
        
        repo_info = response.json()
        return repo_info
    except requests.RequestException as e:
        print(f"Error fetching GitHub repo info: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

def get_repo_lang(repo_id):
    """Get information about a GitHub repository's languages"""
    owner, repo = repo_id.split('/')
    
    try:
        # Use GitHub API to get repository information
        url = f"https://api.github.com/repos/{owner}/{repo}/languages"
        response = requests.get(url)
        response.raise_for_status()
        
        repo_info = response.json()
        return repo_info
    except requests.RequestException as e:
        print(f"Error fetching GitHub repo's language info: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None


def read_markdown_files():
    """Read all markdown files and extract id and title from frontmatter"""
    markdown_dir = os.path.expanduser("~/share/notes/topic/lang")
    results = []
    
    for filename in os.listdir(markdown_dir):
        if filename.endswith(".md"):
            filepath = os.path.join(markdown_dir, filename)
            with open(filepath, 'r') as file:
                content = file.read()
                
                # Extract YAML frontmatter
                if content.startswith('---'):
                    _, frontmatter, _ = content.split('---', 2)
                    try:
                        metadata = yaml.safe_load(frontmatter)
                        if 'id' in metadata and 'title' in metadata:
                            results.append({
                                'id': metadata['id'],
                                'title': metadata['title']
                            })
                    except yaml.YAMLError:
                        continue
    
    return results

def get_or_create_id(title_string):
    """Check if title exists, return its ID or create new note and return new ID"""
    # First check existing files
    existing_files = read_markdown_files()
    
    # Check for match
    for entry in existing_files:
        if entry['title'].lower() == title_string.lower():
            return entry['id']
    
    # If no match found, create new file
    new_id = str(uuid.uuid4())
    markdown_dir = os.path.expanduser("~/share/notes/topic/lang")
    
    # Create frontmatter content
    frontmatter = {
        'id': new_id,
        'title': title_string,
        'class': ['topic', 'language', 'tech'],
        'type': 'language'
    }
    
    # Create new file content
    content = f"""---
{yaml.dump(frontmatter, default_flow_style=False)}---

"""
    
    # Write new file
    new_filepath = os.path.join(markdown_dir, f"{new_id}.md")
    Path(markdown_dir).mkdir(parents=True, exist_ok=True)
    
    with open(new_filepath, 'w') as file:
        file.write(content)
    
    return new_id

def format_language_links(language_list):
    """
    Takes a list of language names and returns a list of formatted Wikilink-style strings
    with their corresponding UUIDs
    """
    formatted_links = []
    
    for language in language_list:
        uuid = get_or_create_id(language)
        formatted_link = f"[[{uuid}|{language}]]"
        formatted_links.append(formatted_link)
    
    return formatted_links

def parse_langs(repo_id):
    repo_lang= get_repo_lang(repo_id)
    if not repo_lang:
        print(f"Failed to get information for languages {repo_id}")
        return None
    language_list = list(repo_lang.keys())
    langs = format_language_links(language_list)
    return langs

def parse_note(frontmatter):
    """Parse a GitHub repository note and update its frontmatter."""
    repo_id = frontmatter.get('locator')
    if not repo_id:
        print("No repository ID found in frontmatter.")
        return None
    
    repo_info = get_repo_info(repo_id)
    if not repo_info:
        print(f"Failed to get information for repository {repo_id}")
        return None

    langs = parse_langs(repo_id)
    if not langs:
        print(f"Failed to get languages for repository {repo_id}")
        return None

    
    # Update frontmatter with repository information
    updated_frontmatter = frontmatter.copy()
    updated_frontmatter.update({
        'title': repo_info.get('name', ''),
        'owner': repo_info.get('owner', '').get('login', ''),
        'description': repo_info.get('description', ''),
        'date': datetime.now().date(),
        'scope': 'github',
        'class': ['repository', 'github', 'resource'],
        'avatar': repo_info.get('owner', '').get('avatar_url', ''),
        'ssh_url': repo_info.get('ssh_url', ''),
        'git_url': repo_info.get('git_url', ''),
        'git': repo_info.get('clone_url', ''),
        # TODO: Consider adding the license
        'created': datetime.fromisoformat(repo_info.get('created_at', '')) , # TODO: check this is parsed as a date
        'releases': repo_info.get('has_downloads', False),
        'gh_wiki': repo_info.get('has_wiki', False),
        'gh_pages': repo_info.get('has_pages', False),
        'mirror': repo_info.get('mirror_url', ''),
        'main': repo_info.get('default_branch', ''),
        'tags': ['inbox'],
        'type': 'repository',
        'gh_topics': repo_info.get('topics', []),
        'url': repo_info.get('html_url', f"https://github.com/{repo_id}"),
        'stars': repo_info.get('stargazers_count', 0),
        'watchers': repo_info.get('watchers_count', 0),
        'forks': repo_info.get('forks_count', 0),
        'language': langs
    })
    
    # Return just the frontmatter since we don't have additional content for GitHub repos
    return updated_frontmatter
