from typing import TypedDict ,List ,Union
from langchain_core.messages import HumanMessage ,AIMessage
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph ,START ,END
from dotenv import load_dotenv
from typing import Annotated , Sequence ,TypedDict
from langchain_core.messages import BaseMessage ,ToolMessage ,SystemMessage
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph  ,END ,START
from langgraph.prebuilt import ToolNode
from langchain.chat_models import init_chat_model
import os
import pandas as pd
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.llms import Ollama
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.output_parsers import StrOutputParser

from typing import Annotated , Sequence ,TypedDict
from langchain_core.messages import BaseMessage ,ToolMessage ,SystemMessage
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph  ,END ,START
from langgraph.prebuilt import ToolNode
from langchain.chat_models import init_chat_model


import operator
from typing import TypedDict, Sequence, Annotated

# Import necessary components from langchain and langgraph
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
# Assuming init_chat_model is a placeholder, using ChatOllama as an example
from langchain_community.chat_models import ChatOllama
from langchain_core.tools import tool # Correct import for @tool decorator
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

PDF_PATH = 'The styrene production.pdf'#'Production_of_Cumene_from_Benzene_Propylene.pdf'#"eg_asp.pdf"#"IPA1.pdf"
LLM_MODEL ='llama3.2:3b'#'deepseek-r1:1.5b'#"llama3.1:latest" #"llama3.2:3b"#"llama3.2:latest",#"phi3.5:latest",# "llama3.1:latest" #
EMBEDDING_MODEL ="mxbai-embed-large"# "snowflake-arctic-embed:33m"#


llm = init_chat_model(
    model="llama3.1:latest ",#"phi3.5:latest",#phi3.5",  # The name of the model in Ollama #'deepseek-r1:1.5b',# llama3.2:latest phi3.5:latest
    model_provider="ollama",  # Explicitly state the provider
    temperature=0.7,  # Optional: control creativity
    # base_url="http://localhost:11434" # Optional: If your Ollama is on a different host/port
)

import os
import shutil
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OllamaEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.prompts import ChatPromptTemplate
from langchain_community.chat_models import ChatOllama
from langchain.schema.output_parser import StrOutputParser
from langchain.schema.runnable import RunnablePassthrough
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain_community.chat_models import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage


# --- (Your global variables and init_chat_model function remain the same) ---

def setup_rag_chain(pdf_path: str):
    """
    Sets up a RAG chain by loading a PDF, creating/updating a ChromaDB vector store,
    and initializing the LangChain components.

    This modified version removes the 'add' and 'remove/replace' options
    and defaults to using the existing vector store if it's found.

    Args:
        pdf_path (str): The file path to the PDF document.

    Returns:
        The configured RAG chain.
    """
    db_name = os.path.splitext(os.path.basename(pdf_path))[0]
    persist_directory = f"./{db_name}_rag_db"

    embeddings = OllamaEmbeddings(model="mxbai-embed-large")  # Use a specific model for embeddings
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

    # RAG Chain setup logic, common to both paths
    retriever = vector_store.as_retriever(search_kwargs={"k": 5})
    llm = ChatOllama(model="llama3.2:3b")  # Use a specific chat model

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
            print("Please make sure the Ollama server is running and the models are pulled.")
            break

# chat_with_pdf()
rag_chain = setup_rag_chain(PDF_PATH)
response = rag_chain.invoke('explain the styrene production process')
print('response',response)

