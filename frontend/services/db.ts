
import { Project } from '../types';

const API_URL = 'http://localhost:8000';
const LOCAL_STORAGE_KEY = 'ai_process_sim_projects';

// Helper to safely read from local storage
const getLocalProjects = (): Project[] => {
    try {
        const stored = localStorage.getItem(LOCAL_STORAGE_KEY);
        return stored ? JSON.parse(stored) : [];
    } catch (error) {
        console.error("Failed to read local storage:", error);
        return [];
    }
};

// Helper to safely write to local storage
const saveLocalProjects = (projects: Project[]) => {
    try {
        localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(projects));
    } catch (error) {
        console.error("Failed to save to local storage:", error);
    }
};

export const dbService = {
  async getAllProjects(): Promise<Project[]> {
    try {
        // Attempt to fetch from API
        const response = await fetch(`${API_URL}/projects`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const projects = await response.json();
        
        // Update local cache with fresh data from server
        saveLocalProjects(projects);
        return projects;
    } catch (error) {
        console.warn("API unavailable (getAllProjects), falling back to local storage.");
        // Fallback to local storage
        return getLocalProjects();
    }
  },

  async saveProject(project: Project): Promise<void> {
    // Always update local storage first ensures no data loss if API fails
    const projects = getLocalProjects();
    const index = projects.findIndex(p => p.id === project.id);
    if (index >= 0) {
        projects[index] = project;
    } else {
        projects.push(project);
    }
    saveLocalProjects(projects);

    // Attempt to sync with API
    try {
        const response = await fetch(`${API_URL}/projects/${project.id}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(project),
        });
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
    } catch (error) {
        console.warn("API unavailable (saveProject), data saved locally only.");
        // We suppress the error here so the UI doesn't break, effectively working in "Offline Mode"
    }
  },

  async deleteProject(id: string): Promise<void> {
    // Delete from local storage immediately
    const projects = getLocalProjects();
    const filtered = projects.filter(p => p.id !== id);
    saveLocalProjects(filtered);

    // Attempt to delete from API
    try {
        const response = await fetch(`${API_URL}/projects/${id}`, {
            method: 'DELETE',
        });
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
    } catch (error) {
        console.warn("API unavailable (deleteProject), deleted locally only.");
    }
  },
  
  async getProject(id: string): Promise<Project | undefined> {
      try {
          const response = await fetch(`${API_URL}/projects/${id}`);
          if (response.status === 404) return undefined;
          if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
          return await response.json();
      } catch (error) {
          console.warn("API unavailable (getProject), searching local storage.");
          const projects = getLocalProjects();
          return projects.find(p => p.id === id);
      }
  }
};
