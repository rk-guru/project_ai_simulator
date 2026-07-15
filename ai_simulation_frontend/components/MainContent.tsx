
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Project, ChatMessage, FlowsheetNode, FlowsheetEdge, EquipmentType } from '../types';
import Chatbot from './Chatbot';
import FlowDiagram from './FlowDiagram';
import ResultTable from './ResultTable';
import SaveIcon from './icons/SaveIcon';
import Modal from './Modal';
import { dbService } from '../services/db';

interface MainContentProps {
  project: Project;
  onUpdateProject: (id: string, data: Partial<Project>) => void;
}

type Tab = 'chat' | 'flow-diagram' | 'result-table';

// Helper to map JSON parameter keys
const mapParamKey = (key: string): string => {
    const map: Record<string, string> = {
        'Temperature': 'temperature',
        'Pressure': 'pressure',
        'Outlet Temperature': 'outletTemperature',
        'Outlet Pressure': 'outletPressure',
        'Stages': 'stages',
        'Condenser Type': 'condenserType',
        'Reflux Ratio': 'refluxRatio'
    };
    if (map[key]) return map[key];
    return key.replace(/(?:^\w|[A-Z]|\b\w)/g, (word, index) => 
        index === 0 ? word.toLowerCase() : word.toUpperCase()
    ).replace(/\s+/g, '');
};

