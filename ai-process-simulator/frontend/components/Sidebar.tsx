
import React from 'react';
import { Project } from '../types';
import PlusIcon from './icons/PlusIcon';

interface SidebarProps {
  projects: Project[];
  activeProjectId: string;
  setActiveProjectId: (id: string) => void;
  createNewProject: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({ projects, activeProjectId, setActiveProjectId, createNewProject }) => {
  return (
    <div className="w-64 bg-slate-800/50 border-r border-slate-700 flex flex-col p-4">
      <button
        onClick={createNewProject}
        className="flex items-center justify-center w-full px-4 py-2 mb-6 text-sm font-semibold text-white bg-indigo-600 rounded-md hover:bg-indigo-500 transition-colors"
      >
        <PlusIcon className="w-5 h-5 mr-2" />
        Create New Project
      </button>

      <h2 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">Saved Projects</h2>
      <ul className="flex flex-col space-y-1">
        {projects.map((project) => (
          <li key={project.id}>
            <button
              onClick={() => setActiveProjectId(project.id)}
              className={`w-full text-left px-3 py-2 text-sm rounded-md transition-colors ${
                activeProjectId === project.id
                  ? 'bg-indigo-500/50 text-white'
                  : 'text-gray-300 hover:bg-slate-700'
              }`}
            >
              {project.name}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default Sidebar;
