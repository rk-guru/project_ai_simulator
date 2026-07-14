import { Project } from '../types';

const API_URL = 'http://localhost:8000';
const LOCAL_STORAGE_KEY = 'ai_process_sim_projects';
const API_TIMEOUT_MS = 3000;

// Helper to safe-read local storage
const getLocalProjects = (): Project[] => {
    try {
        const stored = localStorage.getItem(LOCAL_STORAGE_KEY);
        if (!stored) return [];
        const parsed = JSON.parse(stored);
        return Array.isArray(parsed) ? parsed : [];
    } catch (error) {
        console.error("Failed to read local storage:", error);
        return [];
    }
};

const saveLocalProjects = (projects: Project[]) => {
    try {
        localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(projects));
    } catch (error) {
        console.error("Failed to save to local storage:", error);
    }
};

const fetchWithTimeout = async (url: string, options: RequestInit = {}) => {
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), API_TIMEOUT_MS);
    try {
        const response = await fetch(url, {
            ...options,
            signal: controller.signal
        });
        clearTimeout(id);
        return response;
    } catch (error) {
        clearTimeout(id);
        throw error;
    }
};

export const dbService = {
  async getAllProjects(): Promise<Project[]> {
    try {
        const response = await fetchWithTimeout(`${API_URL}/projects`);
        if (!response.ok) throw new Error("API Error");
        const projects = await response.json();
        saveLocalProjects(projects);
        return projects;
    } catch (error) {
        return getLocalProjects();
    }
  },

  async saveProject(project: Project): Promise<void> {
    // Local save first
    const projects = getLocalProjects();
    const index = projects.findIndex(p => p.id === project.id);
    if (index >= 0) projects[index] = project;
    else projects.push(project);
    saveLocalProjects(projects);

    // API save
    try {
        await fetchWithTimeout(`${API_URL}/projects/${project.id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(project),
        });
    } catch (e) {
        console.warn("API Save failed, data saved locally.");
    }
  },

  async deleteProject(id: string): Promise<void> {
    // Local delete
    const projects = getLocalProjects();
    const filtered = projects.filter(p => p.id !== id);
    saveLocalProjects(filtered);

    // API delete
    try {
        await fetchWithTimeout(`${API_URL}/projects/${id}`, { method: 'DELETE' });
    } catch (e) {
        console.warn("API Delete failed");
    }
  },
  
  async getChemicals(): Promise<string[]> {
      try {
          const response = await fetchWithTimeout(`${API_URL}/chemicals`);
          if (response.ok) return await response.json();
      } catch (e) {}
      return ["Water", "Ethanol", "Methanol", "Oxygen", "Nitrogen", "Carbon Dioxide", "Hydrogen"];
  },

  async uploadFile(projectId: string, file: File): Promise<string> {
      const formData = new FormData();
      formData.append('file', file);
      
      try {
          const response = await fetch(`${API_URL}/projects/${projectId}/upload`, {
              method: 'POST',
              body: formData
          });
          if (!response.ok) throw new Error("Upload failed");
          const data = await response.json();
          return data.filename;
      } catch (e) {
          console.error(e);
          throw e;
      }
  },

  async runSimulation(projectId: string, project: Project): Promise<any[]> {
      try {
          // We send the full project state to be simulated
          const response = await fetch(`${API_URL}/projects/${projectId}/run`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(project)
          });
          if (!response.ok) throw new Error("Simulation failed");
          return await response.json();
      } catch (e) {
          console.error("Backend run failed, fallback not implemented for generic results", e);
          return [{ Error: "Backend not reachable for simulation" }];
      }
  }
};
