import React, { useState, useEffect } from 'react';
import { Project } from '../types';
import Chatbot from './Chatbot';
import FlowDiagram from './FlowDiagram';
import ResultTable from './ResultTable';
import PlayIcon from './icons/PlayIcon';
import { saveFlowDiagram, runSimulation } from '../services/api';

interface MainContentProps {
  project: Project;
}

type Tab = 'simulation' | 'flow-diagram' | 'result-table';

const MainContent: React.FC<MainContentProps> = ({ project }) => {
  const [projectName, setProjectName] = useState(project.name);
  const [activeTab, setActiveTab] = useState<Tab>('simulation');
  const [isSimulating, setIsSimulating] = useState(false);
  const [simulationId, setSimulationId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Auto-save functionality - saves whenever nodes or edges change
  useEffect(() => {
    const autoSave = async () => {
      if (project.nodes && project.nodes.length > 0) {
        try {
          const diagramData = {
            nodes: project.nodes,
            edges: project.edges || [],
          };
          await saveFlowDiagram(diagramData);
          console.log('Auto-saved diagram');
        } catch (error) {
          console.error('Auto-save failed:', error);
        }
      }
    };

    // Debounce auto-save to avoid too many requests
    const timeoutId = setTimeout(autoSave, 1000);
    return () => clearTimeout(timeoutId);
  }, [project.nodes, project.edges]);

  // Auto-save project name changes
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      console.log('Project name saved:', projectName);
      // Add your save logic here if needed
    }, 500);
    return () => clearTimeout(timeoutId);
  }, [projectName]);

  const handleRun = async () => {
    try {
      setIsSimulating(true);
      setErrorMessage(null);
      setSuccessMessage(null);

      const diagramData = {
        nodes: project.nodes || [],
        edges: project.edges || [],
      };

      if (diagramData.nodes.length === 0) {
        setErrorMessage('Cannot run simulation. Add equipment to the flow diagram first.');
        return;
      }

      if (diagramData.edges.length === 0) {
        setErrorMessage('Cannot run simulation. Connect equipment in the flow diagram first.');
        return;
      }

      const result = await runSimulation(diagramData);
      setSimulationId(result.simulation_id);
      setSuccessMessage('Simulation completed successfully!');
      
      console.log('Simulation completed:', result);
      
      setActiveTab('result-table');
      
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (error: any) {
      console.error('Error running simulation:', error);
      const errorDetail = error.response?.data?.detail || error.message;
      setErrorMessage(`Simulation failed: ${errorDetail}`);
    } finally {
      setIsSimulating(false);
    }
  };

  const renderTabContent = () => {
    switch (activeTab) {
      case 'simulation':
        return <Chatbot />;
      case 'flow-diagram':
        return <FlowDiagram />;
      case 'result-table':
        return <ResultTable simulationId={simulationId} />;
      default:
        return null;
    }
  };

  const TabButton = ({ tab, label }: { tab: Tab; label: string }) => (
    <button
      onClick={() => setActiveTab(tab)}
      className={`px-4 py-2 text-sm font-medium rounded-t-md transition-colors ${
        activeTab === tab
          ? 'bg-slate-800 text-white border-b-2 border-indigo-500'
          : 'text-gray-400 hover:bg-slate-700/50'
      }`}
    >
      {label}
    </button>
  );

  return (
    <div className="flex-1 flex flex-col bg-slate-900 relative">
      {/* Header */}
      <div className="border-b border-slate-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-400">Project Name</label>
            <input
              type="text"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              className="text-lg font-semibold bg-transparent border-none text-white focus:ring-0 -ml-1 focus:outline-none"
            />
          </div>
          
          {/* Status Messages */}
          {successMessage && (
            <div className="px-4 py-2 bg-green-500/20 text-green-300 rounded-md text-sm">
              {successMessage}
            </div>
          )}
          {errorMessage && (
            <div className="px-4 py-2 bg-red-500/20 text-red-300 rounded-md text-sm">
              {errorMessage}
            </div>
          )}
        </div>
      </div>

      {/* Content Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Tabs */}
        <div className="border-b border-slate-700 px-6">
          <div className="flex gap-2">
            <TabButton tab="simulation" label="Simulation" />
            <TabButton tab="flow-diagram" label="Flow Diagram" />
            <TabButton tab="result-table" label="Result Table" />
          </div>
        </div>

        {/* Tab Panel - Full height, content extends to bottom */}
        <div className="flex-1 overflow-auto">
          {renderTabContent()}
        </div>
      </div>

      {/* Footer - Fixed position, only visible on Flow Diagram tab, doesn't extend to sidebar */}
      {activeTab === 'flow-diagram' && (
        <div className="border-t border-slate-700 px-4 py-2 bg-slate-900/95 backdrop-blur-sm">
          <div className="flex gap-3 justify-end">
            <button
              onClick={handleRun}
              disabled={isSimulating}
              className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                isSimulating
                  ? 'bg-slate-700 text-gray-400 cursor-not-allowed'
                  : 'bg-green-600 text-white hover:bg-green-700'
              }`}
            >
              <PlayIcon />
              {isSimulating ? 'Running...' : 'Run'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default MainContent;
