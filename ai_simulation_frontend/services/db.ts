import { Project } from '../types';

const API_URL = 'http://localhost:8000';
const API_TIMEOUT_MS = 3000;

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
    const response = await fetchWithTimeout(`${API_URL}/projects`);
    if (!response.ok) throw new Error("API Error");
    return await response.json();
  },

  async createProject(name: string): Promise<{id: string, name: string}> {
    const response = await fetchWithTimeout(`${API_URL}/projects`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
    });
    if (!response.ok) throw new Error("Project creation failed");
    return await response.json();
  },

  async saveProject(project: Project): Promise<void> {
    await fetchWithTimeout(`${API_URL}/projects/${project.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(project),
    });
  },

  async deleteProject(id: string): Promise<void> {
    await fetchWithTimeout(`${API_URL}/projects/${id}`, { method: 'DELETE' });
  },

  async getChemicals(): Promise<string[]> {
      const response = await fetchWithTimeout(`${API_URL}/chemicals`);
      if (!response.ok) throw new Error("Failed to fetch chemicals");
      return await response.json();
  },

  async uploadFile(projectId: string, file: File): Promise<string> {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${API_URL}/projects/${projectId}/upload`, {
          method: 'POST',
          body: formData
      });
      if (!response.ok) throw new Error("Upload failed");
      const data = await response.json();
      return data.filename;
  },

  async runSimulation(projectId: string, project: Project): Promise<any[]> {
      const response = await fetch(`${API_URL}/simulation/run`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
              projectId: projectId,
              project_data: project
          })
      });
      if (!response.ok) throw new Error("Simulation failed");
      return await response.json();
  }
};
