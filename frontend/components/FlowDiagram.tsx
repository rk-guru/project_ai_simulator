import React, { useState, useRef, useCallback, useMemo, useEffect } from 'react';
import { EquipmentType, FlowsheetNode, FlowsheetEdge } from '../types';
import { EquipmentIcon } from './icons/EquipmentIcons';
import PropertiesPanel from './PropertiesPanel';

const PALETTE_GROUPS = [
    {
        title: 'Streams',
        types: [EquipmentType.Feed, EquipmentType.Product]
    },
    {
        title: 'Basic Units',
        types: [EquipmentType.Tank, EquipmentType.Pump, EquipmentType.Mixer, EquipmentType.Splitter]
    },
    {
        title: 'Heat & Pressure',
        types: [EquipmentType.Heater, EquipmentType.Cooler, EquipmentType.Compressor, EquipmentType.Expander, EquipmentType.HeatExchanger]
    },
    {
        title: 'Separation & Reaction',
        types: [EquipmentType.Flash, EquipmentType.DistillationColumn, EquipmentType.Reactor]
    }
];


const NODE_DIMS = { width: 70, height: 80, iconContainerHeight: 56 };

const getDefaultProperties = (type: EquipmentType): Record<string, any> => {
    switch (type) {
        case EquipmentType.Tank:
        case EquipmentType.Flash:
        case EquipmentType.Reactor:
            return { temperature: 300, pressure: 1 };
        case EquipmentType.Pump:
        case EquipmentType.Compressor:
        case EquipmentType.Expander:
            return { outletPressure: 2 };
        case EquipmentType.Heater:
        case EquipmentType.Cooler:
            return { outletTemperature: 350 };
        case EquipmentType.DistillationColumn:
            return { stages: 10, condenserType: 'Total', pressure: 1, temperature: 373, refluxRatio: 2.5 };
        default:
            return {};
    }
};

const getOrthogonalPathD = (fromNode: FlowsheetNode, toNode: FlowsheetNode): string => {
  if (!fromNode || !toNode) return "";

  const fromCenter = {
    x: fromNode.x + NODE_DIMS.width / 2,
    y: fromNode.y + NODE_DIMS.height / 2,
  };
  const toCenter = {
    x: toNode.x + NODE_DIMS.width / 2,
    y: toNode.y + NODE_DIMS.height / 2,
  };

  const dx = toCenter.x - fromCenter.x;
  const dy = toCenter.y - fromCenter.y;

  let startPoint, endPoint;
  let path = '';

  if (Math.abs(dx) > Math.abs(dy)) {
    const midX = fromCenter.x + dx / 2;
    if (dx > 0) {
      startPoint = { x: fromNode.x + NODE_DIMS.width, y: fromCenter.y };
      endPoint = { x: toNode.x, y: toCenter.y };
    } else {
      startPoint = { x: fromNode.x, y: fromCenter.y };
      endPoint = { x: toNode.x + NODE_DIMS.width, y: toCenter.y };
    }
    path = `M ${startPoint.x},${startPoint.y} H ${midX} V ${endPoint.y} H ${endPoint.x}`;
  } else {
    const midY = fromCenter.y + dy / 2;
    if (dy > 0) {
      startPoint = { x: fromCenter.x, y: fromNode.y + NODE_DIMS.height };
      endPoint = { x: toCenter.x, y: toNode.y };
    } else {
      startPoint = { x: fromCenter.x, y: fromNode.y };
      endPoint = { x: toCenter.x, y: toNode.y + NODE_DIMS.height };
    }
    path = `M ${startPoint.x},${startPoint.y} V ${midY} H ${endPoint.x} V ${endPoint.y}`;
  }

  return path;
};


