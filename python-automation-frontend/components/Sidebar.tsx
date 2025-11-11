
import React from 'react';
import { type Project } from '../types';
import { PlusIcon } from './Icons';

interface SidebarProps {
  projects: Project[];
  activeProjectId: string | null;
  onSelectProject: (id: string | null) => void;
  onCreateNewProject: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  projects,
  activeProjectId,
  onSelectProject,
  onCreateNewProject,
}) => {
  return (
    <aside className="w-64 bg-gray-800 flex flex-col border-r border-gray-700">
      <div className="p-4 border-b border-gray-700">
        <button
          onClick={onCreateNewProject}
          className="w-full flex items-center justify-center bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-2 px-4 rounded-lg transition-colors duration-200"
        >
          <PlusIcon className="h-5 w-5 mr-2" />
          Create New Project
        </button>
      </div>
      <nav className="flex-1 overflow-y-auto">
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider p-4">
          Saved Projects
        </h2>
        <ul>
          {projects.map((project) => (
            <li key={project.id} className="px-2">
              <a
                href="#"
                onClick={(e) => {
                  e.preventDefault();
                  onSelectProject(project.id);
                }}
                className={`block px-4 py-2 rounded-md text-sm font-medium transition-colors duration-150 ${
                  activeProjectId === project.id
                    ? 'bg-indigo-500 text-white'
                    : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                }`}
              >
                {project.name}
              </a>
            </li>
          ))}
        </ul>
      </nav>
    </aside>
  );
};
