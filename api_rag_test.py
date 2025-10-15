from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
import os

# Add your API key as a string
API_KEY = 'AIzaSyDsRutviDquMkxuPu2Eq8r2F-HktuGraaQ'

# Define your PDF path
PDF_PATH = "The styrene production2.pdf"


def setup_rag_chain(pdf_path: str):
    """
    Sets up a RAG chain by loading a PDF, creating/updating a ChromaDB vector store,
    and initializing the LangChain components with Google Gemini API.

    Args:
        pdf_path (str): The file path to the PDF document.

    Returns:
        The configured RAG chain.
    """
    db_name = os.path.splitext(os.path.basename(pdf_path))[0]
    persist_directory = f"./{db_name}_rag_db"

    # Initialize Google Gemini Embeddings
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001",
        google_api_key=API_KEY
    )

    vector_store = None  # Initialize vector_store variable

    # Check if the vector store directory exists and is not empty
    if os.path.exists(persist_directory) and os.listdir(persist_directory):
        print(f"A RAG vector store for '{db_name}' already exists. Continuing with the existing store...")
        # Load the existing vector store without making changes
        vector_store = Chroma(
            persist_directory=persist_directory,
            embedding_function=embeddings
        )
    else:
        print(f"Creating a new ChromaDB vector store for '{db_name}' at '{persist_directory}'...")
        loader = PyPDFLoader(pdf_path)
        documents = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        docs = text_splitter.split_documents(documents)

        if not docs:
            print("Error: The PDF file is empty or could not be processed.")
            return None

        vector_store = Chroma.from_documents(
            documents=docs,
            embedding=embeddings,
            persist_directory=persist_directory
        )
        print("New vector store created successfully.")

    # Check if a vector store was successfully created/loaded
    if not vector_store:
        return None

    # RAG Chain setup with Google Gemini
    retriever = vector_store.as_retriever(search_kwargs={"k": 5})

    # Initialize ChatGoogleGenerativeAI model
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        google_api_key=API_KEY,
        temperature=0.7,
        max_tokens=None,
        timeout=None,
        max_retries=2,
    )

    prompt = ChatPromptTemplate.from_template("""
    You are an assistant for question-answering tasks. Use the following pieces of retrieved context to answer the question.
    If you don't know the answer, just say that you don't know. 

    Question: {question}
    Context: {context}
    Answer:
    """)

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    rag_chain = (
            {"context": retriever | format_docs, "question": RunnablePassthrough()}
            | prompt
            | llm
            | StrOutputParser()
    )

    return rag_chain


def chat_with_pdf():
    """
    Main function to run the PDF chatbot.
    """
    rag_chain = setup_rag_chain(PDF_PATH)

    if rag_chain is None:
        return

    print("\n-------------------------------------------")
    print(f"Chatbot is ready. You can now ask questions about '{os.path.basename(PDF_PATH)}'.")
    print("Type 'exit' to quit.")
    print("-------------------------------------------")

    while True:
        user_question = input("\nYour question: ")
        if user_question.lower() == 'exit':
            print("Goodbye!")
            break

        print("Thinking...")
        try:
            response = rag_chain.invoke(user_question)
            print(f"\nChatbot: {response}")
        except Exception as e:
            print(f"An error occurred: {e}")
            break


# Example usage
if __name__ == "__main__":
    # Setup RAG chain
    rag_chain = setup_rag_chain(PDF_PATH)

    if rag_chain:
        # Single query example
        response = rag_chain.invoke('explain the styrene production process')
        print('Response:', response)
        print("\n" + "=" * 50 + "\n")

        # Interactive chat mode (optional - uncomment to use)
        # chat_with_pdf()
