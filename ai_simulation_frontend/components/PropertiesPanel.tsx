import React, { useState, useEffect, useRef } from 'react';
import { FlowsheetNode, FlowsheetEdge, EquipmentType } from '../types';
import CloseIcon from './icons/CloseIcon';
import TrashIcon from './icons/TrashIcon';
import { dbService } from '../services/db';

interface PropertiesPanelProps {
  node: FlowsheetNode;
  allNodes: FlowsheetNode[];
  edges: FlowsheetEdge[];
  onNodeUpdate: (updatedNode: FlowsheetNode) => void;
  onAddEdge: (fromId: string, toId: string, port?: string) => void;
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
    [EquipmentType.HeatExchanger]: { maxInputs: 2, maxOutputs: 2 },
    [EquipmentType.Reactor]: { maxInputs: 1, maxOutputs: 2 },
    [EquipmentType.Flash]: { maxInputs: 1, maxOutputs: 2 },
    [EquipmentType.Tank]: { maxInputs: 1, maxOutputs: 2 },
    [EquipmentType.DistillationColumn]: { maxInputs: 1, maxOutputs: 2 },
    [EquipmentType.Mixer]: { maxInputs: Infinity, maxOutputs: 1 },
    [EquipmentType.Splitter]: { maxInputs: 1, maxOutputs: Infinity },
};

