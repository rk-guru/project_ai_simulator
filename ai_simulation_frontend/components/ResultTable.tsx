import React from 'react';

interface ResultTableProps {
    data: any[];
}

const PROPERTY_METADATA: Record<string, { label: string, unit?: string }> = {
    "Stream Name": { label: "Stream Name" },
    "Equipment Name": { label: "Equipment Name" },
    "Equipment": { label: "Equipment" },
    "Temperature": { label: "Temperature", unit: "K" },
    "Pressure": { label: "Pressure", unit: "Pa" },
    "Molar Flowrate": { label: "Molar Flowrate", unit: "kmol/h" },
    "Mass Flowrate": { label: "Mass Flowrate", unit: "kg/h" },
    "Vapor Fraction": { label: "Vapor Fraction", unit: "-" },
    "Total Molar Composition (Mass Fraction)": { label: "Total Molar Composition" },
    "Liquid Molar Composition": { label: "Liquid Molar Composition" },
    "Vapor Molar Composition": { label: "Vapor Molar Composition" },
    "Enthalpy": { label: "Enthalpy", unit: "kJ/kmol" },
    "Energy Change": { label: "Energy Change", unit: "kJ/h" },
};

const ResultTable: React.FC<ResultTableProps> = ({ data }) => {
  if (!data || data.length === 0) {
      return (
          <div className="flex items-center justify-center h-full text-gray-500">
              No simulation results available.
          </div>
      )
  }

  // Identify all unique components across all streams for composition sub-rows
  const allComponents = new Set<string>();
  data.forEach(row => {
      const compKeys = ["Total Molar Composition (Mass Fraction)", "Liquid Molar Composition", "Vapor Molar Composition"];
      compKeys.forEach(key => {
          if (row[key] && typeof row[key] === 'object') {
              Object.keys(row[key]).forEach(k => allComponents.add(k));
          }
      });
  });
  const componentsList = Array.from(allComponents).sort();

  const getCellClass = (header: string, value: any) => {
      if (header.toLowerCase() === 'status') {
          const valStr = String(value).toLowerCase();
          if (valStr === 'nominal' || valStr === 'active') return 'text-green-400';
          if (valStr === 'warning' || valStr === 'high' || valStr === 'low') return 'text-yellow-400';
          if (valStr === 'error' || valStr === 'critical') return 'text-red-400';
      }
      return 'text-gray-300';
  };

  return (
    <div className="h-full flex flex-col bg-slate-800/50 rounded-lg overflow-hidden border border-slate-700">
      <div className="overflow-auto flex-1 custom-scrollbar">
        <table className="w-full text-sm text-left border-collapse">
            <thead className="text-xs text-gray-400 uppercase bg-slate-700 sticky top-0 z-10">
            <tr className="border-b border-slate-600">
                <th scope="col" className="px-6 py-3 whitespace-nowrap border-r border-slate-600 bg-slate-700">
                    Property
                </th>
                {data.map((row, index) => (
                    <th key={index} scope="col" className="px-6 py-3 whitespace-nowrap">
                        {row["Stream Name"] || `Stream ${index + 1}`}
                    </th>
                ))}
            </tr>
            </thead>
            <tbody className="divide-y divide-slate-700">
            {Object.entries(PROPERTY_METADATA).map(([key, meta]) => {
                const isComposition = key.includes("Composition");

                if (!isComposition) {
                    return (
                        <tr key={key} className="bg-slate-800 border-b border-slate-700 hover:bg-slate-700/80">
                            <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-400 bg-slate-700/50 border-r border-slate-600">
                                {meta.label} {meta.unit ? `(${meta.unit})` : ''}
                            </td>
                            {data.map((row, index) => (
                                <td key={`${index}-${key}`} className={`px-6 py-4 whitespace-nowrap ${getCellClass(key, row[key])}`}>
                                    {row[key] !== null && row[key] !== undefined ? row[key] : '-'}
                                </td>
                            ))}
                        </tr>
                    );
                }

                return (
                    <React.Fragment key={key}>
                        <tr className="bg-slate-700/30 border-b border-slate-700 font-semibold text-gray-300">
                            <td className="px-6 py-2 whitespace-nowrap border-r border-slate-600 bg-slate-700/40">
                                {meta.label}
                            </td>
                            {data.map((_, index) => <td key={`group-${index}`} className="px-6 py-2 border-r border-slate-700/30"></td>)}
                        </tr>
                        {componentsList.map(comp => (
                            <tr key={`${key}-${comp}`} className="bg-slate-800 border-b border-slate-700 hover:bg-slate-700/80 text-xs">
                                <td className="px-6 py-2 whitespace-nowrap pl-10 text-gray-500 bg-slate-700/20 border-r border-slate-600">
                                    {comp}
                                </td>
                                {data.map((row, index) => {
                                    const val = row[key]?.[comp];
                                    return (
                                        <td key={`${index}-${key}-${comp}`} className={`px-6 py-2 whitespace-nowrap ${getCellClass(key, val)}`}>
                                            {val !== null && val !== undefined ? val : '-'}
                                        </td>
                                    );
                                })}
                            </tr>
                        ))}
                    </React.Fragment>
                );
            })}
            </tbody>
        </table>
      </div>
    </div>
  );
};

export default ResultTable;
