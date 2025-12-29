#\!/usr/bin/env python3
# test_cache_manager.py - Test the cache manager

import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys
import os

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from capturemd.cache_manager import (
    extract_frontmatter,
    get_youtube_cached_ids,
    download_youtube_video,
    delete_youtube_video,
    manage_youtube_cache
)

class TestCacheManager(unittest.TestCase):
    
    @patch('capturemd.cache_manager.open')
    @patch('yaml.safe_load')
    def test_extract_frontmatter(self, mock_yaml_load, mock_open):
        # Setup
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = """---
id: 123
locator: abc123
cache: true
---
content here
"""
        mock_open.return_value = mock_file
        mock_yaml_load.return_value = {
            'id': '123',
            'locator': 'abc123',
            'cache': True
        }
        
        # Execute
        result = extract_frontmatter('dummy_path')
        
        # Assert
        self.assertEqual(result, {
            'id': '123',
            'locator': 'abc123',
            'cache': True
        })
    
    @patch('capturemd.cache_manager.YOUTUBE_CACHE_DIR')
    def test_get_youtube_cached_ids(self, mock_cache_dir):
        # Setup
        mock_file1 = MagicMock()
        mock_file1.is_file.return_value = True
        mock_file1.stem = 'video1'
        
        mock_file2 = MagicMock()
        mock_file2.is_file.return_value = True
        mock_file2.stem = 'video2'
        
        mock_dir = MagicMock()
        mock_dir.is_file.return_value = False
        
        mock_cache_dir.exists.return_value = True
        mock_cache_dir.iterdir.return_value = [mock_file1, mock_file2, mock_dir]
        
        # Execute
        result = get_youtube_cached_ids()
        
        # Assert
        self.assertEqual(set(result), {'video1', 'video2'})
    
    @patch('subprocess.run')
    @patch('capturemd.cache_manager.YOUTUBE_CACHE_DIR')
    def test_download_youtube_video(self, mock_cache_dir, mock_subprocess_run):
        # Setup
        mock_cache_dir.mkdir = MagicMock()
        
        # Execute
        result = download_youtube_video('abc123')
        
        # Assert
        self.assertTrue(result)
        mock_cache_dir.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_subprocess_run.assert_called_once()
    
    @patch('capturemd.cache_manager.YOUTUBE_CACHE_DIR')
    def test_delete_youtube_video(self, mock_cache_dir):
        # Setup
        mock_file1 = MagicMock()
        mock_file2 = MagicMock()
        
        mock_cache_dir.glob.return_value = [mock_file1, mock_file2]
        
        # Execute
        result = delete_youtube_video('abc123')
        
        # Assert
        self.assertTrue(result)
        mock_file1.unlink.assert_called_once()
        mock_file2.unlink.assert_called_once()
    
    @patch('capturemd.cache_manager.get_youtube_cached_ids')
    @patch('capturemd.cache_manager.extract_frontmatter')
    @patch('capturemd.cache_manager.download_youtube_video')
    @patch('capturemd.cache_manager.delete_youtube_video')
    @patch('capturemd.cache_manager.YOUTUBE_NOTES_DIR')
    def test_manage_youtube_cache(self, mock_notes_dir, mock_delete, mock_download, 
                                 mock_extract_frontmatter, mock_get_cached_ids):
        # Setup
        mock_notes_dir.exists.return_value = True
        
        mock_file1 = MagicMock()
        mock_file2 = MagicMock()
        
        mock_notes_dir.glob.return_value = [mock_file1, mock_file2]
        
        mock_extract_frontmatter.side_effect = [
            {'locator': 'video1', 'cache': True},
            {'locator': 'video2', 'cache': False}
        ]
        
        mock_get_cached_ids.return_value = {'video2', 'video3'}
        
        # Execute
        manage_youtube_cache()
        
        # Assert
        # Should delete video2 (cache=False) and video3 (not in notes)
        mock_delete.assert_any_call('video2')
        mock_delete.assert_any_call('video3')
        
        # Should download video1 (cache=True but not in cached_ids)
        mock_download.assert_called_once_with('video1')

if __name__ == '__main__':
    unittest.main()
