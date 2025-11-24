"""Backend server with LangGraph chatbot and job finding API."""
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated, List, Dict, Optional
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.message import add_messages
from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os

load_dotenv()

# Initialize LLM
llm = ChatGoogleGenerativeAI(model='gemini-2.5-flash')

# Job-related keywords for intent detection
JOB_KEYWORDS = [
    "find me a job", "search jobs", "job recommendations", "find jobs",
    "job search", "looking for job", "need a job", "job opportunities",
    "career opportunities", "job openings", "help me find a job"
]


class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


def detect_job_intent(user_input: str) -> bool:
    """Detect if user is asking about job search."""
    user_lower = user_input.lower()
    return any(keyword in user_lower for keyword in JOB_KEYWORDS)


def chat_node(state: ChatState):
    """Chat node with intent routing for job-related queries."""
    messages = state['messages']
    
    # Get the last user message
    last_message = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_message = msg
            break
    
    # Check for job intent
    if last_message and detect_job_intent(last_message.content):
        job_response = AIMessage(
            content="Sure! Please upload your resume using the 'Find Jobs With My Resume' button in the left panel."
        )
        return {"messages": [job_response]}
    
    # Normal chat response
    response = llm.invoke(messages)
    return {"messages": [response]}


# Checkpointer
checkpointer = InMemorySaver()

# Build graph
graph = StateGraph(ChatState)
graph.add_node("chat_node", chat_node)
graph.add_edge(START, "chat_node")
graph.add_edge("chat_node", END)

chatbot = graph.compile(checkpointer=checkpointer)

# FastAPI app
app = FastAPI(title="Job Finding AI Assistant")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "Job Finding AI Assistant API is running"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "Job Finding AI Assistant"}


