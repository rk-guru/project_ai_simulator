
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
  const [isBackendOffline, setIsBackendOffline] = useState(false);
  const [showSettings, setShowSettings] = useState(false);

  // Load projects from DB on mount
  useEffect(() => {
    const loadProjects = async () => {
      try {
        const savedProjects = await dbService.getAllProjects();
        setProjects(savedProjects);
        setIsBackendOffline(false);

        // Set active project to the first one if exists, or created one
        if (savedProjects.length > 0) {
           // Try to restore last session or default to first
           setActiveProjectId(savedProjects[0].id);
        }
      } catch (error) {
        console.error("Failed to load projects from DB", error);
        setIsBackendOffline(true);
      } finally {
        setIsLoading(false);
      }
    };
    loadProjects();
  }, []);

  const activeProject = projects.find(p => p.id === activeProjectId);

  const createNewProject = async () => {
    try {
      const projectName = `New Project ${projects.length + 1}`;
      const projectData = await dbService.createProject(projectName);

      const newProject: Project = {
        id: projectData.id,
        name: projectData.name,
        messages: [],
        nodes: [],
        edges: [],
        results: []
      };

      setProjects(prev => [...prev, newProject]);
      setActiveProjectId(newProject.id);
    } catch (error) {
      console.error("Failed to create project", error);
      setIsBackendOffline(true);
    }
  };

  const deleteProject = async (id: string) => {
    try {
      // Optimistic update
      setProjects(prev => prev.filter(p => p.id !== id));
      if (activeProjectId === id) {
        setActiveProjectId('');
      }
      await dbService.deleteProject(id);
    } catch (error) {
      console.error("Failed to delete project", error);
      setIsBackendOffline(true);
    }
  };

  const updateProject = async (id: string, data: Partial<Project>) => {
    setProjects(prev => {
      const updatedProjects = prev.map(p => {
        if (p.id === id) {
          const updatedProject = { ...p, ...data };
          dbService.saveProject(updatedProject).catch(err => {
            console.error("Save failed", err);
            setIsBackendOffline(true);
          });
          return updatedProject;
        }
        return p;
      });
      return updatedProjects;
    });
  };

  if (isBackendOffline) {
      return (
          <div className="flex h-screen items-center justify-center bg-slate-900 text-white flex-col">
              <h1 className="text-2xl font-bold mb-4">Backend Offline</h1>
              <p className="text-gray-400 mb-6 text-center max-w-md px-4">
                  Please ensure the AI Simulation backend is running on port 8000.<br/>
                  If it is running, check your network connection.
              </p>
              <button
                  onClick={() => window.location.reload()}
                  className="px-4 py-2 bg-indigo-600 rounded-md hover:bg-indigo-500 transition-colors"
              >
                  Retry Connection
              </button>
          </div>
      );
  }

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
