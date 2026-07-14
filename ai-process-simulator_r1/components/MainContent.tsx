// // // src/components/MainContent.tsx
// // import React, { useState, useEffect, useCallback, useRef } from 'react';
// // import { Project, ChatMessage, FlowsheetNode, FlowsheetEdge, SimulationResult, EquipmentType } from '../types';
// // import Chatbot from './Chatbot';
// // import FlowDiagram from './FlowDiagram';
// // import ResultTable from './ResultTable';
// // import SaveIcon from './icons/SaveIcon';
// // // import UploadIcon from './icons/UploadIcon';
// // import { api } from '../services/api';

// // interface MainContentProps {
// //   project: Project;
// //   onUpdateProject: (id: string, data: Partial<Project>) => void;
// // }

// // type Tab = 'chat' | 'flow-diagram' | 'result-table';

// // const DEFAULT_MOCK_RESULTS: SimulationResult[] = [
// //   { id: 1, parameter: 'Reactor Temperature', value: '350 K', status: 'Nominal' },
// //   { id: 2, parameter: 'Column Pressure', value: '1.2 atm', status: 'Warning' },
// //   { id: 3, parameter: 'Tank Level', value: '85%', status: 'Nominal' },
// //   { id: 4, parameter: 'Pump Flow Rate', value: '150 L/min', status: 'Nominal' },
// //   { id: 5, parameter: 'Product Purity', value: '99.5%', status: 'Excellent' },
// //   { id: 6, parameter: 'Energy Consumption', value: '5.2 kWh', status: 'High' },
// // ];

// // const mapParamKey = (key: string): string => {
// //   const map: Record<string, string> = {
// //     'Temperature': 'temperature',
// //     'Pressure': 'pressure',
// //     'Outlet Temperature': 'outletTemperature',
// //     'Outlet Pressure': 'outletPressure',
// //     'Stages': 'stages',
// //     'Condenser Type': 'condenserType',
// //     'Reflux Ratio': 'refluxRatio'
// //   };
// //   if (map[key]) return map[key];
// //   return key.replace(/(?:^\w|[A-Z]|\b\w)/g, (word, index) =>
// //     index === 0 ? word.toLowerCase() : word.toUpperCase()
// //   ).replace(/\s+/g, '');
// // };

// // const MainContent: React.FC<MainContentProps> = ({ project, onUpdateProject }) => {
// //   const [projectName, setProjectName] = useState(project.name);
// //   const [activeTab, setActiveTab] = useState<Tab>('chat');
// //   const [messages, setMessages] = useState<ChatMessage[]>(project.messages || []);
// //   const [nodes, setNodes] = useState<FlowsheetNode[]>(project.nodes || []);
// //   const [edges, setEdges] = useState<FlowsheetEdge[]>(project.edges || []);
// //   const [results, setResults] = useState<SimulationResult[]>(project.results || DEFAULT_MOCK_RESULTS);
// //   const [isSaving, setIsSaving] = useState(false);
// //   // const [isUploading, setIsUploading] = useState(false);
// //   // const fileInputRef = useRef<HTMLInputElement>(null);

// //   const processedMessageIds = useRef<Set<string>>(new Set(project.messages?.map(m => m.id) || []));

// //   useEffect(() => {
// //     setProjectName(project.name);
// //     setMessages(project.messages || []);
// //     setNodes(project.nodes || []);
// //     setEdges(project.edges || []);
// //     setResults(project.results || DEFAULT_MOCK_RESULTS);
// //   }, [project]);

// //   useEffect(() => {
// //     if (messages.length === 0) return;
// //     const startIndex = Math.max(0, messages.length - 3);
// //     const recentMessages = messages.slice(startIndex);
    
// //     recentMessages.forEach(msg => {
// //       if (processedMessageIds.current.has(msg.id)) return;
// //       if (msg.isTyping || !msg.text) return;
      
// //       if (msg.text.includes('Equipment_list') && msg.text.includes('Connection')) {
// //         processedMessageIds.current.add(msg.id);
// //         attemptParseAndGenerate(msg.text);
// //       }
// //     });
// //   }, [messages]);

// //   const attemptParseAndGenerate = (text: string) => {
// //     try {
// //       let jsonString = text;
// //       const codeBlockMatch = text.match(/``````/) || text.match(/``````/);
      
// //       if (codeBlockMatch) {
// //         jsonString = codeBlockMatch[1];
// //       } else {
// //         const firstOpen = text.indexOf('{');
// //         const lastClose = text.lastIndexOf('}');
// //         if (firstOpen !== -1 && lastClose !== -1 && lastClose > firstOpen) {
// //           jsonString = text.substring(firstOpen, lastClose + 1);
// //         }
// //       }
      
