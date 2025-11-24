"""Streamlit frontend for Job Finding AI Assistant."""
import streamlit as st
from chatbot_backend import chatbot, llm
from langchain_core.messages import HumanMessage, AIMessage
import uuid
import requests
import os
from typing import Optional

# Backend API URL
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


def test_backend_connection() -> bool:
    """Test if backend is accessible."""
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        try:
            # Try root endpoint if health doesn't work
            response = requests.get(f"{BACKEND_URL}/", timeout=5)
            return response.status_code == 200
        except:
            return False

# **************************************** utility functions *************************

def generate_thread_id():
    thread_id = uuid.uuid4()
    return thread_id

def generate_chat_name(first_question: str) -> str:
    """Generate a concise summary/title for the chat based on the first question."""
    prompt = f"""Generate a concise title (maximum 5-7 words) that summarizes this question: "{first_question}"

Return only the title, nothing else."""
    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content.strip()

def reset_chat():
    thread_id = generate_thread_id()
    st.session_state['thread_id'] = thread_id
    add_thread(st.session_state['thread_id'])
    st.session_state['message_history'] = []

def add_thread(thread_id):
    if thread_id not in st.session_state['chat_threads']:
        st.session_state['chat_threads'].append(thread_id)

def load_conversation(thread_id):
    state = chatbot.get_state(config={'configurable': {'thread_id': thread_id}})
    # Check if messages key exists in state values, return empty list if not
    return state.values.get('messages', [])


# **************************************** Session Setup ****************************
if 'message_history' not in st.session_state:
    st.session_state['message_history'] = []

if 'thread_id' not in st.session_state:
    st.session_state['thread_id'] = generate_thread_id()

if 'chat_threads' not in st.session_state:
    st.session_state['chat_threads'] = []

if 'chat_names' not in st.session_state:
    st.session_state['chat_names'] = {}

if 'job_finder_mode' not in st.session_state:
    st.session_state['job_finder_mode'] = False

add_thread(st.session_state['thread_id'])

# **************************************** Sidebar UI *********************************

st.sidebar.title('Job Finding AI Assistant')

if st.sidebar.button('New Chat'):
    reset_chat()
    st.session_state['job_finder_mode'] = False

# Job Finder Mode Toggle
st.sidebar.divider()
st.sidebar.header('Job Finder')

if st.sidebar.button('Find Jobs With My Resume', use_container_width=True):
    st.session_state['job_finder_mode'] = True
    st.rerun()

if st.session_state['job_finder_mode']:
    st.sidebar.success("Job Finder Mode Active")
    if st.sidebar.button('Return to Chat', use_container_width=True):
        st.session_state['job_finder_mode'] = False
        st.rerun()

st.sidebar.divider()
st.sidebar.header('My Conversations')

for thread_id in st.session_state['chat_threads'][::-1]:
    # Get chat name or use thread_id as fallback
    chat_name = st.session_state['chat_names'].get(thread_id, str(thread_id))
    if st.sidebar.button(chat_name, key=f"chat_{thread_id}"):
        st.session_state['thread_id'] = thread_id
        messages = load_conversation(thread_id)

        temp_messages = []

        for msg in messages:
            if isinstance(msg, HumanMessage):
                role='user'
            else:
                role='assistant'
            temp_messages.append({'role': role, 'content': msg.content})

        st.session_state['message_history'] = temp_messages
        st.session_state['job_finder_mode'] = False
        st.rerun()


# **************************************** Main UI ************************************

