import React, { useState, useEffect, useRef } from 'react';
import { Project, ChatMessage, FlowsheetNode, FlowsheetEdge, SimulationResult, EquipmentType } from '../types';
import Chatbot from './Chatbot';
import FlowDiagram from './FlowDiagram';
import ResultTable from './ResultTable';
import SaveIcon from './icons/SaveIcon';
import PlayIcon from './icons/PlayIcon';
import UploadIcon from './icons/UploadIcon';
import { sendChatMessage, generateFlowDiagram, runSimulation, uploadPDF } from '../services/api';

interface MainContentProps {
  project: Project;
  onUpdateProject: (id: string, data: Partial<Project>) => void;
}

type Tab = 'chat' | 'flow-diagram' | 'result-table';

const DEFAULT_MOCK_RESULTS: SimulationResult[] = [
  { id: 1, parameter: 'Reactor Temperature', value: '350 K', status: 'Nominal' },
  { id: 2, parameter: 'Column Pressure', value: '1.2 atm', status: 'Warning' },
  { id: 3, parameter: 'Tank Level', value: '85%', status: 'Nominal' },
  { id: 4, parameter: 'Pump Flow Rate', value: '150 L/min', status: 'Nominal' },
  { id: 5, parameter: 'Product Purity', value: '99.5%', status: 'Excellent' },
  { id: 6, parameter: 'Energy Consumption', value: '5.2 kWh', status: 'High' },
];

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
  const [results, setResults] = useState<SimulationResult[]>(project.results || DEFAULT_MOCK_RESULTS);
  const [isLoading, setIsLoading] = useState(false);
  const [isSimulating, setIsSimulating] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const processedMessageIds = useRef<Set<string>>(new Set(project.messages?.map(m => m.id) || []));

  useEffect(() => {
    setProjectName(project.name);
    setMessages(project.messages || []);
    setNodes(project.nodes || []);
    setEdges(project.edges || []);
    setResults(project.results || DEFAULT_MOCK_RESULTS);
  }, [project]);

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

  const generateFlowsheetFromData = async (data: any) => {
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

    const incomingEdgeCounts: Record<string, number> = {};
    newNodes.forEach(n => incomingEdgeCounts[n.id] = 0);
    newEdges.forEach(e => {
      if (incomingEdgeCounts[e.to] !== undefined) incomingEdgeCounts[e.to]++;
    });

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

    newNodes.forEach(n => {
      if (levels[n.id] === undefined) levels[n.id] = 0;
    });

    const nodesPerLevel: Record<number, number> = {};
    const X_SPACING = 200;
    const Y_SPACING = 150;
    
    const layoutedNodes = newNodes.map(node => {
      const level = levels[node.id];
      const indexInLevel = nodesPerLevel[level] || 0;
      nodesPerLevel[level] = indexInLevel + 1;
      
      return {
        ...node,
        x: 50 + level * X_SPACING,
        y: 50 + indexInLevel * Y_SPACING
      };
    });

    setNodes(layoutedNodes);
    setEdges(newEdges);
    setActiveTab('flow-diagram');

    try {
      await generateFlowDiagram(layoutedNodes, newEdges);
      setMessages(prev => {
        const lastMsg = prev[prev.length - 1];
        if (lastMsg && lastMsg.text === 'Flowsheet generated successfully.') return prev;
        return [...prev, {
          id: 'sys-' + Date.now(),
          sender: 'ai',
          text: 'Flowsheet generated successfully.'
        }];
      });
    } catch (error: any) {
      console.error('Failed to generate diagram:', error);
    }
  };

  const handleSendMessage = async (messageText: string) => {
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: messageText
    };
    setMessages(prev => [...prev, userMessage]);

    const typingMessage: ChatMessage = {
      id: `typing-${Date.now()}`,
      sender: 'ai',
      text: '',
      isTyping: true
    };
    setMessages(prev => [...prev, typingMessage]);

    try {
      setIsLoading(true);
      const response = await sendChatMessage(messageText, project.id); // ADDED project.id
      setMessages(prev => {
        const withoutTyping = prev.filter(m => !m.isTyping);
        return [...withoutTyping, {
          id: `ai-${Date.now()}`,
          sender: 'ai',
          text: response.message
        }];
      });
    } catch (error: any) {
      console.error('Failed to send message', error);
      setMessages(prev => {
        const withoutTyping = prev.filter(m => !m.isTyping);
        return [...withoutTyping, {
          id: `error-${Date.now()}`,
          sender: 'ai',
          text: `Error: ${error.message}. Please try again.`
        }];
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    const file = files[0];
    
    if (file.type !== 'application/pdf') {
      alert('Please upload a PDF file only.');
      return;
    }

    const maxSize = 10 * 1024 * 1024;
    if (file.size > maxSize) {
      alert('File size exceeds 10MB limit.');
      return;
    }

    try {
      setIsUploading(true);
      const response = await uploadPDF(file, project.id);
      
      setMessages(prev => [...prev, {
        id: `upload-success-${Date.now()}`,
        sender: 'ai',
        text: `✓ PDF uploaded successfully: ${response.filename}`
      }]);
      
      alert(`PDF uploaded successfully: ${response.filename}`);
      
    } catch (error: any) {
      console.error('Upload failed:', error);
      alert(`Upload failed: ${error.message}`);
      
      setMessages(prev => [...prev, {
        id: `upload-error-${Date.now()}`,
        sender: 'ai',
        text: `✗ Upload failed: ${error.message}`
      }]);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const formatPropertyKey = (key: string): string => {
    const result = key.replace(/([A-Z])/g, " $1");
    return result.charAt(0).toUpperCase() + result.slice(1);
  };

  const generateSimulationJson = () => {
    const equipmentList: Record<string, string> = {};
    const connections: any[] = [];

    nodes.forEach(node => {
      equipmentList[node.name] = node.type;

      const nodeEdges = edges.filter(edge => edge.from === node.id);
      const outlets = nodeEdges.map(edge => {
        const targetNode = nodes.find(n => n.id === edge.to);
        return targetNode ? targetNode.id : null;
      }).filter(Boolean);

      const formattedParams: Record<string, any> = {};
      if (node.properties) {
        Object.entries(node.properties).forEach(([key, value]) => {
          formattedParams[formatPropertyKey(key)] = (value === undefined || value === null || value === '') ? 0 : value;
        });
      }

      connections.push({
        equipment: node.name,
        outlet: outlets,
        Param: formattedParams
      });
    });

    return {
      Equipment_list: equipmentList,
      Connection: connections
    };
  };

  const handleRunSimulation = async () => {
    if (nodes.length === 0) {
      alert('Please create a flowsheet before running simulation.');
      return;
    }

    const simulationData = generateSimulationJson();
    console.log('Running simulation with data:', JSON.stringify(simulationData, null, 2));

    try {
      setIsSimulating(true);
      const response = await runSimulation(simulationData);
      
      const newResults: SimulationResult[] = response.results.map((result: any, index: number) => ({
        id: index + 1,
        parameter: result.parameter || result.name,
        value: result.value,
        status: result.status || 'Calculated'
      }));
      
      setResults(newResults);
      setActiveTab('result-table');
      
      setMessages(prev => [...prev, {
        id: `sim-success-${Date.now()}`,
        sender: 'ai',
        text: `Simulation completed successfully. ${response.message || 'Check the results table for details.'}`
      }]);
    } catch (error: any) {
      console.error('Simulation failed:', error);
      alert(`Simulation failed: ${error.message}`);
      
      setMessages(prev => [...prev, {
        id: `sim-error-${Date.now()}`,
        sender: 'ai',
        text: `Simulation error: ${error.message}`
      }]);
    } finally {
      setIsSimulating(false);
    }
  };

  const handleSave = () => {
    const simulationData = generateSimulationJson();
    console.log("Saving Simulation Data (JSON Structure):", JSON.stringify(simulationData, null, 2));

    onUpdateProject(project.id, {
      name: projectName,
      messages,
      nodes,
      edges,
      results
    });
  };

  const renderTabContent = () => {
    switch (activeTab) {
      case 'chat':
        return <Chatbot messages={messages} onSendMessage={handleSendMessage} isLoading={isLoading} />;
      case 'flow-diagram':
        return <FlowDiagram nodes={nodes} edges={edges} setNodes={setNodes} setEdges={setEdges} />;
      case 'result-table':
        return <ResultTable results={results} />;
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
    <div className="flex-1 flex flex-col h-full bg-slate-900 text-white">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-slate-700">
        <div className="flex items-center space-x-2">
          <label className="text-sm text-gray-400">Project Name</label>
          <input
            type="text"
            value={projectName}
            onChange={(e) => setProjectName(e.target.value)}
            className="text-lg font-semibold bg-transparent border-none text-white focus:ring-0 -ml-1"
          />
        </div>
        
        {/* Action Buttons - Conditional Based on Active Tab */}
        <div className="flex space-x-2">
          {/* Hidden File Input */}
          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf"
            onChange={handleFileUpload}
            className="hidden"
          />
          
          {/* Upload PDF Button - Only on Chat Tab */}
          {activeTab === 'chat' && (
            <button
              onClick={handleUploadClick}
              disabled={isUploading}
              className="flex items-center space-x-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 rounded-md transition-colors disabled:opacity-50"
            >
              <UploadIcon />
              <span>{isUploading ? 'Uploading...' : 'Upload PDF'}</span>
            </button>
          )}
          
          {/* Run Button - Only on Flow Diagram Tab */}
          {activeTab === 'flow-diagram' && (
            <button
              onClick={handleRunSimulation}
              disabled={isSimulating || nodes.length === 0}
              className="flex items-center space-x-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 rounded-md transition-colors disabled:opacity-50"
            >
              <PlayIcon />
              <span>{isSimulating ? 'Running...' : 'Run'}</span>
            </button>
          )}
          
          {/* Save Button - Always Visible */}
          <button
            onClick={handleSave}
            className="flex items-center space-x-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 rounded-md transition-colors"
          >
            <SaveIcon />
            <span>Save</span>
          </button>
        </div>
      </div>

      {/* Content Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Tabs */}
        <div className="flex space-x-1 px-4 pt-2 bg-slate-900 border-b border-slate-700">
          <TabButton tab="chat" label="Chat" />
          <TabButton tab="flow-diagram" label="Flow Diagram" />
          <TabButton tab="result-table" label="Result Table" />
        </div>

        {/* Tab Panel */}
        <div className="flex-1 overflow-auto">
          {renderTabContent()}
        </div>
      </div>
    </div>
  );
};

export default MainContent;