// //       const data = JSON.parse(jsonString);
// //       if (data.Equipment_list && data.Connection) {
// //         console.log("Detected valid simulation JSON, generating flowsheet...", data);
// //         generateFlowsheetFromData(data);
// //       }
// //     } catch (e) {
// //       console.debug("Failed to parse simulation JSON from message:", e);
// //     }
// //   };

// //   const generateFlowsheetFromData = (data: any) => {
// //     const equipmentList = data.Equipment_list as Record<string, string>;
// //     const connections = data.Connection as any[];
// //     const newNodes: FlowsheetNode[] = [];
// //     const newEdges: FlowsheetEdge[] = [];

// //     const findEquipmentType = (typeStr: string): EquipmentType => {
// //       if (Object.values(EquipmentType).includes(typeStr as EquipmentType)) {
// //         return typeStr as EquipmentType;
// //       }
// //       const normalized = typeStr.replace(/\s+/g, '').toLowerCase();
// //       const match = Object.values(EquipmentType).find(t => t.toLowerCase() === normalized);
// //       return match || EquipmentType.Tank;
// //     };

// //     Object.entries(equipmentList).forEach(([name, typeStr]) => {
// //       const type = findEquipmentType(typeStr);
// //       const connectionData = connections.find(c => c.equipment === name);
// //       const params = connectionData?.Param || {};
// //       const properties: Record<string, any> = {};
      
// //       Object.entries(params).forEach(([key, value]) => {
// //         properties[mapParamKey(key)] = value;
// //       });

// //       newNodes.push({
// //         id: name,
// //         type: type,
// //         name: name,
// //         x: 0,
// //         y: 0,
// //         properties
// //       });
// //     });

// //     connections.forEach((conn) => {
// //       const fromId = conn.equipment;
// //       const outlets = Array.isArray(conn.outlet) ? conn.outlet : (conn.outlet ? [conn.outlet] : []);
      
// //       outlets.forEach((toId: string) => {
// //         if (newNodes.find(n => n.id === fromId) && newNodes.find(n => n.id === toId)) {
// //           newEdges.push({
// //             id: `edge-${fromId}-${toId}`,
// //             from: fromId,
// //             to: toId
// //           });
// //         }
// //       });
// //     });

// //     // Layout logic (same as before)
// //     const incomingEdgeCounts: Record<string, number> = {};
// //     newNodes.forEach(n => incomingEdgeCounts[n.id] = 0);
// //     newEdges.forEach(e => {
// //       if (incomingEdgeCounts[e.to] !== undefined) incomingEdgeCounts[e.to]++;
// //     });

// //     const levels: Record<string, number> = {};
// //     const queue: {id: string, level: number}[] = [];

// //     newNodes.forEach(n => {
// //       if (incomingEdgeCounts[n.id] === 0) {
// //         queue.push({ id: n.id, level: 0 });
// //         levels[n.id] = 0;
// //       }
// //     });

// //     if (queue.length === 0 && newNodes.length > 0) {
// //       queue.push({ id: newNodes[0].id, level: 0 });
// //       levels[newNodes[0].id] = 0;
// //     }

// //     const visited = new Set<string>();
// //     while (queue.length > 0) {
// //       const { id, level } = queue.shift()!;
// //       if (visited.has(id)) continue;
// //       visited.add(id);
// //       levels[id] = level;

// //       const outgoing = newEdges.filter(e => e.from === id).map(e => e.to);
// //       outgoing.forEach(toId => {
// //         if (!levels[toId] || levels[toId] < level + 1) {
// //           queue.push({ id: toId, level: level + 1 });
// //         }
// //       });
// //     }

// //     newNodes.forEach(n => {
// //       if (levels[n.id] === undefined) levels[n.id] = 0;
// //     });

// //     const nodesPerLevel: Record<number, number> = {};
// //     const X_SPACING = 200;
// //     const Y_SPACING = 150;

// //     const layoutedNodes = newNodes.map(node => {
// //       const level = levels[node.id];
// //       const indexInLevel = nodesPerLevel[level] || 0;
// //       nodesPerLevel[level] = indexInLevel + 1;

// //       return {
// //         ...node,
// //         x: 50 + level * X_SPACING,
// //         y: 50 + indexInLevel * Y_SPACING
// //       };
// //     });

// //     setNodes(layoutedNodes);
// //     setEdges(newEdges);
// //     setActiveTab('flow-diagram');

// //     setMessages(prev => {
// //       const lastMsg = prev[prev.length - 1];
// //       if (lastMsg && lastMsg.text === 'Flowsheet generated successfully.') return prev;
// //       return [...prev, {
// //         id: 'sys-' + Date.now(),
// //         sender: 'ai',
// //         text: 'Flowsheet generated successfully.'
// //       }];
// //     });
// //   };

