import React from 'react';
import { FlowsheetNode, FlowsheetEdge, EquipmentType } from '../types';
import CloseIcon from './icons/CloseIcon';
import TrashIcon from './icons/TrashIcon';

interface PropertiesPanelProps {
  node: FlowsheetNode;
  allNodes: FlowsheetNode[];
  edges: FlowsheetEdge[];
  onNodeUpdate: (updatedNode: FlowsheetNode) => void;
  onAddEdge: (fromId: string, toId: string) => void;
  onRemoveEdge: (edgeId: string) => void;
  onClose: () => void;
}

const CONNECTION_RULES: Record<EquipmentType, { maxInputs: number; maxOutputs: number }> = {
    [EquipmentType.Feed]: { maxInputs: 0, maxOutputs: 1 },
    [EquipmentType.Product]: { maxInputs: 1, maxOutputs: 0 },
    [EquipmentType.Heater]: { maxInputs: 1, maxOutputs: 1 },
    [EquipmentType.Cooler]: { maxInputs: 1, maxOutputs: 1 },
    [EquipmentType.Pump]: { maxInputs: 1, maxOutputs: 1 },
    [EquipmentType.Compressor]: { maxInputs: 1, maxOutputs: 1 },
    [EquipmentType.Expander]: { maxInputs: 1, maxOutputs: 1 },
    [EquipmentType.HeatExchanger]: { maxInputs: 1, maxOutputs: 1 },
    [EquipmentType.Reactor]: { maxInputs: 1, maxOutputs: 2 },
    [EquipmentType.Flash]: { maxInputs: 1, maxOutputs: 2 },
    [EquipmentType.Tank]: { maxInputs: 1, maxOutputs: 2 },
    [EquipmentType.DistillationColumn]: { maxInputs: 1, maxOutputs: 2 },
    [EquipmentType.Mixer]: { maxInputs: Infinity, maxOutputs: 1 },
    [EquipmentType.Splitter]: { maxInputs: 1, maxOutputs: Infinity },
};

const PropertyInput: React.FC<{label: string, name: string, value: any, unit?: string, onChange: (e: React.ChangeEvent<HTMLInputElement>) => void}> = ({ label, name, value, unit, onChange }) => (
    <div>
        <label htmlFor={name} className="text-xs text-gray-400 block mb-1">{label}</label>
        <div className="flex items-center">
            <input 
                id={name}
                name={name}
                type="number"
                value={value}
                onChange={onChange}
                className="w-full bg-slate-700 border border-slate-600 rounded-md px-3 py-1.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            {unit && <span className="text-sm text-gray-400 ml-2 flex-shrink-0">{unit}</span>}
        </div>
    </div>
);


