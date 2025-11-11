
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
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

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
    clear text in the "Email" input field,
    Enter text 'guru44@gmail.com' into the "Email" input field,
    Enter text 'chennai -50' into the "Current Address" input field,
    Enter text 'Tamil Nadu' into the "Permanent Address" input field,
    Click on the "Submit" button,
"""
list_of_performance = """
    Click on the "Elements" card,
    Click on the "Buttons" from menu item,
    double click the "Double Click Me" button ,
    Right click on the "Right Click Me" button,
    click on the "Click Me" button
    ,
"""

# '''
#    - if the tool is drag-drop add two more keys 'drag' containing the element to be dragged and 'drop' containing the info of the drop location'''

prompt = '''
As a web automation expert, your task is to analyze the user's steps and create a JSON dictionary where each step is a separate entry.

**Instructions:**
1. Number each step sequentially starting from "step_1", "step_2", etc.
2. For each step, identify the appropriate tool from: [click, text fill,clear,right-click,double-click,hover , drag-drop , click_and_hold, release_click , keyboard]
3. Create a nested dictionary structure where:
   - The outer key is the step number (e.g., "step_1", "step_2")
   - The value is an object with "tool" and "action" keys
   - If the tool is text fill add one more key 'content' containing only the text to be added 
   - if the tool keys is selected add one more key 'keys' containing the list of keys to click like ['ENTER'] , ['TAB'],['ESCAPE'] , ['CONTROL' ,'a'] , ['CONTROL' ,'c'] 
   

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
  "step_4": {
    "tool": "keyboard",
    "action": "click CONTROL and 'a' in keyboard",
    "keys":['CONTROL' ,'a'] 
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
# driver.maximize_window()
wait = WebDriverWait(driver, 10)
url = 'https://demoqa.com'



try:
    driver.get(url)
    print(f"Navigated to: {url}")

    for i in range(len(data_step)):
        page_html = driver.page_source
        key_from_step = list(data_step.keys())[i]

        prompt = f'''As a web automation expert, your task is to identify the best locator like ID or relative Xpath or relative cssSelector attribute of an input element based on the user's action and the page's HTML.
        Return is the json with the key as the locator and the value as the location like {{"ID":"userName"}} or {{"css":"div[class='category-cards'] div:nth-child(1) div:nth-child(1) div:nth-child(3) h5:nth-child(1)"}}
         or {{"xpath":"//input[@id='userName']"}} or {{"Name":"name attribute is not available for this element"}}
         
        **CRITICAL: Your entire output MUST be valid JSON and NOTHING else.**
        - NO introductory text
        - NO explanations
        - NO markdown code fences (no ``````)
        - ONLY the raw JSON object
        User Action: "{data_step[key_from_step]["action"]}"
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
        element_step = json.loads(element_id)
        if (list(element_step.keys())[0]).lower() == 'xpath':
            input_element = wait.until(EC.presence_of_element_located((By.XPATH, list(element_step.values())[0])))
        if (list(element_step.keys())[0]).lower() == 'id':
            input_element = wait.until(EC.presence_of_element_located((By.ID, list(element_step.values())[0])))
        if (list(element_step.keys())[0]).lower() == 'css':
            input_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, list(element_step.values())[0])))
        if (list(element_step.keys())[0]).lower() == 'name':
            input_element = wait.until(EC.presence_of_element_located((By.NAME, list(element_step.values())[0])))
            
        if data_step[key_from_step]["tool"] == 'click':
            input_element.click()
        elif data_step[key_from_step]["tool"] == "text fill":
            input_element.send_keys(data_step[key_from_step]["content"])
        elif data_step[key_from_step]["tool"] == "clear":
            input_element.clear()
        elif data_step[key_from_step]["tool"] == "right-click": #right-click,double-click,hover , drag-drop
            actions = ActionChains(driver)
            actions.context_click(input_element).perform()
        elif data_step[key_from_step]["tool"] == "double-click":
            actions = ActionChains(driver)
            actions.double_click(input_element).perform()
        elif data_step[key_from_step]["tool"] == "hover":
            actions = ActionChains(driver)
            actions.move_to_element(input_element).perform()
        elif data_step[key_from_step]["tool"] == "click_and_hold":
            actions = ActionChains(driver)
            actions.click_and_hold(input_element).perform()
        elif data_step[key_from_step]["tool"] == "release_click":
            actions = ActionChains(driver)
            actions.release(input_element).perform()

        # if (list(element_step.keys())[0]).lower() == 'id':
        #     input_element = wait.until(EC.presence_of_element_located((By.ID, list(element_step.values())[0])))
        #     if data_step[key_from_step]["tool"] == 'click':
        #         input_element.click()
        #     elif data_step[key_from_step]["tool"] == "text fill":
        #         input_element.send_keys(data_step[key_from_step]["content"])
        #     elif data_step[key_from_step]["tool"] == "clear":
        #         input_element.clear()
        #     elif data_step[key_from_step]["tool"] == "right-click":  # right-click,double-click,hover , drag-drop
        #         actions = ActionChains(driver)
        #         actions.context_click(input_element).perform()
        #     elif data_step[key_from_step]["tool"] == "double-click":
        #         actions = ActionChains(driver)
        #         actions.double_click(input_element).perform()
        #     elif data_step[key_from_step]["tool"] == "hover":
        #         actions = ActionChains(driver)
        #         actions.move_to_element(input_element).perform()
        #
        # if (list(element_step.keys())[0]).lower() == 'css':
        #     input_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, list(element_step.values())[0])))
        #     if data_step[key_from_step]["tool"] == 'click':
        #         input_element.click()
        #     elif data_step[key_from_step]["tool"] == "text fill":
        #         input_element.send_keys(data_step[key_from_step]["content"])
        #     elif data_step[key_from_step]["tool"] == "clear":
        #         input_element.clear()
        #     elif data_step[key_from_step]["tool"] == "right-click":  # right-click,double-click,hover , drag-drop
        #         actions = ActionChains(driver)
        #         actions.context_click(input_element).perform()
        #     elif data_step[key_from_step]["tool"] == "double-click":
        #         actions = ActionChains(driver)
        #         actions.double_click(input_element).perform()
        #     elif data_step[key_from_step]["tool"] == "hover":
        #         actions = ActionChains(driver)
        #         actions.move_to_element(input_element).perform()
        #
        # if (list(element_step.keys())[0]).lower() == 'name':
        #     input_element = wait.until(EC.presence_of_element_located((By.NAME, list(element_step.values())[0])))
        #     if data_step[key_from_step]["tool"] == 'click':
        #         input_element.click()
        #     elif data_step[key_from_step]["tool"] == "text fill":
        #         input_element.send_keys(data_step[key_from_step]["content"])
        #     elif data_step[key_from_step]["tool"] == "clear":
        #         input_element.clear()
        #     elif data_step[key_from_step]["tool"] == "right-click":  # right-click,double-click,hover , drag-drop
        #         actions = ActionChains(driver)
        #         actions.context_click(input_element).perform()
        #     elif data_step[key_from_step]["tool"] == "double-click":
        #         actions = ActionChains(driver)
        #         actions.double_click(input_element).perform()
        #     elif data_step[key_from_step]["tool"] == "hover":
        #         actions = ActionChains(driver)
        #         actions.move_to_element(input_element).perform()

        # input_element.send_keys(content)
        time.sleep(10)

    time.sleep(10)


except Exception as e:
    print(f"An error occurred: {e}")

finally:
    if 'driver' in locals():
        driver.quit()
        print("Browser closed.")