import React, { useState, useRef, useCallback, useMemo, useEffect } from 'react';
import { EquipmentType, FlowsheetNode, FlowsheetEdge } from '../types';
import { EquipmentIcon } from './icons/EquipmentIcons';
import PropertiesPanel from './PropertiesPanel';
import PlayIcon from './icons/PlayIcon';
import TrashIcon from './icons/TrashIcon';

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

const NODE_DIMS = { width: 100, height: 80, iconContainerHeight: 56 };

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

const SVG_OFFSET = 5000;

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
    path = `M ${startPoint.x + SVG_OFFSET},${startPoint.y + SVG_OFFSET} H ${midX + SVG_OFFSET} V ${endPoint.y + SVG_OFFSET} H ${endPoint.x + SVG_OFFSET}`;
  } else {
    const midY = fromCenter.y + dy / 2;
    if (dy > 0) {
      startPoint = { x: fromCenter.x, y: fromNode.y + NODE_DIMS.height };
      endPoint = { x: toCenter.x, y: toNode.y };
    } else {
      startPoint = { x: fromCenter.x, y: fromNode.y };
      endPoint = { x: toCenter.x, y: toNode.y + NODE_DIMS.height };
    }
    path = `M ${startPoint.x + SVG_OFFSET},${startPoint.y + SVG_OFFSET} V ${midY + SVG_OFFSET} H ${endPoint.x + SVG_OFFSET} V ${endPoint.y + SVG_OFFSET}`;
  }

  return path;
};

interface FlowDiagramProps {
    nodes: FlowsheetNode[];
    setNodes: React.Dispatch<React.SetStateAction<FlowsheetNode[]>>;
    edges: FlowsheetEdge[];
    setEdges: React.Dispatch<React.SetStateAction<FlowsheetEdge[]>>;
    onRun: () => void;
    onDeleteSimulation: () => void;
}

