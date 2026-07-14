
import React, { useState, useRef, useEffect } from 'react';
import { ChatMessage } from '../types';
import { generateChatResponse } from '../services/geminiService';
import SendIcon from './icons/SendIcon';
import UploadIcon from './icons/UploadIcon';

interface ChatbotProps {
    messages: ChatMessage[];
    setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>;
}

const Chatbot: React.FC<ChatbotProps> = ({ messages, setMessages }) => {
  const [input, setInput] = useState('');
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
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

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      console.log('Selected file:', file.name);
      setUploadedFile(file);
      // Here you would handle the file upload to the backend
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

    // You can pass the uploaded file context to the AI
    const promptWithContext = uploadedFile 
        ? `Using the context from the document "${uploadedFile.name}", please answer the following: ${input}`
        : input;

    const aiResponseText = await generateChatResponse(promptWithContext);

    const aiMessage: ChatMessage = {
      id: (Date.now() + 1).toString(),
      sender: 'ai',
      text: aiResponseText,
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
                className="flex items-center px-3 py-1.5 text-xs font-semibold text-white bg-slate-700 rounded-md hover:bg-slate-600 transition-colors"
            >
                <UploadIcon className="w-4 h-4 mr-2" />
                {uploadedFile ? uploadedFile.name : 'Upload PDF'}
            </button>
            <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileChange}
                accept=".pdf"
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
                <p className="text-sm whitespace-pre-wrap">{msg.text}</p>
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