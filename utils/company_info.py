"""Company information fetcher using free APIs and web scraping."""
import requests
from typing import Dict, Optional
import re


def get_company_info(company_name: str, job_description: str = "") -> Dict[str, Optional[str]]:
    """
    Fetch company information using free sources and job description analysis.
    
    Returns:
        Dictionary with company_size, industry, description, website
    """
    if not company_name or company_name.lower() in ["not specified", "n/a", ""]:
        return {
            "company_size": None,
            "industry": None,
            "description": None,
            "website": None
        }
    
    info = {
        "company_size": None,
        "industry": None,
        "description": None,
        "website": None
    }
    
    # Extract info from job description if available
    if job_description:
        from utils.job_analyzer import extract_employee_count
        employee_count = extract_employee_count(job_description, company_name)
        if employee_count:
            info["company_size"] = employee_count
        
        # Extract industry from description
        desc_lower = job_description.lower()
        industry_keywords = {
            "technology": ["tech", "software", "saas", "ai", "machine learning", "data science"],
            "healthcare": ["health", "medical", "pharmaceutical", "biotech"],
            "finance": ["finance", "fintech", "banking", "investment", "financial"],
            "education": ["education", "edtech", "learning", "university"],
            "e-commerce": ["e-commerce", "retail", "online shopping"],
            "consulting": ["consulting", "advisory", "strategy"],
        }
        
        for industry, keywords in industry_keywords.items():
            if any(keyword in desc_lower for keyword in keywords):
                info["industry"] = industry.title()
                break
    
    # Try to get info from free APIs
    try:
        # Use DuckDuckGo Instant Answer API (free, no key required)
        # Or use a simple web search approach
        web_info = _fetch_from_web_search(company_name)
        # Merge web info, but prioritize description-based info
        for key in web_info:
            if not info.get(key) and web_info.get(key):
                info[key] = web_info[key]
    except Exception as e:
        print(f"Error fetching company info for {company_name}: {e}")
    
    return info


def _fetch_from_web_search(company_name: str) -> Dict[str, Optional[str]]:
    """Fetch company info using web search (free method)."""
    info = {
        "company_size": None,
        "industry": None,
        "description": None,
        "website": None
    }
    
    # Clean company name
    clean_name = company_name.strip()
    
    # Try to extract website from company name if it looks like a URL
    if "." in clean_name and ("http" in clean_name.lower() or clean_name.count(".") >= 1):
        # Might be a website
        if not clean_name.startswith("http"):
            clean_name = f"https://{clean_name}"
        info["website"] = clean_name
    
    # For now, return basic info
    # In production, you could use:
    # - LinkedIn API (requires auth)
    # - Clearbit API (free tier available)
    # - Web scraping (with proper rate limiting)
    # - Wikipedia API (free)
    
    return info


def generate_company_summary(company_name: str, job_title: str, job_description: str) -> str:
    """Generate a brief company summary from available information."""
    if not company_name or company_name.lower() in ["not specified", "n/a", ""]:
        return "Company information not available."
    
    summary_parts = []
    
    # Add company name
    summary_parts.append(f"{company_name} is")
    
    # Try to infer from job description
    desc_lower = job_description.lower()
    
    # Check for company size indicators
    if any(word in desc_lower for word in ["startup", "early stage", "small team"]):
        summary_parts.append("a startup or small company")
    elif any(word in desc_lower for word in ["fortune", "enterprise", "large scale"]):
        summary_parts.append("a large enterprise")
    elif any(word in desc_lower for word in ["growing", "scaling", "expanding"]):
        summary_parts.append("a growing company")
    else:
        summary_parts.append("a company")
    
    # Check for industry hints
    if "tech" in desc_lower or "software" in desc_lower or "ai" in desc_lower:
        summary_parts.append("in the technology sector")
    elif "health" in desc_lower or "medical" in desc_lower:
        summary_parts.append("in healthcare")
    elif "finance" in desc_lower or "fintech" in desc_lower:
        summary_parts.append("in finance")
    
    return " ".join(summary_parts) + "."

