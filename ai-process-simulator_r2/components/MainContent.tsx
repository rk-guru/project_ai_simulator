import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Project, ChatMessage, FlowsheetNode, FlowsheetEdge, SimulationResult, EquipmentType } from '../types';
import Chatbot from './Chatbot';
import FlowDiagram from './FlowDiagram';
import ResultTable from './ResultTable';
import SaveIcon from './icons/SaveIcon';
import PlayIcon from './icons/PlayIcon';
import UploadIcon from './icons/UploadIcon';
import { dbService } from '../services/db';

interface MainContentProps {
  project: Project;
  onUpdateProject: (id: string, data: Partial<Project>) => void;
}

type Tab = 'chat' | 'flow-diagram' | 'result-table';

const MainContent: React.FC<MainContentProps> = ({ project, onUpdateProject }) => {
  const [projectName, setProjectName] = useState(project.name);
  const [activeTab, setActiveTab] = useState<Tab>('chat');
  const [messages, setMessages] = useState<ChatMessage[]>(project.messages || []);
  const [nodes, setNodes] = useState<FlowsheetNode[]>(project.nodes || []);
  const [edges, setEdges] = useState<FlowsheetEdge[]>(project.edges || []);
  const [results, setResults] = useState<SimulationResult[]>(project.results || []);
  const [isUploading, setIsUploading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const processedMessageIds = useRef<Set<string>>(new Set((project.messages || []).map(m => m.id)));

  // Sync local state when project changes
  useEffect(() => {
    setProjectName(project.name);
    setMessages(project.messages || []);
    setNodes(project.nodes || []);
    setEdges(project.edges || []);
    setResults(project.results || []);
    
    const currentIds = new Set((project.messages || []).map(m => m.id));
    currentIds.forEach(id => processedMessageIds.current.add(id));
  }, [project]);

  // Automatic Flowsheet Generation from JSON in Chat
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
      const codeBlockMatch = text.match(/``````/) || text.match(/``````/);
      
      if (codeBlockMatch) {
        jsonString = codeBlockMatch[1];
      } else {
        const firstOpen = text.indexOf('{');
        const lastClose = text.lastIndexOf('}');
        if (firstOpen !== -1 && lastClose !== -1 && lastClose > firstOpen) {
          jsonString = text.substring(firstOpen, lastClose + 1);
        }
      }

      const data = JSON.parse(jsonString);
      if (data.Equipment_list && data.Connection) {
        console.log("Detected valid simulation JSON, generating flowsheet...", data);
        generateFlowsheetFromData(data);
      }
    } catch (e) {
      console.debug("Failed to parse simulation JSON from message:", e);
    }
  };

  const generateFlowsheetFromData = (data: any) => {
    const equipmentList = data.Equipment_list as Record<string, string>;
    const connections = data.Connection as any[];
    const newNodes: FlowsheetNode[] = [];
    const newEdges: FlowsheetEdge[] = [];

    // Create Nodes
    Object.entries(equipmentList).forEach(([name, typeStr]) => {
      const type = findEquipmentType(typeStr);
      const connectionData = connections.find(c => c.equipment === name);
      const params = connectionData?.Param || {};
      const properties: Record<string, any> = {};
      
      Object.entries(params).forEach(([key, value]) => {
        properties[mapParamKey(key)] = value;
      });

      newNodes.push({
        id: name,
        type: type,
        name: name,
        x: 0,
        y: 0,
        properties
      });
    });

    // Create Edges
    connections.forEach((conn) => {
      const fromId = conn.equipment;
      const outlets = Array.isArray(conn.outlet) ? conn.outlet : (conn.outlet ? [conn.outlet] : []);
      
      outlets.forEach((toId: string) => {
        if (newNodes.find(n => n.id === fromId) && newNodes.find(n => n.id === toId)) {
          newEdges.push({
            id: `edge-${fromId}-${toId}`,
            from: fromId,
            to: toId
          });
        }
      });
    });

    // Auto Layout
    const layoutedNodes = autoLayoutNodes(newNodes, newEdges);
    
    setNodes(layoutedNodes);
    setEdges(newEdges);
    setActiveTab('flow-diagram');
    
    setMessages(prev => {
      const lastMsg = prev[prev.length - 1];
      if (lastMsg && lastMsg.text === 'Flowsheet generated successfully.') return prev;
      return [...prev, {
        id: 'sys-' + Date.now(),
        sender: 'ai',
        text: 'Flowsheet generated successfully.'
      }];
    });
  };

  const autoLayoutNodes = (nodes: FlowsheetNode[], edges: FlowsheetEdge[]): FlowsheetNode[] => {
    const incomingEdgeCounts: Record<string, number> = {};
    nodes.forEach(n => incomingEdgeCounts[n.id] = 0);
    edges.forEach(e => {
      if (incomingEdgeCounts[e.to] !== undefined) incomingEdgeCounts[e.to]++;
    });

    const levels: Record<string, number> = {};
    const queue: {id: string, level: number}[] = [];

    nodes.forEach(n => {
      if (incomingEdgeCounts[n.id] === 0) {
        queue.push({ id: n.id, level: 0 });
        levels[n.id] = 0;
      }
    });

    if (queue.length === 0 && nodes.length > 0) {
      queue.push({ id: nodes[0].id, level: 0 });
      levels[nodes[0].id] = 0;
    }

    const visited = new Set<string>();
    while (queue.length > 0) {
      const { id, level } = queue.shift()!;
      if (visited.has(id)) continue;
      visited.add(id);
      levels[id] = level;

      const outgoing = edges.filter(e => e.from === id).map(e => e.to);
      outgoing.forEach(toId => {
        if (!levels[toId] || levels[toId] < level + 1) {
          queue.push({ id: toId, level: level + 1 });
        }
      });
    }

    nodes.forEach(n => {
      if (levels[n.id] === undefined) levels[n.id] = 0;
    });

    const nodesPerLevel: Record<number, number> = {};
    const X_SPACING = 200;
    const Y_SPACING = 150;

    return nodes.map(node => {
      const level = levels[node.id];
      const indexInLevel = nodesPerLevel[level] || 0;
      nodesPerLevel[level] = indexInLevel + 1;

      return {
        ...node,
        x: 50 + level * X_SPACING,
        y: 50 + indexInLevel * Y_SPACING
      };
    });
  };

  const findEquipmentType = (typeStr: string): EquipmentType => {
    if (Object.values(EquipmentType).includes(typeStr as EquipmentType)) {
      return typeStr as EquipmentType;
    }
    
    const normalized = typeStr.replace(/\s+/g, '').toLowerCase();
    const match = Object.values(EquipmentType).find(t => t.toLowerCase() === normalized);
    return match || EquipmentType.Tank;
  };

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

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await dbService.updateProject(project.id, {
        name: projectName,
        nodes,
        edges,
        messages,
        results
      });
      
      onUpdateProject(project.id, {
        name: projectName,
        nodes,
        edges,
        messages,
        results
      });
      
      alert('Project saved successfully!');
    } catch (error) {
      console.error('Error saving project:', error);
      alert('Failed to save project');
    } finally {
      setIsSaving(false);
    }
  };

  const handleRunSimulation = async () => {
    setIsRunning(true);
    try {
      const response = await dbService.runSimulation(project.id, nodes, edges);
      setResults(response.results);
      onUpdateProject(project.id, { results: response.results });
      setActiveTab('result-table');
      alert('Simulation completed successfully!');
    } catch (error) {
      console.error('Error running simulation:', error);
      alert('Failed to run simulation');
    } finally {
      setIsRunning(false);
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    try {
      await dbService.uploadFile(project.id, file);
      alert(`File "${file.name}" uploaded successfully!`);
    } catch (error) {
      console.error('Error uploading file:', error);
      alert('Failed to upload file');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const renderTabContent = () => {
    switch (activeTab) {
      case 'chat':
        return (
          <Chatbot
            messages={messages}
            onMessagesChange={setMessages}
            projectId={project.id}
          />
        );
      case 'flow-diagram':
        return (
          <FlowDiagram
            nodes={nodes}
            edges={edges}
            onNodesChange={setNodes}
            onEdgesChange={setEdges}
          />
        );
      case 'result-table':
        return <ResultTable data={results} />;
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
    <div className="flex-1 flex flex-col h-screen bg-slate-900">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 bg-slate-800 border-b border-slate-700">
        <div className="flex items-center gap-3">
          <label className="text-sm font-medium text-gray-400">Project Name</label>
          <input
            type="text"
            value={projectName}
            onChange={(e) => setProjectName(e.target.value)}
            className="text-lg font-semibold bg-transparent border-none text-white focus:ring-0 -ml-1"
          />
        </div>
        
        <div className="flex items-center gap-3">
          <input
            ref={fileInputRef}
            type="file"
            onChange={handleFileUpload}
            className="hidden"
            id="file-upload"
          />
          <label
            htmlFor="file-upload"
            className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-md cursor-pointer transition-colors"
          >
            <UploadIcon />
            {isUploading ? 'Uploading...' : 'Upload'}
          </label>
          
          <button
            onClick={handleRunSimulation}
            disabled={isRunning || nodes.length === 0}
            className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-md transition-colors"
          >
            <PlayIcon />
            {isRunning ? 'Running...' : 'Run'}
          </button>
          
          <button
            onClick={handleSave}
            disabled={isSaving}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-md transition-colors"
          >
            <SaveIcon />
            {isSaving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>

      {/* Content Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Tabs */}
        <div className="flex gap-2 px-6 pt-4 bg-slate-900">
          <TabButton tab="chat" label="Chat" />
          <TabButton tab="flow-diagram" label="Flow Diagram" />
          <TabButton tab="result-table" label="Results" />
        </div>

        {/* Tab Panel */}
        <div className="flex-1 overflow-hidden">
          {renderTabContent()}
        </div>
      </div>
    </div>
  );
};

export default MainContent;
