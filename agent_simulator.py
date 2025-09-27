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

from Property_package import PropertyPackage




llm = init_chat_model(
    model="llama3.1:latest ",#phi3.5",  # The name of the model in Ollama #'deepseek-r1:1.5b',#
    model_provider="ollama",  # Explicitly state the provider
    temperature=0.7,  # Optional: control creativity
    # base_url="http://localhost:11434" # Optional: If your Ollama is on a different host/port
)


# --- Example Usage ---
# if __name__ == "__main__":
    # Define the stream conditions and components with mole fractions
    # This temperature should result in a two-phase mixture
chemicals_in_stream = {'Water': 1.0, 'Methane': 0.0}
temperature = 374.0  # K
pressure = 101325.0  # Pa (1 atm)
molar_flowrate = 10.0  # mol/s

# Create an instance of the property package
stream_package = PropertyPackage('Two-Phase Stream', chemicals_in_stream, temperature, pressure, molar_flowrate)

# Calculate all combined properties for the mixture
mixture_properties = stream_package.calculate_all_mixture_properties()
stream_package.stream_result()

# Print the results
# print("--- Combined Mixture Properties Calculation ---")
# for key, value in mixture_properties.items():
#     if isinstance(value, float):
#         print(f"  {key}: {value:.4f}")
#     elif isinstance(value, dict):
#         print(f"  {key}:")
#         for sub_key, sub_value in value.items():
#             print(f"    - {sub_key}: {sub_value:.4f}")
#     else:
#         print(f"  {key}: {value}")
#
# print("\n-------------------------------------")
