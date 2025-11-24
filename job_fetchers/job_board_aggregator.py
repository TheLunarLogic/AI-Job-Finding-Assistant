"""Aggregator for multiple free job board APIs."""
import requests
from typing import List, Dict, Optional
import time
from utils.text_processing import clean_html


def fetch_github_jobs(role: Optional[str] = None, max_results: int = 20) -> List[Dict[str, str]]:
    """Fetch jobs from GitHub Jobs API (free, no auth required)."""
    jobs = []
    
    try:
        # GitHub Jobs API (read-only, free)
        url = "https://jobs.github.com/positions.json"
        params = {}
        
        if role:
            params["description"] = role
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # STRICT ROLE FILTERING
        role_lower = role.lower() if role else ""
        role_keywords = [kw.strip() for kw in role_lower.split() if len(kw.strip()) > 2] if role else []
        
        for item in data[:max_results * 2]:  # Get more to filter
            if role and role_keywords:
                title_lower = item.get("title", "").lower()
                desc_lower = item.get("description", "").lower()
                
                title_match = any(keyword in title_lower for keyword in role_keywords)
                desc_match = any(keyword in desc_lower for keyword in role_keywords)
                
                if not (title_match or desc_match):
                    continue
            
            # Clean HTML from description
            clean_desc = clean_html(item.get("description", ""))
            clean_desc = clean_desc[:500] + "..." if len(clean_desc) > 500 else clean_desc
            
            jobs.append({
                "title": item.get("title", "No Title"),
                "company": item.get("company", "Not specified"),
                "location": item.get("location", "Not specified"),
                "description": clean_desc,
                "link": item.get("url", ""),
                "source": "GitHub Jobs"
            })
            
            if len(jobs) >= max_results:
                break
            
    except Exception as e:
        print(f"Error fetching jobs from GitHub Jobs: {e}")
    
    return jobs[:max_results]


def fetch_hn_jobs(max_results: int = 20) -> List[Dict[str, str]]:
    """Fetch jobs from Hacker News 'Who is Hiring' posts."""
    jobs = []
    
    try:
        # Hacker News API
        url = "https://hacker-news.firebaseio.com/v0/jobstories.json"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        story_ids = response.json()[:max_results]
        
        for story_id in story_ids:
            try:
                story_url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
                story_response = requests.get(story_url, timeout=5)
                story_response.raise_for_status()
                story = story_response.json()
                
                if story and story.get("type") == "job":
                    title = story.get("title", "")
                    # Extract company from title (format: "Company | Job Title" or "Job Title at Company")
                    company = "Not specified"
                    if "|" in title:
                        parts = title.split("|")
                        company = parts[0].strip()
                        title = parts[1].strip() if len(parts) > 1 else title
                    elif " at " in title:
                        parts = title.split(" at ")
                        company = parts[-1].strip()
                        title = parts[0].strip()
                    
                    # Clean HTML from text
                    clean_text = clean_html(story.get("text", ""))
                    clean_text = clean_text[:500] + "..." if len(clean_text) > 500 else clean_text
                    
                    jobs.append({
                        "title": title,
                        "company": company,
                        "location": "Remote",  # Most HN jobs are remote
                        "description": clean_text,
                        "link": story.get("url", f"https://news.ycombinator.com/item?id={story_id}"),
                        "source": "Hacker News"
                    })
                    
                time.sleep(0.1)  # Rate limiting
            except:
                continue
                
    except Exception as e:
        print(f"Error fetching jobs from Hacker News: {e}")
    
    return jobs[:max_results]


def fetch_all_free_jobs(
    role: Optional[str] = None,
    location: Optional[str] = None,
    max_results: int = 20
) -> List[Dict[str, str]]:
    """Fetch jobs from all free job board APIs."""
    all_jobs = []
    
    # GitHub Jobs
    github_jobs = fetch_github_jobs(role=role, max_results=max_results // 2)
    all_jobs.extend(github_jobs)
    
    # Hacker News Jobs
    hn_jobs = fetch_hn_jobs(max_results=max_results // 2)
    all_jobs.extend(hn_jobs)
    
    return all_jobs[:max_results]

