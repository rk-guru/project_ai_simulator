import React from 'react';

interface ResultTableProps {
  data: any[];
}

const statusColor = (status: string) => {
  switch (status) {
    case 'Nominal': return 'bg-blue-500/20 text-blue-300';
    case 'Warning': return 'bg-yellow-500/20 text-yellow-300';
    case 'Excellent': return 'bg-green-500/20 text-green-300';
    case 'High': return 'bg-red-500/20 text-red-300';
    case 'Low': return 'bg-orange-500/20 text-orange-300';
    default: return 'bg-gray-500/20 text-gray-300';
  }
};

const ResultTable: React.FC<ResultTableProps> = ({ data }) => {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-gray-400">
        <p>No simulation results available. Run a simulation to see results.</p>
      </div>
    );
  }

  // Detect if data is DataFrame-like (array of objects with arbitrary keys)
  const isDataFrame = data.length > 0 && typeof data[0] === 'object';
  
  if (isDataFrame) {
    const columns = Object.keys(data[0]);
    
    return (
      <div className="h-full p-6 overflow-auto">
        <div className="bg-slate-800 rounded-lg shadow-xl overflow-hidden">
          <div className="overflow-x-auto max-h-[calc(100vh-250px)] overflow-y-auto">
            <table className="w-full text-left">
              <thead className="bg-slate-700 sticky top-0 z-10">
                <tr>
                  {columns.map((col, idx) => (
                    <th key={idx} className="px-6 py-3 text-xs font-medium text-gray-300 uppercase tracking-wider border-b border-slate-600">
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700">
                {data.map((row, rowIdx) => (
                  <tr key={rowIdx} className="hover:bg-slate-700/50 transition-colors">
                    {columns.map((col, colIdx) => (
                      <td key={colIdx} className="px-6 py-4 text-sm text-gray-300 whitespace-nowrap">
                        {row[col] !== null && row[col] !== undefined ? String(row[col]) : '-'}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    );
  }

  // Standard simulation results format
  return (
    <div className="h-full p-6 overflow-auto">
      <div className="bg-slate-800 rounded-lg shadow-xl overflow-hidden">
        <div className="overflow-x-auto max-h-[calc(100vh-250px)] overflow-y-auto">
          <table className="w-full text-left">
            <thead className="bg-slate-700 sticky top-0 z-10">
              <tr>
                <th className="px-6 py-3 text-xs font-medium text-gray-300 uppercase tracking-wider border-b border-slate-600">
                  Parameter
                </th>
                <th className="px-6 py-3 text-xs font-medium text-gray-300 uppercase tracking-wider border-b border-slate-600">
                  Value
                </th>
                <th className="px-6 py-3 text-xs font-medium text-gray-300 uppercase tracking-wider border-b border-slate-600">
                  Status
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700">
              {data.map((row, idx) => (
                <tr key={row.id || idx} className="hover:bg-slate-700/50 transition-colors">
                  <td className="px-6 py-4 text-sm font-medium text-white whitespace-nowrap">
                    {row.parameter}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-300 whitespace-nowrap">
                    {row.value}
                  </td>
                  <td className="px-6 py-4 text-sm whitespace-nowrap">
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${statusColor(row.status)}`}>
                      {row.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default ResultTable;
