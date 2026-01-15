import { NextResponse } from 'next/server';

// Demo data for testing when the main URL is not accessible
const demoFeedbackData = [
  {
    "agent_name": "Adam Setup",
    "user_email": "admin@adsecura.com",
    "partner_name": "partner_b2p",
    "timestamp": "2025-01-19T07:50:08.660231",
    "user_query": "How many line items do I have?",
    "ai_response": "I encountered an issue while trying to retrieve the total number of line items.\n\nThe system reported an error indicating that the column 'line_items_id' could not be found in the data. This means that either the column is named differently, or it's missing from your `Line_Items` data.\n\nPlease verify the exact name of the column that contains your line item IDs. Once you confirm the correct column name, I can try again to get the total count for you.\n\nWould you like to refine your request with a different column name or explore other aspects of your line items data?",
    "feedback": "Bien",
    "sentiment": "positive"
  },
  {
    "agent_name": "Adam Setup",
    "user_email": "gaetan.godart@programmads.com",
    "partner_name": "partner_b2p",
    "timestamp": "2025-01-19T08:15:22.123456",
    "user_query": "Can you analyze my campaign performance?",
    "ai_response": "I'll analyze your campaign performance data. Let me examine the key metrics including impressions, clicks, conversions, and cost efficiency across your active campaigns.",
    "feedback": "Very helpful analysis",
    "sentiment": "positive"
  },
  {
    "agent_name": "Adam Setup",
    "user_email": "test@example.com",
    "partner_name": "partner_demo",
    "timestamp": "2025-01-19T09:30:15.789012",
    "user_query": "Why are my ads not showing?",
    "ai_response": "There could be several reasons why your ads aren't showing. Let me check your campaign settings, budget allocation, and targeting parameters to identify potential issues.",
    "feedback": "Need more specific guidance",
    "sentiment": "neutral"
  },
  {
    "agent_name": "Adam Setup",
    "user_email": "admin@adsecura.com",
    "partner_name": "partner_b2p",
    "timestamp": "2025-01-19T10:45:33.345678",
    "user_query": "Export my data to CSV",
    "ai_response": "I'm unable to export your data at this time due to a system limitation. Please try again later or contact support for assistance.",
    "feedback": "Feature not working",
    "sentiment": "negative"
  },
  {
    "agent_name": "Adam Setup",
    "user_email": "gaetan.godart@programmads.com",
    "partner_name": "partner_b2p",
    "timestamp": "2025-01-19T11:20:44.567890",
    "user_query": "Show me my top performing campaigns",
    "ai_response": "Here are your top performing campaigns based on ROI and conversion rates. Campaign A shows the highest performance with 15% conversion rate and $2.50 CPA.",
    "feedback": "Perfect, exactly what I needed",
    "sentiment": "positive"
  }
];

export async function GET() {
  try {
    // Return demo data with proper headers
    return NextResponse.json(demoFeedbackData, {
      headers: {
        'Cache-Control': 'no-store, no-cache, must-revalidate',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET',
        'Access-Control-Allow-Headers': 'Content-Type',
      },
    });
  } catch (error) {
    console.error('Error serving demo data:', error);
    
    return NextResponse.json(
      { 
        error: 'Failed to serve demo data',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    );
  }
}
