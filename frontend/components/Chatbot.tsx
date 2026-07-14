import React, { useState, useRef, useEffect } from 'react';
import { ChatMessage } from '../types';
import SendIcon from './icons/SendIcon';

interface ChatbotProps {
  messages: ChatMessage[];
  onSendMessage: (message: string) => void;
  isLoading?: boolean;
}

const Chatbot: React.FC<ChatbotProps> = ({ messages, onSendMessage, isLoading = false }) => {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !isLoading) {
      onSendMessage(input.trim());
      setInput('');
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-900">
      {/* AI Assistant Header */}
      <div className="p-4 border-b border-slate-700">
        <h2 className="text-lg font-semibold text-white">AI Assistant</h2>
      </div>

      {/* Messages Display Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[70%] px-4 py-2 rounded-lg ${
                msg.sender === 'user'
                  ? 'bg-indigo-600 text-white'
                  : 'bg-slate-800 text-gray-200'
              }`}
            >
              {msg.isTyping ? (
                <div className="flex space-x-2">
                  <div 
                    className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" 
                    style={{ animationDelay: '0ms' }} 
                  />
                  <div 
                    className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" 
                    style={{ animationDelay: '150ms' }} 
                  />
                  <div 
                    className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" 
                    style={{ animationDelay: '300ms' }} 
                  />
                </div>
              ) : (
                <pre className="whitespace-pre-wrap font-sans text-sm">
                  {msg.text}
                </pre>
              )}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Form */}
      <form onSubmit={handleSubmit} className="p-4 border-t border-slate-700 bg-slate-900">
        <div className="flex space-x-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your command here..."
            disabled={isLoading}
            className="flex-1 px-4 py-2 bg-slate-700 border border-slate-600 text-white rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-sm"
          />
          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="flex items-center space-x-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-md transition-colors"
          >
            <SendIcon />
            <span>Send</span>
          </button>
        </div>
        {isLoading && (
          <div className="mt-2 text-xs text-gray-400 text-center">
            Waiting for response...
          </div>
        )}
      </form>
    </div>
  );
};

export default Chatbot;
