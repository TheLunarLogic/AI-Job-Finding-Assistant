"""Backend server with LangGraph chatbot and job finding API."""
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated, List, Dict, Optional
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.message import add_messages
from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import uvicorn
import os
import json
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed

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
    experience_level: Optional[str] = Form(None),
    stream: Optional[str] = Form("false"),
):
    """
    Find jobs based on resume and optional filters.

    Args:
        resume: Resume file (PDF, DOCX, or TXT)
        role: Desired job role
        location: Job location
        experience_level: Experience level
        stream: "true" to enable SSE streaming, "false" (default) for batch JSON

    Returns:
        StreamingResponse (SSE) or JSONResponse depending on stream flag
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
        from sklearn.metrics.pairwise import cosine_similarity
        from job_fetchers.jsearch_rapidapi import fetch_jsearch_jobs_rapidapi
        from job_fetchers.rss_fetcher import fetch_all_rss_jobs
        from job_fetchers.adzuna import fetch_adzuna_jobs

        # Read and extract resume text
        resume_content = await resume.read()
        resume_text = extract_resume_text(resume_content, resume.filename)
        logger.info(f"Extracted resume text: {len(resume_text)} characters")

        # Generate resume embedding
        resume_embedding = embed_text(resume_text)
        logger.info("Generated resume embedding")

        logger.info(f"Filters - Role: {role}, Location: {location}, Experience: {experience_level}")

        # --- Concurrent Fetching from all sources ---
        def _fetch_jsearch():
            return fetch_jsearch_jobs_rapidapi(role=role, location=location, max_results=30, num_pages=2)

        def _fetch_rss():
            return fetch_all_rss_jobs(role=role, location=location, max_results=30)

        def _fetch_adzuna():
            return fetch_adzuna_jobs(role=role, location=location, max_results=20)

        source_counts = {"jsearch": 0, "rss": 0, "adzuna": 0}
        all_jobs = []

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(_fetch_jsearch): "jsearch",
                executor.submit(_fetch_rss): "rss",
                executor.submit(_fetch_adzuna): "adzuna",
            }
            for future in as_completed(futures):
                source_name = futures[future]
                try:
                    result = future.result()
                    source_counts[source_name] = len(result)
                    logger.info(f"{source_name} returned {len(result)} jobs")
                    all_jobs.extend(result)
                except Exception as e:
                    logger.error(f"{source_name} failed — continuing: {e}")

        logger.info(f"Total raw jobs fetched: {len(all_jobs)}")

        # --- Deduplication by normalised(title + company) ---
        seen_keys: set = set()
        seen_links: set = set()
        unique_jobs = []
        for job in all_jobs:
            norm_title = job.get("title", "").lower().strip()
            norm_company = job.get("company", "").lower().strip()
            dedup_key = (norm_title, norm_company)
            link = job.get("link", "")
            if dedup_key in seen_keys:
                continue
            if link and link in seen_links:
                continue
            if link:
                seen_links.add(link)
            seen_keys.add(dedup_key)
            unique_jobs.append(job)

        logger.info(f"After deduplication: {len(unique_jobs)} jobs")

        # Batch cap to avoid timeout / memory issues
        jobs_to_process = unique_jobs[:100]

        enable_stream = stream and stream.lower() == "true"

        if not jobs_to_process:
            if enable_stream:
                async def _empty_stream():
                    event = json.dumps({"type": "done", "total": 0, "message": "No jobs found. Try adjusting your search criteria."})
                    yield f"data: {event}\n\n"
                return StreamingResponse(_empty_stream(), media_type="text/event-stream")
            return JSONResponse({
                "jobs": [],
                "message": "No jobs found. Try adjusting your search criteria.",
                "debug_info": {
                    "jsearch_jobs": source_counts["jsearch"],
                    "rss_jobs": source_counts["rss"],
                    "adzuna_jobs": source_counts["adzuna"],
                    "total_raw_fetched": len(all_jobs),
                    "after_dedup": len(unique_jobs),
                    "role_filter": role,
                    "location_filter": location,
                }
            })

        # ============================================================
        # STREAMING PATH — yield jobs one-by-one as SSE events
        # ============================================================
        if enable_stream:
            async def _job_stream():
                streamed = 0
                for job in jobs_to_process:
                    try:
                        desc_text = f"{job['title']} {job['description']} {job.get('company', '')}"
                        job_emb = embed_text(desc_text)
                        similarity = float(cosine_similarity([resume_embedding], [job_emb])[0][0])

                        clean_description = clean_html(job.get("description", ""))
                        clean_description = extract_key_info(clean_description, max_length=400)

                        job_analysis = analyze_job(job.get("description", ""), job.get("company", ""))
                        company_name = job.get("company", "Not specified")
                        company_info = get_company_info(company_name, job.get("description", ""))
                        company_summary = generate_company_summary(
                            company_name, job.get("title", ""), clean_description
                        )
                        enhanced_description = f"{company_summary}\n\n{clean_description}"

                        event_data = {
                            "type": "job",
                            "title": job["title"],
                            "company": company_name,
                            "location": job["location"],
                            "description": enhanced_description,
                            "link": job["link"],
                            "source": job.get("source", "Unknown"),
                            "similarity_score": round(similarity, 3),
                            "match_reason": generate_match_reason(similarity, job, resume_text),
                            "company_info": {
                                "size": company_info.get("company_size") or job_analysis.get("employee_count"),
                                "industry": company_info.get("industry"),
                                "website": company_info.get("website"),
                            },
                            "salary": job_analysis.get("salary"),
                            "requirements": job_analysis.get("requirements", [])[:6],
                            "benefits": job_analysis.get("benefits", [])[:6],
                        }
                        yield f"data: {json.dumps(event_data)}\n\n"
                        streamed += 1
                    except Exception as e:
                        logger.error(f"Error streaming job: {e}")
                        continue

                # Sentinel
                yield f"data: {json.dumps({'type': 'done', 'total': streamed})}\n\n"
                logger.info(f"Streamed {streamed} jobs")

            return StreamingResponse(_job_stream(), media_type="text/event-stream")

        # ============================================================
        # BATCH PATH (default) — same as original behaviour
        # ============================================================

        # --- Embed job descriptions ---
        logger.info(f"Generating embeddings for {len(jobs_to_process)} jobs...")
        job_texts = [
            f"{job['title']} {job['description']} {job.get('company', '')}"
            for job in jobs_to_process
        ]
        job_embeddings = embed_texts(job_texts)
        logger.info("Job embeddings generated")

        # --- Cosine similarity ---
        similarity_scores = cosine_similarity([resume_embedding], job_embeddings)[0]

        for i, job in enumerate(jobs_to_process):
            similarity = float(similarity_scores[i])
            job["similarity_score"] = similarity
            job["match_reason"] = generate_match_reason(similarity, job, resume_text)

        # --- Sort descending, return top 20 (no hard threshold) ---
        ranked_jobs = sorted(
            jobs_to_process,
            key=lambda x: x.get("similarity_score", 0),
            reverse=True,
        )
        top_jobs = ranked_jobs[:20]
        logger.info(f"Top similarity: {top_jobs[0]['similarity_score']:.4f} | selected {len(top_jobs)} jobs")

        # --- Format results ---
        results = []
        for idx, job in enumerate(top_jobs):
            try:
                clean_description = clean_html(job.get("description", ""))
                clean_description = extract_key_info(clean_description, max_length=400)
                job_analysis = analyze_job(job.get("description", ""), job.get("company", ""))
                company_name = job.get("company", "Not specified")
                company_info = get_company_info(company_name, job.get("description", ""))
                company_summary = generate_company_summary(
                    company_name,
                    job.get("title", ""),
                    clean_description,
                )
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
                        "website": company_info.get("website"),
                    },
                    "salary": job_analysis.get("salary"),
                    "requirements": job_analysis.get("requirements", [])[:6],
                    "benefits": job_analysis.get("benefits", [])[:6],
                })
            except Exception as e:
                logger.error(f"Error formatting job {idx}: {e}")
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
                "jsearch_jobs": source_counts["jsearch"],
                "rss_jobs": source_counts["rss"],
                "adzuna_jobs": source_counts["adzuna"],
                "total_raw_fetched": len(all_jobs),
                "after_dedup": len(unique_jobs),
                "ranked_returned": len(results),
                "role_filter": role,
                "location_filter": location,
            }
        })

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Error processing job search: {error_details}")
        raise HTTPException(status_code=500, detail=f"Error processing job search: {str(e)}")


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