const PORT_CONFIG: Record<EquipmentType, { inputs: string[], outputs: string[] } | undefined> = {
    [EquipmentType.HeatExchanger]: {
        inputs: ['hot-in', 'cold-in'],
        outputs: ['hot-out', 'cold-out']
    },
    [EquipmentType.Flash]: {
        inputs: ['inlet'],
        outputs: ['vapor', 'liquid']
    },
    [EquipmentType.DistillationColumn]: {
        inputs: ['feed'],
        outputs: ['distillate', 'bottoms']
    },
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


const SearchableCompoundSelect: React.FC<{
  value: any;
  onChange: (val: string) => void;
  chemicals: string[];
}> = ({ value, onChange, chemicals }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [filter, setFilter] = useState('');

  const filtered = chemicals.filter(c => c.toLowerCase().includes(filter.toLowerCase()));

  return (
    <div className="relative flex-1 min-w-0">
      <div
        onClick={() => setIsOpen(!isOpen)}
        className="w-full bg-slate-800 border border-slate-600 rounded px-1 py-1 text-[10px] text-white cursor-pointer flex justify-between items-center"
      >
        <span className="truncate">{value || 'Select...'}</span>
        <span className="ml-1 text-gray-500">▾</span>
      </div>
      {isOpen && (
        <div className="absolute z-[100] top-full left-0 w-full bg-slate-800 border border-slate-600 rounded-md shadow-xl overflow-hidden">
          <input
            autoFocus
            type="text"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="Search..."
            className="w-full bg-slate-700 border-b border-slate-600 px-2 py-1 text-[10px] text-white focus:outline-none"
          />
          <ul className="max-h-40 overflow-y-auto">
            {filtered.length > 0 ? (
              filtered.map(chem => (
                <li
                  key={chem}
                  onClick={() => {
                    onChange(chem);
                    setIsOpen(false);
                    setFilter('');
                  }}
                  className="px-2 py-1 text-[10px] text-gray-300 hover:bg-indigo-600 hover:text-white cursor-pointer"
                >
                  {chem}
                </li>
              ))
            ) : (
              <li className="px-2 py-1 text-[10px] text-gray-500 italic">No results</li>
            )}
          </ul>
        </div>
      )}
      {isOpen && <div className="fixed inset-0 z-[-1]" onClick={() => setIsOpen(false)} />}
    </div>
  );
};

const PropertiesPanel: React.FC<PropertiesPanelProps> = ({
  node,
  allNodes,
  edges,
  onNodeUpdate,
  onAddEdge,
  onRemoveEdge,
  onClose,
}) => {
  const [chemicals, setChemicals] = useState<string[]>([]);
  const [selectedInputToAdd, setSelectedInputToAdd] = useState('');
  const [selectedOutputToAdd, setSelectedOutputToAdd] = useState('');

  // Fetch chemicals on mount
  useEffect(() => {
    const fetchChemicals = async () => {
        const list = await dbService.getChemicals();
        setChemicals(list);
    };
    fetchChemicals();
  }, []);

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
        setSelectedOutputToAdd(''); // Reset controlled input
    }
  };

  const handleAddInput = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const fromId = e.target.value;
    if (fromId) {
        onAddEdge(fromId, node.id);
        setSelectedInputToAdd(''); // Reset controlled input
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

  // --- Compound Management Logic ---
  const handleAddCompound = (chemicalName: string) => {
      const currentCompounds = node.properties.compounds || [];
      if (!currentCompounds.some((c: any) => c.name === chemicalName)) {
          onNodeUpdate({
              ...node,
              properties: {
                  ...node.properties,
                  compounds: [...currentCompounds, { name: chemicalName, moleFraction: 0 }]
              }
          });
      }
      setSearchTerm('');
      setShowDropdown(false);
  };

  const handleRemoveCompound = (chemicalName: string) => {
      const currentCompounds = node.properties.compounds || [];
      onNodeUpdate({
          ...node,
          properties: {
              ...node.properties,
              compounds: currentCompounds.filter((c: any) => c.name !== chemicalName)
          }
      });
  };

  const handleMoleFractionChange = (chemicalName: string, newValue: string) => {
      const currentCompounds = node.properties.compounds || [];
      const updatedCompounds = currentCompounds.map((c: any) => {
          if (c.name === chemicalName) {
              return { ...c, moleFraction: parseFloat(newValue) || 0 };
          }
          return c;
      });
      onNodeUpdate({
          ...node,
          properties: {
              ...node.properties,
              compounds: updatedCompounds
          }
      });
  };

  const renderStoichiometryTable = (label: string, key: string) => {
    const data = node.properties[key] || [];

    const updateRow = (index: number, field: string, value: any) => {
      const newData = [...data];
      newData[index] = { ...newData[index], [field]: value };
      onNodeUpdate({
        ...node,
        properties: { ...node.properties, [key]: newData }
      });
    };

    const addRow = (index: number) => {
      const newData = [...data];
      newData.splice(index + 1, 0, { compound: '', stoichiometry: 1 });
      onNodeUpdate({
        ...node,
        properties: { ...node.properties, [key]: newData }
      });
    };

    const removeRow = (index: number) => {
      const newData = data.filter((_, i) => i !== index);
      onNodeUpdate({
        ...node,
        properties: { ...node.properties, [key]: newData }
      });
    };

    return (
      <div className="mt-4 space-y-2">
        <h4 className="text-sm font-semibold text-gray-300 mb-2">{label}</h4>
        <div className="space-y-2">
          {data.length === 0 && (
            <button
              onClick={() => addRow(-1)}
              className="w-full py-2 bg-slate-700 hover:bg-slate-600 border border-slate-600 rounded text-xs text-gray-300 transition-colors"
            >
              + Add First Row
            </button>
          )}
          {data.map((row: any, index: number) => (
            <div key={index} className="flex items-center space-x-1 bg-slate-700/30 p-1 rounded">
              <SearchableCompoundSelect
                value={row.compound}
                onChange={(val) => updateRow(index, 'compound', val)}
                chemicals={chemicals}
              />
              <input
                type="number"
                value={row.stoichiometry}
                onChange={(e) => updateRow(index, 'stoichiometry', parseFloat(e.target.value) || 0)}
                className="w-12 bg-slate-800 border border-slate-600 rounded px-1 py-1 text-[10px] text-right text-white focus:ring-1 focus:ring-indigo-500"
              />
              <div className="flex space-x-0.5">
                <button
                  onClick={() => addRow(index)}
                  className="px-1 py-0.5 bg-slate-600 hover:bg-indigo-600 rounded text-[10px] text-white font-bold"
                >
                  +
                </button>
                <button
                  onClick={() => removeRow(index)}
                  className="px-1 py-0.5 bg-slate-600 hover:bg-red-600 rounded text-[10px] text-white font-bold"
                >
                  -
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };


  const renderCompositionSection = () => {
    const compounds = node.properties.compounds || [];
    const totalFraction = compounds.reduce((acc: number, curr: any) => acc + (curr.moleFraction || 0), 0);
    const isTotalValid = Math.abs(totalFraction - 1.0) < 0.01;

    const updateRow = (index: number, field: string, value: any) => {
      const newData = [...compounds];
      newData[index] = { ...newData[index], [field]: value };
      onNodeUpdate({
        ...node,
        properties: { ...node.properties, compounds: newData }
      });
    };

    const addRow = (index: number) => {
      const newData = [...compounds];
      newData.splice(index + 1, 0, { name: '', moleFraction: 0 });
      onNodeUpdate({
        ...node,
        properties: { ...node.properties, compounds: newData }
      });
    };

    const removeRow = (index: number) => {
      const newData = compounds.filter((_, i) => i !== index);
      onNodeUpdate({
        ...node,
        properties: { ...node.properties, compounds: newData }
      });
    };

    return (
        <div className="mt-4 border-t border-slate-700/50 pt-4">
            <h4 className="text-sm font-semibold text-gray-300 mb-2">Composition</h4>

            <div className="space-y-2 mb-3">
                {compounds.length === 0 && (
                    <button
                      onClick={() => addRow(-1)}
                      className="w-full py-2 bg-slate-700 hover:bg-slate-600 border border-slate-600 rounded text-xs text-gray-300 transition-colors"
                    >
                      + Add First Compound
                    </button>
                )}
                {compounds.map((comp: any, index: number) => (
                    <div key={index} className="flex items-center space-x-1 bg-slate-700/30 p-1 rounded">
                        <SearchableCompoundSelect
                            value={comp.name}
                            onChange={(val) => updateRow(index, 'name', val)}
                            chemicals={chemicals}
                        />
                        <input
                            type="number"
                            step="0.01"
                            min="0"
                            max="1"
                            value={comp.moleFraction}
                            onChange={(e) => updateRow(index, 'moleFraction', parseFloat(e.target.value) || 0)}
                            className="w-12 bg-slate-800 border border-slate-600 rounded px-1 py-1 text-[10px] text-right text-white focus:ring-1 focus:ring-indigo-500"
                        />
                        <div className="flex space-x-0.5">
                            <button
                                onClick={() => addRow(index)}
                                className="px-1 py-0.5 bg-slate-600 hover:bg-indigo-600 rounded text-[10px] text-white font-bold"
                            >
                                +
                            </button>
                            <button
                                onClick={() => removeRow(index)}
                                className="px-1 py-0.5 bg-slate-600 hover:bg-red-600 rounded text-[10px] text-white font-bold"
                            >
                                -
                            </button>
                        </div>
                    </div>
                ))}
            </div>

            {compounds.length > 0 && (
                <div className="flex justify-between text-xs mb-3 px-2">
                    <span className="text-gray-400">Total Fraction:</span>
                    <span className={isTotalValid ? "text-green-400 font-bold" : "text-red-400 font-bold"}>
                        {totalFraction.toFixed(3)}
                    </span>
                </div>
            )}
        </div>
    );
  };


  const renderParameters = () => {
    const { type, properties = {} } = node;
    const params: React.ReactElement[] = [];

    switch(type) {
        case EquipmentType.Feed:
            params.push(<PropertyInput key="temp" label="Temperature" name="temperature" unit="K" value={properties.temperature ?? 300} onChange={handlePropertyChange} />);
            params.push(<PropertyInput key="press" label="Pressure" name="pressure" unit="Pa" value={properties.pressure ?? 1} onChange={handlePropertyChange} />);
            params.push(<PropertyInput key="flow" label="Flow Rate" name="flowRate" unit="mol/s" value={properties.flowRate ?? 0} onChange={handlePropertyChange} />);
            break;
        case EquipmentType.Tank:
        case EquipmentType.Flash:
            params.push(<PropertyInput key="temp" label="Temperature" name="temperature" unit="K" value={properties.temperature ?? 300} onChange={handlePropertyChange} />);
            params.push(<PropertyInput key="press" label="Pressure" name="pressure" unit="Pa" value={properties.pressure ?? 1} onChange={handlePropertyChange} />);
            break;
        case EquipmentType.Reactor:
            params.push(<PropertyInput key="temp" label="Temperature" name="temperature" unit="K" value={properties.temperature ?? 300} onChange={handlePropertyChange} />);
            params.push(<PropertyInput key="press" label="Pressure" name="pressure" unit="Pa" value={properties.pressure ?? 1} onChange={handlePropertyChange} />);
            params.push(renderStoichiometryTable('Reactants', 'reactants'));
            params.push(renderStoichiometryTable('Products', 'products'));
            params.push(<PropertyInput key="conv" label="Conversion" name="conversion" unit="%" value={properties.conversion ?? 0} onChange={handlePropertyChange} />);
            break;
        case EquipmentType.Pump:
        case EquipmentType.Compressor:
        case EquipmentType.Expander:
            params.push(<PropertyInput key="out-press" label="Output Pressure" name="outletPressure" unit="Pa" value={properties.outletPressure ?? 2} onChange={handlePropertyChange} />);
            break;
        case EquipmentType.Heater:
        case EquipmentType.Cooler:
            params.push(<PropertyInput key="out-temp" label="Outlet Temperature" name="outletTemperature" unit="K" value={properties.outletTemperature ?? 350} onChange={handlePropertyChange} />);
            break;
        case EquipmentType.DistillationColumn:
            params.push(<PropertyInput key="stages" label="Number of Stages" name="stages" value={properties.stages ?? 10} onChange={handlePropertyChange} />);
            params.push(
                <div key="condenser">
                    <label htmlFor="condenserType" className="text-xs text-gray-400 block mb-1">Condenser Type</label>
                    <select id="condenserType" name="condenserType" value={properties.condenserType ?? 'Total'} onChange={handlePropertyChange} className="w-full bg-slate-700 border border-slate-600 rounded-md px-3 py-1.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500">
                        <option>Total</option>
                        <option>Partial</option>
                    </select>
                </div>
            );
            params.push(<PropertyInput key="dist-press" label="Pressure" name="pressure" unit="Pa" value={properties.pressure ?? 1} onChange={handlePropertyChange} />);
            params.push(<PropertyInput key="dist-temp" label="Temperature" name="temperature" unit="K" value={properties.temperature ?? 373} onChange={handlePropertyChange} />);
            params.push(<PropertyInput key="reflux" label="Reflux Ratio" name="refluxRatio" value={properties.refluxRatio ?? 2.5} onChange={handlePropertyChange} />);
            break;
    }

    // Always render parameters if available, or if it's a Feed, render composition too

    return (
        <div>
            {params.length > 0 && (
                 <div className="mb-4">
                    <h4 className="text-sm font-semibold text-gray-300 mb-2">Parameters</h4>
                    <div className="space-y-3">{params}</div>
                </div>
            )}

            {type === EquipmentType.Feed && renderCompositionSection()}
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

        {/* Parameters & Composition */}
        <div className="flex-1 overflow-y-auto">
             {renderParameters()}
        </div>

        {/* Connections */}
        <div className="space-y-4 pt-2 border-t border-slate-700/50">
            {(() => {
                const config = PORT_CONFIG[node.type];
                if (!config) {
                    // Generic Connection UI
                    return (
                        <>
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
                                        <select
                                            value={selectedInputToAdd}
                                            onChange={handleAddInput}
                                            className="mt-2 w-full bg-slate-700 border border-slate-600 rounded-md px-3 py-1.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                                        >
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
                                        <select
                                            value={selectedOutputToAdd}
                                            onChange={handleAddOutput}
                                            className="mt-2 w-full bg-slate-700 border border-slate-600 rounded-md px-3 py-1.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                                        >
                                            <option value="">Add Output To...</option>
                                            {availableOutputNodes.map(n => (
                                                <option key={n.id} value={n.id}>{n.name}</option>
                                            ))}
                                        </select>
                                    )}
                                </div>
                            )}
                        </>
                    );
                }

                // Specialized Connection UI
                return (
                    <>
                        <div>
                            <h4 className="text-sm font-semibold text-gray-300 mb-2">Inputs</h4>
                            <div className="space-y-3">
                                {config.inputs.map(port => {
                                    const edge = inputs.find(e => e.port === port);
                                    return (
                                        <div key={port} className="space-y-1">
                                            <label className="text-[10px] uppercase tracking-wider text-gray-500 font-bold px-1">{port}</label>
                                            <div className="flex items-center justify-between bg-slate-700/50 p-2 rounded-md">
                                                {edge ? (
                                                    <>
                                                        <span className="text-sm">{getNodeName(edge.from)}</span>
                                                        <button onClick={() => onRemoveEdge(edge.id)} className="text-gray-400 hover:text-red-400">
                                                            <TrashIcon className="w-4 h-4" />
                                                        </button>
                                                    </>
                                                ) : (
                                                    <select
                                                        onChange={(e) => {
                                                            const fromId = e.target.value;
                                                            if (fromId) onAddEdge(fromId, node.id, port);
                                                        }}
                                                        className="w-full bg-slate-800 border border-slate-600 rounded px-2 py-1 text-xs text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
                                                    >
                                                        <option value="">Select Node...</option>
                                                        {availableInputNodes.map(n => (
                                                            <option key={n.id} value={n.id}>{n.name}</option>
                                                        ))}
                                                    </select>
                                                )}
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                        <div>
                            <h4 className="text-sm font-semibold text-gray-300 mb-2">Outputs</h4>
                            <div className="space-y-3">
                                {config.outputs.map(port => {
                                    const edge = outputs.find(e => e.port === port);
                                    return (
                                        <div key={port} className="space-y-1">
                                            <label className="text-[10px] uppercase tracking-wider text-gray-500 font-bold px-1">{port}</label>
                                            <div className="flex items-center justify-between bg-slate-700/50 p-2 rounded-md">
                                                {edge ? (
                                                    <>
                                                        <span className="text-sm">{getNodeName(edge.to)}</span>
                                                        <button onClick={() => onRemoveEdge(edge.id)} className="text-gray-400 hover:text-red-400">
                                                            <TrashIcon className="w-4 h-4" />
                                                        </button>
                                                    </>
                                                ) : (
                                                    <select
                                                        onChange={(e) => {
                                                            const toId = e.target.value;
                                                            if (toId) onAddEdge(node.id, toId, port);
                                                        }}
                                                        className="w-full bg-slate-800 border border-slate-600 rounded px-2 py-1 text-xs text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
                                                    >
                                                        <option value="">Select Node...</option>
                                                        {availableOutputNodes.map(n => (
                                                            <option key={n.id} value={n.id}>{n.name}</option>
                                                        ))}
                                                    </select>
                                                )}
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    </>
                );
            })()}
        </div>
    </div>
  );
};

export default PropertiesPanel;