// //   const formatPropertyKey = (key: string): string => {
// //     const result = key.replace(/([A-Z])/g, " $1");
// //     return result.charAt(0).toUpperCase() + result.slice(1);
// //   };

// //   const generateSimulationJson = () => {
// //     const equipmentList: Record<string, string> = {};
// //     const connections: any[] = [];

// //     nodes.forEach(node => {
// //       equipmentList[node.name] = node.type;
// //       const nodeEdges = edges.filter(edge => edge.from === node.id);
// //       const outlets = nodeEdges.map(edge => {
// //         const targetNode = nodes.find(n => n.id === edge.to);
// //         return targetNode ? targetNode.id : null;
// //       }).filter(Boolean);

// //       const formattedParams: Record<string, any> = {};
// //       if (node.properties) {
// //         Object.entries(node.properties).forEach(([key, value]) => {
// //           formattedParams[formatPropertyKey(key)] = (value === undefined || value === null || value === '') ? 0 : value;
// //         });
// //       }

// //       connections.push({
// //         equipment: node.name,
// //         outlet: outlets,
// //         Param: formattedParams
// //       });
// //     });

// //     return {
// //       Equipment_list: equipmentList,
// //       Connection: connections
// //     };
// //   };

// //   // API INTEGRATION: Save handler
// //   const handleSave = async () => {
// //     setIsSaving(true);
// //     try {
// //       const simulationData = generateSimulationJson();
// //       console.log("Saving Simulation Data (JSON Structure):", JSON.stringify(simulationData, null, 2));

// //       const projectData: Project = {
// //         id: project.id,
// //         name: projectName,
// //         messages,
// //         nodes,
// //         edges,
// //         results
// //       };

// //       const response = await api.saveProject(projectData);
// //       console.log("Save response:", response);

// //       // Update parent state
// //       onUpdateProject(project.id, projectData);

// //       alert('Project saved successfully!');
// //     } catch (error) {
// //       console.error("Error saving project:", error);
// //       alert(`Failed to save project: ${error}`);
// //     } finally {
// //       setIsSaving(false);
// //     }
// //   };

// //   // // API INTEGRATION: PDF Upload handler
  
// //   //   const file = event.target.files?.[0];
// //   //   if (!file) return;

// //   //   setIsUploading(true);
// //   //   try {
// //   //     const response = await api.uploadPDF(file);
// //   //     console.log("PDF Upload response:", response);

// //   //     // Add parsed data to chatconst handlePDFUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
// //   //     setMessages(prev => [...prev, {
// //   //       id: 'pdf-' + Date.now(),
// //   //       sender: 'ai',
// //   //       text: `PDF "${response.filename}" uploaded successfully. Found equipment: ${response.parsed_data.equipment_found.join(', ') || 'None'}`
// //   //     }]);

// //   //     alert(`PDF processed: ${response.parsed_data.equipment_found.length} equipment items found`);
// //   //   } catch (error) {
// //   //     console.error("Error uploading PDF:", error);
// //   //     alert(`Failed to upload PDF: ${error}`);
// //   //   } finally {
// //   //     setIsUploading(false);
// //   //     if (fileInputRef.current) {
// //   //       fileInputRef.current.value = '';
// //   //     }
// //   //   }
// //   // };

// //   const renderTabContent = () => {
// //     switch (activeTab) {
// //       case 'chat':
// //         return <Chatbot messages={messages} setMessages={setMessages} />;
// //       case 'flow-diagram':
// //         return <FlowDiagram nodes={nodes} setNodes={setNodes} edges={edges} setEdges={setEdges} />;
// //       case 'result-table':
// //         return <ResultTable data={results} />;
// //       default:
// //         return null;
// //     }
// //   };

// //   const TabButton = ({ tab, label }: { tab: Tab; label: string }) => (
// //     <button
// //       onClick={() => setActiveTab(tab)}
// //       className={`px-4 py-2 text-sm font-medium rounded-t-md transition-colors ${
// //         activeTab === tab
// //           ? 'bg-slate-800 text-white border-b-2 border-indigo-500'
// //           : 'text-gray-400 hover:bg-slate-700/50'
// //       }`}
// //     >
// //       {label}
// //     </button>
// //   );

