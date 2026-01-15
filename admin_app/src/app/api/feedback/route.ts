import { NextResponse } from 'next/server';

export async function GET(request: Request) {
  // Get backend API URL from environment
  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
  
  // Parse query parameters for filtering and pagination
  const { searchParams } = new URL(request.url);
  const offset = searchParams.get('offset') || '0';
  const limit = searchParams.get('limit') || '100';
  const sentiment = searchParams.get('sentiment');
  const status = searchParams.get('status');
  const partner_name = searchParams.get('partner_name');
  const user_email = searchParams.get('user_email');
  const start_date = searchParams.get('start_date');
  const end_date = searchParams.get('end_date');
  const sort_by = searchParams.get('sort_by') || 'created_at';
  const sort_order = searchParams.get('sort_order') || 'desc';

  console.log('🗄️  Fetching feedback from database API');
  
  try {
    // Build query parameters
    const params = new URLSearchParams();
    params.append('offset', offset);
    params.append('limit', limit);
    params.append('sort_by', sort_by);
    params.append('sort_order', sort_order);
    
    if (sentiment) params.append('sentiment', sentiment);
    if (status) params.append('status', status);
    if (partner_name) params.append('partner_name', partner_name);
    if (user_email) params.append('user_email', user_email);
    if (start_date) params.append('start_date', start_date);
    if (end_date) params.append('end_date', end_date);
    
    const apiUrl = `${backendUrl}/feedback/list?${params.toString()}`;
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
    
    console.log(`✅ Successfully fetched ${data.feedback?.length || 0} feedback items from database`);
    console.log(`📊 Total: ${data.total}, Offset: ${data.offset}, Has more: ${data.has_more}`);
    
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
    console.error('❌ Error fetching feedback from database:', error);
    
    return NextResponse.json(
      { 
        error: 'Failed to fetch feedback from database',
        details: error instanceof Error ? error.message : 'Unknown error',
        suggestion: 'Ensure the backend API is running and NEXT_PUBLIC_BACKEND_URL is configured'
      },
      { status: 500 }
    );
  }
}