const MainContent: React.FC<MainContentProps> = ({ project, onUpdateProject }) => {
  const [projectName, setProjectName] = useState(project.name);
  const [activeTab, setActiveTab] = useState<Tab>('chat');
  
  const [messages, setMessages] = useState<ChatMessage[]>(project.messages || []);
  const [nodes, setNodes] = useState<FlowsheetNode[]>(project.nodes || []);
  const [edges, setEdges] = useState<FlowsheetEdge[]>(project.edges || []);
  const [results, setResults] = useState<any[]>(project.results || []);
  const [isSaveModalOpen, setIsSaveModalOpen] = useState(false);

  const processedMessageIds = useRef<Set<string>>(new Set((project.messages || []).map(m => m.id)));

  useEffect(() => {
    setProjectName(project.name);
    setMessages(project.messages || []);
    setNodes(project.nodes || []);
    setEdges(project.edges || []);
    setResults(project.results || []);
    const currentIds = new Set((project.messages || []).map(m => m.id));
    currentIds.forEach(id => processedMessageIds.current.add(id));
  }, [project]);

  // Automatic Flowsheet Parsing
  useEffect(() => {
    if (messages.length === 0) return;
    const startIndex = Math.max(0, messages.length - 3);
    const recentMessages = messages.slice(startIndex);

    recentMessages.forEach(msg => {
        if (processedMessageIds.current.has(msg.id)) return;
        if (msg.isTyping || !msg.text) return;

        if (msg.text.includes('Equipment_list') && msg.text.includes('Connection')) {
            processedMessageIds.current.add(msg.id);
            attemptParseAndGenerate(msg.text);
        }
    });
  }, [messages]);

  const attemptParseAndGenerate = (text: string) => {
      try {
        let jsonString = text;
        const codeBlockMatch = text.match(/```json\s*([\s\S]*?)\s*```/) || text.match(/```\s*([\s\S]*?)\s*```/);
        if (codeBlockMatch) jsonString = codeBlockMatch[1];
        else {
            const firstOpen = text.indexOf('{');
            const lastClose = text.lastIndexOf('}');
            if (firstOpen !== -1 && lastClose !== -1 && lastClose > firstOpen) {
                jsonString = text.substring(firstOpen, lastClose + 1);
            }
        }
        const data = JSON.parse(jsonString);
        if (data.Equipment_list && data.Connection) {
            generateFlowsheetFromData(data);
        }
      } catch (e) {
          console.debug("Failed to parse JSON", e);
      }
  };

  const generateFlowsheetFromData = (data: any) => {
    const equipmentList = data.Equipment_list as Record<string, string>;
    const connections = data.Connection as any[];

    const newNodes: FlowsheetNode[] = [];
    const newEdges: FlowsheetEdge[] = [];

    const findEquipmentType = (typeStr: string): EquipmentType => {
        if (Object.values(EquipmentType).includes(typeStr as EquipmentType)) {
            return typeStr as EquipmentType;
        }
        const normalized = typeStr.replace(/\s+/g, '').toLowerCase();
        const match = Object.values(EquipmentType).find(t => t.toLowerCase() === normalized);
        return match || EquipmentType.Tank;
    };

    // Create Nodes
    Object.entries(equipmentList).forEach(([name, typeStr]) => {
        const type = findEquipmentType(typeStr);
        const connectionData = connections.find(c => c.equipment === name);
        const params = connectionData?.Param || {};
        
        const properties: Record<string, any> = {};
        Object.entries(params).forEach(([key, value]) => {
            properties[mapParamKey(key)] = value;
        });

        newNodes.push({ id: name, type, name, x: 0, y: 0, properties });
    });

    // Create Edges
    connections.forEach((conn) => {
        const fromId = conn.equipment;
        const outlets = Array.isArray(conn.outlet) ? conn.outlet : (conn.outlet ? [conn.outlet] : []);
        outlets.forEach((toId: string) => {
            if (newNodes.find(n => n.id === fromId) && newNodes.find(n => n.id === toId)) {
                newEdges.push({ id: `edge-${fromId}-${toId}`, from: fromId, to: toId });
            }
        });
    });

    // Auto Layout
    const incomingEdgeCounts: Record<string, number> = {};
    newNodes.forEach(n => incomingEdgeCounts[n.id] = 0);
    newEdges.forEach(e => { if (incomingEdgeCounts[e.to] !== undefined) incomingEdgeCounts[e.to]++; });

    const levels: Record<string, number> = {};
    const queue: {id: string, level: number}[] = [];
    
    newNodes.forEach(n => {
        if (incomingEdgeCounts[n.id] === 0) {
            queue.push({ id: n.id, level: 0 });
            levels[n.id] = 0;
        }
    });

    if (queue.length === 0 && newNodes.length > 0) {
        queue.push({ id: newNodes[0].id, level: 0 });
        levels[newNodes[0].id] = 0;
    }

    const visited = new Set<string>();
    while (queue.length > 0) {
        const { id, level } = queue.shift()!;
        if (visited.has(id)) continue;
        visited.add(id);
        levels[id] = level;

        const outgoing = newEdges.filter(e => e.from === id).map(e => e.to);
        outgoing.forEach(toId => {
            if (!levels[toId] || levels[toId] < level + 1) {
                 queue.push({ id: toId, level: level + 1 });
            }
        });
    }

    newNodes.forEach(n => { if (levels[n.id] === undefined) levels[n.id] = 0; });
    const nodesPerLevel: Record<number, number> = {};
    
    const layoutedNodes = newNodes.map(node => {
        const level = levels[node.id];
        const indexInLevel = nodesPerLevel[level] || 0;
        nodesPerLevel[level] = indexInLevel + 1;
        return { ...node, x: 50 + level * 200, y: 50 + indexInLevel * 150 };
    });

    setNodes(layoutedNodes);
    setEdges(newEdges);
    setActiveTab('flow-diagram');
    setMessages(prev => {
        if (prev[prev.length - 1]?.text === 'Flowsheet generated successfully.') return prev;
        return [...prev, { id: 'sys-' + Date.now(), sender: 'ai', text: 'Flowsheet generated successfully.' }];
    });
  };

  const handleSave = () => {
    setIsSaveModalOpen(true);
  };

  const confirmSave = () => {
    onUpdateProject(project.id, {
        name: projectName,
        messages,
        nodes,
        edges,
        results
    });
    setIsSaveModalOpen(false);
  };

  const handleRunSimulation = async () => {
      // Prepare project object for the backend run
      const currentProjectState: Project = {
          ...project,
          nodes,
          edges,
          properties: {} // Add other needed fields if any
      } as any;

      // Call backend to run simulation
      // This will return the "Dataframe" (array of objects)
      const simulationResults = await dbService.runSimulation(project.id, currentProjectState);
      
      setResults(simulationResults);
      // Save results to project state
      onUpdateProject(project.id, { results: simulationResults });
      setActiveTab('result-table');
  };

  const renderTabContent = () => {
    switch (activeTab) {
      case 'chat':
        return <Chatbot projectId={project.id} messages={messages} setMessages={setMessages} />;
      case 'flow-diagram':
        return <FlowDiagram nodes={nodes} setNodes={setNodes} edges={edges} setEdges={setEdges} onRun={handleRunSimulation} />;
      case 'result-table':
        return <ResultTable data={results} />;
      default: return null;
    }
  };

  return (
    <div className="flex-1 flex flex-col bg-slate-900">
      <div className="flex-shrink-0 p-6 border-b border-slate-700/50">
        <div className="flex justify-between items-center">
          <div className="flex flex-col">
            <label className="text-xs text-gray-400 mb-1">Project Name</label>
            <input
              type="text"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              className="text-lg font-semibold bg-transparent border-none text-white focus:ring-0 -ml-1"
            />
          </div>
          <button onClick={handleSave} className="flex items-center px-3 py-1.5 text-xs font-semibold text-white bg-indigo-600 rounded-md hover:bg-indigo-500">
            <SaveIcon className="w-4 h-4 mr-2" />
            Save
          </button>
        </div>
      </div>
      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="flex-shrink-0 px-6 border-b border-slate-700/50">
          <nav className="flex space-x-2">
            {['chat', 'flow-diagram', 'result-table'].map((t) => (
                <button
                    key={t}
                    onClick={() => setActiveTab(t as Tab)}
                    className={`px-4 py-2 text-sm font-medium rounded-t-md transition-colors ${
                        activeTab === t ? 'bg-slate-800 text-white border-b-2 border-indigo-500' : 'text-gray-400 hover:bg-slate-700/50'
                    }`}
                >
                    {t.replace('-', ' ').replace(/\b\w/g, c => c.toUpperCase())}
                </button>
            ))}
          </nav>
        </div>
        <div className="flex-1 overflow-y-auto p-6">
          {renderTabContent()}
        </div>
        {isSaveModalOpen && (
          <Modal
            title="Save Project"
            confirmLabel="Save"
            onConfirm={confirmSave}
            onClose={() => setIsSaveModalOpen(false)}
          >
            <p className="text-sm text-gray-300">
              Are you sure you want to save the current changes to "{projectName}"?
            </p>
          </Modal>
        )}
      </div>
    </div>
  );
};

export default MainContent;