// //   return (
// //     <div className="flex-1 flex flex-col bg-slate-900">
// //       {/* Header */}
// //       <div className="flex-shrink-0 p-6 border-b border-slate-700/50">
// //         <div className="flex justify-between items-center">
// //           <div className="flex flex-col">
// //             <label htmlFor="projectName" className="text-xs text-gray-400 mb-1">Project Name</label>
// //             <input
// //               id="projectName"
// //               type="text"
// //               value={projectName}
// //               onChange={(e) => setProjectName(e.target.value)}
// //               className="text-lg font-semibold bg-transparent border-none text-white focus:ring-0 -ml-1"
// //             />
// //           </div>
// //           <div className="flex space-x-2">
// //             {/* PDF Upload Button */}
// //             <input
// //               ref={fileInputRef}
// //               type="file"
// //               accept=".pdf"
// //               onChange={handlePDFUpload}
// //               className="hidden"
// //               id="pdf-upload"
// //             />
// //             <button
// //               onClick={() => fileInputRef.current?.click()}
// //               disabled={isUploading}
// //               className="flex items-center px-3 py-1.5 text-xs font-semibold text-white bg-green-600 rounded-md hover:bg-green-500 transition-colors disabled:opacity-50"
// //             >
// //               <UploadIcon className="w-4 h-4 mr-2" />
// //               {isUploading ? 'Uploading...' : 'Upload PDF'}
// //             </button>
            
// //             {/* Save Button */}
// //             <button
// //               onClick={handleSave}
// //               disabled={isSaving}
// //               className="flex items-center px-3 py-1.5 text-xs font-semibold text-white bg-indigo-600 rounded-md hover:bg-indigo-500 transition-colors disabled:opacity-50"
// //             >
// //               <SaveIcon className="w-4 h-4 mr-2" />
// //               {isSaving ? 'Saving...' : 'Save'}
// //             </button>
// //           </div>
// //         </div>
// //       </div>

// //       {/* Content Area */}
// //       <div className="flex-1 flex flex-col overflow-hidden">
// //         {/* Tabs */}
// //         <div className="flex-shrink-0 px-6 border-b border-slate-700/50">
// //           <nav className="flex space-x-2">
// //             <TabButton tab="chat" label="Chat" />
// //             <TabButton tab="flow-diagram" label="Flow Diagram" />
// //             <TabButton tab="result-table" label="Result Table" />
// //           </nav>
// //         </div>

// //         {/* Tab Panel */}
// //         <div className="flex-1 overflow-y-auto p-6">
// //           {renderTabContent()}
// //         </div>
// //       </div>
// //     </div>
// //   );
// // };

// // export default MainContent;
// // src/components/MainContent.tsx
// import React, { useState, useEffect, useCallback, useRef } from 'react';
// import { Project, ChatMessage, FlowsheetNode, FlowsheetEdge, SimulationResult, EquipmentType } from '../types';
// import Chatbot from './Chatbot';
// import FlowDiagram from './FlowDiagram';
// import ResultTable from './ResultTable';
// import SaveIcon from './icons/SaveIcon';
// import { api } from '../services/api';

// interface MainContentProps {
//   project: Project;
//   onUpdateProject: (id: string, data: Partial<Project>) => void;
// }

// type Tab = 'chat' | 'flow-diagram' | 'result-table';

// const DEFAULT_MOCK_RESULTS: SimulationResult[] = [
//   { id: 1, parameter: 'Reactor Temperature', value: '350 K', status: 'Nominal' },
//   { id: 2, parameter: 'Column Pressure', value: '1.2 atm', status: 'Warning' },
//   { id: 3, parameter: 'Tank Level', value: '85%', status: 'Nominal' },
//   { id: 4, parameter: 'Pump Flow Rate', value: '150 L/min', status: 'Nominal' },
//   { id: 5, parameter: 'Product Purity', value: '99.5%', status: 'Excellent' },
//   { id: 6, parameter: 'Energy Consumption', value: '5.2 kWh', status: 'High' },
// ];

// const mapParamKey = (key: string): string => {
//   const map: Record<string, string> = {
//     'Temperature': 'temperature',
//     'Pressure': 'pressure',
//     'Outlet Temperature': 'outletTemperature',
//     'Outlet Pressure': 'outletPressure',
//     'Stages': 'stages',
//     'Condenser Type': 'condenserType',
//     'Reflux Ratio': 'refluxRatio'
//   };
//   if (map[key]) return map[key];
//   return key.replace(/(?:^\w|[A-Z]|\b\w)/g, (word, index) =>
//     index === 0 ? word.toLowerCase() : word.toUpperCase()
//   ).replace(/\s+/g, '');
// };

// const MainContent: React.FC<MainContentProps> = ({ project, onUpdateProject }) => {
//   const [projectName, setProjectName] = useState(project.name);
//   const [activeTab, setActiveTab] = useState<Tab>('chat');
//   const [messages, setMessages] = useState<ChatMessage[]>(project.messages || []);
//   const [nodes, setNodes] = useState<FlowsheetNode[]>(project.nodes || []);
//   const [edges, setEdges] = useState<FlowsheetEdge[]>(project.edges || []);
//   const [results, setResults] = useState<SimulationResult[]>(project.results || DEFAULT_MOCK_RESULTS);
//   const [isSaving, setIsSaving] = useState(false);

