"""RSS feed fetcher for job aggregators like RemoteOK and Arbeitnow."""
import requests
import feedparser
from typing import List, Dict, Optional
from datetime import datetime
from utils.text_processing import clean_html
from utils.role_parser import matches_role


def fetch_remoteok_jobs(
    role: Optional[str] = None,
    max_results: int = 20
) -> List[Dict[str, str]]:
    """
    Fetch jobs from RemoteOK RSS feed.
    
    Args:
        role: Filter by job role/keyword (optional, for flexibility)
        max_results: Maximum number of results
        
    Returns:
        List of job dictionaries
    """
    jobs = []
    
    try:
        # RemoteOK RSS feed - try multiple possible URLs
        urls = [
            "https://remoteok.io/remote-jobs.rss",
            "https://remoteok.com/remote-jobs.rss",
            "https://remoteok.io/api"
        ]
        
        feed = None
        for url in urls:
            try:
                feed = feedparser.parse(url)
                if feed.entries:
                    break
            except:
                continue
        
        if not feed or not feed.entries:
            print("Warning: RemoteOK RSS feed not accessible")
            return []
        
        for entry in feed.entries[:max_results * 2]:  # Get more to filter if needed
            title = entry.get("title", "")
            description = entry.get("summary", "") or entry.get("description", "")
            
            # STRICT ROLE FILTERING: Only include jobs that match the role
            if role:
                if not matches_role(title, description, role):
                    continue
            
            # Extract company from title (format: "Job Title - Company")
            company = "Not specified"
            if " - " in title:
                parts = title.split(" - ")
                if len(parts) > 1:
                    company = parts[-1].strip()
            
            # Clean HTML from description
            clean_desc = clean_html(description) if description else "No description available"
            clean_desc = clean_desc[:500] + "..." if len(clean_desc) > 500 else clean_desc
            
            jobs.append({
                "title": title,
                "company": company,
                "location": "Remote",
                "description": clean_desc,
                "link": entry.get("link", ""),
                "source": "RemoteOK"
            })
            
            if len(jobs) >= max_results:
                break
            
    except Exception as e:
        print(f"Error fetching jobs from RemoteOK: {e}")
        import traceback
        print(traceback.format_exc())
    
    return jobs[:max_results]


def fetch_arbeitnow_jobs(
    role: Optional[str] = None,
    location: Optional[str] = None,
    max_results: int = 20
) -> List[Dict[str, str]]:
    """
    Fetch jobs from Arbeitnow RSS feed.
    
    Args:
        role: Filter by job role/keyword (optional, for flexibility)
        location: Filter by location
        max_results: Maximum number of results
        
    Returns:
        List of job dictionaries
    """
    jobs = []
    
    try:
        # Try multiple possible RSS URLs for Arbeitnow
        rss_urls = [
            "https://www.arbeitnow.com/jobs.rss",
            "https://arbeitnow.com/jobs.rss",
            "https://www.arbeitnow.com/api/job-board-api"
        ]
        
        feed = None
        for rss_url in rss_urls:
            try:
                feed = feedparser.parse(rss_url)
                if feed.entries:
                    break
            except:
                continue
        
        if not feed or not feed.entries:
            print("Warning: Arbeitnow RSS feed not accessible")
            return []
        
        for entry in feed.entries[:max_results * 2]:  # Get more to filter if needed
            title = entry.get("title", "")
            description = entry.get("summary", "") or entry.get("description", "")
            
            # STRICT ROLE FILTERING: Only include jobs that match the role
            if role:
                if not matches_role(title, description, role):
                    continue
            
            # Extract location from description or title
            location_str = location or "Not specified"
            description = entry.get("summary", "")
            
            # Clean HTML from description
            clean_desc = clean_html(description) if description else "No description available"
            clean_desc = clean_desc[:500] + "..." if len(clean_desc) > 500 else clean_desc
            
            jobs.append({
                "title": title,
                "company": extract_company_from_description(description),
                "location": location_str,
                "description": clean_desc,
                "link": entry.get("link", ""),
                "source": "Arbeitnow"
            })
            
            if len(jobs) >= max_results:
                break
            
    except Exception as e:
        print(f"Error fetching jobs from Arbeitnow: {e}")
        import traceback
        print(traceback.format_exc())
    
    return jobs[:max_results]


def extract_company_from_description(description: str) -> str:
    """Extract company name from job description (heuristic)."""
    # Look for common patterns
    lines = description.split("\n")
    for line in lines[:5]:  # Check first few lines
        if "company:" in line.lower() or "employer:" in line.lower():
            parts = line.split(":")
            if len(parts) > 1:
                return parts[-1].strip()
    return "Not specified"


def fetch_all_rss_jobs(
    role: Optional[str] = None,
    location: Optional[str] = None,
    max_results: int = 20
) -> List[Dict[str, str]]:
    """
    Fetch jobs from all available RSS sources.
    
    Args:
        role: Desired job role (STRICT filtering - only returns jobs matching this role)
        location: Job location
        max_results: Maximum number of results per source
        
    Returns:
        Combined list of job dictionaries
    """
    all_jobs = []
    
    # Fetch from RemoteOK (with strict role filtering)
    remoteok_jobs = fetch_remoteok_jobs(role=role, max_results=max_results)
    print(f"RemoteOK: Fetched {len(remoteok_jobs)} jobs matching role '{role}'")
    all_jobs.extend(remoteok_jobs)
    
    # Fetch from Arbeitnow (with strict role filtering)
    arbeitnow_jobs = fetch_arbeitnow_jobs(role=role, location=location, max_results=max_results)
    print(f"Arbeitnow: Fetched {len(arbeitnow_jobs)} jobs matching role '{role}'")
    all_jobs.extend(arbeitnow_jobs)
    
    print(f"Total RSS jobs matching role '{role}': {len(all_jobs)}")
    return all_jobs[:max_results]  # Return filtered jobs

