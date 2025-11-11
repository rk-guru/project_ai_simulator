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


API_KEY = 'AIzaSyDsRutviDquMkxuPu2Eq8r2F-HktuGraaQ'
# PDF_PATH = 'The styrene production3.pdf'
gemini_model ="gemini-2.5-flash-lite"


llm = ChatGoogleGenerativeAI(
    model=gemini_model,
    google_api_key=API_KEY,
    temperature=0.7,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)
'''First set code '''
#
# try:
#     data = requests.get('https://demoqa.com')
#     print(data.text)
#
#     updated_response = llm.invoke([
#         SystemMessage(
#             content=f'''consider you are a web developer and tester and you need tho get the relative xpath for the text
#             of the web element 'Elements' from the html.Return ONLY the XPath string itself, with NO quotes,
#             comments, or extra text.'''),
#         HumanMessage(content=f'html information {data.text}')
#     ])
#
#     print('responce =',updated_response.content)
#     # Initialize the WebDriver
#     driver = webdriver.Chrome()
#     driver.maximize_window()
#     wait = WebDriverWait(driver, 4)
#
#     target_url="https://demoqa.com"
#
#     driver.get(target_url)
#
#     print(f"Navigated to: {target_url}")
#
#     WEB_TABLES_LINK_XPATH =str(updated_response.content)
#
#     # 3. Wait for the link to be clickable
#     link_element = wait.until(
#         EC.element_to_be_clickable((By.XPATH, WEB_TABLES_LINK_XPATH)))
#
#     # 4. Click the link
#     link_element.click()
#     # Wait to view the new page
#     time.sleep(5)
#
# except Exception as e:
#     print(f"An error occurred: {e}")
#
# finally:
#     if 'driver' in locals():
#         driver.quit()
#         print("Browser closed.")

'''second set of code'''
# list_of_performance=['Select the "Elements" button', 'Select the "Web Tables"', 'Click the "Add" button']
# # list_of_performance=['Select the "Elements" button', 'Select the "Text Box"', 'add text to text input "Full Name"', 'add text to text input "Email"']
# inputs=['','','guru','guru44@gmail.com']
# driver = webdriver.Chrome()
# driver.maximize_window()
# wait = WebDriverWait(driver, 4)
# url='https://demoqa.com'
# try:
#     for i in range(len(list_of_performance)):
#         data = requests.get(url)
#         print(data.text)
#
#         updated_response = llm.invoke([
#             SystemMessage(
#                 content=f'''consider you are a web developer and tester and you need tho get the relative xpath for the text
#                    of the web element needed for the user action from the html.Return ONLY the XPath string itself, with NO quotes,
#                    comments, or extra text.'''),
#             HumanMessage(content=f'user action {list_of_performance[i]} ,  html information {data.text}')
#         ])
#
#         print('responce =', updated_response.content)
#         # Initialize the WebDriver
#
#         target_url = url  # "https://demoqa.com"
#
#         driver.get(target_url)
#
#         print(f"Navigated to: {target_url}")
#
#         WEB_TABLES_LINK_XPATH = str(updated_response.content)
#         link_element = wait.until(EC.element_to_be_clickable((By.XPATH, WEB_TABLES_LINK_XPATH)))
#         link_element.click()
#
#
#         url = driver.current_url
#         # Wait to view the new page
#         time.sleep(5)
#
# except Exception as e:
#     print(f"An error occurred: {e}")
#
# finally:
#     if 'driver' in locals():
#         driver.quit()
#         print("Browser closed.")  #//*[text()='Element']


"""third iter"""

# list_of_performance=['Select the "Elements" button', 'Select the "Web Tables"', 'Click the "Add" button']
# list_of_performance=['Select the "Elements" button', 'Select the "Text Box"', 'add text to text input "Full Name"', 'add text to text input "Email"']
# inputs=['','','guru','guru44@gmail.com']
# driver = webdriver.Chrome()
# driver.maximize_window()
# wait = WebDriverWait(driver, 4)
# url='https://demoqa.com'
# try:
#     for i in range(len(list_of_performance)):
#         data = requests.get(url)
#         print(data.text)
#
#         # 4. Click the link
#         if i not in [2, 3]:
#             updated_response = llm.invoke([
#                 SystemMessage(
#                     content=f'''consider you are a web developer and tester and you need tho get the relative xpath for the text
#             of the web element needed for the user action from the html.Return ONLY the XPath string itself, with NO quotes,
#             comments, or extra text.'''),
#                 HumanMessage(content=f'user action {list_of_performance[i]} ,  html information {data.text}')
#             ])
#
#             print('responce =', updated_response.content)
#             # Initialize the WebDriver
#
#             target_url = url  # "https://demoqa.com"
#
#             driver.get(target_url)
#
#             print(f"Navigated to: {target_url}")
#
#             WEB_TABLES_LINK_XPATH = str(updated_response.content)
#             link_element = wait.until(EC.element_to_be_clickable((By.XPATH, WEB_TABLES_LINK_XPATH)))
#             link_element.click()
#         else:
#             updated_response = llm.invoke([
#                 SystemMessage(
#                     content=f'''consider you are a web developer and tester and you need tho get the relative ID for
#                      web element needed for the user action from the html.Return ONLY the ID string itself, with NO quotes,
#             comments, or extra text.'''),
#                 HumanMessage(content=f'user action {list_of_performance[i]} ,  html information {data.text}')
#             ])
#
#             print('responce =', updated_response.content)
#             # Initialize the WebDriver
#
#             target_url = url  # "https://demoqa.com"
#
#             driver.get(target_url)
#
#             print(f"Navigated to: {target_url}")
#
#             WEB_TABLES_LINK_XPATH = str(updated_response.content)
#             link_element = wait.until(EC.element_to_be_clickable((By.ID, WEB_TABLES_LINK_XPATH)))
#             link_element.send_keys(inputs[i])
#         url = driver.current_url
#         # Wait to view the new page
#         time.sleep(5)
#
# except Exception as e:
#     print(f"An error occurred: {e}")
#
# finally:
#     if 'driver' in locals():
#         driver.quit()
#         print("Browser closed.")  #//*[text()='Element']