//   const processedMessageIds = useRef<Set<string>>(new Set(project.messages?.map(m => m.id) || []));

//   useEffect(() => {
//     setProjectName(project.name);
//     setMessages(project.messages || []);
//     setNodes(project.nodes || []);
//     setEdges(project.edges || []);
//     setResults(project.results || DEFAULT_MOCK_RESULTS);
//   }, [project]);

//   useEffect(() => {
//     if (messages.length === 0) return;
//     const startIndex = Math.max(0, messages.length - 3);
//     const recentMessages = messages.slice(startIndex);
    
//     recentMessages.forEach(msg => {
//       if (processedMessageIds.current.has(msg.id)) return;
//       if (msg.isTyping || !msg.text) return;
      
//       if (msg.text.includes('Equipment_list') && msg.text.includes('Connection')) {
//         processedMessageIds.current.add(msg.id);
//         attemptParseAndGenerate(msg.text);
//       }
//     });
//   }, [messages]);

//   const attemptParseAndGenerate = (text: string) => {
//     try {
//       let jsonString = text;
//       const codeBlockMatch = text.match(/``````/) || text.match(/``````/);
      
//       if (codeBlockMatch) {
//         jsonString = codeBlockMatch[1];
//       } else {
//         const firstOpen = text.indexOf('{');
//         const lastClose = text.lastIndexOf('}');
//         if (firstOpen !== -1 && lastClose !== -1 && lastClose > firstOpen) {
//           jsonString = text.substring(firstOpen, lastClose + 1);
//         }
//       }
      
//       const data = JSON.parse(jsonString);
//       if (data.Equipment_list && data.Connection) {
//         console.log("Detected valid simulation JSON, generating flowsheet...", data);
//         generateFlowsheetFromData(data);
//       }
//     } catch (e) {
//       console.debug("Failed to parse simulation JSON from message:", e);
//     }
//   };

//   const generateFlowsheetFromData = (data: any) => {
//     const equipmentList = data.Equipment_list as Record<string, string>;
//     const connections = data.Connection as any[];
//     const newNodes: FlowsheetNode[] = [];
//     const newEdges: FlowsheetEdge[] = [];

//     const findEquipmentType = (typeStr: string): EquipmentType => {
//       if (Object.values(EquipmentType).includes(typeStr as EquipmentType)) {
//         return typeStr as EquipmentType;
//       }
//       const normalized = typeStr.replace(/\s+/g, '').toLowerCase();
//       const match = Object.values(EquipmentType).find(t => t.toLowerCase() === normalized);
//       return match || EquipmentType.Tank;
//     };

//     Object.entries(equipmentList).forEach(([name, typeStr]) => {
//       const type = findEquipmentType(typeStr);
//       const connectionData = connections.find(c => c.equipment === name);
//       const params = connectionData?.Param || {};
//       const properties: Record<string, any> = {};
      
//       Object.entries(params).forEach(([key, value]) => {
//         properties[mapParamKey(key)] = value;
//       });

//       newNodes.push({
//         id: name,
//         type: type,
//         name: name,
//         x: 0,
//         y: 0,
//         properties
//       });
//     });

//     connections.forEach((conn) => {
//       const fromId = conn.equipment;
//       const outlets = Array.isArray(conn.outlet) ? conn.outlet : (conn.outlet ? [conn.outlet] : []);
      
//       outlets.forEach((toId: string) => {
//         if (newNodes.find(n => n.id === fromId) && newNodes.find(n => n.id === toId)) {
//           newEdges.push({
//             id: `edge-${fromId}-${toId}`,
//             from: fromId,
//             to: toId
//           });
//         }
//       });
//     });

//     // Layout logic
//     const incomingEdgeCounts: Record<string, number> = {};
//     newNodes.forEach(n => incomingEdgeCounts[n.id] = 0);
//     newEdges.forEach(e => {
//       if (incomingEdgeCounts[e.to] !== undefined) incomingEdgeCounts[e.to]++;
//     });

//     const levels: Record<string, number> = {};
//     const queue: {id: string, level: number}[] = [];

//     newNodes.forEach(n => {
//       if (incomingEdgeCounts[n.id] === 0) {
//         queue.push({ id: n.id, level: 0 });
//         levels[n.id] = 0;
//       }
//     });

//     if (queue.length === 0 && newNodes.length > 0) {
//       queue.push({ id: newNodes[0].id, level: 0 });
//       levels[newNodes[0].id] = 0;
//     }

