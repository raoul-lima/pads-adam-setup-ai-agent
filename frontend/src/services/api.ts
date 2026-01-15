import axios, { AxiosInstance } from 'axios';
import {
  HealthResponse,
  Message,
  SendMessageResponse
} from '@/types/api';

export interface Feedback {
  user_query: string;
  ai_response: string;
  feedback: string;
  partner_name: string;
  user_email: string;
  sentiment: string;
}

class ApiService {
  private api: AxiosInstance;
  private user_email: string | null = null;
  private partner: string | null = null;

  constructor() {
    this.api = axios.create({
      baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (typeof window !== 'undefined') {
      const urlParams = new URLSearchParams(window.location.search);
      this.user_email = urlParams.get('email');
      this.partner = urlParams.get('partner');
    }
  }

  // API endpoints
  async sendMessage(content: string, useMemory: boolean = true): Promise<SendMessageResponse> {
    if (!this.user_email || !this.partner) {
      throw new Error("User email or partner not found in URL parameters.");
    }
    const response = await this.api.post('/chat/message', { 
      content,
      user_email: this.user_email,
      partner: this.partner,
      use_memory: useMemory
    });
    return response.data;
  }

  async getConversationHistory(): Promise<{ messages: Message[], conversation_id: string | null }> {
    if (!this.user_email || !this.partner) {
        return { messages: [], conversation_id: null };
    }
    try {
      const response = await this.api.post('/chat/history', { 
        user_email: this.user_email,
        partner: this.partner 
      });
      // Ensure messages that include download_links are properly typed
      const data = response.data as { messages: Message[]; conversation_id: string | null };
      return data;
    } catch (error) {
      console.error('Failed to get conversation history:', error);
      return { messages: [], conversation_id: null };
    }
  }

  async resetConversation(): Promise<void> {
    if (!this.user_email || !this.partner) {
      throw new Error("User email or partner not found in URL parameters.");
    }
    await this.api.post('/chat/reset', { 
      user_email: this.user_email,
      partner: this.partner 
    });
  }

  async getHealth(): Promise<HealthResponse> {
    const response = await this.api.get('/health');
    return response.data;
  }

  async sendFeedback(feedbackData: Omit<Feedback, 'user_email'>): Promise<void> {
    if (!this.user_email) {
        throw new Error("User email not found in URL parameters.");
    }
    const feedback: Feedback = {
        ...feedbackData,
        user_email: this.user_email
    };
    await this.api.post('/feedback', feedback);
  }

  async getCsvPreview(url: string, offset: number = 0, limit: number = 100): Promise<{
    headers: string[];
    rows: string[][];
    total_rows: number;
    offset: number;
    limit: number;
    has_more: boolean;
  }> {
    const response = await this.api.get('/csv/preview', {
      params: { url, offset, limit }
    });
    return response.data;
  }
}

export const apiService = new ApiService(); 