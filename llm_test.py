# from langchain_community.chat_models import ChatOllama
# from langchain_core.messages import HumanMessage, SystemMessage
# import time
#
#
# start=time.time()
# # Instantiate the ChatOllama model
# chat_model = ChatOllama(model="llama3.1:latest")
#
# # Define messages for interaction
# messages = [
#     SystemMessage(content="You are a helpful assistant."),
#     HumanMessage(content="Explain the concept of quantum entanglement.")
# ]
#
# # Invoke the model to get a response
# response = chat_model.invoke(messages)
# print(response.content)
# end=time.time()
#
# total_time=end- start
# print(total_time)


from langchain_community.chat_models import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
import time

# --- Configuration for GPU usage ---
# Setting 'num_gpu': -1 tells Ollama to offload all available layers to the GPU.
GPU_CONFIG = {'num_gpu': -1}
# -----------------------------------

start=time.time()
# Instantiate the ChatOllama model, passing the GPU configuration
chat_model = ChatOllama(
    model="phi4:latest",
    model_kwargs=GPU_CONFIG
)

# Define messages for interaction
messages = [
    SystemMessage(content="You are a helpful assistant."),
    HumanMessage(content="Explain the concept of quantum entanglement.")
]

# Invoke the model to get a response
response = chat_model.invoke(messages)
print(response.content)
end=time.time()

total_time=end- start
print(f"\nTotal execution time: {total_time:.2f} seconds")
