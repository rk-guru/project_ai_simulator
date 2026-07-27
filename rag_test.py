import os
from ai_tools import retrieve_rag_documents, RAG_DIR
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.messages import HumanMessage

def test_rag_response(question: str, api_key: str, project_index: int):
    """
    Tests RAG retrieval and response for a specific project index in the RAG folder.
    """
    # 1. Identify the project folder by index
    if not os.path.exists(RAG_DIR):
        return "Error: RAG directory does not exist."

    project_folders = [f for f in os.listdir(RAG_DIR) if os.path.isdir(os.path.join(RAG_DIR, f))]

    if not project_folders:
        return "Error: No RAG project folders found."

    if project_index < 0 or project_index >= len(project_folders):
        return f"Error: Project index {project_index} out of range. Available indices: 0 to {len(project_folders)-1}"

    project_id = project_folders[project_index]
    print(f"Testing with Project ID: {project_id} (Index: {project_index})")

    # 2. Retrieve documents from RAG
    print(f"Retrieving documents for query: {question}...")
    docs = retrieve_rag_documents(api_key, project_id, question)

    if not docs:
        return f"No relevant documents found in RAG folder for project {project_id}."

    # 3. Prepare context for the LLM
    context_text = "\n\n".join([f"Source: {doc.metadata.get('source', 'unknown')}\nContent: {doc.page_content}" for doc in docs])

    prompt = (
        f"You are a helpful assistant. Use the following retrieved context from the project files to answer the user's question.\n\n"
        f"Context:\n{context_text}\n\n"
        f"User Question: {question}\n\n"
        f"Answer based strictly on the provided context. If the answer is not in the context, say 'I cannot find the answer in the uploaded project files'."
    )

    # 4. Generate response using Gemini
    try:
        llm = ChatGoogleGenerativeAI(
            model="gemma-4-31b-it",#"gemini-embedding-001",#"gemini-2.0-flash",
            google_api_key=api_key,
            temperature=0.1
        )
        response = llm.invoke([HumanMessage(content=prompt)])
        return response.content
    except Exception as e:
        return f"LLM Error: {str(e)}"

if __name__ == "__main__":
    print("--- RAG Testing Script ---")
    user_api_key = 123#input("Enter your Google API Key: ").strip()
    user_question = "explain the cumene process in the uploaded file ?"#input("Enter your question: ").strip()

    # List available projects
    if os.path.exists(RAG_DIR):
        folders = [f for f in os.listdir(RAG_DIR) if os.path.isdir(os.path.join(RAG_DIR, f))]
        print("\nAvailable RAG Projects:")
        for i, folder in enumerate(folders):
            print(f"[{i}] {folder}")
    else:
        print("RAG directory not found.")

    try:
        idx = 0#int(input("\nEnter the project index to test: "))
        result = test_rag_response(user_question, user_api_key, idx)
        print("\n--- AI Response ---")
        print(result)
        print("-------------------\n")
    except ValueError:
        print("Invalid index. Please enter a number.")