@app.post("/find_jobs")
async def find_jobs(
    resume: UploadFile = File(...),
    role: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    experience_level: Optional[str] = Form(None)
):
    """
    Find jobs based on resume and optional filters.
    
    Args:
        resume: Resume file (PDF, DOCX, or TXT)
        role: Desired job role
        location: Job location
        experience_level: Experience level
        
    Returns:
        JSON response with ranked job results
    """
    try:
        # Import here to avoid circular imports
        import logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)
        
        from resume_pipeline import extract_resume_text
        from utils.embeddings import embed_text, embed_texts
        from utils.text_processing import clean_html, extract_key_info
        from utils.company_info import get_company_info, generate_company_summary
        from utils.job_analyzer import analyze_job
        from utils.role_parser import parse_roles, matches_role
        from sklearn.metrics.pairwise import cosine_similarity
        from job_fetchers.google_cse import search_jobs as google_cse_search
        from job_fetchers.rss_fetcher import fetch_all_rss_jobs
        from job_fetchers.adzuna import fetch_adzuna_jobs
        from job_fetchers.job_board_aggregator import fetch_all_free_jobs
        
        # Read resume file
        resume_content = await resume.read()
        
        # Extract text from resume
        resume_text = extract_resume_text(resume_content, resume.filename)
        logger.info(f"Extracted resume text: {len(resume_text)} characters")
        
        # Generate resume embedding
        resume_embedding = embed_text(resume_text)
        logger.info("Generated resume embedding")
        
        # Fetch jobs from multiple sources
        all_jobs = []
        google_jobs = []
        rss_jobs = []
        
        # Search query based on resume text and filters
        search_query = resume_text[:500]  # Use first 500 chars as search query
        if role:
            search_query = f"{role} {search_query}"
        
        logger.info(f"Search query: {search_query[:100]}...")
        logger.info(f"Filters - Role: {role}, Location: {location}, Experience: {experience_level}")
        
        # Fetch from Google CSE
        logger.info("Fetching jobs from Google CSE...")
        google_jobs = google_cse_search(
            query=search_query,
            role=role,
            location=location,
            max_results=15
        )
        logger.info(f"Google CSE returned {len(google_jobs)} jobs")
        all_jobs.extend(google_jobs)
        
        # Fetch from RSS feeds WITH role filter (strict matching)
        logger.info("Fetching jobs from RSS feeds...")
        rss_jobs = fetch_all_rss_jobs(
            role=role,  # STRICT: Only fetch jobs matching the user's role
            location=location,
            max_results=30
        )
        logger.info(f"RSS feeds returned {len(rss_jobs)} jobs")
        all_jobs.extend(rss_jobs)
        
        # Fetch from Adzuna API
        logger.info("Fetching jobs from Adzuna...")
        adzuna_jobs = fetch_adzuna_jobs(
            role=role,
            location=location,
            max_results=15
        )
        logger.info(f"Adzuna returned {len(adzuna_jobs)} jobs")
        all_jobs.extend(adzuna_jobs)
        
        # Fetch from free job board aggregators
        logger.info("Fetching jobs from free job boards...")
        free_jobs = fetch_all_free_jobs(
            role=role,
            location=location,
            max_results=20
        )
        logger.info(f"Free job boards returned {len(free_jobs)} jobs")
        all_jobs.extend(free_jobs)
        
        logger.info(f"Total jobs fetched: {len(all_jobs)}")
        
        # If no jobs found, add fallback jobs based on role
        if len(all_jobs) == 0:
            logger.warning("No jobs found from any source, adding fallback jobs")
            fallback_jobs = _get_fallback_jobs(role, location)
            all_jobs.extend(fallback_jobs)
            logger.info(f"Added {len(fallback_jobs)} fallback jobs")
        
        # Remove duplicates based on link
        seen_links = set()
        unique_jobs = []
        for job in all_jobs:
            if job["link"] not in seen_links and job.get("link"):
                seen_links.add(job["link"])
                unique_jobs.append(job)
        
        # STRICT ROLE FILTERING: Filter jobs to only include those matching the user's entered role
        if role:
            logger.info(f"Filtering jobs to match role(s): {role}")
            parsed_roles = parse_roles(role)
            logger.info(f"Parsed roles: {parsed_roles}")
            
            filtered_jobs = []
            for job in unique_jobs:
                if matches_role(job.get("title", ""), job.get("description", ""), role):
                    filtered_jobs.append(job)
            
            logger.info(f"Filtered from {len(unique_jobs)} to {len(filtered_jobs)} jobs matching role(s)")
            unique_jobs = filtered_jobs
            
            # If filtering removed all jobs, don't fallback - return empty
            # This ensures we only show relevant jobs
            if len(unique_jobs) == 0:
                logger.warning(f"No jobs matched role '{role}' exactly. Returning empty results.")
                return JSONResponse({
                    "jobs": [],
                    "message": f"No jobs found matching '{role}'. Try adjusting your role keywords or search criteria.",
                    "debug_info": {
                        "google_cse_jobs": len(google_jobs),
                        "rss_jobs": len(rss_jobs),
                        "total_fetched": len(all_jobs),
                        "role_filter": role,
                        "location_filter": location
                    }
                })
        
        # Limit jobs to process to avoid timeout (max 50 jobs)
        jobs_to_process = unique_jobs[:50]
        logger.info(f"Processing {len(jobs_to_process)} jobs for similarity matching")
        
        # Generate embeddings for job descriptions
        job_texts = [
            f"{job['title']} {job['description']} {job.get('company', '')}"
            for job in jobs_to_process
        ]
        
        if not job_texts:
            logger.warning("No jobs found after fetching from all sources")
            return JSONResponse({
                "jobs": [],
                "message": "No jobs found. Try adjusting your search criteria.",
                "debug_info": {
                    "google_cse_jobs": len(google_jobs),
                    "rss_jobs": len(rss_jobs),
                    "total_fetched": len(all_jobs),
                    "role_filter": role,
                    "location_filter": location
                }
            })
        
        logger.info("Generating job embeddings...")
        job_embeddings = embed_texts(job_texts)
        logger.info("Job embeddings generated")
        
        # Calculate similarity scores using sklearn
        # cosine_similarity expects 2D arrays: [resume_vec] and job_vecs
        logger.info("Calculating similarity scores...")
        similarity_scores = cosine_similarity([resume_embedding], job_embeddings)[0]
        
        # MINIMUM SIMILARITY THRESHOLD - filter out low-quality matches
        MIN_SIMILARITY_THRESHOLD = 0.25  # 25% minimum similarity
        
        scored_jobs = []
        for i, job in enumerate(jobs_to_process):
            similarity = float(similarity_scores[i])
            job["similarity_score"] = similarity
            job["match_reason"] = generate_match_reason(similarity, job, resume_text)
            
            # Only include jobs above threshold
            if similarity >= MIN_SIMILARITY_THRESHOLD:
                scored_jobs.append(job)
        
        logger.info(f"Filtered to {len(scored_jobs)} jobs above {MIN_SIMILARITY_THRESHOLD:.0%} similarity threshold")
        
        # Sort by similarity score (highest first)
        ranked_jobs = sorted(
            scored_jobs,
            key=lambda x: x.get("similarity_score", 0),
            reverse=True
        )
        
        # Return top 20 jobs (or fewer if not enough meet threshold)
        top_jobs = ranked_jobs[:20]
        logger.info(f"Selected top {len(top_jobs)} jobs")
        
        # Format response with cleaned descriptions and comprehensive job analysis
        logger.info("Formatting job results...")
        results = []
        for idx, job in enumerate(top_jobs):
            try:
                # Clean HTML from description
                clean_description = clean_html(job.get("description", ""))
                clean_description = extract_key_info(clean_description, max_length=400)
                
                # Analyze job for salary, requirements, benefits, etc. (fast, limited analysis)
                job_analysis = analyze_job(job.get("description", ""), job.get("company", ""))
                
                # Get company information (pass description for better analysis)
                company_name = job.get("company", "Not specified")
                company_info = get_company_info(company_name, job.get("description", ""))
                company_summary = generate_company_summary(
                    company_name,
                    job.get("title", ""),
                    clean_description
                )
                
                # Enhanced description with company info
                enhanced_description = f"{company_summary}\n\n{clean_description}"
                
                results.append({
                    "title": job["title"],
                    "company": company_name,
                    "location": job["location"],
                    "description": enhanced_description,
                    "link": job["link"],
                    "match_reason": job.get("match_reason", "Good match based on your resume"),
                    "similarity_score": round(job.get("similarity_score", 0), 3),
                    "company_info": {
                        "size": company_info.get("company_size") or job_analysis.get("employee_count"),
                        "industry": company_info.get("industry"),
                        "website": company_info.get("website")
                    },
                    "salary": job_analysis.get("salary"),
                    "requirements": job_analysis.get("requirements", [])[:6],  # Top 6 requirements
                    "benefits": job_analysis.get("benefits", [])[:6],  # Top 6 benefits
                })
            except Exception as e:
                logger.error(f"Error formatting job {idx}: {e}")
                # Add job with minimal info if analysis fails
                results.append({
                    "title": job.get("title", "Unknown"),
                    "company": job.get("company", "Not specified"),
                    "location": job.get("location", "Not specified"),
                    "description": clean_html(job.get("description", ""))[:400],
                    "link": job.get("link", ""),
                    "match_reason": job.get("match_reason", "Good match based on your resume"),
                    "similarity_score": round(job.get("similarity_score", 0), 3),
                    "company_info": {},
                    "salary": None,
                    "requirements": [],
                    "benefits": [],
                })
        
        logger.info(f"Returning {len(results)} ranked jobs")
        return JSONResponse({
            "jobs": results,
            "total_found": len(results),
            "debug_info": {
                "google_cse_jobs": len(google_jobs),
                "rss_jobs": len(rss_jobs),
                "total_fetched": len(all_jobs),
                "unique_jobs": len(unique_jobs),
                "ranked_jobs": len(results)
            }
        })
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Error processing job search: {error_details}")
        raise HTTPException(status_code=500, detail=f"Error processing job search: {str(e)}")


