# Job Finding AI Assistant

A production-ready AI-powered job search assistant built with FastAPI, Streamlit, LangGraph, and Google Gemini. It combines a conversational AI chatbot with a semantic resume-matching pipeline that pulls live job listings from stable external APIs.

## Features

- **Conversational AI Chat** — Powered by LangGraph + `gemini-2.5-flash` for natural, stateful conversations
- **Resume-Based Semantic Matching** — Upload a PDF, DOCX, or TXT resume; jobs are ranked by cosine similarity using `all-MiniLM-L6-v2` embeddings
- **Multi-Source Job Aggregation** — Adzuna API + RSS feeds (RemoteOK, Arbeitnow) + JSearch (RapidAPI)
- **Pure Cosine Ranking** — No keyword pre-filtering, no hard thresholds; all jobs ranked by embedding similarity, top 20 returned
- **Clean Deduplication** — Cross-source deduplication by normalised `title + company`
- **Intent Detection** — Chatbot auto-detects job-search intent and routes users to the job finder

## Project Structure

```
AI-Job-Finding-Assistant/
├── backend.py                   # FastAPI server — /find_jobs endpoint + LangGraph chatbot
├── streamlit_app.py             # Streamlit UI (chat + job finder)
├── chatbot_backend.py           # LangGraph chatbot with intent routing
├── resume_pipeline.py           # Resume text extraction (PDF / DOCX / TXT)
├── requirements.txt
├── .env
├── job_fetchers/
│   ├── adzuna.py                # Adzuna job search API
│   ├── jsearch_rapidapi.py      # JSearch via RapidAPI (paginated)
│   ├── rss_fetcher.py           # RSS feeds (RemoteOK, Arbeitnow, ...)
│   └── __init__.py
└── utils/
    ├── embeddings.py            # SentenceTransformer embedding helpers
    ├── query_builder.py         # Structured boolean query builder
    ├── text_processing.py       # HTML cleaning, key-info extraction
    ├── company_info.py          # Company info enrichment
    ├── job_analyzer.py          # Salary / requirements / benefits parser
    └── role_parser.py           # Role keyword parsing utilities
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

> **Note:** `sentence-transformers` requires PyTorch. The first run downloads the `all-MiniLM-L6-v2` model (~80 MB) automatically.

### 2. Environment Variables

Create a `.env` file in the project root:

```env
# Required -- Google Gemini (chatbot LLM)
GOOGLE_API_KEY=your_gemini_api_key_here

# Required for JSearch source
RAPIDAPI_KEY=your_rapidapi_key_here

# Adzuna job search API
ADZUNA_APP_ID=your_adzuna_app_id
ADZUNA_API_KEY=your_adzuna_api_key

# Optional -- override defaults
BACKEND_URL=http://localhost:8000
PORT=8000
```

### 3. Get API Keys

#### Google Gemini
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create an API key and set it as `GOOGLE_API_KEY`

#### RapidAPI (JSearch)
1. Sign up at [RapidAPI Hub](https://rapidapi.com/hub)
2. Subscribe to **JSearch** -- `jsearch.p.rapidapi.com` (free tier available)
3. Set the key as `RAPIDAPI_KEY`

#### Adzuna
Register at [developer.adzuna.com](https://developer.adzuna.com/) and set `ADZUNA_APP_ID` and `ADZUNA_API_KEY`.

#### RSS Feeds
Free and public -- no key required (RemoteOK, Arbeitnow).

## Running the Application

Start the backend in one terminal:

```bash
python backend.py
```

Start the frontend in another terminal:

```bash
streamlit run streamlit_app.py
```

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:8501`

## Usage

### Chat Mode
Type any message in the chat input. The AI responds naturally. If it detects job-search intent (e.g. "find me a job"), it guides you to the job finder.

### Job Finder Mode
1. Click **"Find Jobs With My Resume"** in the sidebar
2. Upload your resume (PDF, DOCX, or TXT)
3. Optionally fill in: desired role, location, experience level
4. Click **"Find Jobs"**
5. Results show: title, company, location, similarity score, match reason, salary, requirements, benefits, and a direct apply link

## How the Pipeline Works

```
Resume Upload
     |
     v
Text Extraction (PyPDF2 / python-docx / plain text)
     |
     v
Embed resume  <-- SentenceTransformers all-MiniLM-L6-v2 (local, free)
     |
     v
Parallel Job Fetch (each source in isolated try/except)
  +-- JSearch RapidAPI   up to 30 jobs x 2 pages
  +-- RSS feeds          up to 30 jobs (RemoteOK, Arbeitnow)
  +-- Adzuna             up to 20 jobs
     |
     v
Deduplication  <-- normalised(title + company), also dedupe by link
     |
     v
Embed job descriptions (batch cap: 100)
     |
     v
Cosine similarity vs resume embedding
     |
     v
Sort descending by similarity
     |
     v
Return top 20 results (no hard threshold)
     |
     v
Enrich: company info, salary, requirements, benefits
     |
     v
JSON response
```

## Adding a New Job Source

1. Create `job_fetchers/my_source.py`:

```python
def fetch_my_source_jobs(
    role=None,
    location=None,
    max_results=20,
):
    # Return list of dicts: title, company, location, description, link, source
    ...
```

2. In `backend.py`, add it inside `/find_jobs` (wrap in `try/except`):

```python
from job_fetchers.my_source import fetch_my_source_jobs

try:
    my_jobs = fetch_my_source_jobs(role=role, location=location, max_results=20)
    logger.info(f"My Source returned {len(my_jobs)} jobs")
    all_jobs.extend(my_jobs)
except Exception as e:
    logger.error(f"My Source failed -- continuing: {e}")
```

## Troubleshooting

### Backend won't start
- Check `GOOGLE_API_KEY` is set -- the LLM is initialised at startup
- Verify all packages: `pip install -r requirements.txt`

### 0 jobs returned
- Confirm `RAPIDAPI_KEY` is set and the JSearch RapidAPI subscription is active
- Verify Adzuna credentials (`ADZUNA_APP_ID` / `ADZUNA_API_KEY`)
- RSS feeds are free but may be temporarily unavailable

### Slow first run
`all-MiniLM-L6-v2` downloads ~80 MB on first use. Subsequent runs are fast.

### Resume upload issues
Supported formats: PDF, DOCX, TXT. Very large files (>5 MB) may time out.

### Embedding errors
```bash
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```

## Key Dependencies

| Package | Purpose |
|---------|---------|
| `fastapi` + `uvicorn` | REST API backend |
| `streamlit` | Frontend UI |
| `langgraph` + `langchain-google-genai` | LLM chatbot |
| `sentence-transformers` | Resume + job embeddings (local, free) |
| `scikit-learn` | Cosine similarity calculation |
| `requests` | API calls |
| `feedparser` | RSS feed parsing |
| `beautifulsoup4` | HTML description cleaning |
| `PyPDF2` + `python-docx` | Resume parsing |

## License

Open source -- free to use, modify, and distribute.
