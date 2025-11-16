
import React, { useState, useCallback } from 'react';
import { Sidebar } from './components/Sidebar';
import { MainContent } from './components/MainContent';
import { type Project, type Step } from './types';

const initialProjects: Project[] = [
  {
    id: 'proj-1',
    name: 'Login Test',
    url: 'https://example.com/login',
    steps: [
      { id: 'step-1-1', command: 'TYPE #username testuser' },
      { id: 'step-1-2', command: 'TYPE #password password123' },
      { id: 'step-1-3', command: 'CLICK button[type="submit"]' },
    ],
  },
  {
    id: 'proj-2',
    name: 'Search for Kittens',
    url: 'https://google.com',
    steps: [
      { id: 'step-2-1', command: 'TYPE textarea[name="q"] cute kittens' },
      { id: 'step-2-2', command: 'CLICK input[name="btnK"]' },
    ],
  },
];

const App: React.FC = () => {
  const [projects, setProjects] = useState<Project[]>(initialProjects);
  const [activeProject, setActiveProject] = useState<Project | null>(initialProjects[0]);
  const [runResult, setRunResult] = useState<string>('');

  const handleSelectProject = useCallback((projectId: string | null) => {
    setRunResult('');
    if (projectId === null) {
      setActiveProject(null);
      return;
    }
    const project = projects.find(p => p.id === projectId);
    setActiveProject(project || null);
  }, [projects]);

  const handleCreateNewProject = useCallback(() => {
    setRunResult('');
    const newProject: Project = {
      id: `proj-${Date.now()}`,
      name: 'New Project',
      url: '',
      steps: [],
    };
    setProjects(prev => [...prev, newProject]);
    setActiveProject(newProject);
  }, []);

  const updateActiveProject = useCallback((updatedProject: Project) => {
    setActiveProject(updatedProject);
    setProjects(prevProjects => 
      prevProjects.map(p => p.id === updatedProject.id ? updatedProject : p)
    );
  }, []);
  
  const handleSave = () => {
    if (activeProject) {
      console.log('Saving project:', activeProject);
      // Here you would typically make an API call to a Python backend
      alert(`Project "${activeProject.name}" saved!`);
    }
  };

  const handleRun = () => {
    if (activeProject) {
      console.log('Running project:', activeProject);
      const resultText = `--- Running Project: ${activeProject.name} ---\n\n` +
                         `Target URL: ${activeProject.url}\n\n` +
                         `Steps Executed:\n` +
                         `${activeProject.steps.map((step, i) => `  ${i + 1}. ${step.command}`).join('\n')}\n\n` +
                         `--- Run Complete ---`;
      setRunResult(resultText);
      alert(`Running project "${activeProject.name}"! Check the result panel.`);
    }
  };

  return (
    <div className="flex h-screen bg-gray-900 text-gray-200 font-sans">
      <Sidebar
        projects={projects}
        activeProjectId={activeProject?.id || null}
        onSelectProject={handleSelectProject}
        onCreateNewProject={handleCreateNewProject}
      />
      <MainContent
        project={activeProject}
        onUpdateProject={updateActiveProject}
        onSave={handleSave}
        onRun={handleRun}
        runResult={runResult}
      />
    </div>
  );
};

export default App;