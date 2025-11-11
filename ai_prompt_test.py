'''case 1 test with x path'''

# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# import time
# import json
# import os
# import ast
# from typing import TypedDict, Sequence, Annotated
# from pydantic import BaseModel, Field
# from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
# from langchain_core.tools import tool
# from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
# from langchain_community.document_loaders import PyPDFLoader
# from langchain.text_splitter import RecursiveCharacterTextSplitter
# from langchain_community.vectorstores import Chroma
# from langchain_core.prompts import ChatPromptTemplate
# from langchain_core.runnables import RunnablePassthrough
# from langchain_core.output_parsers import StrOutputParser
# from langgraph.graph import StateGraph, END, START
# from langgraph.prebuilt import ToolNode
# from graphviz import Digraph
# import uuid
# import pandas as pd
# import requests
# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# import time
#
# def clean_string(input_string):
#     """
#     Removes '```json', '\n', and '```' from a string.
#     """
#     cleaned_string = input_string.replace('```json', '')
#     cleaned_string = cleaned_string.replace('\n', '')
#     cleaned_string = cleaned_string.replace('```', '')
#     return cleaned_string
#
# API_KEY = 'AIzaSyDsRutviDquMkxuPu2Eq8r2F-HktuGraaQ'
# # PDF_PATH = 'The styrene production3.pdf'
# gemini_model ="gemini-2.5-flash-lite"
#
# # Initialize Google Generative AI components
# # embeddings = GoogleGenerativeAIEmbeddings(
# #     model="models/text-embedding-004",
# #     google_api_key=API_KEY
# # )
#
# llm = ChatGoogleGenerativeAI(
#     model=gemini_model,
#     google_api_key=API_KEY,
#     temperature=0.3,
#     max_tokens=None,
#     timeout=None,
#     max_retries=2,
# )
#
#
# list_of_performance = """
#     Click on the "Elements" card,
#     Click on the "Text Box" menu item,
#     Enter text 'guru' into the "Full Name" input field,
#     Enter text 'guru44@gmail.com' into the "Email" input field,
#     Enter text 'chennai -50' into the "Current Address" input field,
#     Enter text 'Tamil Nadu' into the "Permanent Address" input field,
#     Click on the "Submit" button,
# """
#
# # list_of_performance = """
# #     Click on the "Elements" card,
# #     Click on the "Radio Button" menu item,
# #     Click the 'yes' radio button,
# #     Click the 'No' radio button,then click 'impressive' radio button """
# # #     Enter text 'guru' into the "Full Name" input field,
# # #     Enter text 'guru44@gmail.com' into the "Email" input field,
# # #     Enter text 'chennai -50' into the "Current Address" input field,
# # #     Enter text 'Tamil Nadu' into the "Permanent Address" input field,
# # #     Click on the "Submit" button,
# # # """
#
#
# prompt = '''
# As a web automation expert, your task is to analyze the user's steps and create a JSON dictionary where each step is a separate entry.
#
# **Instructions:**
# 1. Number each step sequentially starting from "step_1", "step_2", etc.
# 2. For each step, identify the appropriate tool from: [click, text fill, check box, expand and compress]
# 3. Create a nested dictionary structure where:
#    - The outer key is the step number (e.g., "step_1", "step_2")
#    - The value is an object with "tool" and "action" keys
#    - If the tool is text fill add one more key 'content' containing only the text to be added
#
# **CRITICAL: Your entire output MUST be valid JSON and NOTHING else.**
# - NO introductory text
# - NO explanations
# - NO markdown code fences (no ``````)
# - ONLY the raw JSON object
#
# **Required JSON Structure:**
# {
#   "step_1": {
#     "tool": "click",
#     "action": "Click on the 'Elements' card"
#   },
#   "step_2": {
#     "tool": "click",
#     "action": "Click on the 'Text Box' menu item"
#   }
#   "step_3": {
#     "tool": "text fill",
#     "action": "Fill the "Full Name" text fill with 'guru'",
#     "content":'guru'
#   }
# }
# '''
# updated_response = llm.invoke([
#     SystemMessage(content=prompt),
#     HumanMessage(content=f'user required steps : {list_of_performance}')
# ])
# xpath = updated_response.content
# print(xpath)
# data_step=json.loads(clean_string(xpath))
# # print()
#
# driver = webdriver.Chrome()
# driver.maximize_window()
# # Increased wait time for more reliability
# wait = WebDriverWait(driver, 10)
# url = 'https://demoqa.com'
#
# # def click_fun( path):
# #     link_element = wait.until(EC.element_to_be_clickable((By.XPATH, path)))
# #     link_element.click()
# #     time.sleep(1)
# #
# # def type_fun( element_id ,content):
# #     input_element = wait.until(EC.presence_of_element_located((By.ID, element_id)))
# #     input_element.send_keys(content)
# #     time.sleep(1)
#
# def click_fun(page_html,dict_input):
#     # prompt = f'''
#     # As a web automation expert, your task is to provide the most reliable
#     # XPath if the user action is 'click' or identify the 'id' attribute of an input element if the user action is 'text fill'
#     # from the page's HTML.
#     #
#     # User Action: "{dict_input["action"]}"
#     # HTML Snippet:
#     # {page_html}
#     # Return ONLY the XPath string,or the id without any additional text, quotes, or explanations.
#     # '''
#     prompt = f'''
# As a web automation expert, your task is to provide the most reliable XPath for an element based on the user's action and the page's HTML.
#
# User Action: "{dict_input["action"]}"
# HTML Snippet:
# ```
# {page_html}
# ```
# Return ONLY the XPath string, without any additional text, quotes, or explanations.'''
#
#     # prompt = f'''
#     # As a web automation expert, your task is to identify the 'id' attribute of an input element based on the user's action and the page's HTML.
#     # User Action: "{dict_input["action"]}"
#     # HTML Snippet:
#     # ```
#     # {page_html}
#     # ```
#     # Return ONLY the 'id' string, without any additional text, quotes, or explanations.
#     # '''
#     # print(page_html)
#
#
#
#     updated_response = llm.invoke([
#         SystemMessage(content="You are a web automation expert."),
#         HumanMessage(content=prompt)
#     ])
#     element_id = updated_response.content.strip()
#     link_element = wait.until(EC.element_to_be_clickable((By.XPATH, element_id)))
#     # link_element =wait.until(EC.presence_of_element_located((By.ID, element_id)))
#     link_element.click()
#     time.sleep(10)
#
# def type_fun( page_html,dict_input):
#     prompt = f'''
# As a web automation expert, your task is to identify the 'id' attribute of an input element based on the user's action and the page's HTML.
# User Action: "{dict_input["action"]}"
# HTML Snippet:
# ```
# {page_html}
# ```
# Return ONLY the 'id' string, without any additional text, quotes, or explanations.
# '''
#     updated_response = llm.invoke([
#         SystemMessage(content="You are a web automation expert."),
#         HumanMessage(content=prompt)
#     ])
#     element_id = updated_response.content.strip()
#     input_element = wait.until(EC.presence_of_element_located((By.ID, element_id)))
#     input_element.send_keys(dict_input["content"])
#     # input_element = wait.until(EC.presence_of_element_located((By.ID, element_id)))
#     # input_element.send_keys(content)
#     time.sleep(10)
#
# try:
#     driver.get(url)
#     print(f"Navigated to: {url}")
#
#     for i in range(len(data_step)):
#         page_html = driver.page_source
#         key_from_step = list(data_step.keys())[i]
#         if data_step[key_from_step]["tool"] == 'click':
#             click_fun(page_html,data_step[key_from_step])
#
#         elif data_step[key_from_step]["tool"] == "text fill":
#             type_fun(page_html, data_step[key_from_step])
#
#     time.sleep(10)
#
#
# except Exception as e:
#     print(f"An error occurred: {e}")
#
# finally:
#     if 'driver' in locals():
#         driver.quit()
#         print("Browser closed.")
#
#

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json
import os
import ast
from typing import TypedDict, Sequence, Annotated
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolNode
from graphviz import Digraph
import uuid
import pandas as pd
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def clean_string(input_string):
    """
    Removes '```json', '\n', and '```' from a string.
    """
    cleaned_string = input_string.replace('```json', '')
    cleaned_string = cleaned_string.replace('\n', '')
    cleaned_string = cleaned_string.replace('```', '')
    return cleaned_string