//     const visited = new Set<string>();
//     while (queue.length > 0) {
//       const { id, level } = queue.shift()!;
//       if (visited.has(id)) continue;
//       visited.add(id);
//       levels[id] = level;

//       const outgoing = newEdges.filter(e => e.from === id).map(e => e.to);
//       outgoing.forEach(toId => {
//         if (!levels[toId] || levels[toId] < level + 1) {
//           queue.push({ id: toId, level: level + 1 });
//         }
//       });
//     }

//     newNodes.forEach(n => {
//       if (levels[n.id] === undefined) levels[n.id] = 0;
//     });

//     const nodesPerLevel: Record<number, number> = {};
//     const X_SPACING = 200;
//     const Y_SPACING = 150;

//     const layoutedNodes = newNodes.map(node => {
//       const level = levels[node.id];
//       const indexInLevel = nodesPerLevel[level] || 0;
//       nodesPerLevel[level] = indexInLevel + 1;

//       return {
//         ...node,
//         x: 50 + level * X_SPACING,
//         y: 50 + indexInLevel * Y_SPACING
//       };
//     });

//     setNodes(layoutedNodes);
//     setEdges(newEdges);
//     setActiveTab('flow-diagram');

//     setMessages(prev => {
//       const lastMsg = prev[prev.length - 1];
//       if (lastMsg && lastMsg.text === 'Flowsheet generated successfully.') return prev;
//       return [...prev, {
//         id: 'sys-' + Date.now(),
//         sender: 'ai',
//         text: 'Flowsheet generated successfully.'
//       }];
//     });
//   };

//   const formatPropertyKey = (key: string): string => {
//     const result = key.replace(/([A-Z])/g, " $1");
//     return result.charAt(0).toUpperCase() + result.slice(1);
//   };

//   const generateSimulationJson = () => {
//     const equipmentList: Record<string, string> = {};
//     const connections: any[] = [];

//     nodes.forEach(node => {
//       equipmentList[node.name] = node.type;
//       const nodeEdges = edges.filter(edge => edge.from === node.id);
//       const outlets = nodeEdges.map(edge => {
//         const targetNode = nodes.find(n => n.id === edge.to);
//         return targetNode ? targetNode.id : null;
//       }).filter(Boolean);

//       const formattedParams: Record<string, any> = {};
//       if (node.properties) {
//         Object.entries(node.properties).forEach(([key, value]) => {
//           formattedParams[formatPropertyKey(key)] = (value === undefined || value === null || value === '') ? 0 : value;
//         });
//       }

//       connections.push({
//         equipment: node.name,
//         outlet: outlets,
//         Param: formattedParams
//       });
//     });

//     return {
//       Equipment_list: equipmentList,
//       Connection: connections
//     };
//   };

//   // API INTEGRATION: Save handler
//   const handleSave = async () => {
//     setIsSaving(true);
//     try {
//       const simulationData = generateSimulationJson();
//       console.log("Saving Simulation Data (JSON Structure):", JSON.stringify(simulationData, null, 2));

//       const projectData: Project = {
//         id: project.id,
//         name: projectName,
//         messages,
//         nodes,
//         edges,
//         results
//       };

//       const response = await api.saveProject(projectData);
//       console.log("Save response:", response);

//       onUpdateProject(project.id, projectData);

//       alert('Project saved successfully!');
//     } catch (error) {
//       console.error("Error saving project:", error);
//       alert(`Failed to save project: ${error}`);
//     } finally {
//       setIsSaving(false);
//     }
//   };

//   const renderTabContent = () => {
//     switch (activeTab) {
//       case 'chat':
//         return <Chatbot messages={messages} setMessages={setMessages} />;
//       case 'flow-diagram':
//         return <FlowDiagram nodes={nodes} setNodes={setNodes} edges={edges} setEdges={setEdges} />;
//       case 'result-table':
//         return <ResultTable data={results} />;
//       default:
//         return null;
//     }
//   };

//   const TabButton = ({ tab, label }: { tab: Tab; label: string }) => (
//     <button
//       onClick={() => setActiveTab(tab)}
//       className={`px-4 py-2 text-sm font-medium rounded-t-md transition-colors ${
//         activeTab === tab
//           ? 'bg-slate-800 text-white border-b-2 border-indigo-500'
//           : 'text-gray-400 hover:bg-slate-700/50'
//       }`}
//     >
//       {label}
//     </button>
//   );

//   return (
//     <div className="flex-1 flex flex-col bg-slate-900">
//       {/* Header */}
//       <div className="flex-shrink-0 p-6 border-b border-slate-700/50">
//         <div className="flex justify-between items-center">
//           <div className="flex flex-col">
//             <label htmlFor="projectName" className="text-xs text-gray-400 mb-1">Project Name</label>
//             <input
//               id="projectName"
//               type="text"
//               value={projectName}
//               onChange={(e) => setProjectName(e.target.value)}
//               className="text-lg font-semibold bg-transparent border-none text-white focus:ring-0 -ml-1"
//             />
//           </div>
          
