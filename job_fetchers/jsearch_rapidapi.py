"""JSearch RapidAPI integration for job fetching."""
import logging
import os
import requests
from typing import List, Dict, Optional
from dotenv import load_dotenv
from utils.text_processing import clean_html
from utils.query_builder import build_search_query, parse_role_input, parse_location_input

load_dotenv()

logger = logging.getLogger(__name__)

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
JSEARCH_API_URL = "https://jsearch.p.rapidapi.com/search"

COUNTRY_MAP = {
    "india": "in",
    "united states": "us",
    "usa": "us",
    "uk": "gb",
    "canada": "ca",
}


def _parse_jsearch_item(item: dict) -> Dict[str, str]:
    """Parse a single JSearch result item into the standard job dict."""
    title = item.get("job_title") or item.get("title") or "No Title"
    company = item.get("employer_name") or item.get("company") or "Not specified"

    job_location = (
        item.get("job_city")
        or item.get("job_location")
        or item.get("location")
        or "Not specified"
    )
    if item.get("job_state") and job_location != "Not specified":
        job_location = f"{job_location}, {item['job_state']}"
    if item.get("job_country") and job_location != "Not specified":
        job_location = f"{job_location}, {item['job_country']}"
    if item.get("job_is_remote") and str(item["job_is_remote"]).lower() in ("true", "1"):
        job_location = f"{job_location} (Remote)" if job_location != "Not specified" else "Remote"

    raw_desc = item.get("job_description") or item.get("description") or ""
    if not raw_desc and isinstance(item.get("job_highlights"), dict):
        quals = item["job_highlights"].get("Qualifications", [])
        raw_desc = quals[0] if quals else ""
    clean_desc = clean_html(raw_desc)
    clean_desc = clean_desc[:500] + "..." if len(clean_desc) > 500 else clean_desc

    url = (
        item.get("job_apply_link")
        or item.get("job_google_link")
        or item.get("url")
        or item.get("link")
        or ""
    )

    return {
        "title": title,
        "company": company,
        "location": job_location,
        "description": clean_desc,
        "link": url,
        "source": "JSearch RapidAPI",
    }


def fetch_jsearch_jobs_rapidapi(
    role: Optional[str] = None,
    location: Optional[str] = None,
    max_results: int = 30,
    num_pages: int = 2,
    date_posted: str = "month",
) -> List[Dict[str, str]]:
    """
    Fetch jobs from the JSearch RapidAPI endpoint.

    Args:
        role: Desired job role (parsed into structured query).
        location: Job location.
        max_results: Maximum number of results to return.
        num_pages: Number of result pages to request (1-3).
        date_posted: Date filter — "today", "3days", "week", "month", "all".

    Returns:
        List of job dicts with title, company, location, description, link, source.
    """
    if not RAPIDAPI_KEY:
        logger.warning("RAPIDAPI_KEY not configured. Skipping JSearch RapidAPI.")
        return []

    roles = parse_role_input(role) or ["software engineer"]
    locations = parse_location_input(location)
    # Use a simple query for JSearch — complex boolean OR groups cause timeouts
    query = f"{roles[0]} {locations[0]}" if locations else roles[0]
    logger.info(f"JSearch RapidAPI query: {query}")

    jobs: List[Dict[str, str]] = []

    try:
        params = {
            "query": query,
            "num_pages": min(num_pages, 3),
            "date_posted": date_posted,
        }
        # Add country hint if a single recognisable country is given
        if locations and len(locations) == 1:
            loc = locations[0].lower()
            if loc in COUNTRY_MAP:
                params["country"] = COUNTRY_MAP[loc]

        headers = {
            "x-rapidapi-host": "jsearch.p.rapidapi.com",
            "x-rapidapi-key": RAPIDAPI_KEY,
        }

        response = None
        for attempt in range(3):
            try:
                response = requests.get(
                    JSEARCH_API_URL,
                    params=params,
                    headers=headers,
                    timeout=30,
                )
                break
            except requests.exceptions.Timeout:
                logger.warning(f"JSearch timeout attempt {attempt + 1}")
                if attempt == 2:
                    raise

        if response is None:
            logger.error("JSearch RapidAPI: all retry attempts failed")
            return []

        if response.status_code == 403:
            logger.error("JSearch RapidAPI returned 403 Forbidden — check RAPIDAPI_KEY or subscription")
            return []
        response.raise_for_status()

        data = response.json()
        items = data.get("data") or data.get("jobs") or data.get("results") or []
        if not isinstance(items, list):
            items = []
        logger.info(f"JSearch returned {len(items)} raw jobs")

        for item in items:
            if len(jobs) >= max_results:
                break
            parsed = _parse_jsearch_item(item)
            jobs.append(parsed)

        # Deduplicate by job link
        unique = {}
        for job in jobs:
            unique[job["link"]] = job
        jobs = list(unique.values())

        logger.info(f"Parsed {len(jobs)} jobs after processing")

    except requests.exceptions.RequestException as e:
        logger.error(f"JSearch RapidAPI failed — continuing pipeline: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in JSearch RapidAPI: {e}")

    return jobs[:max_results]


