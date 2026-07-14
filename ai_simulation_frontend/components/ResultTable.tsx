
import React from 'react';

interface ResultTableProps {
    data: any[];
}

const ResultTable: React.FC<ResultTableProps> = ({ data }) => {
  if (!data || data.length === 0) {
      return (
          <div className="flex items-center justify-center h-full text-gray-500">
              No simulation results available.
          </div>
      )
  }

  // Dynamically determine columns from the first object
  const columns = Object.keys(data[0]);

  // Helper to check for specific status strings to colorize
  const getCellClass = (key: string, value: any) => {
      if (key.toLowerCase() === 'status') {
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
        <table className="w-full text-sm text-left">
            <thead className="text-xs text-gray-400 uppercase bg-slate-700 sticky top-0 z-10">
            <tr>
                {columns.map((col) => (
                    <th key={col} scope="col" className="px-6 py-3 whitespace-nowrap">
                        {col}
                    </th>
                ))}
            </tr>
            </thead>
            <tbody>
            {data.map((row, index) => (
                <tr key={index} className="bg-slate-800 border-b border-slate-700 hover:bg-slate-700/80">
                    {columns.map((col) => (
                        <td key={`${index}-${col}`} className={`px-6 py-4 whitespace-nowrap ${getCellClass(col, row[col])}`}>
                            {row[col]}
                        </td>
                    ))}
                </tr>
            ))}
            </tbody>
        </table>
      </div>
    </div>
  );
};

export default ResultTable;
