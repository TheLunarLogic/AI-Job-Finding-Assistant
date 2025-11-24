# Job Finding AI Assistant

A comprehensive AI-powered job search assistant built with Streamlit, LangGraph, and Gemini. This application combines conversational AI with intelligent job matching based on resume analysis.

## Features

- **Conversational AI Chat**: Powered by LangGraph and Google Gemini for natural conversations
- **Resume-Based Job Matching**: Upload your resume (PDF, DOCX, TXT) and get ranked job recommendations
- **Multi-Source Job Aggregation**: Fetches jobs from Google Custom Search, RemoteOK, and Arbeitnow
- **Semantic Matching**: Uses Gemini embeddings to find the best job matches based on your resume
- **Intent Detection**: Automatically detects when users ask about job search and guides them to the job finder

## Project Structure

```
agent/
├── chatbot_backend.py      # LangGraph chatbot with intent routing
├── backend.py              # FastAPI server with /find_jobs endpoint
├── streamlit_app.py        # Streamlit frontend UI
├── resume_pipeline.py      # Resume text extraction (PDF/DOCX/TXT)
├── job_fetchers/
│   ├── google_cse.py       # Google Custom Search Engine integration
│   └── rss_fetcher.py      # RSS feed job aggregators
├── utils/
│   └── embeddings.py       # Gemini embeddings utilities
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Variables

Create a `.env` file in the project root with the following variables:

```env
# Required: Google Gemini API Key
GOOGLE_API_KEY=your_gemini_api_key_here

# Optional: Google Custom Search Engine (for enhanced job search)
GOOGLE_CSE_API_KEY=your_google_cse_api_key_here
GOOGLE_CSE_ID=your_google_cse_id_here

# Optional: Backend URL (defaults to http://localhost:8000)
BACKEND_URL=http://localhost:8000

# Optional: Backend server port (defaults to 8000)
PORT=8000
```

### 3. Get API Keys

#### Google Gemini API Key
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Add it to your `.env` file as `GOOGLE_API_KEY`

#### Google Custom Search Engine (Optional but Recommended)
1. Go to [Google Custom Search](https://programmablesearchengine.google.com/)
2. Create a new search engine
3. Add sites like:
   - `linkedin.com`
   - `indeed.com`
   - `glassdoor.com`
   - `monster.com`
4. Get your API key from [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
5. Add `GOOGLE_CSE_API_KEY` and `GOOGLE_CSE_ID` to your `.env` file

## Running the Application

### Start the Backend Server

In one terminal:

```bash
python backend.py
```

The backend will start on `http://localhost:8000` (or the port specified in your `.env` file).

### Start the Frontend

In another terminal:

```bash
streamlit run streamlit_app.py
```

The frontend will open in your browser at `http://localhost:8501`.

## Usage

### Chat Mode

1. Type your message in the chat input
2. The AI will respond naturally
3. If you ask about jobs (e.g., "find me a job"), the AI will guide you to use the job finder

### Job Finder Mode

1. Click "Find Jobs With My Resume" in the sidebar
2. Upload your resume (PDF, DOCX, or TXT)
3. Optionally fill in:
   - Desired Job Role
   - Location
   - Experience Level
4. Click "Find Jobs"
5. View ranked job results with:
   - Job title and company
   - Location
   - Match reason and similarity score
   - Direct link to apply

## How It Works

### Resume Processing
1. **Text Extraction**: Extracts text from PDF, DOCX, or TXT files
2. **Embedding Generation**: Creates a semantic embedding of your resume using Gemini
3. **Job Fetching**: Aggregates jobs from multiple sources:
   - Google Custom Search (LinkedIn, Indeed, Glassdoor)
   - RemoteOK RSS feed
   - Arbeitnow RSS feed
4. **Semantic Matching**: Generates embeddings for each job description and calculates cosine similarity
5. **Ranking**: Sorts jobs by similarity score (highest match first)
6. **Results**: Returns top 20 most relevant jobs

### Intent Detection

The chatbot automatically detects job-related queries using keyword matching:
- "find me a job"
- "search jobs"
- "job recommendations"
- "looking for job"
- And more...

When detected, the assistant guides users to the job finder UI.

## Adding New Job Sources

### Add a New RSS Feed

Edit `job_fetchers/rss_fetcher.py` and add a new function:

```python
def fetch_new_source_jobs(role: Optional[str] = None, max_results: int = 20) -> List[Dict[str, str]]:
    """Fetch jobs from new source."""
    # Implementation here
    pass
```

Then add it to `fetch_all_rss_jobs()`.

### Add a New API Source

Create a new file in `job_fetchers/` (e.g., `new_source.py`) and implement:

```python
def fetch_new_source_jobs(role: Optional[str] = None, location: Optional[str] = None) -> List[Dict[str, str]]:
    """Fetch jobs from new API source."""
    # Implementation here
    pass
```

Import and use it in `backend.py` in the `/find_jobs` endpoint.

## Changing Embedding Provider

To use a different embedding provider, edit `utils/embeddings.py`:

1. Import your embedding model
2. Replace `GoogleGenerativeAIEmbeddings` with your provider
3. Update the model initialization

Example for OpenAI:

```python
from langchain_openai import OpenAIEmbeddings
embeddings_model = OpenAIEmbeddings(model="text-embedding-ada-002")
```

## Troubleshooting

### Backend Connection Error

- Ensure the backend server is running (`python backend.py`)
- Check that `BACKEND_URL` in `.env` matches the backend server URL
- Verify the port is not already in use

### Resume Upload Issues

- Ensure your file is PDF, DOCX, or TXT format
- Check file size (very large files may timeout)
- Verify PyPDF2 and python-docx are installed

### No Jobs Found

- Check your Google CSE API key and ID are configured
- Verify internet connection for RSS feeds
- Try adjusting search criteria (role, location)
- Check that job sources are accessible

### Embedding Errors

- Verify `GOOGLE_API_KEY` is set correctly
- Check API quota/limits
- Ensure you have internet connection

## Development

### Project Architecture

- **Modular Design**: Each component (resume processing, job fetching, embeddings) is in separate modules
- **Separation of Concerns**: Frontend (Streamlit), Backend (FastAPI), and Chatbot (LangGraph) are separate
- **Extensible**: Easy to add new job sources, embedding providers, or features

### Key Files

- `chatbot_backend.py`: LangGraph state machine with intent routing
- `backend.py`: FastAPI REST API for job search
- `streamlit_app.py`: User interface with chat and job finder modes
- `resume_pipeline.py`: File parsing and text extraction
- `job_fetchers/`: Job source integrations
- `utils/embeddings.py`: Embedding generation and similarity calculation

## License

This project is open source and available for modification and distribution.

## Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.

