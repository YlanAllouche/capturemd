#!/usr/bin/env python3
# error_logger.py - Centralized error logging utility for structured JSON output

import json
import sys
import traceback
from datetime import datetime
from typing import Optional, Dict, Any


def log_error(
    context: Dict[str, Any],
    error: Exception,
    error_type: Optional[str] = None,
    subprocess_info: Optional[Dict[str, Any]] = None,
    **extra
):
    """
    Log a structured error as JSON to stderr.
    
    Args:
        context: Dictionary with context info (file, entry_id, operation, etc.)
        error: The exception that occurred
        error_type: Optional error classification (network_error, parsing_error, etc.)
        subprocess_info: Optional subprocess details (command, stderr, exit_code)
        **extra: Additional fields to include in the error JSON
    """
    error_data = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "level": "error",
        "context": context,
        "error": {
            "type": error_type or type(error).__name__,
            "message": str(error),
            "details": traceback.format_exc() if error else None
        }
    }
    
    # Add subprocess info if provided
    if subprocess_info:
        error_data["subprocess"] = subprocess_info
    
    # Add any extra fields
    for key, value in extra.items():
        error_data[key] = value
    
    # Write to stderr
    json.dump(error_data, sys.stderr)
    sys.stderr.write("\n")
    sys.stderr.flush()


def classify_ytdlp_error(stderr_output: str, exit_code: int) -> str:
    """
    Classify yt-dlp errors based on stderr output patterns.
    
    Args:
        stderr_output: The stderr output from yt-dlp
        exit_code: The exit code from yt-dlp
        
    Returns:
        str: Error type classification
    """
    stderr_lower = stderr_output.lower()
    
    # Network-related errors
    if any(pattern in stderr_lower for pattern in [
        "unable to download",
        "http error",
        "connection",
        "timeout",
        "network",
        "urlopen error"
    ]):
        return "network_error"
    
    # Geo-restriction errors (check before video_unavailable due to overlapping patterns)
    if any(pattern in stderr_lower for pattern in [
        "not available in your country",
        "not made this video available in your country",
        "geo-restricted",
        "geo restricted"
    ]):
        return "geo_restriction"
    
    # Permission/authentication errors
    if any(pattern in stderr_lower for pattern in [
        "sign in",
        "age-restricted",
        "restricted",
        "members-only",
        "confirm your age",
        "login required",
        "requires payment",
        "paid content"
    ]):
        return "permission_error"
    
    # Video unavailable errors
    if any(pattern in stderr_lower for pattern in [
        "video unavailable",
        "video has been removed",
        "this video is not available",
        "not made this video available",
        "private video",
        "this video is private",
        "deleted",
        "video is no longer available",
        "blocked"
    ]):
        return "video_unavailable"
    
    # Format errors
    if any(pattern in stderr_lower for pattern in [
        "no video formats",
        "format not available",
        "requested format",
        "no suitable formats"
    ]):
        return "format_error"
    
    # Unknown error
    return "unknown_error"


def log_subprocess_error(
    context: Dict[str, Any],
    command: list,
    exit_code: int,
    stdout: str = "",
    stderr: str = "",
    error_type: Optional[str] = None
):
    """
    Log a subprocess error with full command and output details.
    
    Args:
        context: Dictionary with context info (file, entry_id, operation, etc.)
        command: The command that was executed
        exit_code: The exit code from the subprocess
        stdout: The stdout output
        stderr: The stderr output
        error_type: Optional error classification (will auto-classify for yt-dlp)
    """
    # Auto-classify yt-dlp errors
    if "yt-dlp" in " ".join(command) and not error_type:
        error_type = classify_ytdlp_error(stderr, exit_code)
    
    subprocess_info = {
        "command": " ".join(command),
        "exit_code": exit_code,
        "stdout": stdout.strip() if stdout else "",
        "stderr": stderr.strip() if stderr else ""
    }
    
    # Create a pseudo-exception for logging
    error_msg = f"Subprocess failed with exit code {exit_code}"
    
    error_data = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "level": "error",
        "context": context,
        "error": {
            "type": error_type or "subprocess_error",
            "message": error_msg,
            "details": stderr.strip() if stderr else stdout.strip()
        },
        "subprocess": subprocess_info
    }
    
    # Write to stderr
    json.dump(error_data, sys.stderr)
    sys.stderr.write("\n")
    sys.stderr.flush()
