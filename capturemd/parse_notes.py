#!/usr/bin/env python3
# parse_notes.py

import importlib.util
import json
import os
import re
import subprocess
from datetime import date, datetime
from pathlib import Path

import yaml

from .paths import MARKDOWN_DIR

try:
    from capturemd.error_logger import log_error
except ImportError:
    from error_logger import log_error

# Paths
SCRIPTS_DIR = Path(__file__).parent


# Custom YAML representer for date objects
def date_representer(dumper, data):
    return dumper.represent_scalar("tag:yaml.org,2002:timestamp", data.isoformat())


# Register the date representer
yaml.add_representer(date, date_representer)


def extract_frontmatter(content):
    """Extract YAML frontmatter from markdown content."""
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if match:
        try:
            frontmatter = yaml.safe_load(match.group(1))
            rest_content = content[match.end() :]
            return frontmatter, rest_content
        except yaml.YAMLError:
            return None, content
    return None, content


def save_with_frontmatter(file_path, frontmatter, content):
    """Save markdown file with updated frontmatter."""
    frontmatter_yaml = yaml.dump(frontmatter, sort_keys=False, default_flow_style=False)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"---\n{frontmatter_yaml}---\n{content}")


def find_unparsed_notes(locator=None):
    """Find all notes with parsed=false, optionally filtered by locator."""
    unparsed_notes = []

    for directory in MARKDOWN_DIR.glob("**/"):
        for file_path in directory.glob("*.md"):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            frontmatter, rest_content = extract_frontmatter(content)
            if frontmatter and frontmatter.get("parsed") is False:
                if locator is not None:
                    if frontmatter.get("locator") != locator:
                        continue
                unparsed_notes.append(
                    {
                        "path": file_path,
                        "frontmatter": frontmatter,
                        "content": rest_content,
                    }
                )

    return unparsed_notes


def load_parser_module(scope):
    """Load the parser module for the given scope."""
    module_name = f"capture_{scope}"
    module_path = SCRIPTS_DIR / f"{module_name}.py"

    if not module_path.exists():
        print(f"Parser module not found: {module_path}")
        error = FileNotFoundError(f"Parser module not found: {module_path}")
        log_error(
            context={
                "operation": "load_parser_module",
                "scope": scope,
                "module_path": str(module_path),
            },
            error=error,
            error_type="module_not_found",
        )
        return None

    try:
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
    except Exception as e:
        print(f"Error loading parser module for {scope}: {e}")
        log_error(
            context={
                "operation": "load_parser_module",
                "scope": scope,
                "module_path": str(module_path),
            },
            error=e,
            error_type="module_load_error",
        )
        return None

    return None


def parse_note(note):
    """Parse a single note using its scope-specific parser."""
    scope = note["frontmatter"].get("scope")
    note_path = str(note["path"])
    note_id = note["frontmatter"].get("id", "unknown")
    locator = note["frontmatter"].get("locator", "unknown")

    if not scope:
        print(f"No scope defined for note: {note_path}")
        error = ValueError("No scope defined for note")
        log_error(
            context={
                "operation": "parse",
                "file": note_path,
                "entry_id": note_id,
                "locator": locator,
            },
            error=error,
            error_type="validation_error",
        )
        return False

    parser_module = load_parser_module(scope)
    if not parser_module:
        # Error already logged in load_parser_module
        return False

    try:
        # Save original tags before parsing
        original_tags = note["frontmatter"].get("tags", [])

        # Call the parse_note function from the module
        parser_result = parser_module.parse_note(note["frontmatter"])

        # Check if the parser returned a tuple with frontmatter and additional content
        if isinstance(parser_result, tuple) and len(parser_result) == 2:
            updated_frontmatter, additional_content = parser_result
            content = additional_content + note["content"]
        else:
            updated_frontmatter = parser_result
            content = note["content"]

        if updated_frontmatter:
            # Update the frontmatter
            updated_frontmatter["parsed"] = True

            # Merge tags (keep both original and new tags, removing duplicates)
            new_tags = updated_frontmatter.get("tags", [])
            merged_tags = list(set(original_tags + new_tags))
            updated_frontmatter["tags"] = merged_tags

            save_with_frontmatter(note["path"], updated_frontmatter, content)
            print(f"Successfully parsed note: {note_path}")
            return True
        else:
            print(f"Failed to parse note: {note_path}")
            error = RuntimeError("Parser returned None or empty result")
            log_error(
                context={
                    "operation": "parse",
                    "file": note_path,
                    "entry_id": note_id,
                    "locator": locator,
                    "scope": scope,
                },
                error=error,
                error_type="parsing_error",
            )
            return False
    except Exception as e:
        print(f"Error parsing note {note_path}: {e}")
        log_error(
            context={
                "operation": "parse",
                "file": note_path,
                "entry_id": note_id,
                "locator": locator,
                "scope": scope,
            },
            error=e,
            error_type="parsing_error",
        )
        return False


def parse_notes(locator=None):
    """Parse unparsed notes, optionally only the one with the given locator."""
    unparsed_notes = find_unparsed_notes(locator)
    print(f"Found {len(unparsed_notes)} unparsed notes.")

    for note in unparsed_notes:
        parse_note(note)


def main():
    parse_notes()


if __name__ == "__main__":
    main()
