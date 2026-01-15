import { Feedback, FeedbackStats } from '@/types/feedback';

interface FeedbackListResponse {
  feedback: Feedback[];
  total: number;
  offset: number;
  limit: number;
  has_more: boolean;
}

interface FetchFeedbackOptions {
  useDemoData?: boolean;
  offset?: number;
  limit?: number;
  sentiment?: string;
  status?: string;
  partner_name?: string;
  user_email?: string;
  start_date?: string;
  end_date?: string;
  sort_by?: string;
  sort_order?: string;
}

export async function fetchFeedbackData(options: FetchFeedbackOptions = {}): Promise<FeedbackListResponse> {
  try {
    const {
      useDemoData = false,
      offset = 0,
      limit = 100,
      sentiment,
      status,
      partner_name,
      user_email,
      start_date,
      end_date,
      sort_by = 'created_at',
      sort_order = 'desc',
    } = options;

    // Use demo data if requested
    const apiUrl = useDemoData ? '/api/feedback/demo' : '/api/feedback';
    
    // Build query parameters
    const params = new URLSearchParams();
    params.append('offset', offset.toString());
    params.append('limit', limit.toString());
    params.append('sort_by', sort_by);
    params.append('sort_order', sort_order);
    
    if (sentiment) params.append('sentiment', sentiment);
    if (status) params.append('status', status);
    if (partner_name) params.append('partner_name', partner_name);
    if (user_email) params.append('user_email', user_email);
    if (start_date) params.append('start_date', start_date);
    if (end_date) params.append('end_date', end_date);
    
    // Add cache-busting
    const timestamp = Date.now();
    params.append('_t', timestamp.toString());
    
    const finalUrl = `${apiUrl}?${params.toString()}`;
    console.log(`🔄 Requesting fresh data from: ${finalUrl}`);
    
    const response = await fetch(finalUrl, {
      cache: 'no-store',
      headers: {
        'Content-Type': 'application/json',
        'Cache-Control': 'no-cache, no-store, must-revalidate, max-age=0',
        'Pragma': 'no-cache',
        'Expires': '0',
        'X-Requested-At': timestamp.toString(),
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(
        errorData.error || 
        `Failed to fetch feedback: ${response.status} ${response.statusText}`
      );
    }

    const data: FeedbackListResponse = await response.json();
    
    // Handle legacy format (array) for demo data
    if (Array.isArray(data)) {
      return {
        feedback: data as Feedback[],
        total: data.length,
        offset: 0,
        limit: data.length,
        has_more: false,
      };
    }
    
    return data;
  } catch (error) {
    console.error('Error fetching feedback data:', error);
    throw error;
  }
}

export async function fetchFeedbackStats(
  partner_name?: string,
  start_date?: string,
  end_date?: string
): Promise<FeedbackStats> {
  try {
    const params = new URLSearchParams();
    if (partner_name) params.append('partner_name', partner_name);
    if (start_date) params.append('start_date', start_date);
    if (end_date) params.append('end_date', end_date);
    
    // Add cache-busting
    const timestamp = Date.now();
    params.append('_t', timestamp.toString());
    
    const finalUrl = `/api/feedback/stats?${params.toString()}`;
    console.log(`📊 Requesting stats from: ${finalUrl}`);
    
    const response = await fetch(finalUrl, {
      cache: 'no-store',
      headers: {
        'Content-Type': 'application/json',
        'Cache-Control': 'no-cache, no-store, must-revalidate, max-age=0',
        'Pragma': 'no-cache',
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(
        errorData.error || 
        `Failed to fetch feedback stats: ${response.status} ${response.statusText}`
      );
    }

    const data: FeedbackStats = await response.json();
    return data;
  } catch (error) {
    console.error('Error fetching feedback stats:', error);
    throw error;
  }
}

export function calculateFeedbackStats(feedbacks: Feedback[]): FeedbackStats {
  const stats: FeedbackStats = {
    total: feedbacks.length,
    positive: 0,
    negative: 0,
    neutral: 0,
    to_consider: 0,
    considered: 0,
    ignored: 0,
    by_partner: {},
  };

  feedbacks.forEach((feedback) => {
    // Count by sentiment
    switch (feedback.sentiment) {
      case 'positive':
        stats.positive++;
        break;
      case 'negative':
        stats.negative++;
        break;
      case 'neutral':
        stats.neutral++;
        break;
    }

    // Count by status
    switch (feedback.status) {
      case 'To Consider':
        stats.to_consider++;
        break;
      case 'Considered':
        stats.considered++;
        break;
      case 'Ignored':
        stats.ignored++;
        break;
    }

    // Count by partner
    if (!stats.by_partner[feedback.partner_name]) {
      stats.by_partner[feedback.partner_name] = {
        total: 0,
        positive: 0,
        negative: 0,
        neutral: 0,
      };
    }
    
    stats.by_partner[feedback.partner_name].total++;
    if (feedback.sentiment === 'positive') stats.by_partner[feedback.partner_name].positive++;
    if (feedback.sentiment === 'negative') stats.by_partner[feedback.partner_name].negative++;
    if (feedback.sentiment === 'neutral') stats.by_partner[feedback.partner_name].neutral++;
  });

  return stats;
}

export function formatTimestamp(timestamp: string): string {
  try {
    return new Date(timestamp).toLocaleString();
  } catch {
    return timestamp; // Return original if parsing fails
  }
}