def _get_fallback_jobs(role: Optional[str] = None, location: Optional[str] = None) -> List[Dict[str, str]]:
    """Generate fallback jobs when no jobs are found from external sources."""
    fallback_jobs = []
    
    # Common job sites to search
    job_sites = [
        {"name": "LinkedIn", "url": "https://www.linkedin.com/jobs/search/"},
        {"name": "Indeed", "url": "https://www.indeed.com/jobs"},
        {"name": "Glassdoor", "url": "https://www.glassdoor.com/Job/jobs.htm"},
        {"name": "Monster", "url": "https://www.monster.com/jobs/search/"},
        {"name": "Remote.co", "url": "https://remote.co/remote-jobs/"},
    ]
    
    role_str = role or "your field"
    location_str = location or "your location"
    
    for site in job_sites:
        search_url = f"{site['url']}?q={role_str.replace(' ', '+')}"
        if location_str and location_str.lower() != "remote":
            search_url += f"&l={location_str.replace(' ', '+')}"
        
        fallback_jobs.append({
            "title": f"{role_str.title()} - Search on {site['name']}",
            "company": site['name'],
            "location": location_str or "Various",
            "description": f"Search for {role_str} jobs on {site['name']}. Visit the link to see current openings matching your criteria.",
            "link": search_url,
            "source": "Fallback"
        })
    
    return fallback_jobs