const PropertiesPanel: React.FC<PropertiesPanelProps> = ({
  node,
  allNodes,
  edges,
  onNodeUpdate,
  onAddEdge,
  onRemoveEdge,
  onClose,
}) => {
  const otherNodes = allNodes.filter(n => n.id !== node.id);

  const inputs = edges.filter(e => e.to === node.id);
  const outputs = edges.filter(e => e.from === node.id);
  
  const rules = CONNECTION_RULES[node.type];
  const canAddInput = inputs.length < rules.maxInputs;
  const canAddOutput = outputs.length < rules.maxOutputs;

  const availableInputNodes = otherNodes.filter(n => {
    if (inputs.some(i => i.from === n.id)) return false; 
    const nodeOutputsCount = edges.filter(e => e.from === n.id).length;
    const nodeRules = CONNECTION_RULES[n.type];
    return nodeOutputsCount < nodeRules.maxOutputs;
  });

  const availableOutputNodes = otherNodes.filter(n => {
    if (outputs.some(o => o.to === n.id)) return false; 
    const nodeInputsCount = edges.filter(e => e.to === n.id).length;
    const nodeRules = CONNECTION_RULES[n.type];
    return nodeInputsCount < nodeRules.maxInputs;
  });

  const getNodeName = (id: string) => allNodes.find(n => n.id === id)?.name || 'Unknown';

  const handleAddOutput = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const toId = e.target.value;
    if (toId) {
        onAddEdge(node.id, toId);
        e.target.value = '';
    }
  };
  
  const handleAddInput = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const fromId = e.target.value;
    if (fromId) {
        onAddEdge(fromId, node.id);
        e.target.value = '';
    }
  };
  
  const handleNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onNodeUpdate({ ...node, name: e.target.value });
  };

  const handlePropertyChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    const isNumber = e.target.type === 'number';
    
    onNodeUpdate({
      ...node,
      properties: {
        ...node.properties,
        [name]: isNumber ? parseFloat(value) || 0 : value,
      }
    });
  };

  const renderParameters = () => {
    const { type, properties } = node;
    // FIX: Changed JSX.Element[] to React.ReactElement[] to avoid "Cannot find namespace 'JSX'" error.
    const params: React.ReactElement[] = [];

    switch(type) {
        case EquipmentType.Tank:
        case EquipmentType.Flash:
        case EquipmentType.Reactor:
            params.push(<PropertyInput key="temp" label="Temperature" name="temperature" unit="K" value={properties.temperature} onChange={handlePropertyChange} />);
            params.push(<PropertyInput key="press" label="Pressure" name="pressure" unit="bar" value={properties.pressure} onChange={handlePropertyChange} />);
            break;
        case EquipmentType.Pump:
        case EquipmentType.Compressor:
        case EquipmentType.Expander:
            params.push(<PropertyInput key="out-press" label="Output Pressure" name="outletPressure" unit="bar" value={properties.outletPressure} onChange={handlePropertyChange} />);
            break;
        case EquipmentType.Heater:
        case EquipmentType.Cooler:
            params.push(<PropertyInput key="out-temp" label="Outlet Temperature" name="outletTemperature" unit="K" value={properties.outletTemperature} onChange={handlePropertyChange} />);
            break;
        case EquipmentType.DistillationColumn:
            params.push(<PropertyInput key="stages" label="Number of Stages" name="stages" value={properties.stages} onChange={handlePropertyChange} />);
            params.push(
                <div key="condenser">
                    <label htmlFor="condenserType" className="text-xs text-gray-400 block mb-1">Condenser Type</label>
                    <select id="condenserType" name="condenserType" value={properties.condenserType} onChange={handlePropertyChange} className="w-full bg-slate-700 border border-slate-600 rounded-md px-3 py-1.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500">
                        <option>Total</option>
                        <option>Partial</option>
                    </select>
                </div>
            );
            params.push(<PropertyInput key="dist-press" label="Pressure" name="pressure" unit="bar" value={properties.pressure} onChange={handlePropertyChange} />);
            params.push(<PropertyInput key="dist-temp" label="Temperature" name="temperature" unit="K" value={properties.temperature} onChange={handlePropertyChange} />);
            params.push(<PropertyInput key="reflux" label="Reflux Ratio" name="refluxRatio" value={properties.refluxRatio} onChange={handlePropertyChange} />);
            break;
    }
    
    if (params.length === 0) return null;

    return (
        <div>
            <h4 className="text-sm font-semibold text-gray-300 mb-2">Parameters</h4>
            <div className="space-y-3">{params}</div>
        </div>
    );
  };


  return (
    <div className="w-72 bg-slate-800/50 rounded-lg p-4 flex flex-col space-y-4 flex-shrink-0">
        <div className="flex justify-between items-center">
            <h3 className="text-md font-bold text-gray-200">Properties</h3>
            <button onClick={onClose} className="text-gray-400 hover:text-white">
                <CloseIcon className="w-5 h-5" />
            </button>
        </div>
        
        {/* Name Editor */}
        <div>
            <label htmlFor="nodeName" className="text-xs text-gray-400 block mb-1">Equipment Name</label>
            <input 
                id="nodeName"
                type="text"
                value={node.name}
                onChange={handleNameChange}
                className="w-full bg-slate-700 border border-slate-600 rounded-md px-3 py-1.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
        </div>

        {/* Parameters */}
        {renderParameters()}

        {/* Connections */}
        <div className="space-y-4 flex-1 overflow-y-auto">
            {rules.maxInputs > 0 && (
                <div>
                    <h4 className="text-sm font-semibold text-gray-300 mb-2">Inputs ({inputs.length}/{isFinite(rules.maxInputs) ? rules.maxInputs : '∞'})</h4>
                    <div className="space-y-1">
                        {inputs.map(edge => (
                            <div key={edge.id} className="flex items-center justify-between bg-slate-700/50 p-2 rounded-md">
                                <span className="text-sm">{getNodeName(edge.from)}</span>
                                <button onClick={() => onRemoveEdge(edge.id)} className="text-gray-400 hover:text-red-400">
                                    <TrashIcon className="w-4 h-4" />
                                </button>
                            </div>
                        ))}
                        {inputs.length === 0 && <p className="text-xs text-gray-500 px-2">No inputs</p>}
                    </div>
                    {canAddInput && (
                        <select onChange={handleAddInput} className="mt-2 w-full bg-slate-700 border border-slate-600 rounded-md px-3 py-1.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500">
                            <option value="">Add Input From...</option>
                            {availableInputNodes.map(n => (
                                <option key={n.id} value={n.id}>{n.name}</option>
                            ))}
                        </select>
                    )}
                </div>
            )}

            {rules.maxOutputs > 0 && (
                <div>
                    <h4 className="text-sm font-semibold text-gray-300 mb-2">Outputs ({outputs.length}/{isFinite(rules.maxOutputs) ? rules.maxOutputs : '∞'})</h4>
                    <div className="space-y-1">
                        {outputs.map(edge => (
                            <div key={edge.id} className="flex items-center justify-between bg-slate-700/50 p-2 rounded-md">
                                <span className="text-sm">{getNodeName(edge.to)}</span>
                                <button onClick={() => onRemoveEdge(edge.id)} className="text-gray-400 hover:text-red-400">
                                    <TrashIcon className="w-4 h-4" />
                                </button>
                            </div>
                        ))}
                        {outputs.length === 0 && <p className="text-xs text-gray-500 px-2">No outputs</p>}
                    </div>
                    {canAddOutput && (
                        <select onChange={handleAddOutput} className="mt-2 w-full bg-slate-700 border border-slate-600 rounded-md px-3 py-1.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500">
                            <option value="">Add Output To...</option>
                            {availableOutputNodes.map(n => (
                                <option key={n.id} value={n.id}>{n.name}</option>
                            ))}
                        </select>
                    )}
                </div>
            )}
        </div>
    </div>
  );
};

export default PropertiesPanel;