import React, { useState, useEffect } from 'react';
import { getSimulationResults } from '../services/api';

interface SimulationResult {
  id: number;
  parameter: string;
  value: string;
  status: string;
}

interface ResultTableProps {
  simulationId?: string | null;
}

const ResultTable: React.FC<ResultTableProps> = ({ simulationId }) => {
  const [data, setData] = useState<SimulationResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (simulationId) {
      fetchResults();
    }
  }, [simulationId]);

  const fetchResults = async () => {
    if (!simulationId) return;

    try {
      setLoading(true);
      setError(null);
      const results = await getSimulationResults(simulationId);
      setData(results);
    } catch (err: any) {
      console.error('Error fetching results:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to fetch results');
    } finally {
      setLoading(false);
    }
  };

  const statusColor = (status: string) => {
    switch (status) {
      case 'Nominal':
        return 'bg-blue-500/20 text-blue-300';
      case 'Warning':
        return 'bg-yellow-500/20 text-yellow-300';
      case 'Excellent':
        return 'bg-green-500/20 text-green-300';
      case 'High':
        return 'bg-red-500/20 text-red-300';
      case 'Critical':
        return 'bg-red-600/30 text-red-200';
      case 'Low':
        return 'bg-orange-500/20 text-orange-300';
      default:
        return 'bg-gray-500/20 text-gray-300';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'Nominal':
        return '✓';
      case 'Warning':
        return '⚠';
      case 'Excellent':
        return '★';
      case 'High':
      case 'Critical':
        return '!';
      case 'Low':
        return '↓';
      default:
        return '•';
    }
  };

  // Show loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center h-full bg-slate-900">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-500"></div>
          <p className="mt-4 text-gray-400">Loading simulation results...</p>
        </div>
      </div>
    );
  }

  // Show error state
  if (error) {
    return (
      <div className="flex items-center justify-center h-full bg-slate-900">
        <div className="text-center max-w-md">
          <div className="text-red-400 text-5xl mb-4">⚠</div>
          <h3 className="text-xl font-semibold text-white mb-2">Error Loading Results</h3>
          <p className="text-gray-400 mb-4">{error}</p>
          <button
            onClick={fetchResults}
            className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  // Show empty state
  if (!simulationId || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-full bg-slate-900">
        <div className="text-center max-w-md">
          <div className="text-gray-600 text-5xl mb-4">📊</div>
          <h3 className="text-xl font-semibold text-white mb-2">No Results Yet</h3>
          <p className="text-gray-400">
            Run a simulation to see the results here. Click the "Run" button to start.
          </p>
        </div>
      </div>
    );
  }

  // Show results table
  return (
    <div className="h-full bg-slate-900 overflow-auto">
      <div className="p-6">
        <div className="mb-6">
          <h2 className="text-2xl font-bold text-white mb-2">Simulation Results</h2>
          <p className="text-gray-400 text-sm">
            Simulation ID: <span className="font-mono text-indigo-400">{simulationId}</span>
          </p>
          <p className="text-gray-400 text-sm">
            Total Parameters: <span className="text-white font-medium">{data.length}</span>
          </p>
        </div>

        <div className="overflow-x-auto rounded-lg border border-slate-700">
          <table className="w-full">
            <thead>
              <tr className="bg-slate-800 border-b border-slate-700">
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                  #
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                  Parameter
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                  Value
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                  Status
                </th>
              </tr>
            </thead>
            <tbody className="bg-slate-900 divide-y divide-slate-800">
              {data.map((row, index) => (
                <tr
                  key={row.id}
                  className="hover:bg-slate-800/50 transition-colors"
                >
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-400">
                    {index + 1}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-white">
                    {row.parameter}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300 font-mono">
                    {row.value}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <span
                      className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium ${statusColor(
                        row.status
                      )}`}
                    >
                      <span>{getStatusIcon(row.status)}</span>
                      {row.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Summary Statistics */}
        <div className="mt-6 grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
            <div className="text-xs text-gray-400 uppercase">Excellent</div>
            <div className="text-2xl font-bold text-green-400 mt-1">
              {data.filter((r) => r.status === 'Excellent').length}
            </div>
          </div>
          <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
            <div className="text-xs text-gray-400 uppercase">Nominal</div>
            <div className="text-2xl font-bold text-blue-400 mt-1">
              {data.filter((r) => r.status === 'Nominal').length}
            </div>
          </div>
          <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
            <div className="text-xs text-gray-400 uppercase">Warning</div>
            <div className="text-2xl font-bold text-yellow-400 mt-1">
              {data.filter((r) => r.status === 'Warning').length}
            </div>
          </div>
          <div className="bg-slate-800 rounded-lg p-4 border border-slate-700">
            <div className="text-xs text-gray-400 uppercase">High/Critical</div>
            <div className="text-2xl font-bold text-red-400 mt-1">
              {data.filter((r) => r.status === 'High' || r.status === 'Critical').length}
            </div>
          </div>
        </div>

        {/* Export Button */}
        <div className="mt-6 flex justify-end">
          <button
            onClick={() => {
              const csv = [
                ['#', 'Parameter', 'Value', 'Status'],
                ...data.map((row, idx) => [idx + 1, row.parameter, row.value, row.status]),
              ]
                .map((row) => row.join(','))
                .join('\n');
              const blob = new Blob([csv], { type: 'text/csv' });
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = `simulation_results_${simulationId}.csv`;
              a.click();
            }}
            className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 transition-colors flex items-center gap-2"
          >
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
              />
            </svg>
            Export CSV
          </button>
        </div>
      </div>
    </div>
  );
};

export default ResultTable;
