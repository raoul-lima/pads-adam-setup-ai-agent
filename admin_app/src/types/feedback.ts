export interface Feedback {
  feedback_id: string;
  agent_name: string;
  user_email: string;
  partner_name: string;
  created_at: string;
  user_query: string;
  ai_response: string;
  feedback: string;
  sentiment: "positive" | "negative" | "neutral";
  status: "To Consider" | "Considered" | "Ignored";
  notes: string;
  metadata?: Record<string, unknown>;
}

export interface FeedbackStats {
  total: number;
  positive: number;
  negative: number;
  neutral: number;
  to_consider: number;
  considered: number;
  ignored: number;
  by_partner: Record<string, {
    total: number;
    positive: number;
    negative: number;
    neutral: number;
  }>;
}
