"""Text processing utilities for cleaning and formatting."""
import re
from html import unescape
try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False


def clean_html(html_text: str) -> str:
    """Remove HTML tags and decode HTML entities from text."""
    if not html_text:
        return ""
    
    # First decode HTML entities
    text = unescape(html_text)
    
    # Remove HTML tags
    if BS4_AVAILABLE:
        try:
            soup = BeautifulSoup(text, 'html.parser')
            text = soup.get_text(separator=' ', strip=True)
        except:
            # Fallback to regex if BeautifulSoup fails
            text = re.sub(r'<[^>]+>', '', text)
    else:
        # Use regex to remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
    
    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    return text


def extract_key_info(text: str, max_length: int = 500) -> str:
    """Extract key information from job description."""
    # Remove common noise
    text = clean_html(text)
    
    # Remove email patterns (often in job descriptions)
    text = re.sub(r'\S+@\S+', '', text)
    
    # Remove URLs (keep the text but remove the actual URL)
    text = re.sub(r'http[s]?://\S+', '', text)
    
    # Clean up multiple spaces
    text = re.sub(r'\s+', ' ', text)
    
    # Truncate if too long
    if len(text) > max_length:
        # Try to cut at sentence boundary
        truncated = text[:max_length]
        last_period = truncated.rfind('.')
        if last_period > max_length * 0.7:  # If period is in last 30%, use it
            text = truncated[:last_period + 1]
        else:
            text = truncated + "..."
    
    return text.strip()

