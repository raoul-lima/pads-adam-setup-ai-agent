import { NextResponse } from 'next/server';

export async function GET(request: Request) {
  // Get backend API URL from environment
  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
  
  // Parse query parameters for filtering
  const { searchParams } = new URL(request.url);
  const partner_name = searchParams.get('partner_name');
  const start_date = searchParams.get('start_date');
  const end_date = searchParams.get('end_date');

  console.log('📊 Fetching feedback statistics from database API');
  
  try {
    // Build query parameters
    const params = new URLSearchParams();
    if (partner_name) params.append('partner_name', partner_name);
    if (start_date) params.append('start_date', start_date);
    if (end_date) params.append('end_date', end_date);
    
    const apiUrl = `${backendUrl}/feedback/stats${params.toString() ? `?${params.toString()}` : ''}`;
    console.log(`🔄 Fetching from: ${apiUrl}`);
    
    const response = await fetch(apiUrl, {
      cache: 'no-store',
      next: { revalidate: 0 },
      headers: {
        'Accept': 'application/json',
        'Cache-Control': 'no-cache',
      },
    });
    
    if (!response.ok) {
      throw new Error(`Backend API error: ${response.status} ${response.statusText}`);
    }
    
    const data = await response.json();
    
    console.log(`✅ Successfully fetched feedback statistics`);
    console.log(`📊 Total: ${data.total}, Positive: ${data.positive}, Negative: ${data.negative}`);
    
    return NextResponse.json(data, {
      headers: {
        'Cache-Control': 'no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0',
        'Pragma': 'no-cache',
        'Expires': '0',
        'X-Fetch-Method': 'database-api',
        'X-Fetch-Timestamp': new Date().toISOString(),
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET',
        'Access-Control-Allow-Headers': 'Content-Type, Cache-Control',
      },
    });
    
  } catch (error) {
    console.error('❌ Error fetching feedback stats from database:', error);
    
    return NextResponse.json(
      { 
        error: 'Failed to fetch feedback statistics from database',
        details: error instanceof Error ? error.message : 'Unknown error',
        suggestion: 'Ensure the backend API is running and NEXT_PUBLIC_BACKEND_URL is configured'
      },
      { status: 500 }
    );
  }
}