# Job Finder Mode UI
if st.session_state['job_finder_mode']:
    st.title("🔍 Find Jobs With Your Resume")
    st.markdown("Upload your resume and we'll find the best matching jobs for you!")
    
    with st.form("job_finder_form"):
        # File uploader
        uploaded_file = st.file_uploader(
            "Upload Your Resume",
            type=['pdf', 'docx', 'txt'],
            help="Supported formats: PDF, DOCX, TXT"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            desired_role = st.text_input("Desired Job Role (Optional)", placeholder="e.g., Software Engineer")
            location = st.text_input("Location (Optional)", placeholder="e.g., Remote, New York")
        
        with col2:
            experience_level = st.selectbox(
                "Experience Level (Optional)",
                ["", "Entry Level", "Mid Level", "Senior Level", "Executive"]
            )
        
        submitted = st.form_submit_button("Find Jobs", use_container_width=True)
        
        # Test backend connection before processing
        if submitted and not test_backend_connection():
            st.error(f"❌ **Backend not accessible** at `{BACKEND_URL}`")
            st.info("**Please ensure:**")
            st.info("1. Backend server is running: `python backend.py`")
            st.info("2. Backend is accessible at the URL above")
            st.info("3. No firewall is blocking the connection")
            st.stop()
        
        if submitted:
            if uploaded_file is None:
                st.error("Please upload your resume file.")
            else:
                with st.spinner("Processing your resume and searching for jobs..."):
                    try:
                        # Read file content (reset file pointer if needed)
                        file_content = uploaded_file.read()
                        # Reset file pointer for potential re-read
                        uploaded_file.seek(0)
                        
                        # Prepare file for upload
                        files = {"resume": (uploaded_file.name, file_content, uploaded_file.type or "application/pdf")}
                        data = {
                            "role": desired_role if desired_role else None,
                            "location": location if location else None,
                            "experience_level": experience_level if experience_level else None
                        }
                        
                        # Remove None values
                        data = {k: v for k, v in data.items() if v is not None}
                        
                        # Make API request with longer timeout for processing
                        response = requests.post(
                            f"{BACKEND_URL}/find_jobs",
                            files=files,
                            data=data,
                            timeout=180  # 3 minutes timeout (reduced from 5, should be enough)
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            jobs = result.get("jobs", [])
                            
                            if jobs:
                                st.success(f"Found {len(jobs)} matching jobs!")
                                st.divider()
                                
                                # Display jobs in cards
                                for idx, job in enumerate(jobs, 1):
                                    with st.container():
                                        col1, col2 = st.columns([3, 1])
                                        
                                        with col1:
                                            st.markdown(f"### {idx}. {job['title']}")
                                            
                                            # Company info with details
                                            company_info = job.get('company_info', {})
                                            company_display = job['company']
                                            if company_info.get('size'):
                                                company_display += f" ({company_info['size']})"
                                            if company_info.get('industry'):
                                                company_display += f" - {company_info['industry']}"
                                            
                                            st.markdown(f"**Company:** {company_display}")
                                            st.markdown(f"**Location:** {job['location']}")
                                            
                                            # Salary information
                                            if job.get('salary'):
                                                st.markdown(f"💰 **Salary:** {job['salary']}")
                                            
                                            # Match reason with better formatting
                                            st.markdown(f"**Why this matches:** {job['match_reason']}")
                                            
                                            # Requirements
                                            if job.get('requirements'):
                                                with st.expander("📋 What They Need From You"):
                                                    for req in job['requirements']:
                                                        st.markdown(f"• {req}")
                                            
                                            # Benefits
                                            if job.get('benefits'):
                                                with st.expander("🎁 Benefits & Perks"):
                                                    for benefit in job['benefits']:
                                                        st.markdown(f"✓ {benefit}")
                                            
                                            # Description
                                            st.markdown("**Job Details:**")
                                            st.markdown(job['description'])
                                            
                                            # Company website if available
                                            if company_info.get('website'):
                                                st.markdown(f"🌐 [Company Website]({company_info['website']})")
                                        
                                        with col2:
                                            st.markdown(f"**Match Score:** {job['similarity_score']:.1%}")
                                            if job['link']:
                                                st.link_button("🔗 View Job", job['link'], use_container_width=True)
                                        
                                        st.divider()
                            else:
                                st.warning("No jobs found. Try adjusting your search criteria or uploading a different resume.")
                        else:
                            st.error(f"Backend returned error (status {response.status_code}): {response.text}")
                            
                    except requests.exceptions.ConnectionError as e:
                        st.error(f"❌ **Connection Error**: Could not connect to backend at `{BACKEND_URL}`")
                        st.info("**Troubleshooting:**")
                        st.info("1. Make sure the backend server is running: `python backend.py`")
                        st.info("2. Check that the backend is running on port 8000")
                        st.info(f"3. Verify the backend URL in your `.env` file or environment variables")
                        st.code(f"Error details: {str(e)}", language="text")
                    except requests.exceptions.Timeout as e:
                        st.error(f"⏱️ **Request Timeout**: The backend took too long to respond (>5 minutes)")
                        st.info("This might happen on the first request while the model is loading.")
                        st.info("Please try again - subsequent requests should be faster.")
                    except requests.exceptions.RequestException as e:
                        st.error(f"❌ **Request Error**: {str(e)}")
                        st.info(f"Backend URL: `{BACKEND_URL}`")
                    except Exception as e:
                        st.error(f"❌ **Unexpected Error**: {str(e)}")
                        import traceback
                        with st.expander("Error Details"):
                            st.code(traceback.format_exc(), language="python")

else:
    # Normal Chat Mode UI
    # loading the conversation history
    for message in st.session_state['message_history']:
        with st.chat_message(message['role']):
            st.text(message['content'])

    user_input = st.chat_input('Type here')

    if user_input:
        # Check if this is the first message in the conversation
        current_thread_id = st.session_state['thread_id']
        existing_messages = load_conversation(current_thread_id)
        is_first_message = len(existing_messages) == 0

        # first add the message to message_history
        st.session_state['message_history'].append({'role': 'user', 'content': user_input})
        with st.chat_message('user'):
            st.text(user_input)

        # Generate chat name from first question
        if is_first_message and current_thread_id not in st.session_state['chat_names']:
            chat_name = generate_chat_name(user_input)
            st.session_state['chat_names'][current_thread_id] = chat_name

        CONFIG = {'configurable': {'thread_id': current_thread_id}}

         # first add the message to message_history
        with st.chat_message("assistant"):
            def ai_only_stream():
                for message_chunk, metadata in chatbot.stream(
                    {"messages": [HumanMessage(content=user_input)]},
                    config=CONFIG,
                    stream_mode="messages"
                ):
                    if isinstance(message_chunk, AIMessage):
                        # yield only assistant tokens
                        yield message_chunk.content

            ai_message = st.write_stream(ai_only_stream())

        st.session_state['message_history'].append({'role': 'assistant', 'content': ai_message})

