import os
import uuid
from typing import List, Dict, Any, Optional
from deepagents import create_deep_agent
from deepagents.backends import StateBackend
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.messages import HumanMessage, AIMessage
from langchain.tools import tool
from ai_tools import process_project_rag, retrieve_rag_documents, DUMMY_FLOW_DIAGRAM_DATA

async def generate_deep_agent_response(api_key: str, model_name: str, project_id: str, chat: str, chat_history: List[Dict[str, Any]] = None):
    """
    Function: Deep Agent Responder
    Orchestrates the AI response using the project's RAG data from ai_tools.
    """
    # Shared backend for the agent and its tools in this session
    backend = StateBackend()

    # Tools list
    tools = []

    # The RAG tool uses retrieve_rag_documents from ai_tools
    @tool(parse_docstring=True)
    def search_project_files(query: str) -> str:
        """this tool is a rag data extraction tool where the user query or the required information is passed to the rag db

        Args:
            query: Natural language search query.

        Returns:
            retrieved chunks data is returned
        """
        retrieved_docs = retrieve_rag_documents(api_key, project_id, query)
        print("retrieved_docs",retrieved_docs)
        if not retrieved_docs:
            return "No relevant information found in uploaded files."

        # batch_id = uuid.uuid4().hex[:8]
        # uploads = []
        # saved_paths = []
        #
        # for index, doc in enumerate(retrieved_docs, start=1):
        #     path = f"/retrieved/{batch_id}/chunk_{index}.md"
        #     content = f"# Source: {doc.metadata.get('source', 'unknown')}\n\n{doc.page_content}"
        #     uploads.append((path, content.encode("utf-8")))
        #     saved_paths.append(path)
        #
        # backend.upload_files(uploads)
        return retrieved_docs#f"Saved {len(saved_paths)} chunks:\n" + "\n".join(saved_paths)

    tools.append(search_project_files)

    # RAG Status
    from ai_tools import get_rag_dir
    rag_path = get_rag_dir(project_id)
    rag_exists = os.path.exists(rag_path) and os.listdir(rag_path)

    # Define the Analyst Subagent (from ref_script)
    chunk_analyst_subagent = {
        "name": "chunk-analyst",
        "description": "Analyze one retrieved project file chunk. Extract facts and return a concise summary.",
        "system_prompt": "You analyze retrieved project file chunks. Extract facts and return a concise summary under 300 words with key details and source.",
    }

    if rag_exists:
        instructions = (
            "# Project Files Q&A workflow\n"
            "Answer questions using the indexed project files.\n"
            "1. **Plan**: Use write_todos to break complex questions into focused search queries.\n"
            "2. **Search**: Call search_project_files with a query .\n"
            "3. **Analyze**: Delegate each chunk file to the chunk-analyst subagent with task().\n"
            "for question check if the data is already present in the rag information"
            "Do not answer from memory when file evidence is required. Search first."
        )
    else:
        instructions = "You are a helpful AI assistant. No project files have been uploaded, so please answer based on your general knowledge."

    model = ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        temperature=0.7,
    )

    agent = create_deep_agent(
        model,
        tools=tools,
        backend=backend,
        system_prompt=instructions,
        # subagents=[chunk_analyst_subagent] if rag_exists else [],
    )

    # Prepare messages
    messages = []
    if chat_history:
        for msg in chat_history:
            role = "user" if msg.get('sender') == 'user' else "ai"
            content = msg.get('text', '')
            messages.append(HumanMessage(content=content) if role == 'user' else AIMessage(content=content))

    messages.append(HumanMessage(content=chat))

    # Execute agent
    result = agent.invoke({"messages": messages})

    print("result", result)

    # Extraction logic for DeepAgent response
    try:
        # DeepAgent typically returns a list of messages. We want the content of the last AI message.
        last_msg = result["messages"][-1]

        # Handle the specific response structure if it's a list of content chunks
        if hasattr(last_msg, 'content') and isinstance(last_msg.content, list):
            # Try to find the 'text' key in the content chunks
            for chunk in last_msg.content:
                if isinstance(chunk, dict) and 'text' in chunk:
                    response = chunk['text']
                    break
            else:
                response = str(last_msg.content)
        elif hasattr(last_msg, 'content'):
            response = last_msg.content
        else:
            response = str(last_msg)

    except Exception as e:
        print(f"Error parsing agent response: {e}")
        response = "I encountered an error generating a response."

    return response, DUMMY_FLOW_DIAGRAM_DATA