//           {/* Save Button Only */}
//           <button
//             onClick={handleSave}
//             disabled={isSaving}
//             className="flex items-center px-3 py-1.5 text-xs font-semibold text-white bg-indigo-600 rounded-md hover:bg-indigo-500 transition-colors disabled:opacity-50"
//           >
//             <SaveIcon className="w-4 h-4 mr-2" />
//             {isSaving ? 'Saving...' : 'Save'}
//           </button>
//         </div>
//       </div>

//       {/* Content Area */}
//       <div className="flex-1 flex flex-col overflow-hidden">
//         {/* Tabs */}
//         <div className="flex-shrink-0 px-6 border-b border-slate-700/50">
//           <nav className="flex space-x-2">
//             <TabButton tab="chat" label="Chat" />
//             <TabButton tab="flow-diagram" label="Flow Diagram" />
//             <TabButton tab="result-table" label="Result Table" />
//           </nav>
//         </div>

//         {/* Tab Panel */}
//         <div className="flex-1 overflow-y-auto p-6">
//           {renderTabContent()}
//         </div>
//       </div>
//     </div>
//   );
// };

// export default MainContent;
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Project, ChatMessage, FlowsheetNode, FlowsheetEdge, SimulationResult, EquipmentType } from '../types';
import Chatbot from './Chatbot';
import FlowDiagram from './FlowDiagram';
import ResultTable from './ResultTable';
import SaveIcon from './icons/SaveIcon';

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
  const [isSaving, setIsSaving] = useState(false);

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

  const handleSave = async () => {
    setIsSaving(true);
    try {
      const simulationData = generateSimulationJson();
      console.log("Saving Simulation Data (JSON Structure):", JSON.stringify(simulationData, null, 2));

      onUpdateProject(project.id, {
        name: projectName,
        messages,
        nodes,
        edges,
        results
      });

      alert('Project saved successfully!');
    } catch (error) {
      console.error("Error saving project:", error);
      alert(`Failed to save project: ${error}`);
    } finally {
      setIsSaving(false);
    }
  };

  // Run Simulation Handler (called from FlowDiagram)
  const handleRunSimulation = async () => {
    if (nodes.length === 0) {
      alert('No equipment in flowsheet. Please add equipment first.');
      return;
    }

    try {
      const newResults: SimulationResult[] = [];
      let idCounter = 1;

      // Generate results based on node types and properties
      nodes.forEach(node => {
        switch(node.type) {
          case EquipmentType.Reactor:
            newResults.push({ 
              id: idCounter++, 
              parameter: `${node.name} Temperature`, 
              value: `${node.properties?.temperature || 350} K`, 
              status: 'Nominal' 
            });
            newResults.push({ 
              id: idCounter++, 
              parameter: `${node.name} Conversion`, 
              value: '92%', 
              status: 'Excellent' 
            });
            break;
          case EquipmentType.DistillationColumn:
            newResults.push({ 
              id: idCounter++, 
              parameter: `${node.name} Purity`, 
              value: '99.2%', 
              status: 'Nominal' 
            });
            newResults.push({ 
              id: idCounter++, 
              parameter: `${node.name} Reflux Ratio`, 
              value: `${node.properties?.refluxRatio || 2.5}`, 
              status: 'Nominal' 
            });
            newResults.push({ 
              id: idCounter++, 
              parameter: `${node.name} Duty`, 
              value: '2.5 MW', 
              status: 'High' 
            });
            break;
          case EquipmentType.Heater:
            newResults.push({ 
              id: idCounter++, 
              parameter: `${node.name} Outlet Temp`, 
              value: `${node.properties?.outletTemperature || 400} K`, 
              status: 'Nominal' 
            });
            newResults.push({ 
              id: idCounter++, 
              parameter: `${node.name} Heat Duty`, 
              value: '150 kW', 
              status: 'Nominal' 
            });
            break;
          case EquipmentType.Cooler:
            newResults.push({ 
              id: idCounter++, 
              parameter: `${node.name} Outlet Temp`, 
              value: `${node.properties?.outletTemperature || 300} K`, 
              status: 'Nominal' 
            });
            newResults.push({ 
              id: idCounter++, 
              parameter: `${node.name} Cooling Duty`, 
              value: '120 kW', 
              status: 'Nominal' 
            });
            break;
          case EquipmentType.Pump:
            newResults.push({ 
              id: idCounter++, 
              parameter: `${node.name} Flow`, 
              value: '120 L/min', 
              status: 'Nominal' 
            });
            newResults.push({ 
              id: idCounter++, 
              parameter: `${node.name} Outlet Pressure`, 
              value: `${node.properties?.outletPressure || 2} bar`, 
              status: 'Nominal' 
            });
            newResults.push({ 
              id: idCounter++, 
              parameter: `${node.name} Power`, 
              value: '15 kW', 
              status: 'Nominal' 
            });
            break;
          case EquipmentType.Compressor:
            newResults.push({ 
              id: idCounter++, 
              parameter: `${node.name} Outlet Pressure`, 
              value: `${node.properties?.outletPressure || 5} bar`, 
              status: 'Nominal' 
            });
            newResults.push({ 
              id: idCounter++, 
              parameter: `${node.name} Power`, 
              value: '85 kW', 
              status: 'High' 
            });
            break;
          case EquipmentType.Flash:
            newResults.push({ 
              id: idCounter++, 
              parameter: `${node.name} Temperature`, 
              value: `${node.properties?.temperature || 320} K`, 
              status: 'Nominal' 
            });
            newResults.push({ 
              id: idCounter++, 
              parameter: `${node.name} Vapor Fraction`, 
              value: '0.45', 
              status: 'Nominal' 
            });
            break;
          case EquipmentType.Tank:
            newResults.push({ 
              id: idCounter++, 
              parameter: `${node.name} Level`, 
              value: '75%', 
              status: 'Nominal' 
            });
            newResults.push({ 
              id: idCounter++, 
              parameter: `${node.name} Temperature`, 
              value: `${node.properties?.temperature || 298} K`, 
              status: 'Nominal' 
            });
            break;
          case EquipmentType.Feed:
            newResults.push({ 
              id: idCounter++, 
              parameter: `${node.name} Flow`, 
              value: '200 kg/hr', 
              status: 'Nominal' 
            });
            break;
          case EquipmentType.Product:
            newResults.push({ 
              id: idCounter++, 
              parameter: `${node.name} Flow`, 
              value: '180 kg/hr', 
              status: 'Nominal' 
            });
            break;
          default:
            newResults.push({ 
              id: idCounter++, 
              parameter: `${node.name} Status`, 
              value: 'Active', 
              status: 'Nominal' 
            });
        }
      });

      // Add overall metrics
      newResults.push({ 
        id: idCounter++, 
        parameter: 'Total Energy Consumption', 
        value: '5.8 kWh', 
        status: 'High' 
      });
      newResults.push({ 
        id: idCounter++, 
        parameter: 'Process Efficiency', 
        value: '87%', 
        status: 'Excellent' 
      });

      setResults(newResults);
      
      // Update project with new results
      onUpdateProject(project.id, { 
        results: newResults 
      });

      // Switch to result table
      setActiveTab('result-table');
      
      alert('Simulation completed successfully!');
    } catch (error) {
      console.error("Error running simulation:", error);
      alert(`Simulation failed: ${error}`);
    }
  };

  const renderTabContent = () => {
    switch (activeTab) {
      case 'chat':
        return <Chatbot messages={messages} setMessages={setMessages} projectId={project.id} />;
      case 'flow-diagram':
        return (
          <FlowDiagram 
            nodes={nodes} 
            setNodes={setNodes} 
            edges={edges} 
            setEdges={setEdges}
            onRun={handleRunSimulation}
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
    <div className="flex-1 flex flex-col bg-slate-900">
      {/* Header */}
      <div className="flex-shrink-0 p-6 border-b border-slate-700/50">
        <div className="flex justify-between items-center">
          <div className="flex flex-col">
            <label htmlFor="projectName" className="text-xs text-gray-400 mb-1">Project Name</label>
            <input
              id="projectName"
              type="text"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              className="text-lg font-semibold bg-transparent border-none text-white focus:ring-0 -ml-1"
            />
          </div>
          
          {/* Save Button Only */}
          <button
            onClick={handleSave}
            disabled={isSaving}
            className="flex items-center px-3 py-1.5 text-xs font-semibold text-white bg-indigo-600 rounded-md hover:bg-indigo-500 transition-colors disabled:opacity-50"
          >
            <SaveIcon className="w-4 h-4 mr-2" />
            {isSaving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>

      {/* Content Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Tabs */}
        <div className="flex-shrink-0 px-6 border-b border-slate-700/50">
          <nav className="flex space-x-2">
            <TabButton tab="chat" label="Chat" />
            <TabButton tab="flow-diagram" label="Flow Diagram" />
            <TabButton tab="result-table" label="Result Table" />
          </nav>
        </div>

        {/* Tab Panel */}
        <div className="flex-1 overflow-y-auto p-6">
          {renderTabContent()}
        </div>
      </div>
    </div>
  );
};

export default MainContent;
