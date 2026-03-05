def is_resume(text: str) -> bool:
    """
    Check if the uploaded text contains typical resume keywords.
    Returns True if it's likely a resume, False otherwise.
    """
    if not text:
        return False

    text_lower = text.lower()
    
    keywords = [
        "experience",
        "education",
        "skills",
        "projects",
        "work experience",
        "internship",
        "university",
        "bachelor",
        "master",
        "certifications",
        "technical skills",
        "summary",
        "objective",
        "employment",
        "degree",
        "college",
        "profile"
    ]
    
    # Count how many of these keywords appear in the text
    keyword_count = sum(1 for keyword in keywords if keyword in text_lower)
    
    # Threshold: If at least 3 keywords are found, consider it a resume
    return keyword_count >= 3