def generate_match_reason(similarity: float, job: Dict, resume_text: str = "") -> str:
    """Generate a human-readable match reason based on similarity score and resume content."""
    job_title = job.get("title", "").lower()
    job_desc = job.get("description", "").lower()
    resume_lower = resume_text.lower()
    
    # Extract key skills/technologies from resume
    tech_keywords = ["python", "java", "javascript", "sql", "machine learning", "ai", "data science", 
                    "react", "node", "aws", "docker", "kubernetes", "tensorflow", "pytorch"]
    found_skills = [skill for skill in tech_keywords if skill in resume_lower]
    
    # Build personalized reason
    reason_parts = []
    
    if similarity >= 0.8:
        reason_parts.append("Excellent match")
    elif similarity >= 0.6:
        reason_parts.append("Good match")
    elif similarity >= 0.4:
        reason_parts.append("Moderate match")
    else:
        reason_parts.append("Potential match")
    
    # Add specific reasons
    specific_reasons = []
    
    # Check for skill matches
    if found_skills:
        matching_skills = [skill for skill in found_skills if skill in job_desc or skill in job_title]
        if matching_skills:
            specific_reasons.append(f"matches your {', '.join(matching_skills[:2])} experience")
    
    # Check for role match
    if resume_lower and job_title:
        # Simple keyword matching
        resume_words = set(resume_lower.split())
        job_words = set(job_title.split())
        common_words = resume_words.intersection(job_words)
        if len(common_words) > 2:
            specific_reasons.append("aligns with your career focus")
    
    # Check for experience level
    if "entry" in job_desc or "junior" in job_desc:
        if "entry" in resume_lower or "junior" in resume_lower or "recent graduate" in resume_lower:
            specific_reasons.append("suitable for your experience level")
    elif "senior" in job_desc or "lead" in job_desc:
        if "senior" in resume_lower or "lead" in resume_lower or "5+" in resume_lower or "years" in resume_lower:
            specific_reasons.append("matches your seniority level")
    
    if specific_reasons:
        reason_parts.append("- " + ", ".join(specific_reasons))
    else:
        reason_parts.append("- Strong alignment with your skills and experience")
    
    return " ".join(reason_parts)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