API_KEY = 'AIzaSyDsRutviDquMkxuPu2Eq8r2F-HktuGraaQ'
# PDF_PATH = 'The styrene production3.pdf'
gemini_model ="gemini-2.5-flash-lite"

# Initialize Google Generative AI components
# embeddings = GoogleGenerativeAIEmbeddings(
#     model="models/text-embedding-004",
#     google_api_key=API_KEY
# )

llm = ChatGoogleGenerativeAI(
    model=gemini_model,
    google_api_key=API_KEY,
    temperature=0.3,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)


list_of_performance = """
    Click on the "Elements" card,
    Click on the "Text Box" menu item,
    Enter text 'guru' into the "Full Name" input field,
    Enter text 'guru44@gmail.com' into the "Email" input field,
    Enter text 'chennai -50' into the "Current Address" input field,
    Enter text 'Tamil Nadu' into the "Permanent Address" input field,
    Click on the "Submit" button,
"""

# list_of_performance = """
#     Click on the "Elements" card,
#     Click on the "Radio Button" menu item,
#     Click the 'yes' radio button,
#     Click the 'No' radio button,then click 'impressive' radio button """
# #     Enter text 'guru' into the "Full Name" input field,
# #     Enter text 'guru44@gmail.com' into the "Email" input field,
# #     Enter text 'chennai -50' into the "Current Address" input field,
# #     Enter text 'Tamil Nadu' into the "Permanent Address" input field,
# #     Click on the "Submit" button,
# # """


