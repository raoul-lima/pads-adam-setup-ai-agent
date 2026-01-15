export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  user_id: string;
  email: string;
  role: string;
}

export interface ChatMessage {
  content: string;
  user_email: string;
  partner: string;
  use_memory?: boolean;
}

export interface ChatResponse {
  response: string;
  conversation_id: string;
  timestamp: string;
  download_links?: DownloadLink[];
}

export interface UserProfile {
  email: string;
  role: string;
}

export interface DownloadLink {
  label: string;
  url: string;
}

export interface Message {
  type: 'human' | 'ai';
  content: string;
  timestamp: string;
  download_links?: DownloadLink[];
}

export interface SendMessageResponse {
  response: string;
  conversation_id: string;
  timestamp: string;
  download_links: DownloadLink[];
}

export interface ConversationHistory {
  messages: Message[];
  conversation_id: string | null;
}

export interface HealthResponse {
  status: string;
  timestamp: string;
  active_sessions: number;
  active_graphs: number;
}

export interface User {
  email: string;
  role: string;
  user_id: string;
} 