const FlowDiagram: React.FC<FlowDiagramProps> = ({ nodes, setNodes, edges, setEdges, onRun, onDeleteSimulation }) => {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [viewState, setViewState] = useState({ panX: 0, panY: 0, zoom: 1 });
  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState({ x: 0, y: 0 });

  const equipmentCounters = useRef<Record<string, number>>(
    Object.values(EquipmentType).reduce((acc, curr) => ({ ...acc, [curr]: 0 }), {})
  );

  const canvasRef = useRef<HTMLDivElement>(null);
  const [draggingInfo, setDraggingInfo] = useState<{ id: string; offsetX: number; offsetY: number } | null>(null);

  const selectedNode = useMemo(() => nodes.find(n => n.id === selectedNodeId), [nodes, selectedNodeId]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
        if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
            return;
        }

        if ((e.key === 'Delete' || e.key === 'Backspace') && selectedNodeId) {
            if (window.confirm("Are you sure you want to delete the selected equipment and all its connections?")) {
                setNodes(prev => prev.filter(n => n.id !== selectedNodeId));
                setEdges(prev => prev.filter(edge => edge.from !== selectedNodeId && edge.to !== selectedNodeId));
                setSelectedNodeId(null);
            }
        }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
        window.removeEventListener('keydown', handleKeyDown);
    };
  }, [selectedNodeId, setNodes, setEdges]);

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
    // Account for current pan and zoom when placing a new node
    const x = (e.clientX - rect.left - NODE_DIMS.width / 2 - viewState.panX) / viewState.zoom;
    const y = (e.clientY - rect.top - NODE_DIMS.height / 2 - viewState.panY) / viewState.zoom;

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

  const addEdge = (from: string, to: string, port?: string) => {
     if (from === to) return;
     const newEdge: FlowsheetEdge = { id: `edge-${from}-${to}-${port || 'default'}`, from, to, port };
      if (!edges.some(e => (e.from === newEdge.from && e.to === newEdge.to && e.port === newEdge.port))) {
        setEdges(prev => [...prev, newEdge]);
      }
  }

  const handleNodeMouseDown = (e: React.MouseEvent, nodeId: string) => {
    if (e.button !== 0) return;

    e.stopPropagation();

    setSelectedNodeId(nodeId);

    const node = nodes.find(n => n.id === nodeId);
    if (!node || !canvasRef.current) return;

    const canvasRect = canvasRef.current.getBoundingClientRect();
    // Correct offset calculation: worldX = (screenX - panX) / zoom
    const offsetX = (e.clientX - canvasRect.left - viewState.panX - node.x * viewState.zoom) / viewState.zoom;
    const offsetY = (e.clientY - canvasRect.top - viewState.panY - node.y * viewState.zoom) / viewState.zoom;

    setDraggingInfo({ id: nodeId, offsetX, offsetY });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
      if (draggingInfo && canvasRef.current) {
         const canvasRect = canvasRef.current.getBoundingClientRect();
         const x = (e.clientX - canvasRect.left - draggingInfo.offsetX * viewState.zoom - viewState.panX) / viewState.zoom;
         const y = (e.clientY - canvasRect.top - draggingInfo.offsetY * viewState.zoom - viewState.panY) / viewState.zoom;

         setNodes(prevNodes =>
             prevNodes.map(n =>
                 n.id === draggingInfo.id ? { ...n, x, y } : n
             )
         );
      }

      if (isPanning) {
          setViewState(prev => ({
              ...prev,
              panX: prev.panX + (e.clientX - panStart.x),
              panY: prev.panY + (e.clientY - panStart.y)
          }));
          setPanStart({ x: e.clientX, y: e.clientY });
      }
  };

  const handleMouseUp = () => {
      setDraggingInfo(null);
      setIsPanning(false);
  };

  const handleCanvasMouseDown = (e: React.MouseEvent) => {
    if(e.target === e.currentTarget) {
        setSelectedNodeId(null);
    }

    if (e.button === 0 && !draggingInfo) {
        setIsPanning(true);
        setPanStart({ x: e.clientX, y: e.clientY });
    }
  }

  const handleWheel = (e: React.WheelEvent) => {
      e.preventDefault();
      const zoomSpeed = 0.0002;
      const delta = -e.deltaY;
      const newZoom = Math.min(Math.max(0.2, viewState.zoom + delta * zoomSpeed), 3);

      // Zoom towards cursor
      const rect = canvasRef.current?.getBoundingClientRect();
      if (!rect) return;

      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      const worldX = (mouseX - viewState.panX) / viewState.zoom;
      const worldY = (mouseY - viewState.panY) / viewState.zoom;

      setViewState(prev => ({
          ...prev,
          zoom: newZoom,
          panX: mouseX - worldX * newZoom,
          panY: mouseY - worldY * newZoom
      }));
  }

  const resetView = () => {
      setViewState({ panX: 0, panY: 0, zoom: 1 });
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
      <div className="flex-1 flex gap-4 overflow-hidden">
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
          onWheel={handleWheel}
          onDoubleClick={resetView}
          onMouseLeave={() => {
            setDraggingInfo(null);
            setIsPanning(false);
          }}
          style={{ cursor: draggingInfo ? 'grabbing' : (isPanning ? 'grabbing' : 'crosshair') }}
        >
          {/* Controls Overlay */}
          <div className="absolute top-4 right-4 flex flex-col gap-2 z-10">
              <button
                  onClick={onRun}
                  className="flex items-center px-4 py-2 bg-green-600 hover:bg-green-500 text-white text-sm font-semibold rounded-md shadow-lg transition-colors"
              >
                  <PlayIcon className="w-4 h-4 mr-2" />
                  Run Simulation
              </button>
              <button
                  onClick={onDeleteSimulation}
                  className="flex items-center px-4 py-2 bg-red-600 hover:bg-red-500 text-white text-sm font-semibold rounded-md shadow-lg transition-colors"
              >
                  <TrashIcon className="w-4 h-4 mr-2" />
                  Delete Simulation
              </button>
          </div>

          <div
            style={{
                transform: `translate(${viewState.panX}px, ${viewState.panY}px) scale(${viewState.zoom})`,
                transformOrigin: '0 0',
                transition: isPanning ? 'none' : 'transform 0.1s ease-out'
            }}
            className="absolute inset-0 pointer-events-none"
          >
            <svg
              className="absolute pointer-events-none"
              width="10000"
              height="10000"
              style={{ top: '-5000px', left: '-5000px' }}
            >
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
                      strokeWidth={`${2 / viewState.zoom}px`}
                      fill="none"
                      markerEnd="url(#arrowhead)"
                    />
                  )
              })}
            </svg>

            {nodes.map(node => (
              <div
                key={node.id}
                style={{
                    left: node.x,
                    top: node.y,
                    width: NODE_DIMS.width,
                    height: NODE_DIMS.height,
                    pointerEvents: 'auto'
                }}
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
                <span className="text-xs text-center text-gray-300 w-full px-1 leading-tight">{node.name}</span>
              </div>
            ))}
          </div>

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