""" test text input"""

# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.chrome.service import Service as ChromeService
# from webdriver_manager.chrome import ChromeDriverManager
# import time
#
# # --- Configuration ---
# # Assuming the user is targeting a known demo site's form (Text Box)
# TARGET_URL = "https://demoqa.com/text-box"
#
#
# def fill_and_submit_form():
#     """
#     Initializes the Chrome WebDriver, navigates to the URL, fills the form fields,
#     and clicks the submit button.
#     """
#     print("Starting WebDriver...")
#     try:
#         # Automatically set up the Chrome driver
#         service = ChromeService(ChromeDriverManager().install())
#         driver = webdriver.Chrome(service=service)
#         driver.maximize_window()
#
#         # 1. Navigate to the target page
#         driver.get(TARGET_URL)
#         print(f"Successfully navigated to: {TARGET_URL}")
#
#         # Give the page a moment to load and render the form (especially for SPA frameworks)
#         time.sleep(2)
#
#         # --- Data to input ---
#         test_data = {
#             # Assumed ID for 'name' text box
#             "userName": "Alice Tester",
#             # Assumed ID for 'mail id' text box
#             "userEmail": "alice.tester@example.com",
#             # Assumed ID for 'other box' (Current Address)
#             "currentAddress": "123 Automation Lane, Selenium City, CA 90001",
#         }
#
#         # 2. Locate and fill the fields
#         for element_id, value in test_data.items():
#             try:
#                 # Find the element by its ID and use send_keys() to type the value
#                 input_element = driver.find_element(By.ID, element_id)
#                 input_element.send_keys(value)
#                 print(f"Filled '{element_id}' with: '{value}'")
#             except Exception as e:
#                 print(f"Error locating or filling element with ID '{element_id}': {e}")
#                 # Continue execution even if one element fails
#
#         # 3. Locate and click the Submit button
#         # The submit button is typically a <button> or <input type="submit">
#         try:
#             submit_button = driver.find_element(By.ID, "submit")
#             submit_button.click()
#             print("\nClicked the Submit button.")
#         except Exception as e:
#             print(f"Error locating or clicking the Submit button: {e}")
#
#         # Wait a moment to see the result of the submission
#         time.sleep(3)
#
#     except Exception as e:
#         print(f"An error occurred during automation: {e}")
#
#     # finally:
#     #     # 4. Close the browser
#     #     if 'driver' in locals():
#     #         driver.quit()
#     #         print("WebDriver closed.")
#
#
# if __name__ == "__main__":
#     # NOTE: You need to have Python and the 'selenium' and 'webdriver-manager' libraries installed
#     # (e.g., pip install selenium webdriver-manager) to run this script.
#     fill_and_submit_form()


list_of_performance = [
    'Click on the "Elements" card',
    'Click on the "Text Box" menu item',
    'Enter text into the "Full Name" input field',
    'Enter text into the "Email" input field',
    'Enter text into the "Current Address" input field',
    'Enter text into the "Permanent Address" input field',
    'Click on the "Submit" button',
]
inputs = ['', '', 'guru', 'guru44@gmail.com',"chennai-28" ,"tamil nadu"]

driver = webdriver.Chrome()
driver.maximize_window()
# Increased wait time for more reliability
wait = WebDriverWait(driver, 7)
url = 'https://demoqa.com'

try:
    # Navigate to the initial URL once before the loop
    driver.get(url)
    print(f"Navigated to: {url}")

    for i in range(len(list_of_performance)):
        # Use driver.page_source to get the current HTML of the page
        page_html = driver.page_source

        if i not in [2, 3,4,5]:
            # This block is for clicking elements
            prompt = f'''
            As a web automation expert, your task is to provide the most reliable XPath for an element based on the user's action and the page's HTML.

            User Action: "{list_of_performance[i]}"
            HTML Snippet:
            ```
            {page_html}
            ```
            Return ONLY the XPath string, without any additional text, quotes, or explanations.
            '''
            updated_response = llm.invoke([
                SystemMessage(content="You are a web automation expert."),
                HumanMessage(content=prompt)
            ])
            xpath = updated_response.content.strip()
            print(f"Action: {list_of_performance[i]}, Generated XPath: {xpath}")

            link_element = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
            link_element.click()
        else:
            # This block is for inputting text
            prompt = f'''
            As a web automation expert, your task is to identify the 'id' attribute of an input element based on the user's action and the page's HTML.

            User Action: "{list_of_performance[i]}"
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
            print(f"Action: {list_of_performance[i]}, Generated ID: {element_id}")

            input_element = wait.until(EC.presence_of_element_located((By.ID, element_id)))
            input_element.send_keys(inputs[i])

        # A short pause to observe the result of the action
        time.sleep(10)

except Exception as e:
    print(f"An error occurred: {e}")

finally:
    if 'driver' in locals():
        driver.quit()
        print("Browser closed.")
