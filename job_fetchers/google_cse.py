"""Google Custom Search Engine integration for job fetching."""
import os
import requests
from typing import List, Dict, Optional
from dotenv import load_dotenv
from utils.text_processing import clean_html

load_dotenv()

# Google Custom Search API configuration
GOOGLE_CSE_API_KEY = os.getenv("GOOGLE_CSE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")


def search_jobs(
    query: str,
    role: Optional[str] = None,
    location: Optional[str] = None,
    max_results: int = 20
) -> List[Dict[str, str]]:
    """
    Search for jobs using Google Custom Search Engine.
    
    Args:
        query: Base search query
        role: Desired job role
        location: Job location
        max_results: Maximum number of results to return
        
    Returns:
        List of job dictionaries with title, link, snippet, etc.
    """
    if not GOOGLE_CSE_API_KEY or not GOOGLE_CSE_ID:
        print("Warning: Google CSE API key or ID not configured. Skipping Google CSE job search.")
        return []
    
    # Build search query - prioritize role in title
    if role:
        # Parse roles and use the first one for search
        from utils.role_parser import parse_roles
        parsed_roles = parse_roles(role)
        if parsed_roles:
            # Use first role and add "title" to make it more specific
            primary_role = parsed_roles[0]
            search_query = f'"{primary_role}" OR "{primary_role} engineer" OR "{primary_role} scientist"'
        else:
            search_query = f'"{role}"'
    else:
        search_query = query
    
    if location:
        search_query += f" {location}"
    search_query += " job site:linkedin.com OR site:indeed.com OR site:glassdoor.com"
    
    jobs = []
    start_index = 1
    
    try:
        while len(jobs) < max_results:
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "key": GOOGLE_CSE_API_KEY,
                "cx": GOOGLE_CSE_ID,
                "q": search_query,
                "start": start_index,
                "num": min(10, max_results - len(jobs))  # Google CSE returns max 10 per request
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if "items" not in data:
                break
            
            for item in data["items"]:
                # Clean HTML from snippet
                clean_snippet = clean_html(item.get("snippet", ""))
                clean_snippet = clean_snippet[:500] + "..." if len(clean_snippet) > 500 else clean_snippet
                
                jobs.append({
                    "title": item.get("title", "No Title"),
                    "company": extract_company_from_title(item.get("title", "")),
                    "location": location or "Not specified",
                    "description": clean_snippet,
                    "link": item.get("link", ""),
                    "source": "Google CSE"
                })
                
                if len(jobs) >= max_results:
                    break
            
            # Check if there are more results
            if "queries" in data and "nextPage" in data["queries"]:
                start_index += 10
            else:
                break
                
    except requests.exceptions.RequestException as e:
        print(f"Error fetching jobs from Google CSE: {e}")
    
    return jobs[:max_results]


def extract_company_from_title(title: str) -> str:
    """Extract company name from job title (heuristic)."""
    # Common patterns: "Job Title - Company Name" or "Job Title at Company Name"
    if " - " in title:
        parts = title.split(" - ")
        if len(parts) > 1:
            company = parts[-1].strip()
            # Clean up common suffixes
            company = company.replace(" | LinkedIn", "").replace(" | Indeed", "").replace(" | Glassdoor", "").strip()
            return company if company else "Not specified"
    elif " at " in title:
        parts = title.split(" at ")
        if len(parts) > 1:
            company = parts[-1].strip()
            company = company.replace(" | LinkedIn", "").replace(" | Indeed", "").replace(" | Glassdoor", "").strip()
            return company if company else "Not specified"
    elif "|" in title:
        # Pattern: "Company | Job Title"
        parts = title.split("|")
        if len(parts) > 0:
            company = parts[0].strip()
            return company if company else "Not specified"
    return "Not specified"