const FlowDiagram: React.FC = () => {
  const [nodes, setNodes] = useState<FlowsheetNode[]>([]);
  const [edges, setEdges] = useState<FlowsheetEdge[]>([]);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  const equipmentCounters = useRef<Record<string, number>>(
    Object.values(EquipmentType).reduce((acc, curr) => ({ ...acc, [curr]: 0 }), {})
  );
  
  const canvasRef = useRef<HTMLDivElement>(null);
  const [draggingInfo, setDraggingInfo] = useState<{ id: string; offsetX: number; offsetY: number } | null>(null);

  const selectedNode = useMemo(() => nodes.find(n => n.id === selectedNodeId), [nodes, selectedNodeId]);
  
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
        if ((e.key === 'Delete' || e.key === 'Backspace') && selectedNodeId) {
            setNodes(prev => prev.filter(n => n.id !== selectedNodeId));
            setEdges(prev => prev.filter(edge => edge.from !== selectedNodeId && edge.to !== selectedNodeId));
            setSelectedNodeId(null);
        }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
        window.removeEventListener('keydown', handleKeyDown);
    };
  }, [selectedNodeId]);

  const handleDragStart = (e: React.DragEvent<HTMLDivElement>, type: EquipmentType) => {
    e.dataTransfer.setData('application/reactflow', type);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (!canvasRef.current) return;

    const type = e.dataTransfer.getData('application/reactflow') as EquipmentType;
    if (!type) return;

    const rect = canvasRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left - NODE_DIMS.width / 2;
    const y = e.clientY - rect.top - NODE_DIMS.height / 2;

    equipmentCounters.current[type]++;
    const newName = `${type}-${equipmentCounters.current[type]}`;

    const newNode: FlowsheetNode = {
      id: `${type}-${Date.now()}`,
      type,
      name: newName,
      x,
      y,
      properties: getDefaultProperties(type),
    };
    setNodes(prev => [...prev, newNode]);
  };
  
  const addEdge = (from: string, to: string) => {
     if (from === to) return;
     const newEdge: FlowsheetEdge = { id: `edge-${from}-${to}`, from, to };
      if (!edges.some(e => (e.from === newEdge.from && e.to === newEdge.to))) {
        setEdges(prev => [...prev, newEdge]);
      }
  }

  const handleNodeMouseDown = (e: React.MouseEvent, nodeId: string) => {
    if (e.button !== 0) return; 
    
    setSelectedNodeId(nodeId);

    const node = nodes.find(n => n.id === nodeId);
    if (!node || !canvasRef.current) return;
    
    const canvasRect = canvasRef.current.getBoundingClientRect();
    const offsetX = e.clientX - canvasRect.left - node.x;
    const offsetY = e.clientY - canvasRect.top - node.y;
    
    setDraggingInfo({ id: nodeId, offsetX, offsetY });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
      if (draggingInfo && canvasRef.current) {
         const canvasRect = canvasRef.current.getBoundingClientRect();
         const x = e.clientX - canvasRect.left - draggingInfo.offsetX;
         const y = e.clientY - canvasRect.top - draggingInfo.offsetY;
         
         setNodes(prevNodes => 
             prevNodes.map(n => 
                 n.id === draggingInfo.id ? { ...n, x, y } : n
             )
         );
      }
  };

  const handleMouseUp = () => {
      setDraggingInfo(null);
  };

  const handleCanvasMouseDown = (e: React.MouseEvent) => {
    if(e.target === e.currentTarget) {
        setSelectedNodeId(null);
    }
  }

  const handleNodeDoubleClick = (nodeId: string) => {
    setSelectedNodeId(nodeId);
  };
  
  const handleNodeUpdate = (updatedNode: FlowsheetNode) => {
    setNodes(prev => prev.map(n => n.id === updatedNode.id ? updatedNode : n));
  };

  const handleRemoveEdge = (edgeId: string) => {
    setEdges(prev => prev.filter(e => e.id !== edgeId));
  };


  return (
    <div className="flex h-full min-h-[500px] gap-4">
      <div className="flex-1 flex gap-4">
        {/* Palette */}
        <div className="w-40 bg-slate-800/50 rounded-lg p-4 flex flex-col space-y-4 overflow-y-auto">
            {PALETTE_GROUPS.map(group => (
                <div key={group.title} className="w-full">
                    <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">{group.title}</h3>
                    <div className="space-y-2">
                    {group.types.map(type => (
                        <div
                        key={type}
                        className="flex flex-col items-center p-2 rounded-md hover:bg-slate-700 cursor-grab w-full"
                        onDragStart={(e) => handleDragStart(e, type)}
                        draggable
                        >
                        <EquipmentIcon type={type} className="w-10 h-10 text-gray-200" />
                        <span className="text-xs mt-1 text-center">{type}</span>
                        </div>
                    ))}
                    </div>
                </div>
            ))}
        </div>

        {/* Canvas */}
        <div 
          className="flex-1 bg-slate-800/50 rounded-lg relative overflow-hidden" 
          ref={canvasRef} 
          onDragOver={handleDragOver} 
          onDrop={handleDrop}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseDown={handleCanvasMouseDown}
          onMouseLeave={() => {
            setDraggingInfo(null);
          }}
          style={{ cursor: draggingInfo ? 'grabbing' : 'default' }}
        >
          <svg className="absolute top-0 left-0 w-full h-full pointer-events-none">
            <defs>
              <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="8" refY="3.5" orient="auto">
                <polygon points="0 0, 10 3.5, 0 7" fill="#4f46e5" />
              </marker>
            </defs>
            {edges.map(edge => {
                const fromNode = nodes.find(n => n.id === edge.from);
                const toNode = nodes.find(n => n.id === edge.to);
                if (!fromNode || !toNode) return null;

                const pathD = getOrthogonalPathD(fromNode, toNode);
                return (
                  <path 
                    key={edge.id} 
                    d={pathD}
                    stroke="#4f46e5" 
                    strokeWidth="2"
                    fill="none" 
                    markerEnd="url(#arrowhead)" 
                  />
                )
            })}
          </svg>

          {nodes.map(node => (
            <div
              key={node.id}
              style={{ left: node.x, top: node.y, width: NODE_DIMS.width, height: NODE_DIMS.height }}
              className={`absolute flex flex-col items-center justify-start p-1 rounded-md border-2 transition-colors
                ${selectedNodeId === node.id ? 'border-indigo-500' : 'border-transparent'}
                ${draggingInfo?.id === node.id ? '' : 'hover:border-indigo-500/50'}
              `}
              onMouseDown={(e) => handleNodeMouseDown(e, node.id)}
              onDoubleClick={() => handleNodeDoubleClick(node.id)}
            >
              <div style={{height: NODE_DIMS.iconContainerHeight}} className="w-full flex items-center justify-center">
                  <EquipmentIcon type={node.type} className="w-full h-full text-gray-200" style={{ cursor: 'grab' }} />
              </div>
              <span className="text-xs text-center text-gray-300 w-full truncate px-1">{node.name}</span>
            </div>
          ))}
          {nodes.length === 0 && (
              <div className="w-full h-full flex items-center justify-center text-gray-500 pointer-events-none">
                  <p>Drag equipment from the left panel to build your diagram</p>
              </div>
          )}
        </div>
      </div>
      {selectedNode && (
        <PropertiesPanel
            key={selectedNode.id}
            node={selectedNode}
            allNodes={nodes}
            edges={edges}
            onNodeUpdate={handleNodeUpdate}
            onAddEdge={addEdge}
            onRemoveEdge={handleRemoveEdge}
            onClose={() => setSelectedNodeId(null)}
        />
      )}
    </div>
  );
};

export default FlowDiagram;
