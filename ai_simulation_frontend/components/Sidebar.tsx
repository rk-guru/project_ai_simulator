import React, { useState } from 'react';
import { Project } from '../types';
import PlusIcon from './icons/PlusIcon';
import Modal from './Modal';
import SettingsIcon from './icons/SettingsIcon';
import TrashIcon from './icons/TrashIcon';

interface SidebarProps {
  projects: Project[];
  activeProjectId: string;
  setActiveProjectId: (id: string) => void;
  createNewProject: () => void;
  deleteProject: (id: string) => void;
  openSettings: () => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({ projects, activeProjectId, setActiveProjectId, createNewProject, deleteProject, openSettings, isCollapsed, onToggleCollapse }) => {
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [projectToDelete, setProjectToDelete] = useState<Project | null>(null);

  const handleDeleteClick = (e: React.MouseEvent, project: Project) => {
    e.stopPropagation();
    setProjectToDelete(project);
    setDeleteModalOpen(true);
  };

  const confirmDelete = () => {
    if (projectToDelete) {
      deleteProject(projectToDelete.id);
      setDeleteModalOpen(false);
      setProjectToDelete(null);
    }
  };

  return (
    <div className={`${isCollapsed ? 'w-16' : 'w-64'} bg-slate-800/50 border-r border-slate-700 flex flex-col p-4 transition-all duration-300 ease-in-out relative`}>
      <button
        onClick={createNewProject}
        className={`flex items-center justify-center ${isCollapsed ? 'w-10 px-0' : 'w-full px-4'} py-2 mb-6 text-sm font-semibold text-white bg-indigo-600 rounded-md hover:bg-indigo-500 transition-colors`}
        title={isCollapsed ? 'Create New Project' : ''}
      >
        <PlusIcon className="w-5 h-5" />
        {!isCollapsed && <span className="ml-2">Create New Project</span>}
      </button>

      {!isCollapsed && <h2 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">Saved Projects</h2>}
      <ul className="flex flex-col space-y-1">
        {projects.map((project) => (
          <li key={project.id} className="group flex items-center space-x-2">
            <button
              onClick={() => setActiveProjectId(project.id)}
              className={`flex-1 text-left px-3 py-2 text-sm rounded-md transition-colors truncate ${
                activeProjectId === project.id
                  ? 'bg-indigo-500/50 text-white'
                  : 'text-gray-300 hover:bg-slate-700'
              } ${isCollapsed ? 'justify-center text-center px-0' : ''}`}
              title={isCollapsed ? project.name : ''}
            >
              {!isCollapsed ? project.name : <div className="w-2 h-2 rounded-full bg-gray-400" />}
            </button>
            {!isCollapsed && (
              <button
                  onClick={(e) => handleDeleteClick(e, project)}
                  className="p-2 text-gray-400 hover:text-red-400 hover:bg-slate-700 rounded-md opacity-0 group-hover:opacity-100 transition-all"
                  aria-label="Delete project"
              >
                  <TrashIcon className="w-4 h-4" />
              </button>
            )}
          </li>
        ))}
      </ul>
      <button
        onClick={openSettings}
        className={`mt-auto flex items-center ${isCollapsed ? 'justify-center px-0' : 'justify-start w-full px-4'} py-2 text-sm font-semibold text-gray-300 border border-transparent rounded-md hover:border-gray-400 hover:bg-slate-700 hover:text-white focus:outline-none focus:ring-2 focus:ring-gray-400 active:border-gray-400 transition-all`}
        title={isCollapsed ? 'Settings' : ''}
      >
        <SettingsIcon className="w-5 h-5" />
        {!isCollapsed && <span className="ml-2">Settings</span>}
      </button>

      <button
        onClick={onToggleCollapse}
        className="absolute -right-3 top-1/2 -translate-y-1/2 w-6 h-6 bg-slate-700 border border-slate-600 rounded-full flex items-center justify-center text-gray-400 hover:text-white z-10 cursor-pointer"
      >
        {isCollapsed ? '→' : '←'}
      </button>

      {deleteModalOpen && (
        <Modal
          title="Delete Project"
          confirmLabel="Delete"
          onConfirm={confirmDelete}
          onClose={() => setDeleteModalOpen(false)}
        >
          <p className="text-sm text-gray-300">
            Are you sure you want to delete "{projectToDelete?.name}"? This action cannot be undone.
          </p>
        </Modal>
      )}
    </div>
  );
};

export default Sidebar;
