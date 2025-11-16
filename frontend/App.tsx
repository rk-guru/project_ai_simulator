
import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import MainContent from './components/MainContent';
import { Project } from './types';

const App: React.FC = () => {
  const [projects, setProjects] = useState<Project[]>([
    { id: '1', name: 'demo_app' },
    { id: '2', name: 'Search for kittens' },
    { id: '3', name: 'New Project' },
  ]);
  const [activeProjectId, setActiveProjectId] = useState<string>('3');

  const activeProject = projects.find(p => p.id === activeProjectId);

  const createNewProject = () => {
    const newId = String(Date.now());
    const newProject: Project = {
      id: newId,
      name: `New Project ${projects.length}`,
    };
    setProjects(prev => [...prev, newProject]);
    setActiveProjectId(newId);
  };

  return (
    <div className="flex h-screen bg-slate-900 text-gray-200 font-sans">
      <Sidebar
        projects={projects}
        activeProjectId={activeProjectId}
        setActiveProjectId={setActiveProjectId}
        createNewProject={createNewProject}
      />
      {activeProject ? (
        <MainContent key={activeProject.id} project={activeProject} />
      ) : (
        <div className="flex-1 flex items-center justify-center">
            <p>Select a project or create a new one to start.</p>
        </div>
      )}
    </div>
  );
};

export default App;