# def setup_rag_chain(pdf_path: str):
#     """
#     Sets up a RAG chain by loading a PDF, creating/updating a ChromaDB vector store,
#     and initializing the LangChain components.
#
#     Args:
#         pdf_path (str): The file path to the PDF document.
#
#     Returns:
#         The configured RAG chain.
#     """
#     # Create a directory name based on the PDF file name
#     db_name = os.path.splitext(os.path.basename(pdf_path))[0]
#     persist_directory = f"./{db_name}_rag_db"
#
#     # Check if the vector store already exists
#     if os.path.exists(persist_directory) and os.listdir(persist_directory):
#         print(f"A RAG vector store for '{db_name}' already exists at '{persist_directory}'.")
#         choice = input \
#             ("Do you want to (a)dd to it, (r)emove and replace it, or (c)ontinue with old RAG? (a/r/c): ").lower()
#
#         if choice == 'r':
#             print(f"Removing old vector store and creating a new one...")
#             # Remove existing directory and its contents
#             shutil.rmtree(persist_directory)
#             print("Old vector store removed.")
#
#             # Load and process the new PDF
#             loader = PyPDFLoader(pdf_path)
#             documents = loader.load()
#             text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
#             docs = text_splitter.split_documents(documents)
#
#             if not docs:
#                 print("Error: The PDF file is empty or could not be processed.")
#                 return None
#
#             embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)
#             vector_store = Chroma.from_documents(
#                 documents=docs,
#                 embedding=embeddings,
#                 persist_directory=persist_directory
#             )
#         elif choice == 'a':
#             print("Adding documents to the existing vector store...")
#             embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)
#             # Load the existing vector store
#             vector_store = Chroma(
#                 persist_directory=persist_directory,
#                 embedding_function=embeddings
#             )
#             # Load and process the new PDF to add to the existing store
#             loader = PyPDFLoader(pdf_path)
#             documents = loader.load()
#             text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
#             docs = text_splitter.split_documents(documents)
#
#             if not docs:
#                 print("Error: The new PDF file is empty or could not be processed.")
#                 return None
#
#             vector_store.add_documents(documents=docs)
#             print("Documents added successfully.")
#         elif choice == 'c':
#             print("Continuing with the existing vector store...")
#             embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)
#             # Load the existing vector store without making changes
#             vector_store = Chroma(
#                 persist_directory=persist_directory,
#                 embedding_function=embeddings
#             )
#         else:
#             print("Invalid choice. Operation cancelled.")
#             return None
#     else:
#         print(f"Creating a new ChromaDB vector store for '{db_name}' at '{persist_directory}'...")
#         loader = PyPDFLoader(pdf_path)
#         documents = loader.load()
#         text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
#         docs = text_splitter.split_documents(documents)
#
#         if not docs:
#             print("Error: The PDF file is empty or could not be processed.")
#             return None
#
#         embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)
#         vector_store = Chroma.from_documents(
#             documents=docs,
#             embedding=embeddings,
#             persist_directory=persist_directory
#         )
#         print("New vector store created successfully.")
#
#     print("Continuing with the existing vector store...")
#     embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)
#     # Load the existing vector store without making changes
#     vector_store = Chroma(
#         persist_directory=persist_directory,
#         embedding_function=embeddings
#     )
#     retriever = vector_store.as_retriever(search_kwargs={"k": 5})
#     llm = Ollama(model=LLM_MODEL)
#
#     prompt = ChatPromptTemplate.from_template("""
#     You are an assistant for question-answering tasks. Use the following pieces of retrieved context to answer the question.
#     If you don't know the answer, just say that you don't know.
#
#     Question: {question}
#     Context: {context}
#     Answer:
#     """)
#
#     def format_docs(docs):
#         return "\n\n".join(doc.page_content for doc in docs)
#
#     rag_chain = (
#             {"context": retriever | format_docs, "question": RunnablePassthrough()}
#             | prompt
#             | llm
#             | StrOutputParser()
#     )
#
#     return rag_chain
#
# def chat_with_pdf():
#     """
#     Main function to run the PDF chatbot.
#     """
#     rag_chain = setup_rag_chain(PDF_PATH)
#
#     if rag_chain is None:
#         return
#
#     print("\n-------------------------------------------")
#     print(f"Chatbot is ready. You can now ask questions about '{os.path.basename(PDF_PATH)}'.")
#     print("Type 'exit' to quit.")
#     print("-------------------------------------------")
#
#     while True:
#         user_question = input("\nYour question: ")
#         if user_question.lower() == 'exit':
#             print("Goodbye!")
#             break
#
#         print("Thinking...")
#         try:
#             response = rag_chain.invoke(user_question)
#             print(f"\nChatbot: {response}")
#         except Exception as e:
#             print(f"An error occurred: {e}")
#             print("Please make sure the Ollama server is running and the models are pulled.")
#             break
#
# chat_with_pdf()