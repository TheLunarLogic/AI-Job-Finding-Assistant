"""Query builder utilities for constructing structured search queries."""
from typing import List, Optional
import re


def build_search_query(roles: Optional[List[str]] = None, locations: Optional[List[str]] = None) -> str:
    """
    Build a structured boolean search query from roles and locations.

    Examples:
        roles=["data scientist", "AI Engineer"], locations=["remote", "India"]
        → '("data scientist" OR "AI Engineer") (remote OR India)'

        roles=["ML Engineer"], locations=None
        → '"ML Engineer"'

    Args:
        roles: List of role keywords / titles.
        locations: List of location keywords.

    Returns:
        A structured query string suitable for job search APIs.
    """
    parts: List[str] = []

    if roles:
        # Clean up each role
        cleaned = [r.strip() for r in roles if r.strip()]
        if len(cleaned) == 1:
            parts.append(f'"{cleaned[0]}"')
        elif cleaned:
            quoted = " OR ".join(f'"{r}"' for r in cleaned)
            parts.append(f"({quoted})")

    if locations:
        cleaned_locs = [l.strip() for l in locations if l.strip()]
        if len(cleaned_locs) == 1:
            parts.append(cleaned_locs[0])
        elif cleaned_locs:
            parts.append(f"({' OR '.join(cleaned_locs)})")

    return " ".join(parts) if parts else "software engineer"


def parse_role_input(role: Optional[str]) -> List[str]:
    """
    Parse a free-form role input string into a list of individual roles.

    Handles comma-separated, slash-separated, and 'OR' separated inputs.
    Examples:
        "data scientist, AI Engineer, ML" → ["data scientist", "AI Engineer", "ML"]
        "backend / fullstack" → ["backend", "fullstack"]
    """
    if not role:
        return []
    # Split on comma, slash, or literal ' OR '
    parts = re.split(r"[,/]|\bOR\b", role, flags=re.IGNORECASE)
    return [p.strip() for p in parts if p.strip()]


def parse_location_input(location: Optional[str]) -> List[str]:
    """
    Parse a free-form location input string into a list of locations.

    Examples:
        "remote, India" → ["remote", "India"]
        "New York / San Francisco" → ["New York", "San Francisco"]
    """
    if not location:
        return []
    parts = re.split(r"[,/]|\bOR\b", location, flags=re.IGNORECASE)
    return [p.strip() for p in parts if p.strip()]
