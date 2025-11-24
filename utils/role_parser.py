"""Utility to parse and normalize role strings."""
from typing import List, Set


def parse_roles(role_string: str) -> List[str]:
    """
    Parse comma-separated or space-separated roles into a list.
    
    Args:
        role_string: Role string like "data scientist, machine learning engineer"
        
    Returns:
        List of normalized role strings
    """
    if not role_string:
        return []
    
    # Split by comma first, then by common separators
    roles = []
    
    # Split by comma
    parts = role_string.split(',')
    
    for part in parts:
        part = part.strip()
        if part:
            # Also split by "and" or "&"
            if ' and ' in part.lower():
                subparts = part.split(' and ')
                roles.extend([p.strip() for p in subparts if p.strip()])
            elif ' & ' in part:
                subparts = part.split(' & ')
                roles.extend([p.strip() for p in subparts if p.strip()])
            else:
                roles.append(part)
    
    return [r for r in roles if r]  # Remove empty strings


def get_role_keywords(role_string: str) -> Set[str]:
    """
    Extract keywords from role string for matching.
    
    Args:
        role_string: Role string
        
    Returns:
        Set of keywords for matching
    """
    if not role_string:
        return set()
    
    roles = parse_roles(role_string)
    keywords = set()
    
    for role in roles:
        role_lower = role.lower()
        # Split into words
        words = [w.strip() for w in role_lower.split() if len(w.strip()) > 2]
        keywords.update(words)
        
        # Add common variations
        if "data scientist" in role_lower or "data science" in role_lower:
            keywords.update(["data", "scientist", "science", "analyst", "ml", "machine", "learning"])
        if "machine learning" in role_lower or "ml engineer" in role_lower:
            keywords.update(["machine", "learning", "ml", "ai", "engineer", "data", "scientist"])
        if "ai engineer" in role_lower or "artificial intelligence" in role_lower:
            keywords.update(["ai", "artificial", "intelligence", "engineer", "ml", "machine", "learning"])
        if "engineer" in role_lower:
            keywords.add("engineer")
        if "analyst" in role_lower:
            keywords.add("analyst")
    
    return keywords


def matches_role(job_title: str, job_description: str, role_string: str) -> bool:
    """
    STRICT role matching - job title MUST contain the role keywords.
    
    Args:
        job_title: Job title
        job_description: Job description
        role_string: Comma-separated roles
        
    Returns:
        True if job title matches any role (STRICT matching)
    """
    if not role_string:
        return True  # No filter, match all
    
    # EXCLUDE non-technical roles
    excluded_keywords = [
        "customer success", "product manager", "copywriter", "marketer", "marketing",
        "account executive", "sales", "consultant", "sap", "functional consultant",
        "vp protocol", "strategic account", "growth marketer", "finance data analyst"
    ]
    
    title_lower = job_title.lower()
    desc_lower = job_description.lower()
    
    # If job title contains excluded keywords, reject it
    if any(excluded in title_lower for excluded in excluded_keywords):
        return False
    
    roles = parse_roles(role_string)
    role_lower = role_string.lower()
    
    # STRICT: Role must appear in JOB TITLE (not just description)
    # Define exact role patterns that must appear in title
    required_title_patterns = []
    
    if "data scientist" in role_lower:
        required_title_patterns.extend([
            "data scientist", "data science", "ml engineer", "machine learning engineer",
            "data analyst", "research scientist", "applied scientist"
        ])
    
    if "machine learning" in role_lower or "ml engineer" in role_lower:
        required_title_patterns.extend([
            "machine learning", "ml engineer", "ml", "ai engineer", 
            "data scientist", "research scientist"
        ])
    
    if "ai engineer" in role_lower:
        required_title_patterns.extend([
            "ai engineer", "artificial intelligence", "ml engineer", 
            "machine learning engineer", "ai/ml engineer"
        ])
    
    if "gen ai engineer" in role_lower or "generative ai" in role_lower:
        required_title_patterns.extend([
            "gen ai", "generative ai", "llm engineer", "ai engineer",
            "machine learning engineer", "ml engineer"
        ])
    
    # Also check parsed individual roles
    for role in roles:
        role_l = role.lower()
        if "data scientist" in role_l or "data science" in role_l:
            required_title_patterns.extend(["data scientist", "data science", "ml engineer"])
        if "machine learning" in role_l or "ml" in role_l:
            required_title_patterns.extend(["machine learning", "ml engineer", "ml"])
        if "ai engineer" in role_l or "ai" in role_l:
            required_title_patterns.extend(["ai engineer", "ai", "artificial intelligence"])
        if "engineer" in role_l:
            required_title_patterns.append("engineer")
    
    # Remove duplicates
    required_title_patterns = list(set(required_title_patterns))
    
    # STRICT CHECK: At least one pattern MUST be in the job title
    title_has_role = any(pattern in title_lower for pattern in required_title_patterns)
    
    if not title_has_role:
        return False
    
    # Additional validation: Check that it's not a non-technical role
    # Even if title has "ai", make sure it's an engineering/scientist role
    technical_indicators = ["engineer", "scientist", "developer", "researcher", "analyst", "specialist"]
    has_technical_indicator = any(indicator in title_lower for indicator in technical_indicators)
    
    # For AI/ML roles, require technical indicator
    if any(keyword in role_lower for keyword in ["ai", "ml", "machine learning", "data scientist"]):
        if not has_technical_indicator:
            return False
    
    return True

