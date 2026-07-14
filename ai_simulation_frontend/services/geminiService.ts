const API_URL = 'http://localhost:8000';

export const generateChatResponse = async (
  projectId: string,
  message: string,
  history: any[],
  modelName: string,
  apiKey: string
): Promise<string> => {
  try {
    const response = await fetch(`${API_URL}/projects/${projectId}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message,
        chat_history: history,
        model_name: modelName,
        api_key: apiKey
      }),
    });

    if (!response.ok) {
      // Handle missing API key on backend specific error or general failure
      if (response.status === 500) {
           return "Backend Error: Please ensure the API_KEY environment variable is set on the Python server.";
      }
      throw new Error(`Backend API error: ${response.statusText}`);
    }

    const data = await response.json();
    return data.text;
  } catch (error) {
    console.error("Error generating content:", error);
    if (error instanceof Error) {
      return `Connection Error: ${error.message}. Is the backend running?`;
    }
    return "An unknown error occurred while contacting the backend.";
  }
};