prompt = '''
As a web automation expert, your task is to analyze the user's steps and create a JSON dictionary where each step is a separate entry.

**Instructions:**
1. Number each step sequentially starting from "step_1", "step_2", etc.
2. For each step, identify the appropriate tool from: [click, text fill, check box, expand and compress]
3. Create a nested dictionary structure where:
   - The outer key is the step number (e.g., "step_1", "step_2")
   - The value is an object with "tool" and "action" keys
   - If the tool is text fill add one more key 'content' containing only the text to be added 

**CRITICAL: Your entire output MUST be valid JSON and NOTHING else.**
- NO introductory text
- NO explanations
- NO markdown code fences (no ``````)
- ONLY the raw JSON object

**Required JSON Structure:**
{
  "step_1": {
    "tool": "click",
    "action": "Click on the 'Elements' card"
  },
  "step_2": {
    "tool": "click",
    "action": "Click on the 'Text Box' menu item"
  }
  "step_3": {
    "tool": "text fill",
    "action": "Fill the "Full Name" text fill with 'guru'",
    "content":'guru'
  }
}
'''
updated_response = llm.invoke([
    SystemMessage(content=prompt),
    HumanMessage(content=f'user required steps : {list_of_performance}')
])
xpath = updated_response.content
print(xpath)
data_step=json.loads(clean_string(xpath))
# print()

driver = webdriver.Chrome()
driver.maximize_window()
# Increased wait time for more reliability
wait = WebDriverWait(driver, 10)
url = 'https://demoqa.com'


def click_fun(page_html,dict_input):

#     prompt = f'''
# As a web automation expert, your task is to provide the most reliable XPath for an element based on the user's action and the page's HTML.
#
# User Action: "{dict_input["action"]}"
# HTML Snippet:
# ```
# {page_html}
# ```
# Return ONLY the XPath string, without any additional text, quotes, or explanations.'''
#
#     updated_response = llm.invoke([
#         SystemMessage(content="You are a web automation expert."),
#         HumanMessage(content=prompt)
#     ])
#     element_id = updated_response.content.strip()
#     link_element = wait.until(EC.element_to_be_clickable((By.XPATH, element_id)))
#     # link_element =wait.until(EC.presence_of_element_located((By.ID, element_id)))
#     link_element.click()
#     time.sleep(10)
    print('enter click')
    prompt = f'''As a web automation expert, your task is to identify the best locator like ID or Xpath attribute of an input element based on the user's action and the page's HTML.
Return is the json with the key as the locator and the value as the location like {{"ID":"userName"}} or {{"css":"div[class='category-cards'] div:nth-child(1) div:nth-child(1) div:nth-child(3) h5:nth-child(1)"}}
 or {{"xpath":"//input[@id='userName']"}} or {{"Name":"name attribute is not available for this element"}}
**CRITICAL: Your entire output MUST be valid JSON and NOTHING else.**
- NO introductory text
- NO explanations
- NO markdown code fences (no ``````)
- ONLY the raw JSON object
User Action: "{dict_input["action"]}"
HTML Snippet:
```
{page_html}
```
Return ONLY the 'id' string, without any additional text, quotes, or explanations.
'''
    print('exit prompt')
    updated_response = llm.invoke([
        SystemMessage(content="You are a web automation expert."),
        HumanMessage(content=prompt)
    ])
    print('updated_response=',updated_response)
    element_id = updated_response.content.strip()
    print('element_id=',element_id)
    data_step=json.loads(element_id)
    print('data =',list(data_step.values())[0]) #data_step)#
    input_element = wait.until(EC.presence_of_element_located((By.XPATH, list(data_step.values())[0])))
    # input_element.send_keys(dict_input["content"])
    # input_element = wait.until(EC.presence_of_element_located((By.ID, element_id)))
    input_element.click()
    # input_element.send_keys(content)
    time.sleep(10)

def type_fun( page_html,dict_input):
    prompt = f'''
As a web automation expert, your task is to identify the 'id' attribute of an input element based on the user's action and the page's HTML.
User Action: "{dict_input["action"]}"
HTML Snippet:
```
{page_html}
```
Return ONLY the 'id' string, without any additional text, quotes, or explanations.
'''
    updated_response = llm.invoke([
        SystemMessage(content="You are a web automation expert."),
        HumanMessage(content=prompt)
    ])
    element_id = updated_response.content.strip()
    input_element = wait.until(EC.presence_of_element_located((By.ID, element_id)))
    input_element.send_keys(dict_input["content"])
    # input_element = wait.until(EC.presence_of_element_located((By.ID, element_id)))
    # input_element.send_keys(content)
    time.sleep(10)

