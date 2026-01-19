import re
import json
import os
import ast
from typing import TypedDict, Sequence, Annotated
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
# from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolNode
from graphviz import Digraph
import uuid
import pandas as pd


API_KEY = 'AIzaSyDsRutviDquMkxuPu2Eq8r2F-HktuGraaQ'
PDF_PATH = 'The ethylbenzene production.pdf'
gemini_model ="gemini-2.5-flash-lite"

embeddings = GoogleGenerativeAIEmbeddings(
    model="models/text-embedding-004",
    google_api_key=API_KEY
)

llm = ChatGoogleGenerativeAI(
    model=gemini_model,
    google_api_key=API_KEY,
    temperature=0.7,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)


# --- State Management ---
def add_messages(left: list, right: list):
    """Function to add messages for state management"""
    return left + right


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


def clean_string(input_string):
    """
    Removes '```json', '\n', and '```' from a string.
    """
    cleaned_string = input_string.replace('```json', '')
    cleaned_string = cleaned_string.replace('\n', '')
    cleaned_string = cleaned_string.replace('```', '')
    return cleaned_string


def setup_rag_chain(pdf_path: str):
    """Sets up a RAG chain by loading a PDF and creating a ChromaDB vector store."""
    db_name = os.path.splitext(os.path.basename(pdf_path))
    persist_directory = f"./{db_name}_rag_db"

    if not os.path.exists(pdf_path):
        print(f"Error: The PDF file '{pdf_path}' was not found.")
        return None

    if not os.path.exists(persist_directory) or not os.listdir(persist_directory):
        print(f"Creating a new RAG vector store for '{db_name}'...")
        try:
            loader = PyPDFLoader(pdf_path)
            docs = loader.load()
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            splits = text_splitter.split_documents(docs)

            vector_store = Chroma.from_documents(
                documents=splits,
                embedding=embeddings,
                persist_directory=persist_directory
            )
            print(f"Vector store created at '{persist_directory}'.")
        except Exception as e:
            # print(f"Error creating vector store: {e}")
            return None
    else:
        # print(f"Loading existing RAG vector store for '{db_name}'.")
        vector_store = Chroma(
            persist_directory=persist_directory,
            embedding_function=embeddings
        )

    retriever = vector_store.as_retriever(search_kwargs={"k": 3})

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


# Initialize the RAG chain globally
RAG_CHAIN = setup_rag_chain(PDF_PATH)