const API_URL = 'http://localhost:8000';

export const generateChatResponse = async (
  projectId: string,
  message: string,
  history: any[],
  modelName: string,
  apiKey: string
): Promise<{ text: string; flowDiagram: any | null }> => {
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
      if (response.status === 500) {
           return { text: "Backend Error: Please ensure the API_KEY environment variable is set on the Python server.", flowDiagram: null };
      }
      throw new Error(`Backend API error: ${response.statusText}`);
    }

    const data = await response.json();
    return {
        text: data.text,
        flowDiagram: data.flow_diagram || null
    };
  } catch (error) {
    console.error("Error generating content:", error);
    if (error instanceof Error) {
      return { text: `Connection Error: ${error.message}. Is the backend running?`, flowDiagram: null };
    }
    return { text: "An unknown error occurred while contacting the backend.", flowDiagram: null };
  }
};