try:
    driver.get(url)
    print(f"Navigated to: {url}")

    for i in range(len(data_step)):
        page_html = driver.page_source
        key_from_step = list(data_step.keys())[i]
        if data_step[key_from_step]["tool"] == 'click':
            click_fun(page_html,data_step[key_from_step])



    time.sleep(10)


except Exception as e:
    print(f"An error occurred: {e}")

finally:
    if 'driver' in locals():
        driver.quit()
        print("Browser closed.")



# """
#
# list_of_performance = """
#     Click on the "Elements" card,
#     Click on the "Text Box" menu item,
#     Enter text 'guru' into the "Full Name" input field,
#     Enter text 'guru44@gmail.com' into the "Email" input field,
#     Enter text 'chennai -50' into the "Current Address" input field,
#     Enter text 'Tamil Nadu' into the "Permanent Address" input field,
#     Click on the "Submit" button,
# """
#
# prompt = '''
# As a web automation expert, your task is to analyze the user's steps and create a JSON dictionary where each step is a separate entry.
#
# **Instructions:**
# 1. Number each step sequentially starting from "step_1", "step_2", etc.
# 2. For each step, identify the appropriate tool from: [click, text fill, check box, expand and compress]
# 3. Create a nested dictionary structure where:
#    - The outer key is the step number (e.g., "step_1", "step_2")
#    - The value is an object with "tool" and "action" keys
#    - If the tool is "text fill", add one more key "content" containing only the text to be entered
#
# **CRITICAL: Your entire output MUST be valid JSON and NOTHING else.**
# - NO introductory text
# - NO explanations
# - NO markdown code fences (no ``````)
# - ONLY the raw JSON object
#
# **Required JSON Structure:**
# {
#   "step_1": {
#     "tool": "click",
#     "action": "Click on the 'Elements' card"
#   },
#   "step_2": {
#     "tool": "click",
#     "action": "Click on the 'Text Box' menu item"
#   },
#   "step_3": {
#     "tool": "text fill",
#     "action": "Fill the 'Full Name' text box with 'guru'",
#     "content": "guru"
#   }
# }
# '''
#
# # Helper function to clean JSON string
# def clean_string(text):
#     """Remove markdown code fences and extra whitespace"""
#     text = text.strip()
#     if text.startswith("```
#         text = text[7:]
#     elif text.startswith("```"):
#         text = text[3:]
#     if text.endswith("```
#         text = text[:-3]
#     return text.strip()
#
# # Get structured steps from LLM
# updated_response = llm.invoke([
#     SystemMessage(content=prompt),
#     HumanMessage(content=f'user required steps: {list_of_performance}')
# ])
#
# xpath_response = updated_response.content
# data_step = json.loads(clean_string(xpath_response))
# print("Parsed Steps:")
# print(json.dumps(data_step, indent=2))
#
# # Initialize WebDriver
# driver = webdriver.Chrome()
# driver.maximize_window()
# wait = WebDriverWait(driver, 10)
# url = 'https://demoqa.com'
#
# def click_fun(xpath_path):
#     """Click an element using XPath"""
#     try:
#         link_element = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_path)))
#         link_element.click()
#         time.sleep(1)
#         print(f"✓ Clicked element: {xpath_path}")
#     except Exception as e:
#         print(f"✗ Failed to click: {e}")
#
# def type_fun(element_id, content):
#     """Type text into an input field using ID"""
#     try:
#         input_element = wait.until(EC.presence_of_element_located((By.ID, element_id)))
#         input_element.clear()
#         input_element.send_keys(content)
#         time.sleep(1)
#         print(f"✓ Typed '{content}' into element: {element_id}")
#     except Exception as e:
#         print(f"✗ Failed to type: {e}")
#
# try:
#     driver.get(url)
#     print(f"Navigated to: {url}\n")
#
#     # Iterate through steps using .items()
#     for step_key, step_data in data_step.items():
#         print(f"\n--- Processing {step_key} ---")
#         print(f"Tool: {step_data['tool']}")
#         print(f"Action: {step_data['action']}")
#
#         # Get current page HTML
#         page_html = driver.page_source
#
#         # Create prompt based on tool type
#         if step_data['tool'] == 'click':
#             locator_prompt = f'''
# As a web automation expert, provide the most reliable XPath for clicking the element.
#
# User Action: "{step_data['action']}"
# HTML Snippet:
#
#
# """