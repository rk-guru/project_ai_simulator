import os
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

# --- Configuration ---

# Ensure you set the GEMINI_API_KEY environment variable.
# Example: export GEMINI_API_KEY="YOUR_API_KEY"
if not os.getenv("GEMINI_API_KEY"):
    print("Error: The GEMINI_API_KEY environment variable is not set.")
    print("Please set the key to use the Gemini API.")
    # Exit or use a placeholder/default mechanism if needed, but for security,
    # relying on the environment variable is best practice.
    # We will assume the key is set for the rest of the script logic.

PDF_PATH = 'The styrene production.pdf'
# Use recommended free-tier models for chat and embeddings
LLM_MODEL = "gemini-2.5-flash"
EMBEDDING_MODEL = "text-embedding-004"
COLLECTION_NAME = "styrene_production_2"


def setup_rag_chain(pdf_path: str):
    """
    Sets up the RAG chain: loads PDF, creates/loads vector store, and defines the LangChain runnable.
    """
    db_name = os.path.splitext(os.path.basename(pdf_path))[0]
    persist_directory = f"./{db_name}_rag_db"

    # Initialize Gemini Embeddings
    embeddings = GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL)

    if not os.path.exists(pdf_path):
        print(f"FATAL ERROR: PDF file '{pdf_path}' not found. Please place it in the script directory.")
        return None

    if not os.path.exists(persist_directory) or not os.listdir(persist_directory):
        print(f"Creating a new RAG vector store for '{COLLECTION_NAME}'...")
        try:
            # 1. Load Documents
            loader = PyPDFLoader(pdf_path)
            docs = loader.load()

            # 2. Split Documents
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            splits = text_splitter.split_documents(docs)

            # 3. Create Vector Store (ChromaDB)
            vector_store = Chroma.from_documents(
                documents=splits,
                embedding=embeddings,
                persist_directory=persist_directory,
                collection_name=COLLECTION_NAME
            )
            print(f"Vector store created at '{persist_directory}'.")
        except Exception as e:
            print(f"Error creating vector store: {e}")
            return None
    else:
        print(f"Loading existing RAG vector store from '{persist_directory}'.")
        # Load existing vector store
        vector_store = Chroma(
            persist_directory=persist_directory,
            embedding_function=embeddings,
            collection_name=COLLECTION_NAME
        )

    # 4. Define Retriever and LLM
    retriever = vector_store.as_retriever(search_kwargs={"k": 3})

    # Initialize Gemini Chat Model
    llm = ChatGoogleGenerativeAI(model=LLM_MODEL, temperature=0.1)

    # 5. Define Prompt Template
    prompt = ChatPromptTemplate.from_template("""
    You are an expert assistant for question-answering based on the provided document context.
    Use the following pieces of retrieved context to answer the question accurately.
    If the context does not contain the answer, state clearly that the information is not available in the document.

    Question: {question}
    Context: {context}
    Answer:
    """)

    # Helper function to format retrieved documents
    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    # 6. Construct the RAG Chain
    rag_chain = (
            {"context": retriever | format_docs, "question": RunnablePassthrough()}
            | prompt
            | llm
            | StrOutputParser()
    )

    return rag_chain


def run_rag_query(rag_chain, query: str):
    """Executes a query against the RAG chain and prints the result."""
    print(f"\n--- Running Query ---")
    print(f"Query: {query}")

    # Check if RAG chain is ready
    if not rag_chain:
        print("\nRAG chain is not initialized. Cannot run query.")
        return

    # Invoke the RAG chain
    try:
        response = rag_chain.invoke(query)
        print("\n--- RAG Response ---")
        print(response)
        print("----------------------")
    except Exception as e:
        print(f"\nAn error occurred during API call or processing: {e}")
        print("Please check your GEMINI_API_KEY and ensure it is valid.")


if __name__ == '__main__':
    rag_system = setup_rag_chain(PDF_PATH)

    # Example Query
    test_query = "What is the primary reaction involved in the styrene production process and what are the typical operating conditions?"

    run_rag_query(rag_system, test_query)

    # Another example query
    second_query = "Describe the purpose of the flash unit in the process flow diagram."

    run_rag_query(rag_system, second_query)
