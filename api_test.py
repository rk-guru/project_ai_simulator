#
# import os
# from langchain_google_genai import ChatGoogleGenerativeAI
# from langchain_core.prompts import ChatPromptTemplate
# from langchain_core.output_parsers import StrOutputParser
#
# # --- Configuration for PyCharm/Local Development ---
#
# # 1. Check if the GOOGLE_API_KEY environment variable is set.
# #    In PyCharm, set this variable in your 'Run/Debug Configurations' environment variables.
# # gemini_api_key_string =  # Replace with your actual key if needed
# api_key = 'AIzaSyDsRutviDquMkxuPu2Eq8r2F-HktuGraaQ'#os.getenv(gemini_api_key_string)
#
# # if not api_key:
# #     # If the key is not set, print an error and exit gracefully.
# #     print("FATAL ERROR: The GOOGLE_API_KEY environment variable is not set.")
# #     print("Please set your Gemini API key in PyCharm's 'Run/Debug Configurations' environment variables.")
# #     exit(1)
#
# # --- LangChain Setup ---
#
# # 2. Initialize the LangChain model wrapper.
# # LangChain automatically uses the GOOGLE_API_KEY environment variable if it's set.
# MODEL_NAME = 'gemini-2.5-flash'
# llm = ChatGoogleGenerativeAI(model=MODEL_NAME)
#
# # 3. Define the prompt template.
# prompt_template = ChatPromptTemplate.from_messages([
#     ("system", "You are a creative poet focused on themes of education and growth."),
#     ("user", "{user_prompt}")
# ])
#
# # 4. Define the prompt and build the chain (Prompt -> Model -> Output Parser).
# user_prompt = "Write a short poem about the importance of learning."
# chain = prompt_template | llm | StrOutputParser()
#
# print(f"Attempting to generate content using LangChain and model: {MODEL_NAME}...")
# print("-" * 40)
#
# try:
#     # 5. Invoke the chain.
#     response = chain.invoke({"user_prompt": user_prompt})
#
#     # Print the response text
#     print("Gemini API Response (via LangChain):")
#     print(response)
#
# except Exception as e:
#     # This block handles network errors, API rate limits, or invalid keys.
#     print(f"An error occurred: {e}")

# Install required package first:
# pip install langchain-google-genai

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

# Add your API key as a string
API_KEY = 'AIzaSyDsRutviDquMkxuPu2Eq8r2F-HktuGraaQ'

# Initialize the ChatGoogleGenerativeAI model with API key
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-lite",  # or "gemini-pro", "gemini-1.5-pro"
    google_api_key=API_KEY,
    temperature=0.7,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)

# Example 1: Simple text generation
print("Example 1: Simple invoke")
response = llm.invoke("Explain quantum computing in simple terms")
print(response.content)
print("\n" + "="*50 + "\n")

# Example 2: Using messages with system and human prompts
print("Example 2: Using message format")
messages = [
    SystemMessage(content="You are a helpful assistant that translates English to French."),
    HumanMessage(content="I love programming with Python."),
]
response = llm.invoke(messages)
print(response.content)
print("\n" + "="*50 + "\n")

# Example 3: Streaming response
print("Example 3: Streaming response")
for chunk in llm.stream("Write a short poem about artificial intelligence"):
    print(chunk.content, end="", flush=True)
print("\n" + "="*50 + "\n")
