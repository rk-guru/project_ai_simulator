import React, { useState, useEffect } from 'react';
import Modal from './Modal';

interface SettingsProps {
  onBack: () => void;
}

const Settings: React.FC<SettingsProps> = ({ onBack }) => {
  const [showSaved, setShowSaved] = useState(false);
  const [modelName, setModelName] = useState('');
  const [apiKey, setApiKey] = useState('');

  useEffect(() => {
    const savedName = localStorage.getItem('modelName') ?? '';
    const savedKey = localStorage.getItem('apiKey') ?? '';
    setModelName(savedName);
    setApiKey(savedKey);
  }, []);

  const handleSave = () => {
    localStorage.setItem('modelName', modelName);
    localStorage.setItem('apiKey', apiKey);
    setShowSaved(true);
  };

  return (
    <div className="flex-1 flex flex-col bg-slate-900 p-6 text-gray-200">
      <div className="flex items-center mb-6">
        <button
          onClick={onBack}
          className="px-3 py-1 text-sm font-medium text-white bg-indigo-600 rounded-md hover:bg-indigo-500"
        >
          Back
        </button>
        <h1 className="ml-4 text-xl font-semibold">Settings</h1>
      </div>
      <div className="space-y-4 max-w-md">
        <div className="flex flex-col">
          <label className="block text-sm font-medium text-gray-400 mb-1">Model Name</label>
          <div className="flex space-x-2">
            <input
              type="text"
              value={modelName}
              onChange={e => setModelName(e.target.value)}
              className="flex-1 px-3 py-2 bg-slate-800 border border-slate-600 rounded-md text-white focus:outline-none"
              placeholder="e.g., gemini-2.5-flash"
            />
            <button
              onClick={handleSave}
              className="px-4 py-2 text-sm font-semibold text-white bg-indigo-600 rounded-md hover:bg-indigo-500 transition-colors"
            >
              Save
            </button>
          </div>
        </div>
        <div className="flex flex-col">
          <label className="block text-sm font-medium text-gray-400 mb-1">Model API Key</label>
          <div className="flex space-x-2">
            <input
              type="password"
              value={apiKey}
              onChange={e => setApiKey(e.target.value)}
              className="flex-1 px-3 py-2 bg-slate-800 border border-slate-600 rounded-md text-white focus:outline-none"
              placeholder="Enter API key"
            />
            <button
              onClick={handleSave}
              className="px-4 py-2 text-sm font-semibold text-white bg-indigo-600 rounded-md hover:bg-indigo-500 transition-colors"
            >
              Save
            </button>
          </div>
        </div>
        {showSaved && (
          <Modal title="Success" onClose={() => setShowSaved(false)}>
            Settings saved.
          </Modal>
        )}
      </div>
    </div>
  );
};

export default Settings;
