import { GoogleGenAI } from "@google/genai";

// Safely attempt to get the API key from the environment
// Check if 'process' is defined to avoid crashing in browser environments
const getApiKey = () => {
  try {
    if (typeof process !== 'undefined' && process.env) {
      return process.env.API_KEY;
    }
  } catch (e) {
    // Ignore errors accessing process
  }
  return undefined;
};

const API_KEY = getApiKey();

if (!API_KEY) {
  console.warn("API_KEY environment variable not set. Using a mock response.");
}

const ai = API_KEY ? new GoogleGenAI({ apiKey: API_KEY }) : null;

export const generateChatResponse = async (prompt: string): Promise<string> => {
  if (!ai) {
    // Mock response for development without an API key
    await new Promise(resolve => setTimeout(resolve, 1000));
    return `This is a mock response for your prompt: "${prompt}". To use the real AI, please provide a Gemini API key.`;
  }

  try {
    const response = await ai.models.generateContent({
      model: 'gemini-2.5-flash',
      contents: prompt,
    });
    return response.text;
  } catch (error) {
    console.error("Error generating content:", error);
    if (error instanceof Error) {
      return `An error occurred: ${error.message}`;
    }
    return "An unknown error occurred while contacting the AI.";
  }
};