from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.message import add_messages
from dotenv import load_dotenv

load_dotenv()

llm = ChatGoogleGenerativeAI(model='gemini-2.5-flash',stream='True')

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

graph = StateGraph(ChatState)
graph.add_node("chat_node", chat_node)
graph.add_edge(START, "chat_node")
graph.add_edge("chat_node", END)

chatbot = graph.compile(checkpointer=checkpointer)



