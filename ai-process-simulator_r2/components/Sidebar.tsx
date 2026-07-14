import React from 'react';
import { Project } from '../types';
import PlusIcon from './icons/PlusIcon';
import TrashIcon from './icons/TrashIcon';
import { dbService } from '../services/db';

interface SidebarProps {
  projects: Project[];
  activeProjectId: string;
  setActiveProjectId: (id: string) => void;
  createNewProject: () => void;
  deleteProject: (id: string) => void;
}

const Sidebar: React.FC<SidebarProps> = ({ 
  projects, 
  activeProjectId, 
  setActiveProjectId, 
  createNewProject, 
  deleteProject 
}) => {
  
  const handleDeleteProject = async (e: React.MouseEvent, projectId: string, projectName: string) => {
    e.stopPropagation();
    
    if (window.confirm(`Are you sure you want to delete "${projectName}"? This will delete all associated data and files.`)) {
      try {
        await dbService.deleteProject(projectId);
        deleteProject(projectId);
      } catch (error) {
        console.error('Error deleting project:', error);
        alert('Failed to delete project');
      }
    }
  };

  return (
    <div className="w-64 bg-slate-800 border-r border-slate-700 flex flex-col h-screen">
      <div className="p-4 border-b border-slate-700">
        <button
          onClick={createNewProject}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-md transition-colors font-medium"
        >
          <PlusIcon />
          Create New Project
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
          Saved Projects
        </h2>
        <div className="space-y-2">
          {projects.map((project) => (
            <div
              key={project.id}
              className={`flex items-center gap-2 rounded-md overflow-hidden ${
                activeProjectId === project.id ? 'bg-indigo-500/20 ring-1 ring-indigo-500' : ''
              }`}
            >
              <button
                onClick={() => setActiveProjectId(project.id)}
                className={`flex-1 text-left px-3 py-2 text-sm rounded-md transition-colors truncate ${
                  activeProjectId === project.id
                    ? 'bg-indigo-500/50 text-white'
                    : 'text-gray-300 hover:bg-slate-700'
                }`}
              >
                {project.name}
              </button>
              <button
                onClick={(e) => handleDeleteProject(e, project.id, project.name)}
                className="p-2 text-gray-400 hover:text-red-400 hover:bg-slate-700 rounded-md transition-all"
                aria-label="Delete project"
              >
                <TrashIcon />
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Sidebar;
