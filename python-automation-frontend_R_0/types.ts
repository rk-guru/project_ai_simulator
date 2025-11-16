
export interface Step {
  id: string;
  command: string;
}

export interface Project {
  id: string;
  name: string;
  url: string;
  steps: Step[];
}
