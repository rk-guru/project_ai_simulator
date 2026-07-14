
import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import Settings from './components/Settings';
import { Project } from './types';
import { dbService } from './services/db';

import MainContent from './components/MainContent';
const App: React.FC = () => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeProjectId, setActiveProjectId] = useState<string>('');
  const [isLoading, setIsLoading] = useState(true);
  const [showSettings, setShowSettings] = useState(false);

  // Load projects from DB on mount
  useEffect(() => {
    const loadProjects = async () => {
      try {
        const savedProjects = await dbService.getAllProjects();
        setProjects(savedProjects);
        
        // Set active project to the first one if exists, or created one
        if (savedProjects.length > 0) {
           // Try to restore last session or default to first
           setActiveProjectId(savedProjects[0].id);
        }
      } catch (error) {
        console.error("Failed to load projects from DB", error);
      } finally {
        setIsLoading(false);
      }
    };
    loadProjects();
  }, []);

  const activeProject = projects.find(p => p.id === activeProjectId);

  const createNewProject = async () => {
    const newId = String(Date.now());
    const newProject: Project = {
      id: newId,
      name: `New Project ${projects.length + 1}`,
      messages: [],
      nodes: [],
      edges: [],
      results: []
    };
    
    // Optimistic update
    setProjects(prev => [...prev, newProject]);
    setActiveProjectId(newId);

    // Save to DB
    await dbService.saveProject(newProject);
  };

  const deleteProject = async (id: string) => {
    // Optimistic update
    setProjects(prev => prev.filter(p => p.id !== id));
    if (activeProjectId === id) {
      setActiveProjectId('');
    }

    // Delete from DB
    await dbService.deleteProject(id);
  };

  const updateProject = async (id: string, data: Partial<Project>) => {
    setProjects(prev => {
      const updatedProjects = prev.map(p => {
        if (p.id === id) {
          const updatedProject = { ...p, ...data };
          // Fire and forget save to DB (or handle async separately)
          dbService.saveProject(updatedProject).catch(err => console.error("Save failed", err));
          return updatedProject;
        }
        return p;
      });
      return updatedProjects;
    });
  };

  if (isLoading) {
      return <div className="flex h-screen items-center justify-center bg-slate-900 text-white">Loading...</div>;
  }

  return (
    <div className="flex h-screen bg-slate-900 text-gray-200 font-sans">
      <Sidebar
        projects={projects}
        activeProjectId={activeProjectId}
        setActiveProjectId={setActiveProjectId}
        createNewProject={createNewProject}
        deleteProject={deleteProject}
        openSettings={() => setShowSettings(true)}
      />
            {showSettings ? (
        <Settings onBack={() => setShowSettings(false)} />
      ) : activeProject ? (
        <MainContent
          key={activeProject.id}
          project={activeProject}
          onUpdateProject={updateProject}
        />
      ) : (
        <div className="flex-1 flex items-center justify-center text-gray-500">
            <div className="text-center">
                <p className="mb-4">Select a project to view details</p>
                <button
                    onClick={createNewProject}
                    className="px-4 py-2 text-sm font-semibold text-white bg-indigo-600 rounded-md hover:bg-indigo-500 transition-colors"
                >
                    Create First Project
                </button>
            </div>
        </div>
      )}
    </div>
  );
};

export default App;
