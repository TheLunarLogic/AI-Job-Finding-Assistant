"""Job description analyzer to extract salary, requirements, and company details."""
import re
from typing import Dict, List, Optional


def extract_salary(job_description: str) -> Optional[str]:
    """Extract salary information from job description."""
    if not job_description:
        return None
    
    desc_lower = job_description.lower()
    
    # Common salary patterns
    salary_patterns = [
        r'\$[\d,]+(?:-\$?[\d,]+)?\s*(?:per\s+)?(?:year|yr|annually|hour|hr|month)',
        r'\$[\d,]+k?\s*(?:-\$?[\d,]+k?)?\s*(?:per\s+)?(?:year|yr|annually)',
        r'[\d,]+(?:-[\d,]+)?\s*(?:USD|usd|\$)\s*(?:per\s+)?(?:year|yr|annually)',
        r'salary[:\s]+[\$]?[\d,]+(?:-[\$]?[\d,]+)?',
        r'compensation[:\s]+[\$]?[\d,]+(?:-[\$]?[\d,]+)?',
        r'pay[:\s]+[\$]?[\d,]+(?:-[\$]?[\d,]+)?',
    ]
    
    for pattern in salary_patterns:
        matches = re.findall(pattern, desc_lower, re.IGNORECASE)
        if matches:
            # Clean up the match
            salary = matches[0].strip()
            # Capitalize first letter
            salary = salary[0].upper() + salary[1:] if salary else salary
            return salary
    
    # Look for salary ranges in different formats
    range_patterns = [
        r'(\$[\d,]+)\s*-\s*(\$[\d,]+)',
        r'(\$[\d,]+)\s*to\s*(\$[\d,]+)',
    ]
    
    for pattern in range_patterns:
        match = re.search(pattern, desc_lower, re.IGNORECASE)
        if match:
            return f"{match.group(1)} - {match.group(2)}"
    
    return None


def extract_employee_count(job_description: str, company_name: str = "") -> Optional[str]:
    """Extract employee count information from job description."""
    if not job_description:
        return None
    
    desc_lower = job_description.lower()
    
    # Patterns for employee count
    employee_patterns = [
        r'(\d+(?:,\d+)?)\s*(?:employees|people|staff|team\s+members)',
        r'(?:company|organization|firm)\s+(?:of|with|has)\s+(\d+(?:,\d+)?)\s*(?:employees|people)',
        r'(\d+(?:,\d+)?)\s*(?:person|people)\s+(?:team|company|organization)',
    ]
    
    for pattern in employee_patterns:
        match = re.search(pattern, desc_lower, re.IGNORECASE)
        if match:
            count = match.group(1)
            return f"{count} employees"
    
    # Look for size indicators
    size_keywords = {
        "startup": "1-50 employees",
        "small company": "1-50 employees",
        "small team": "1-50 employees",
        "early stage": "1-50 employees",
        "growing company": "50-200 employees",
        "mid-size": "200-1000 employees",
        "mid-size company": "200-1000 employees",
        "large company": "1000+ employees",
        "enterprise": "1000+ employees",
        "fortune 500": "1000+ employees",
        "multinational": "1000+ employees",
    }
    
    for keyword, size in size_keywords.items():
        if keyword in desc_lower:
            return size
    
    return None


def extract_requirements(job_description: str) -> List[str]:
    """Extract job requirements from description."""
    if not job_description:
        return []
    
    requirements = []
    desc_lower = job_description.lower()
    
    # Common requirement sections
    requirement_sections = [
        r'requirements?:?\s*(.*?)(?:\n\n|responsibilities|qualifications|benefits|about)',
        r'qualifications?:?\s*(.*?)(?:\n\n|responsibilities|requirements|benefits|about)',
        r'must\s+have:?\s*(.*?)(?:\n\n|nice\s+to\s+have|preferred)',
        r'required:?\s*(.*?)(?:\n\n|preferred|nice\s+to\s+have)',
    ]
    
    for pattern in requirement_sections:
        match = re.search(pattern, desc_lower, re.IGNORECASE | re.DOTALL)
        if match:
            section = match.group(1)
            # Split by bullet points or new lines
            items = re.split(r'[•\-\*]\s*|\n\s*[\-\*•]\s*', section)
            for item in items[:10]:  # Limit to 10 requirements
                item = item.strip()
                if len(item) > 20 and len(item) < 200:  # Reasonable length
                    requirements.append(item)
            break
    
    # If no structured section found, look for common requirement patterns
    if not requirements:
        # Look for degree requirements
        degree_patterns = [
            r"(bachelor'?s?\s+(?:degree|in|of))",
            r"(master'?s?\s+(?:degree|in|of))",
            r"(ph\.?d\.?\s+(?:degree|in|of))",
            r"(degree\s+in)",
        ]
        for pattern in degree_patterns:
            match = re.search(pattern, desc_lower, re.IGNORECASE)
            if match:
                requirements.append(match.group(0).title())
        
        # Look for experience requirements
        exp_patterns = [
            r'(\d+\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:experience|exp))',
            r'((?:minimum|at\s+least)\s+\d+\s+(?:years?|yrs?)\s+(?:of\s+)?(?:experience|exp))',
        ]
        for pattern in exp_patterns:
            match = re.search(pattern, desc_lower, re.IGNORECASE)
            if match:
                requirements.append(match.group(0).title())
        
        # Look for skill requirements
        skill_keywords = [
            "python", "java", "javascript", "sql", "machine learning", "ai",
            "react", "node", "aws", "docker", "kubernetes", "tensorflow",
            "data science", "analytics", "statistics", "r programming"
        ]
        found_skills = [skill for skill in skill_keywords if skill in desc_lower]
        requirements.extend([f"Experience with {skill.title()}" for skill in found_skills[:5]])
    
    return requirements[:8]  # Return top 8 requirements


def extract_benefits(job_description: str) -> List[str]:
    """Extract benefits from job description."""
    if not job_description:
        return []
    
    benefits = []
    desc_lower = job_description.lower()
    
    # Common benefits
    benefit_keywords = {
        "health insurance": "Health Insurance",
        "dental insurance": "Dental Insurance",
        "vision insurance": "Vision Insurance",
        "401k": "401(k) Retirement Plan",
        "retirement plan": "Retirement Plan",
        "remote work": "Remote Work",
        "work from home": "Remote Work",
        "flexible schedule": "Flexible Schedule",
        "paid time off": "Paid Time Off",
        "pto": "Paid Time Off",
        "vacation": "Paid Vacation",
        "stock options": "Stock Options",
        "equity": "Equity",
        "bonus": "Performance Bonus",
        "professional development": "Professional Development",
        "learning budget": "Learning & Development Budget",
    }
    
    for keyword, benefit in benefit_keywords.items():
        if keyword in desc_lower:
            benefits.append(benefit)
    
    return benefits[:6]  # Return top 6 benefits


def analyze_job(job_description: str, company_name: str = "") -> Dict:
    """Comprehensive job analysis extracting all relevant information."""
    return {
        "salary": extract_salary(job_description),
        "employee_count": extract_employee_count(job_description, company_name),
        "requirements": extract_requirements(job_description),
        "benefits": extract_benefits(job_description),
    }

