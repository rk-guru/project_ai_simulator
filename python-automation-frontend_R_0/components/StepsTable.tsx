import React from 'react';
import { type Step } from '../types';
import { PlusIcon, TrashIcon } from './Icons';

interface StepsTableProps {
  steps: Step[];
  onStepsChange: (steps: Step[]) => void;
}

export const StepsTable: React.FC<StepsTableProps> = ({ steps, onStepsChange }) => {
  const handleAddStep = () => {
    const newStep: Step = {
      id: `step-${Date.now()}`,
      command: '',
    };
    onStepsChange([...steps, newStep]);
  };

  const handleUpdateStep = (index: number, newCommand: string) => {
    const newSteps = steps.map((step, i) =>
      i === index ? { ...step, command: newCommand } : step
    );
    onStepsChange(newSteps);
  };

  const handleDeleteStep = (index: number) => {
    const newSteps = steps.filter((_, i) => i !== index);
    onStepsChange(newSteps);
  };

  return (
    <div className="bg-gray-800 rounded-lg overflow-hidden shadow-lg">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-700">
          <thead className="bg-gray-700/50">
            <tr>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Command</th>
              <th scope="col" className="relative px-6 py-3">
                <span className="sr-only">Delete</span>
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700">
            {steps.map((step, index) => (
              <tr key={step.id} className="hover:bg-gray-700/30">
                <td className="w-full">
                  <input
                    type="text"
                    value={step.command}
                    onChange={(e) => handleUpdateStep(index, e.target.value)}
                    placeholder="e.g., CLICK #submit-button"
                    className="w-full bg-transparent px-6 py-4 text-sm text-gray-200 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-indigo-500"
                  />
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                  <button onClick={() => handleDeleteStep(index)} className="text-red-400 hover:text-red-600 transition-colors">
                    <TrashIcon className="h-5 w-5" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="p-4 bg-gray-800 border-t border-gray-700">
        <button
          onClick={handleAddStep}
          className="flex items-center text-sm font-medium text-indigo-400 hover:text-indigo-300"
        >
          <PlusIcon className="h-5 w-5 mr-2" />
          Add Step
        </button>
      </div>
    </div>
  );
};