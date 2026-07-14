const API_URL = 'http://localhost:8000/api';

export interface Project {
  id: string;
  name: string;
  created_at: string;
  nodes?: any[];
  edges?: any[];
  messages?: any[];
  results?: any[];
}

export const dbService = {
  // Projects
  async createProject(name: string): Promise<Project> {
    const response = await fetch(`${API_URL}/projects`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name })
    });
    if (!response.ok) throw new Error('Failed to create project');
    return response.json();
  },

  async getAllProjects(): Promise<Project[]> {
    const response = await fetch(`${API_URL}/projects`);
    if (!response.ok) throw new Error('Failed to fetch projects');
    return response.json();
  },

  async getProject(projectId: string): Promise<Project> {
    const response = await fetch(`${API_URL}/projects/${projectId}`);
    if (!response.ok) throw new Error('Failed to fetch project');
    return response.json();
  },

  async updateProject(projectId: string, data: Partial<Project>): Promise<void> {
    const response = await fetch(`${API_URL}/projects/${projectId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!response.ok) throw new Error('Failed to update project');
  },

  async deleteProject(projectId: string): Promise<void> {
    const response = await fetch(`${API_URL}/projects/${projectId}`, {
      method: 'DELETE'
    });
    if (!response.ok) throw new Error('Failed to delete project');
  },

  // Simulation
  async runSimulation(projectId: string, nodes: any[], edges: any[]): Promise<any> {
    const response = await fetch(`${API_URL}/projects/${projectId}/simulate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ nodes, edges })
    });
    if (!response.ok) throw new Error('Failed to run simulation');
    return response.json();
  },

  // File Upload
  async uploadFile(projectId: string, file: File): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch(`${API_URL}/projects/${projectId}/upload`, {
      method: 'POST',
      body: formData
    });
    if (!response.ok) throw new Error('Failed to upload file');
    return response.json();
  },

  async getProjectFiles(projectId: string): Promise<any[]> {
    const response = await fetch(`${API_URL}/projects/${projectId}/files`);
    if (!response.ok) throw new Error('Failed to fetch files');
    return response.json();
  },

  // Chemicals
  async getChemicals(): Promise<string[]> {
    const response = await fetch(`${API_URL}/chemicals`);
    if (!response.ok) throw new Error('Failed to fetch chemicals');
    return response.json();
  },

  async importChemicals(file: File): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch(`${API_URL}/chemicals/import`, {
      method: 'POST',
      body: formData
    });
    if (!response.ok) throw new Error('Failed to import chemicals');
    return response.json();
  }
};
