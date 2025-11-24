"""Adzuna job search API integration (free tier available)."""
import os
import requests
from typing import List, Dict, Optional
from dotenv import load_dotenv
from utils.text_processing import clean_html

load_dotenv()

# Adzuna API (free tier: 1000 requests/month)
ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID")
ADZUNA_API_KEY = os.getenv("ADZUNA_API_KEY")


def fetch_adzuna_jobs(
    role: Optional[str] = None,
    location: Optional[str] = None,
    max_results: int = 20
) -> List[Dict[str, str]]:
    """
    Fetch jobs from Adzuna API.
    
    Args:
        role: Job role/keyword
        location: Job location
        max_results: Maximum number of results
        
    Returns:
        List of job dictionaries
    """
    if not ADZUNA_APP_ID or not ADZUNA_API_KEY:
        print("Warning: Adzuna API credentials not configured. Skipping Adzuna job search.")
        return []
    
    jobs = []
    
    try:
        # Adzuna API endpoint (US jobs)
        base_url = "https://api.adzuna.com/v1/api/jobs/us/search/1"
        
        params = {
            "app_id": ADZUNA_APP_ID,
            "app_key": ADZUNA_API_KEY,
            "results_per_page": min(max_results, 50),
            "what": role or "developer",  # Default search term
        }
        
        if location:
            params["where"] = location
        
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if "results" in data:
            for item in data["results"][:max_results]:
                # Clean HTML from description
                clean_desc = clean_html(item.get("description", ""))
                clean_desc = clean_desc[:500] + "..." if len(clean_desc) > 500 else clean_desc
                
                jobs.append({
                    "title": item.get("title", "No Title"),
                    "company": item.get("company", {}).get("display_name", "Not specified"),
                    "location": item.get("location", {}).get("display_name", location or "Not specified"),
                    "description": clean_desc,
                    "link": item.get("redirect_url", ""),
                    "source": "Adzuna"
                })
                
    except requests.exceptions.RequestException as e:
        print(f"Error fetching jobs from Adzuna: {e}")
    except Exception as e:
        print(f"Error processing Adzuna jobs: {e}")
    
    return jobs[:max_results]

