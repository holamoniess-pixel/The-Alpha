export interface User {
  user_id: string;
  username: string;
  roles: string[];
}

export interface Intent {
  intent_id: string;
  user_id: string;
  command: string;
  status: 'pending' | 'approved' | 'rejected' | 'executed' | 'failed' | 'paused';
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  risk_score: number;
  requires_approval: boolean;
  reason: string;
  timestamp: string;
}

export interface Secret {
  secret_id: string;
  service: string;
  label: string;
  created_at: string;
  updated_at: string;
  access_count?: number;
  last_accessed?: string;
}

export interface SystemStatus {
  paused: boolean;
  active_intents: number;
  connected_clients: number;
}

export interface WebSocketMessage {
  type: string;
  data?: any;
  timestamp?: number;
}
