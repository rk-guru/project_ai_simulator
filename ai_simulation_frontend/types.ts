
export interface Project {
  id: string;
  name: string;
  messages?: ChatMessage[];
  nodes?: FlowsheetNode[];
  edges?: FlowsheetEdge[];
  results?: any[]; // Changed to any[] to support generic DataFrame structures
  files?: { name: string }[];
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'ai';
  text: string;
  isTyping?: boolean;
}

export enum EquipmentType {
  // Streams
  Feed = 'Feed',
  Product = 'Product',

  // Basic Units
  Tank = 'Tank',
  Pump = 'Pump',
  Mixer = 'Mixer',
  Splitter = 'Splitter',

  // Heat Exchange
  Heater = 'Heater',
  Cooler = 'Cooler',
  HeatExchanger = 'HeatExchanger',

  // Pressure Change
  Compressor = 'Compressor',
  Expander = 'Expander',

  // Separation
  Flash = 'Flash',
  DistillationColumn = 'DistillationColumn',
  Reactor = 'Reactor',
}

export interface FlowsheetNode {
  id: string;
  type: EquipmentType;
  name: string;
  x: number;
  y: number;
  properties: Record<string, any>;
}

export interface FlowsheetEdge {
  id: string;
  from: string;
  to: string;
  port?: string; // e.g., 'hot-in', 'cold-in', 'hot-out', 'cold-out', 'vapor', 'liquid'
}

export interface ReactionComponent {
  compound: string;
  stoichiometry: number;
}

export interface Reaction {
  reactants: ReactionComponent[];
  products: ReactionComponent[];
  conversion: number;
  notes: string;
}
