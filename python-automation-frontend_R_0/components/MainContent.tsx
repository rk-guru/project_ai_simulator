import React, { useState } from 'react';
import { type Project, type Step } from '../types';
import { StepsTable } from './StepsTable';
import { PlayIcon, SaveIcon } from './Icons';

interface MainContentProps {
  project: Project | null;
  onUpdateProject: (project: Project) => void;
  onSave: () => void;
  onRun: () => void;
  runResult: string;
}

export const MainContent: React.FC<MainContentProps> = ({
  project,
  onUpdateProject,
  onSave,
  onRun,
  runResult,
}) => {
  const [activeTab, setActiveTab] = useState('main');
  
  if (!project) {
    return (
      <main className="flex-1 flex items-center justify-center bg-gray-900">
        <div className="text-center">
          <h2 className="text-2xl font-semibold text-gray-400">No Project Selected</h2>
          <p className="mt-2 text-gray-500">Select a project from the sidebar or create a new one to begin.</p>
        </div>
      </main>
    );
  }

  const handleNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onUpdateProject({ ...project, name: e.target.value });
  };

  const handleUrlChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onUpdateProject({ ...project, url: e.target.value });
  };
  
  const handleStepsChange = (newSteps: Step[]) => {
    onUpdateProject({ ...project, steps: newSteps });
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Non-scrolling Header */}
      <div className="p-6">
        <div className="mb-6">
          <label htmlFor="project-name-input" className="block text-sm font-medium text-gray-400 mb-2">
            Project Name
          </label>
          <input
            type="text"
            id="project-name-input"
            value={project.name}
            onChange={handleNameChange}
            placeholder="My Awesome Project"
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-gray-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-shadow"
          />
        </div>

        <div>
          <label htmlFor="url-input" className="block text-sm font-medium text-gray-400 mb-2">
            Target URL
          </label>
          <input
            type="text"
            id="url-input"
            value={project.url}
            onChange={handleUrlChange}
            placeholder="https://example.com"
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-gray-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-shadow"
          />
        </div>
      </div>
      
      {/* Non-scrolling Tabs */}
      <div className="px-6">
        <div className="border-b border-gray-700">
          <nav className="-mb-px flex space-x-4" aria-label="Tabs">
            <button
              onClick={() => setActiveTab('main')}
              className={`${
                activeTab === 'main'
                  ? 'border-indigo-500 text-indigo-400'
                  : 'border-transparent text-gray-400 hover:text-gray-200 hover:border-gray-500'
              } whitespace-nowrap py-3 px-1 border-b-2 font-medium text-sm`}
            >
              Steps
            </button>
            <button
              onClick={() => setActiveTab('settings')}
              className={`${
                activeTab === 'settings'
                  ? 'border-indigo-500 text-indigo-400'
                  : 'border-transparent text-gray-400 hover:text-gray-200 hover:border-gray-500'
              } whitespace-nowrap py-3 px-1 border-b-2 font-medium text-sm`}
            >
              Settings (Placeholder)
            </button>
          </nav>
        </div>
      </div>

      {/* Scrolling Content Area */}
      <main className="flex-1 px-6 pt-4 pb-6 overflow-y-auto">
        {activeTab === 'main' && (
           <StepsTable steps={project.steps} onStepsChange={handleStepsChange} />
        )}
        {activeTab === 'settings' && (
          <div className="p-8 bg-gray-800 rounded-lg text-center text-gray-500">
            Project settings would appear here.
          </div>
        )}
      </main>
      
      {/* Non-scrolling Result Area */}
      <div className="p-6 pt-0">
        <label htmlFor="result-output" className="block text-sm font-medium text-gray-400 mb-2">
          Result
        </label>
        <textarea
          id="result-output"
          readOnly
          value={runResult}
          placeholder="Run results will appear here..."
          className="w-full h-32 bg-gray-900 border border-gray-700 rounded-lg px-4 py-2 text-gray-300 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-shadow resize-y"
        />
      </div>

      {/* Non-scrolling Footer */}
      <footer className="bg-gray-800/80 backdrop-blur-sm border-t border-gray-700 p-4">
        <div className="flex justify-end space-x-4">
          <button
            onClick={onSave}
            className="flex items-center bg-gray-600 hover:bg-gray-700 text-white font-bold py-2 px-4 rounded-lg transition-colors duration-200"
          >
            <SaveIcon className="h-5 w-5 mr-2" />
            Save
          </button>
          <button
            onClick={onRun}
            className="flex items-center bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-6 rounded-lg transition-colors duration-200"
          >
            <PlayIcon className="h-5 w-5 mr-2" />
            Run
          </button>
        </div>
      </footer>
    </div>
  );
};
