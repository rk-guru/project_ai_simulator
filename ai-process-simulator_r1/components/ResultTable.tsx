
import React from 'react';
import { SimulationResult } from '../types';

interface ResultTableProps {
    data: SimulationResult[];
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
}

const ResultTable: React.FC<ResultTableProps> = ({ data }) => {
  if (!data || data.length === 0) {
      return (
          <div className="flex items-center justify-center h-full text-gray-500">
              No simulation results available.
          </div>
      )
  }

  return (
    <div className="bg-slate-800/50 rounded-lg overflow-hidden">
      <table className="w-full text-sm text-left text-gray-300">
        <thead className="text-xs text-gray-400 uppercase bg-slate-700/50">
          <tr>
            <th scope="col" className="px-6 py-3">
              Parameter
            </th>
            <th scope="col" className="px-6 py-3">
              Value
            </th>
            <th scope="col" className="px-6 py-3">
              Status
            </th>
          </tr>
        </thead>
        <tbody>
          {data.map((row) => (
            <tr key={row.id} className="bg-slate-800 border-b border-slate-700 hover:bg-slate-700/50">
              <th scope="row" className="px-6 py-4 font-medium text-white whitespace-nowrap">
                {row.parameter}
              </th>
              <td className="px-6 py-4">
                {row.value}
              </td>
              <td className="px-6 py-4">
                <span className={`px-2 py-1 text-xs font-semibold rounded-full ${statusColor(row.status)}`}>
                    {row.status}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default ResultTable;
