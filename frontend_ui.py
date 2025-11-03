import streamlit as st
import pandas as pd
import time
from PIL import Image
import io
from ai_5 import run_document_agent

# --- Configuration and History Setup ---
st.set_page_config(page_title="Rich Chatbot Demo", layout="wide")
st.title("🤖 Rich Content Chatbot Demo")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []


# --- Custom Response Logic ---
def generate_response(prompt):
    """
    This function simulates the backend logic, returning different types
    of content based on the user's prompt.
    """
    prompt = prompt.lower().strip()

    if "table" in prompt or "dataframe" in prompt:
        # Simulate a DataFrame response
        data = {
            'Product': ['Laptop', 'Monitor', 'Keyboard', 'Mouse'],
            'Price (USD)': [1200, 350, 75, 25],
            'In Stock': [True, True, False, True]
        }
        df = pd.DataFrame(data)

        # Simulate a large response introduction
        yield "assistant", "Here is a large response with the sales data table you requested:"
        time.sleep(1)  # Simulate processing time
        yield "assistant", df

    elif "image" in prompt or "picture" in prompt:
        # Simulate an image response (create a simple image in memory)
        try:
            # You would normally load a saved image here: Image.open("path/to/image.jpg")
            # For this demo, we'll use a placeholder
            img = Image.new('RGB', (400, 200), color='lightblue')
            d = st.image(img, caption="Simulated Image Response", width=200)
            yield "assistant", "Here is a large response with a simulated image:"
            time.sleep(1)
            yield "assistant", d  # Streamlit will render components in the chat

        except Exception as e:
            yield "assistant", f"Sorry, could not display the image: {e}"

    elif len(prompt.split()) > 10:
        # Simulate a very large text response for long inputs
        large_text = "Thank you for your detailed query. My response needs to be quite extensive to cover all the points you raised. " * 10
        yield "assistant", "Here is a **very large text response** addressing your request:"
        time.sleep(1)
        yield "assistant", large_text

    elif prompt in ["hello", "hi"]:
        yield "assistant", "Hello! I can display **tables** and **images**. Try asking for one!"

    else:
        # Default text response
        yield "assistant", f"I received your message: '{prompt}'. You can ask me to display a **table** or an **image**."


# --- Display Chat History ---
for role, content in st.session_state.messages:
    with st.chat_message(role):
        # Streamlit intelligently handles different content types
        if isinstance(content, pd.DataFrame):
            st.dataframe(content)
        elif isinstance(content, st._DeltaGenerator):
            # For Streamlit component elements created inside the response generator
            content
        else:
            st.markdown(content)

# --- Chat Input ---
if prompt := st.chat_input("Ask me about a table or an image..."):
    # 1. Add user message to chat history and display
    st.session_state.messages.append(("user", prompt))
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Get and display assistant response (including rich content)
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""

        # Generator for streaming the response
        response_generator = generate_response(prompt)

        for role, content in response_generator:
            if isinstance(content, (pd.DataFrame, st._DeltaGenerator)):
                # Handle DataFrame and Streamlit components (images) separately
                st.session_state.messages.append((role, content))

                # Rerunning the app will display the component in the chat history
                st.rerun()
            else:
                # Handle text content
                # Stream the text for a better user experience
                for chunk in content.split():
                    full_response += chunk + " "
                    time.sleep(0.05)
                    message_placeholder.markdown(full_response + "▌")
                message_placeholder.markdown(full_response)
                st.session_state.messages.append((role, full_response))