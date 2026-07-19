import React, { useState, useRef, useEffect } from 'react';
import { ChatMessage } from '../types';
import { generateChatResponse } from '../services/geminiService';
import { dbService } from '../services/db';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import SendIcon from './icons/SendIcon';
import UploadIcon from './icons/UploadIcon';

interface ChatbotProps {
    projectId: string;
    messages: ChatMessage[];
    setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>;
    onFlowDiagramReceived?: (diagramData: any) => void;
}

const Chatbot: React.FC<ChatbotProps> = ({ projectId, messages, setMessages, onFlowDiagramReceived }) => {
  const [input, setInput] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [uploadedFileName, setUploadedFileName] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);
  
  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setIsUploading(true);
      try {
          // Get API key from localStorage
          const apiKey = localStorage.getItem('apiKey') || '';
          // Upload to backend linked to project ID
          await dbService.uploadFile(projectId, file, apiKey);
          setUploadedFileName(file.name);
          
          // Add system message about upload
          setMessages(prev => [...prev, {
              id: Date.now().toString(),
              sender: 'ai',
              text: `File "${file.name}" uploaded successfully. I can now use it for context.`
          }]);
      } catch (error) {
          console.error("Upload failed", error);
          alert("Failed to upload file to backend.");
      } finally {
          setIsUploading(false);
      }
    }
  };

  const handleSend = async () => {
    if (input.trim() === '') return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      sender: 'user',
      text: input,
    };

    const typingMessage: ChatMessage = {
      id: (Date.now() + 1).toString(),
      sender: 'ai',
      text: '',
      isTyping: true,
    }

    setMessages(prev => [...prev, userMessage, typingMessage]);
    setInput('');

    // Call backend API for chat response (context is handled on backend via file system)
    const modelName = localStorage.getItem('modelName') || 'gemini-2.0-flash';
    const apiKey = localStorage.getItem('apiKey') || '';
    const currentHistory = [...messages, userMessage];

    const response = await generateChatResponse(
      projectId,
      input,
      currentHistory,
      modelName,
      apiKey
    );

    if (response.flowDiagram) {
        onFlowDiagramReceived?.(response.flowDiagram);
    }

    const aiMessage: ChatMessage = {
      id: (Date.now() + 1).toString(),
      sender: 'ai',
      text: response.text,
    };
    
    setMessages(prev => [...prev.slice(0, -1), aiMessage]);
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-800/50 rounded-lg">
      <div className="p-4 border-b border-slate-700/50 flex items-center justify-between">
         <p className="text-sm text-gray-400">AI Assistant</p>
         <div>
            <button
                onClick={handleUploadClick}
                disabled={isUploading}
                className="flex items-center px-3 py-1.5 text-xs font-semibold text-white bg-slate-700 rounded-md hover:bg-slate-600 transition-colors disabled:opacity-50"
            >
                <UploadIcon className="w-4 h-4 mr-2" />
                {isUploading ? 'Uploading...' : (uploadedFileName ? 'File Uploaded' : 'Upload PDF')}
            </button>
            <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileChange}
                accept=".pdf,.csv,.txt"
                className="hidden"
            />
         </div>
      </div>
      <div className="flex-1 p-4 overflow-y-auto space-y-4">
        {messages.map((msg) => (
          <div key={msg.id} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-lg px-4 py-2 rounded-lg ${msg.sender === 'user' ? 'bg-indigo-600 text-white' : 'bg-slate-700 text-gray-200'}`}>
              {msg.isTyping ? (
                 <div className="flex items-center space-x-1">
                    <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0s'}}></span>
                    <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></span>
                    <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.4s'}}></span>
                 </div>
              ) : (
                <div className="text-sm prose prose-invert max-w-none">
                  <ReactMarkdown
                    remarkPlugins={[remarkMath]}
                    rehypePlugins={[rehypeKatex]}
                  >
                    {msg.text}
                  </ReactMarkdown>
                </div>
              )}
            </div>
          </div>
        ))}
         <div ref={messagesEndRef} />
      </div>
      <div className="p-4 border-t border-slate-700/50 flex items-center space-x-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Type your command here..."
          className="flex-1 bg-slate-700 border border-slate-600 rounded-md px-4 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
        <button
          onClick={handleSend}
          className="bg-indigo-600 text-white p-2 rounded-md hover:bg-indigo-500 transition-colors"
        >
          <SendIcon className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
};

export default Chatbot;
