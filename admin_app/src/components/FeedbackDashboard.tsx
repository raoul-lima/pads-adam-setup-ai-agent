'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { Feedback, FeedbackStats } from '@/types/feedback';
import { calculateFeedbackStats, formatTimestamp } from '@/lib/feedbackService';

interface FeedbackDashboardProps {
  onLogout: () => void;
}

export default function FeedbackDashboard({ onLogout }: FeedbackDashboardProps) {
  const [feedbacks, setFeedbacks] = useState<Feedback[]>([]);
  const [stats, setStats] = useState<FeedbackStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedFeedback, setSelectedFeedback] = useState<Feedback | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterSentiment, setFilterSentiment] = useState<string>('all');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [selectedEmails, setSelectedEmails] = useState<string[]>([]);
  const [showEmailFilter, setShowEmailFilter] = useState(false);
  const [isDemoMode, setIsDemoMode] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [fileMetadata, setFileMetadata] = useState<{etag?: string, lastModified?: string, fetchMethod?: string} | null>(null);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [totalCount, setTotalCount] = useState(0);
  const [updatingStatus, setUpdatingStatus] = useState(false);
  const [deletingFeedback, setDeletingFeedback] = useState(false);
  const [selectedFeedbackIds, setSelectedFeedbackIds] = useState<string[]>([]);
  const [showBatchActions, setShowBatchActions] = useState(false);
  const [autoFetching, setAutoFetching] = useState(false);
  const [editingNotes, setEditingNotes] = useState(false);
  const [notesValue, setNotesValue] = useState('');
  const emailFilterRef = useRef<HTMLDivElement>(null);
  const batchActionsRef = useRef<HTMLDivElement>(null);

  const ITEMS_PER_PAGE = 50;
  const MIN_VISIBLE_ITEMS = 50;

  useEffect(() => {
    loadInitialData(false);
  }, []);

  // Initialize notes value when selectedFeedback changes
  useEffect(() => {
    if (selectedFeedback) {
      setNotesValue(selectedFeedback.notes);
    }
  }, [selectedFeedback]);

  // Close batch actions dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (batchActionsRef.current && !batchActionsRef.current.contains(event.target as Node)) {
        setShowBatchActions(false);
      }
    }

    if (showBatchActions) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => {
        document.removeEventListener('mousedown', handleClickOutside);
      };
    }
  }, [showBatchActions]);

  // Close email filter dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (emailFilterRef.current && !emailFilterRef.current.contains(event.target as Node)) {
        setShowEmailFilter(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const loadInitialData = async (useDemoData = false) => {
    try {
      setLoading(true);
      setError(null);
      
      console.log(`🔄 Loading initial feedback data (Demo mode: ${useDemoData})`);
      
      if (useDemoData) {
        // Load demo data (legacy format)
        const response = await fetch('/api/feedback/demo', {
          cache: 'no-store',
          headers: {
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'X-Force-Refresh': 'true',
          }
        });
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        setFeedbacks(data);
        setStats(calculateFeedbackStats(data));
        setIsDemoMode(true);
        setHasMore(false);
        setTotalCount(data.length);
        setLastUpdated(new Date());
      } else {
        // Load from database with stats API
        const [feedbackResponse, statsResponse] = await Promise.all([
          fetch(`/api/feedback?offset=0&limit=${ITEMS_PER_PAGE}`, {
            cache: 'no-store',
            headers: { 'Cache-Control': 'no-cache, no-store, must-revalidate' }
          }),
          fetch('/api/feedback/stats', {
            cache: 'no-store',
            headers: { 'Cache-Control': 'no-cache, no-store, must-revalidate' }
          })
        ]);
        
        if (!feedbackResponse.ok || !statsResponse.ok) {
          throw new Error('Failed to load feedback data');
        }
        
        const feedbackData = await feedbackResponse.json();
        const statsData = await statsResponse.json();
        
        // Extract metadata
        const fetchMethod = feedbackResponse.headers.get('x-fetch-method');
        
        // Handle API response
        const feedbackArray = feedbackData.feedback || [];
        
        // Debug: Check if created_at exists
        if (feedbackArray.length > 0) {
          console.log('📅 First feedback item:', {
            has_created_at: 'created_at' in feedbackArray[0],
            created_at: feedbackArray[0].created_at,
            all_keys: Object.keys(feedbackArray[0])
          });
        }
        
        setFeedbacks(feedbackArray);
        setStats(statsData);
        setOffset(ITEMS_PER_PAGE);
        setHasMore(feedbackData.has_more || false);
        setTotalCount(feedbackData.total || 0);
        setIsDemoMode(false);
        setLastUpdated(new Date());
        setFileMetadata({ fetchMethod: fetchMethod || undefined });
        
        console.log(`✅ Loaded ${feedbackArray.length} feedback items`);
        console.log(`📊 Total in DB: ${feedbackData.total}, Has more: ${feedbackData.has_more}`);
      }
      
    } catch (err) {
      console.error('❌ Failed to load feedback data:', err);
      setError(err instanceof Error ? err.message : 'Failed to load feedback data');
    } finally {
      setLoading(false);
    }
  };

  const loadMoreFeedback = useCallback(async () => {
    if (loadingMore || !hasMore || isDemoMode) return;
    
    try {
      setLoadingMore(true);
      
      console.log(`🔄 Loading more feedback (offset: ${offset})`);
      
      const response = await fetch(
        `/api/feedback?offset=${offset}&limit=${ITEMS_PER_PAGE}`,
        {
          cache: 'no-store',
          headers: { 'Cache-Control': 'no-cache, no-store, must-revalidate' }
        }
      );
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      const newFeedback = data.feedback || [];
      
      setFeedbacks(prev => [...prev, ...newFeedback]);
      setOffset(prev => prev + ITEMS_PER_PAGE);
      setHasMore(data.has_more || false);
      
      console.log(`✅ Loaded ${newFeedback.length} more items. Total: ${feedbacks.length + newFeedback.length}/${data.total}`);
      
    } catch (err) {
      console.error('❌ Failed to load more feedback:', err);
      setError(err instanceof Error ? err.message : 'Failed to load more feedback');
    } finally {
      setLoadingMore(false);
    }
  }, [loadingMore, hasMore, isDemoMode, offset, feedbacks.length]);

  const updateFeedbackStatus = async (feedbackId: string, newStatus: string) => {
    if (isDemoMode) {
      alert('Cannot update status in demo mode');
      return;
    }

    try {
      setUpdatingStatus(true);
      
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
      const response = await fetch(
        `${backendUrl}/feedback/${feedbackId}/status?status=${encodeURIComponent(newStatus)}`,
        {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );
      
      if (!response.ok) {
        throw new Error(`Failed to update status: ${response.status}`);
      }
      
      // Update local state
      setFeedbacks(prev => 
        prev.map(f => 
          f.feedback_id === feedbackId ? { ...f, status: newStatus as Feedback['status'] } : f
        )
      );
      
      // Update selected feedback if it's the one being updated
      if (selectedFeedback && selectedFeedback.feedback_id === feedbackId) {
        setSelectedFeedback({ ...selectedFeedback, status: newStatus as Feedback['status'] });
      }
      
      // Refresh stats
      const statsResponse = await fetch('/api/feedback/stats', {
        cache: 'no-store',
      });
      if (statsResponse.ok) {
        const statsData = await statsResponse.json();
        setStats(statsData);
      }
      
      console.log(`✅ Updated feedback ${feedbackId} status to: ${newStatus}`);
      
    } catch (err) {
      console.error('❌ Failed to update feedback status:', err);
      alert(err instanceof Error ? err.message : 'Failed to update feedback status');
    } finally {
      setUpdatingStatus(false);
    }
  };

  const updateFeedbackNotes = async (feedbackId: string, notes: string) => {
    if (isDemoMode) {
      alert('Cannot update notes in demo mode');
      return;
    }

    try {
      setEditingNotes(true);
      
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
      const response = await fetch(
        `${backendUrl}/feedback/${feedbackId}/notes?notes=${encodeURIComponent(notes)}`,
        {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );
      
      if (!response.ok) {
        throw new Error(`Failed to update notes: ${response.status}`);
      }
      
      // Update local state
      setFeedbacks(prev => 
        prev.map(f => 
          f.feedback_id === feedbackId ? { ...f, notes } : f
        )
      );
      
      // Update selected feedback if it's the one being updated
      if (selectedFeedback && selectedFeedback.feedback_id === feedbackId) {
        setSelectedFeedback({ ...selectedFeedback, notes });
      }
      
      console.log(`✅ Updated feedback ${feedbackId} notes`);
      
    } catch (err) {
      console.error('❌ Failed to update feedback notes:', err);
      alert(err instanceof Error ? err.message : 'Failed to update feedback notes');
    } finally {
      setEditingNotes(false);
    }
  };

  const deleteFeedback = async (feedbackId: string) => {
    if (isDemoMode) {
      alert('Cannot delete feedback in demo mode');
      return;
    }

    if (!confirm('Are you sure you want to delete this feedback? This action cannot be undone.')) {
      return;
    }

    try {
      setDeletingFeedback(true);
      
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
      const response = await fetch(
        `${backendUrl}/feedback/${feedbackId}`,
        {
          method: 'DELETE',
        }
      );
      
      if (!response.ok) {
        throw new Error(`Failed to delete feedback: ${response.status}`);
      }
      
      // Remove from local state
      setFeedbacks(prev => prev.filter(f => f.feedback_id !== feedbackId));
      setTotalCount(prev => prev - 1);
      
      // Close modal
      setSelectedFeedback(null);
      
      // Refresh stats
      const statsResponse = await fetch('/api/feedback/stats', {
        cache: 'no-store',
      });
      if (statsResponse.ok) {
        const statsData = await statsResponse.json();
        setStats(statsData);
      }
      
      console.log(`✅ Deleted feedback ${feedbackId}`);
      
    } catch (err) {
      console.error('❌ Failed to delete feedback:', err);
      alert(err instanceof Error ? err.message : 'Failed to delete feedback');
    } finally {
      setDeletingFeedback(false);
    }
  };

  // Batch actions
  const handleSelectAll = () => {
    if (selectedFeedbackIds.length === filteredFeedbacks.length) {
      setSelectedFeedbackIds([]);
    } else {
      setSelectedFeedbackIds(filteredFeedbacks.map(f => f.feedback_id));
    }
  };

  const handleSelectFeedback = (feedbackId: string) => {
    setSelectedFeedbackIds(prev =>
      prev.includes(feedbackId)
        ? prev.filter(id => id !== feedbackId)
        : [...prev, feedbackId]
    );
  };

  const batchUpdateStatus = async (newStatus: string) => {
    if (isDemoMode || selectedFeedbackIds.length === 0) return;

    try {
      setUpdatingStatus(true);
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
      
      // Update all selected feedback
      const promises = selectedFeedbackIds.map(id =>
        fetch(`${backendUrl}/feedback/${id}/status?status=${encodeURIComponent(newStatus)}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
        })
      );
      
      const results = await Promise.all(promises);
      const failedCount = results.filter(r => !r.ok).length;
      
      if (failedCount > 0) {
        alert(`Updated ${results.length - failedCount} feedback, ${failedCount} failed`);
      }
      
      // Update local state
      setFeedbacks(prev =>
        prev.map(f =>
          selectedFeedbackIds.includes(f.feedback_id)
            ? { ...f, status: newStatus as Feedback['status'] }
            : f
        )
      );
      
      // Clear selection
      setSelectedFeedbackIds([]);
      setShowBatchActions(false);
      
      // Refresh stats
      const statsResponse = await fetch('/api/feedback/stats', { cache: 'no-store' });
      if (statsResponse.ok) {
        setStats(await statsResponse.json());
      }
      
      console.log(`✅ Batch updated ${selectedFeedbackIds.length} feedback to: ${newStatus}`);
      
    } catch (err) {
      console.error('❌ Failed to batch update:', err);
      alert('Failed to update feedback in batch');
    } finally {
      setUpdatingStatus(false);
    }
  };

  const batchDelete = async () => {
    if (isDemoMode || selectedFeedbackIds.length === 0) return;

    if (!confirm(`Are you sure you want to delete ${selectedFeedbackIds.length} feedback items? This action cannot be undone.`)) {
      return;
    }

    try {
      setDeletingFeedback(true);
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
      
      // Delete all selected feedback
      const promises = selectedFeedbackIds.map(id =>
        fetch(`${backendUrl}/feedback/${id}`, { method: 'DELETE' })
      );
      
      const results = await Promise.all(promises);
      const successCount = results.filter(r => r.ok).length;
      
      if (successCount < results.length) {
        alert(`Deleted ${successCount} feedback, ${results.length - successCount} failed`);
      }
      
      // Remove from local state
      setFeedbacks(prev => prev.filter(f => !selectedFeedbackIds.includes(f.feedback_id)));
      setTotalCount(prev => prev - successCount);
      
      // Clear selection
      setSelectedFeedbackIds([]);
      setShowBatchActions(false);
      
      // Refresh stats
      const statsResponse = await fetch('/api/feedback/stats', { cache: 'no-store' });
      if (statsResponse.ok) {
        setStats(await statsResponse.json());
      }
      
      console.log(`✅ Batch deleted ${successCount} feedback`);
      
    } catch (err) {
      console.error('❌ Failed to batch delete:', err);
      alert('Failed to delete feedback in batch');
    } finally {
      setDeletingFeedback(false);
    }
  };

  // Get unique emails for filter options
  const uniqueEmails = [...new Set(feedbacks.map(feedback => feedback.user_email))].sort();

  // Handle email selection
  const handleEmailToggle = (email: string) => {
    setSelectedEmails(prev => 
      prev.includes(email) 
        ? prev.filter(e => e !== email)
        : [...prev, email]
    );
  };

  const handleSelectAllEmails = () => {
    setSelectedEmails(uniqueEmails);
  };

  const handleClearAllEmails = () => {
    setSelectedEmails([]);
  };

  const filteredFeedbacks = feedbacks.filter((feedback) => {
    const matchesSearch = 
      feedback.user_query.toLowerCase().includes(searchTerm.toLowerCase()) ||
      feedback.feedback.toLowerCase().includes(searchTerm.toLowerCase()) ||
      feedback.user_email.toLowerCase().includes(searchTerm.toLowerCase()) ||
      feedback.agent_name.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesSentiment = filterSentiment === 'all' || feedback.sentiment === filterSentiment;
    
    const matchesStatus = filterStatus === 'all' || feedback.status === filterStatus;
    
    const matchesEmail = selectedEmails.length === 0 || selectedEmails.includes(feedback.user_email);
    
    return matchesSearch && matchesSentiment && matchesStatus && matchesEmail;
  });

  // Auto-fetch more data when filtered results are less than MIN_VISIBLE_ITEMS
  useEffect(() => {
    const shouldAutoFetch = 
      !isDemoMode &&
      !loading &&
      !loadingMore &&
      !autoFetching &&
      hasMore &&
      filteredFeedbacks.length < MIN_VISIBLE_ITEMS &&
      feedbacks.length > 0 &&
      feedbacks.length < totalCount; // Don't fetch if we already have all data

    if (shouldAutoFetch) {
      console.log(`🔄 Auto-fetching: ${filteredFeedbacks.length} visible items < ${MIN_VISIBLE_ITEMS} minimum (${feedbacks.length}/${totalCount} loaded)`);
      setAutoFetching(true);
      loadMoreFeedback().finally(() => setAutoFetching(false));
    }
  }, [filteredFeedbacks.length, hasMore, loading, loadingMore, autoFetching, isDemoMode, feedbacks.length, totalCount, loadMoreFeedback]);

  const getSentimentColor = (sentiment: string) => {
    switch (sentiment) {
      case 'positive': return 'text-green-600 bg-green-100';
      case 'negative': return 'text-red-600 bg-red-100';
      case 'neutral': return 'text-yellow-600 bg-yellow-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-indigo-600"></div>
          <p className="mt-4 text-gray-600">Loading feedback data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="rounded-md bg-red-50 p-6 max-w-lg">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-red-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">Error Loading Feedback Data</h3>
                <div className="mt-2 text-sm text-red-700">{error}</div>
                <div className="mt-4">
                  <div className="-mx-2 -my-1.5 flex flex-wrap gap-2">
                    <button
                      onClick={() => loadInitialData(false)}
                      disabled={loading}
                      className="bg-red-100 hover:bg-red-200 disabled:bg-red-50 text-red-800 px-4 py-2 rounded text-sm font-medium"
                    >
                      {loading ? 'Retrying...' : 'Try Again'}
                    </button>
                    <button
                      onClick={() => loadInitialData(true)}
                      disabled={loading}
                      className="bg-yellow-100 hover:bg-yellow-200 disabled:bg-yellow-50 text-yellow-800 px-4 py-2 rounded text-sm font-medium"
                    >
                      {loading ? 'Loading...' : 'Use Demo Data'}
                    </button>
                    <button
                      onClick={() => {
                        console.log('🔍 Debug Information:');
                        console.log('Current URL:', window.location.href);
                        console.log('Demo Mode:', isDemoMode);
                        console.log('Error:', error);
                      }}
                      className="bg-gray-100 hover:bg-gray-200 text-gray-800 px-4 py-2 rounded text-sm font-medium"
                    >
                      Debug Info
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                Adam Agent Feedback Dashboard
                {isDemoMode && (
                  <span className="ml-3 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                    Demo Mode
                  </span>
                )}
              </h1>
              <p className="mt-1 text-sm text-gray-500">
                Monitor user feedback and sentiment
                {isDemoMode && ' (using demo data)'}
                {lastUpdated && (
                  <span className="block mt-1">
                    Last fetched: {lastUpdated.toLocaleString()}
                    {!isDemoMode && fileMetadata?.lastModified && fileMetadata.lastModified !== 'none' && (
                      <span className="block">
                        File last modified: {new Date(fileMetadata.lastModified).toLocaleString()}
                      </span>
                    )}
                    {!isDemoMode && fileMetadata?.fetchMethod && (
                      <span className="flex items-center gap-2 mt-1">
                        Access method: 
                        <span className={`px-2 py-1 rounded text-xs font-medium ${
                          fileMetadata.fetchMethod === 'gcs-authenticated'
                            ? 'bg-green-100 text-green-800' 
                            : 'bg-blue-100 text-blue-800'
                        }`}>
                          {fileMetadata.fetchMethod === 'gcs-authenticated' ? '🔐 GCS Authenticated' : '🌐 Direct URL'}
                        </span>
                      </span>
                    )}
                    {!isDemoMode && fileMetadata?.etag && fileMetadata.etag !== 'none' && (
                      <span className="block text-xs text-gray-400">
                        File version: {fileMetadata.etag.substring(1, 13)}...
                      </span>
                    )}
                  </span>
                )}
              </p>
            </div>
            <div className="flex space-x-3">
              <button
                onClick={() => window.location.href = '/evaluation'}
                className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-md text-sm font-medium flex items-center"
              >
                <svg className="-ml-1 mr-2 h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                </svg>
                Run Evaluation
              </button>
              <button
                onClick={() => loadInitialData(isDemoMode)}
                disabled={loading}
                className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white px-4 py-2 rounded-md text-sm font-medium flex items-center"
              >
                {loading ? (
                  <>
                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Loading...
                  </>
                ) : (
                  <>
                    <svg className="-ml-1 mr-2 h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    Refresh
                  </>
                )}
              </button>
              <button
                onClick={onLogout}
                className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-md text-sm font-medium"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        {/* Stats Overview */}
        {stats && (
          <div className="mb-8 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="p-5">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 bg-indigo-500 rounded-md flex items-center justify-center">
                      <span className="text-white text-sm font-medium">{stats.total}</span>
                    </div>
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 truncate">Total Feedback</dt>
                      <dd className="text-lg font-medium text-gray-900">{stats.total}</dd>
                    </dl>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="p-5">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 bg-green-500 rounded-md flex items-center justify-center">
                      <span className="text-white text-sm font-medium">{stats.positive}</span>
                    </div>
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 truncate">Positive</dt>
                      <dd className="text-lg font-medium text-gray-900">{stats.positive}</dd>
                    </dl>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="p-5">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 bg-red-500 rounded-md flex items-center justify-center">
                      <span className="text-white text-sm font-medium">{stats.negative}</span>
                    </div>
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 truncate">Negative</dt>
                      <dd className="text-lg font-medium text-gray-900">{stats.negative}</dd>
                    </dl>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="p-5">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 bg-yellow-500 rounded-md flex items-center justify-center">
                      <span className="text-white text-sm font-medium">{stats.neutral}</span>
                    </div>
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 truncate">Neutral</dt>
                      <dd className="text-lg font-medium text-gray-900">{stats.neutral}</dd>
                    </dl>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Status Stats */}
        {stats && !isDemoMode && (
          <div className="mb-8 grid grid-cols-1 gap-5 sm:grid-cols-3">
            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="p-5">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 bg-blue-500 rounded-md flex items-center justify-center">
                      <span className="text-white text-sm font-medium">{stats.to_consider}</span>
                    </div>
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 truncate">To Consider</dt>
                      <dd className="text-lg font-medium text-gray-900">{stats.to_consider}</dd>
                    </dl>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="p-5">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 bg-purple-500 rounded-md flex items-center justify-center">
                      <span className="text-white text-sm font-medium">{stats.considered}</span>
                    </div>
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 truncate">Considered</dt>
                      <dd className="text-lg font-medium text-gray-900">{stats.considered}</dd>
                    </dl>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="p-5">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 bg-gray-500 rounded-md flex items-center justify-center">
                      <span className="text-white text-sm font-medium">{stats.ignored}</span>
                    </div>
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 truncate">Ignored</dt>
                      <dd className="text-lg font-medium text-gray-900">{stats.ignored}</dd>
                    </dl>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="mb-6 bg-white shadow rounded-lg p-6">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <label htmlFor="search" className="block text-sm font-medium text-gray-700">
                Search
              </label>
              <input
                type="text"
                id="search"
                className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm text-gray-900 bg-white placeholder-gray-500"
                placeholder="Search feedback, queries, emails..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
            <div>
              <label htmlFor="sentiment" className="block text-sm font-medium text-gray-700">
                Filter by Sentiment
              </label>
              <select
                id="sentiment"
                className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm text-gray-900 bg-white"
                value={filterSentiment}
                onChange={(e) => setFilterSentiment(e.target.value)}
              >
                <option value="all" className="text-gray-900">All Sentiments</option>
                <option value="positive" className="text-gray-900">Positive</option>
                <option value="negative" className="text-gray-900">Negative</option>
                <option value="neutral" className="text-gray-900">Neutral</option>
              </select>
            </div>
            {!isDemoMode && (
              <div>
                <label htmlFor="status" className="block text-sm font-medium text-gray-700">
                  Filter by Status
                </label>
                <select
                  id="status"
                  className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm text-gray-900 bg-white"
                  value={filterStatus}
                  onChange={(e) => setFilterStatus(e.target.value)}
                >
                  <option value="all" className="text-gray-900">All Status</option>
                  <option value="To Consider" className="text-gray-900">To Consider</option>
                  <option value="Considered" className="text-gray-900">Considered</option>
                  <option value="Ignored" className="text-gray-900">Ignored</option>
                </select>
              </div>
            )}
            <div ref={emailFilterRef}>
              <label className="block text-sm font-medium text-gray-700">
                Filter by Email ({selectedEmails.length} selected)
              </label>
              <div className="mt-1 relative">
                <button
                  type="button"
                  onClick={() => setShowEmailFilter(!showEmailFilter)}
                  className="w-full bg-white border border-gray-300 rounded-md shadow-sm px-3 py-2 text-left text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 text-gray-900"
                >
                  {selectedEmails.length === 0 
                    ? 'All emails' 
                    : selectedEmails.length === 1 
                      ? selectedEmails[0]
                      : `${selectedEmails.length} emails selected`
                  }
                  <svg className="float-right mt-0.5 h-4 w-4 text-gray-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clipRule="evenodd" />
                  </svg>
                </button>
                
                {showEmailFilter && (
                  <div className="absolute z-10 mt-1 w-full bg-white shadow-lg max-h-60 rounded-md py-1 text-base ring-1 ring-black ring-opacity-5 overflow-auto focus:outline-none sm:text-sm">
                    <div className="sticky top-0 bg-gray-50 px-3 py-2 border-b">
                      <div className="flex justify-between">
                        <button
                          type="button"
                          onClick={handleSelectAllEmails}
                          className="text-xs text-indigo-600 hover:text-indigo-500"
                        >
                          Select All
                        </button>
                        <button
                          type="button"
                          onClick={handleClearAllEmails}
                          className="text-xs text-gray-500 hover:text-gray-400"
                        >
                          Clear All
                        </button>
                      </div>
                    </div>
                    {uniqueEmails.map((email) => (
                      <div key={email} className="px-3 py-2 hover:bg-gray-50">
                        <label className="flex items-center cursor-pointer">
                          <input
                            type="checkbox"
                            className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                            checked={selectedEmails.includes(email)}
                            onChange={() => handleEmailToggle(email)}
                          />
                          <span className="ml-2 text-sm text-gray-900 truncate">{email}</span>
                          <span className="ml-auto text-xs text-gray-500">
                            ({feedbacks.filter(f => f.user_email === email).length})
                          </span>
                        </label>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
          
          {/* Active Filters Display */}
          {(selectedEmails.length > 0 || filterSentiment !== 'all' || searchTerm) && (
            <div className="mt-4 pt-4 border-t border-gray-200">
              <div className="flex flex-wrap gap-2 items-center">
                <span className="text-sm text-gray-500">Active filters:</span>
                
                {searchTerm && (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                    Search: &quot;{searchTerm}&quot;
                    <button
                      type="button"
                      onClick={() => setSearchTerm('')}
                      className="ml-1 inline-flex items-center justify-center w-4 h-4 rounded-full text-blue-400 hover:bg-blue-200 hover:text-blue-500"
                    >
                      <svg className="w-2 h-2" stroke="currentColor" fill="none" viewBox="0 0 8 8">
                        <path strokeLinecap="round" strokeWidth="1.5" d="m1 1 6 6m0-6L1 7" />
                      </svg>
                    </button>
                  </span>
                )}
                
                {filterSentiment !== 'all' && (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                    Sentiment: {filterSentiment}
                    <button
                      type="button"
                      onClick={() => setFilterSentiment('all')}
                      className="ml-1 inline-flex items-center justify-center w-4 h-4 rounded-full text-green-400 hover:bg-green-200 hover:text-green-500"
                    >
                      <svg className="w-2 h-2" stroke="currentColor" fill="none" viewBox="0 0 8 8">
                        <path strokeLinecap="round" strokeWidth="1.5" d="m1 1 6 6m0-6L1 7" />
                      </svg>
                    </button>
                  </span>
                )}
                
                {selectedEmails.map((email) => (
                  <span key={email} className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                    {email}
                    <button
                      type="button"
                      onClick={() => handleEmailToggle(email)}
                      className="ml-1 inline-flex items-center justify-center w-4 h-4 rounded-full text-purple-400 hover:bg-purple-200 hover:text-purple-500"
                    >
                      <svg className="w-2 h-2" stroke="currentColor" fill="none" viewBox="0 0 8 8">
                        <path strokeLinecap="round" strokeWidth="1.5" d="m1 1 6 6m0-6L1 7" />
                      </svg>
                    </button>
                  </span>
                ))}
                
                <button
                  type="button"
                  onClick={() => {
                    setSearchTerm('');
                    setFilterSentiment('all');
                    setSelectedEmails([]);
                  }}
                  className="text-xs text-gray-500 hover:text-gray-700 underline"
                >
                  Clear all filters
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Batch Actions Bar */}
        {!isDemoMode && selectedFeedbackIds.length > 0 && (
          <div className="mb-4 bg-indigo-50 border border-indigo-200 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <span className="text-sm font-medium text-indigo-900">
                  {selectedFeedbackIds.length} item{selectedFeedbackIds.length > 1 ? 's' : ''} selected
                </span>
                <button
                  onClick={() => setSelectedFeedbackIds([])}
                  className="text-xs text-indigo-600 hover:text-indigo-800 underline"
                >
                  Clear selection
                </button>
              </div>
              
              <div className="flex items-center space-x-2">
                <div className="relative" ref={batchActionsRef}>
                  <button
                    onClick={() => setShowBatchActions(!showBatchActions)}
                    disabled={updatingStatus}
                    className="inline-flex items-center px-3 py-1.5 border border-indigo-300 text-sm font-medium rounded-md text-indigo-700 bg-white hover:bg-indigo-50 disabled:opacity-50"
                  >
                    Update Status
                    <svg className="ml-1 h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>
                  
                  {showBatchActions && (
                    <div className="absolute right-0 mt-2 w-48 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 z-20">
                      <div className="py-1">
                        <button
                          onClick={() => batchUpdateStatus('To Consider')}
                          className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                        >
                          To Consider
                        </button>
                        <button
                          onClick={() => batchUpdateStatus('Considered')}
                          className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                        >
                          Considered
                        </button>
                        <button
                          onClick={() => batchUpdateStatus('Ignored')}
                          className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                        >
                          Ignored
                        </button>
                      </div>
                    </div>
                  )}
                </div>
                
                <button
                  onClick={batchDelete}
                  disabled={deletingFeedback}
                  className="inline-flex items-center px-3 py-1.5 border border-red-300 text-sm font-medium rounded-md text-red-700 bg-white hover:bg-red-50 disabled:opacity-50"
                >
                  <svg className="mr-1 h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                  Delete
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Feedback Table */}
        <div className="bg-white shadow overflow-hidden rounded-lg">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gradient-to-r from-gray-50 to-gray-100">
                <tr>
                  {!isDemoMode && (
                    <th scope="col" className="px-4 py-3.5 w-12">
                      <input
                        type="checkbox"
                        className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded cursor-pointer"
                        checked={selectedFeedbackIds.length === filteredFeedbacks.length && filteredFeedbacks.length > 0}
                        onChange={handleSelectAll}
                      />
                    </th>
                  )}
                  <th scope="col" className="px-4 py-3.5 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    Date
                  </th>
                  <th scope="col" className="px-4 py-3.5 text-center text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    <span className="inline-block">Sentiment</span>
                  </th>
                  <th scope="col" className="px-4 py-3.5 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    User
                  </th>
                  {!isDemoMode && (
                    <th scope="col" className="px-4 py-3.5 text-center text-xs font-semibold text-gray-700 uppercase tracking-wider">
                      Status
                    </th>
                  )}
                  <th scope="col" className="px-4 py-3.5 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    Feedback Details
                  </th>
                  {!isDemoMode && (
                    <th scope="col" className="px-4 py-3.5 text-center text-xs font-semibold text-gray-700 uppercase tracking-wider">
                      <span className="inline-block">Notes</span>
                    </th>
                  )}
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-100">
                {filteredFeedbacks.map((feedback, index) => {
                  // Parse date once for the row
                  const createdDate = feedback.created_at ? new Date(feedback.created_at) : null;
                  const isValidDate = createdDate && !isNaN(createdDate.getTime());
                  const hasNotes = feedback.notes.trim().length > 0;
                  
                  return (
                    <tr 
                      key={feedback.feedback_id || index} 
                      className="hover:bg-blue-50 cursor-pointer transition-all duration-150 ease-in-out group"
                      onClick={(e) => {
                        // Don't open modal if clicking checkbox
                        if ((e.target as HTMLElement).tagName !== 'INPUT') {
                          setSelectedFeedback(feedback);
                        }
                      }}
                    >
                      {!isDemoMode && (
                        <td className="px-4 py-4 whitespace-nowrap" onClick={(e) => e.stopPropagation()}>
                          <input
                            type="checkbox"
                            className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded cursor-pointer"
                            checked={selectedFeedbackIds.includes(feedback.feedback_id)}
                            onChange={() => handleSelectFeedback(feedback.feedback_id)}
                          />
                        </td>
                      )}
                      <td className="px-4 py-4 whitespace-nowrap">
                        {isValidDate ? (
                          <div className="text-sm">
                            <div className="font-medium text-gray-900">
                              {createdDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                            </div>
                            <div className="text-gray-500 text-xs">
                              {createdDate.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
                            </div>
                          </div>
                        ) : (
                          <span className="text-sm text-gray-400 italic">No date</span>
                        )}
                      </td>
                      <td className="px-4 py-4 whitespace-nowrap text-center">
                        <span className={`inline-flex items-center justify-center w-8 h-8 rounded-full text-sm font-semibold ${getSentimentColor(feedback.sentiment)}`}>
                          {feedback.sentiment === 'positive' ? '😊' : feedback.sentiment === 'negative' ? '😞' : '😐'}
                        </span>
                      </td>
                      <td className="px-4 py-4">
                        <div className="max-w-xs">
                          <div className="text-sm font-medium text-gray-900 truncate" title={feedback.user_email}>
                            {feedback.user_email}
                          </div>
                          <div className="text-xs text-gray-500 truncate mt-0.5">
                            {feedback.agent_name}
                          </div>
                        </div>
                      </td>
                      {!isDemoMode && (
                        <td className="px-4 py-4 whitespace-nowrap text-center">
                          <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${
                            feedback.status === 'To Consider' ? 'bg-yellow-100 text-yellow-800 border border-yellow-200' :
                            feedback.status === 'Considered' ? 'bg-green-100 text-green-800 border border-green-200' :
                            'bg-gray-100 text-gray-800 border border-gray-200'
                          }`}>
                            <span className="mr-1">{feedback.status === 'To Consider' ? '⏳' : feedback.status === 'Considered' ? '✓' : '✕'}</span>
                            <span className="hidden lg:inline">{feedback.status}</span>
                          </span>
                        </td>
                      )}
                      <td className="px-4 py-4">
                        <div className="space-y-2 max-w-2xl">
                          <div className="flex items-start">
                            <span className="inline-flex items-center justify-center h-5 w-5 rounded bg-indigo-100 text-indigo-700 text-xs font-bold mr-2 flex-shrink-0">
                              Q
                            </span>
                            <p className="text-sm text-gray-900 line-clamp-2" title={feedback.user_query}>
                              {feedback.user_query}
                            </p>
                          </div>
                          <div className="flex items-start">
                            <span className="inline-flex items-center justify-center h-5 w-5 rounded bg-blue-100 text-blue-700 text-xs font-bold mr-2 flex-shrink-0">
                              F
                            </span>
                            <p className="text-sm text-gray-700 line-clamp-2" title={feedback.feedback}>
                              {feedback.feedback}
                            </p>
                          </div>
                        </div>
                      </td>
                      {!isDemoMode && (
                        <td className="px-4 py-4 text-center whitespace-nowrap">
                          <div className="flex justify-center">
                            {hasNotes ? (
                              <span 
                                className="inline-flex items-center justify-center h-8 w-8 rounded-full bg-indigo-100 group-hover:bg-indigo-200 transition-colors" 
                                title="Has notes"
                              >
                                <svg className="h-5 w-5 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                </svg>
                              </span>
                            ) : (
                              <span 
                                className="inline-flex items-center justify-center h-8 w-8 rounded-full bg-gray-100 group-hover:bg-gray-200 transition-colors" 
                                title="No notes"
                              >
                                <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                </svg>
                              </span>
                            )}
                          </div>
                        </td>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          
          {filteredFeedbacks.length === 0 && (
            <div className="text-center py-12">
              <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
              </svg>
              <p className="mt-2 text-gray-500">No feedback matches your search criteria.</p>
            </div>
          )}
          
          {/* Auto-fetching indicator */}
          {!isDemoMode && autoFetching && (
            <div className="px-4 py-3 border-t border-gray-200 bg-blue-50 text-center">
              <div className="flex items-center justify-center text-sm text-blue-700">
                <svg className="animate-spin h-4 w-4 mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Auto-loading more results... ({filteredFeedbacks.length} of {MIN_VISIBLE_ITEMS} minimum)
              </div>
            </div>
          )}

          {/* Load More Button */}
          {!isDemoMode && hasMore && filteredFeedbacks.length > 0 && !autoFetching && (
            <div className="px-4 py-4 border-t border-gray-200 bg-gray-50 text-center">
              <button
                onClick={loadMoreFeedback}
                disabled={loadingMore}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400 disabled:cursor-not-allowed"
              >
                {loadingMore ? (
                  <>
                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Loading...
                  </>
                ) : (
                  <>
                    <svg className="-ml-1 mr-2 h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                    Load More ({feedbacks.length} of {totalCount})
                  </>
                )}
              </button>
            </div>
          )}
        </div>
      </main>

      {/* Modal for detailed view */}
      {selectedFeedback && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-60 overflow-y-auto h-full w-full z-50 flex items-center justify-center p-4"
          onClick={() => {
            setSelectedFeedback(null);
            setNotesValue('');
          }}
        >
          <div 
            className="relative bg-white rounded-xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="sticky top-0 bg-gradient-to-r from-indigo-600 to-indigo-700 px-6 py-4 flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="flex-shrink-0">
                  <svg className="h-8 w-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z" />
                  </svg>
                </div>
                <div>
                  <h3 className="text-xl font-semibold text-white">Feedback Details</h3>
                  <p className="text-sm text-indigo-200">{selectedFeedback.user_email}</p>
                </div>
              </div>
              <button
                onClick={() => {
                  setSelectedFeedback(null);
                  setNotesValue('');
                }}
                className="text-white hover:text-indigo-200 transition-colors"
              >
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Content */}
            <div className="overflow-y-auto max-h-[calc(90vh-140px)] p-6">
              {/* Metadata Cards */}
              <div className="grid grid-cols-2 gap-4 mb-6">
                <div className="bg-gray-50 rounded-lg p-4">
                  <div className="flex items-center space-x-2 mb-2">
                    <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                    </svg>
                    <span className="text-xs font-medium text-gray-500 uppercase">Agent</span>
                  </div>
                  <p className="text-sm font-medium text-gray-900">{selectedFeedback.agent_name}</p>
                </div>

                <div className="bg-gray-50 rounded-lg p-4">
                  <div className="flex items-center space-x-2 mb-2">
                    <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                    </svg>
                    <span className="text-xs font-medium text-gray-500 uppercase">Partner</span>
                  </div>
                  <p className="text-sm font-medium text-gray-900">{selectedFeedback.partner_name}</p>
                </div>

                <div className="bg-gray-50 rounded-lg p-4">
                  <div className="flex items-center space-x-2 mb-2">
                    <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span className="text-xs font-medium text-gray-500 uppercase">Date</span>
                  </div>
                  <p className="text-sm font-medium text-gray-900">{formatTimestamp(selectedFeedback.created_at)}</p>
                </div>

                <div className="bg-gray-50 rounded-lg p-4">
                  <div className="flex items-center space-x-2 mb-2">
                    <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.828 14.828a4 4 0 01-5.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span className="text-xs font-medium text-gray-500 uppercase">Sentiment</span>
                  </div>
                  <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${getSentimentColor(selectedFeedback.sentiment)}`}>
                    {selectedFeedback.sentiment}
                  </span>
                </div>
              </div>

              {/* Status Control */}
              {!isDemoMode && (
                <div className="mb-6 bg-indigo-50 border border-indigo-200 rounded-lg p-4">
                  <label htmlFor="modal-status" className="block text-sm font-medium text-indigo-900 mb-2">
                    Review Status
                  </label>
                  <div className="flex items-center space-x-3">
                    {['To Consider', 'Considered', 'Ignored'].map((statusOption) => (
                      <button
                        key={statusOption}
                        onClick={() => updateFeedbackStatus(selectedFeedback.feedback_id, statusOption)}
                        disabled={updatingStatus}
                        className={`flex-1 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                          selectedFeedback.status === statusOption
                            ? statusOption === 'To Consider' ? 'bg-yellow-500 text-white'
                            : statusOption === 'Considered' ? 'bg-green-500 text-white'
                            : 'bg-gray-500 text-white'
                            : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
                        } disabled:opacity-50 disabled:cursor-not-allowed`}
                      >
                        {statusOption === 'To Consider' && '⏳ '}
                        {statusOption === 'Considered' && '✓ '}
                        {statusOption === 'Ignored' && '✕ '}
                        {statusOption}
                      </button>
                    ))}
                  </div>
                  {updatingStatus && (
                    <p className="mt-2 text-xs text-indigo-600 flex items-center">
                      <svg className="animate-spin h-3 w-3 mr-1" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Updating...
                    </p>
                  )}
                </div>
              )}

              {/* Conversation Flow */}
              <div className="space-y-4">
                {/* User Query */}
                <div className="bg-blue-50 border-l-4 border-blue-500 rounded-r-lg p-4">
                  <div className="flex items-center mb-2">
                    <svg className="h-5 w-5 text-blue-500 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                    </svg>
                    <span className="text-sm font-semibold text-blue-900">User Query</span>
                  </div>
                  <p className="text-sm text-gray-900 leading-relaxed whitespace-pre-wrap">{selectedFeedback.user_query}</p>
                </div>

                {/* AI Response */}
                <div className="bg-gray-50 border-l-4 border-gray-400 rounded-r-lg p-4">
                  <div className="flex items-center mb-2">
                    <svg className="h-5 w-5 text-gray-500 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <span className="text-sm font-semibold text-gray-900">AI Response</span>
                  </div>
                  <div className="text-sm text-gray-900 leading-relaxed whitespace-pre-wrap max-h-60 overflow-y-auto">
                    {selectedFeedback.ai_response}
                  </div>
                </div>

                {/* User Feedback */}
                <div className={`border-l-4 rounded-r-lg p-4 ${
                  selectedFeedback.sentiment === 'positive' ? 'bg-green-50 border-green-500' :
                  selectedFeedback.sentiment === 'negative' ? 'bg-red-50 border-red-500' :
                  'bg-yellow-50 border-yellow-500'
                }`}>
                  <div className="flex items-center mb-2">
                    <svg className={`h-5 w-5 mr-2 ${
                      selectedFeedback.sentiment === 'positive' ? 'text-green-500' :
                      selectedFeedback.sentiment === 'negative' ? 'text-red-500' :
                      'text-yellow-500'
                    }`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z" />
                    </svg>
                    <span className={`text-sm font-semibold ${
                      selectedFeedback.sentiment === 'positive' ? 'text-green-900' :
                      selectedFeedback.sentiment === 'negative' ? 'text-red-900' :
                      'text-yellow-900'
                    }`}>User Feedback</span>
                  </div>
                  <p className="text-sm text-gray-900 leading-relaxed whitespace-pre-wrap font-medium">
                    {selectedFeedback.feedback}
                  </p>
                </div>

                {/* Admin Notes */}
                {!isDemoMode && (
                  <div className="bg-gray-50 border-l-4 border-gray-400 rounded-r-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center">
                        <svg className="h-5 w-5 mr-2 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                        <span className="text-sm font-semibold text-gray-900">Admin Notes</span>
                      </div>
                      {notesValue !== selectedFeedback.notes && (
                        <button
                          onClick={() => {
                            if (notesValue !== selectedFeedback.notes) {
                              updateFeedbackNotes(selectedFeedback.feedback_id, notesValue);
                            }
                          }}
                          disabled={editingNotes}
                          className="inline-flex items-center px-3 py-1 text-xs font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400 disabled:cursor-not-allowed"
                        >
                          {editingNotes ? (
                            <>
                              <svg className="animate-spin -ml-1 mr-1 h-3 w-3 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                              </svg>
                              Saving...
                            </>
                          ) : (
                            <>
                              <svg className="-ml-1 mr-1 h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                              </svg>
                              Save
                            </>
                          )}
                        </button>
                      )}
                    </div>
                    <textarea
                      value={notesValue}
                      onChange={(e) => setNotesValue(e.target.value)}
                      placeholder="Add notes about how you considered this feedback..."
                      className="w-full mt-2 px-3 py-2 text-sm text-gray-900 bg-white border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500 min-h-[100px] resize-y"
                      onFocus={() => {
                        if (notesValue === '' && selectedFeedback.notes.length > 0) {
                          setNotesValue(selectedFeedback.notes);
                        }
                      }}
                    />
                    {notesValue !== selectedFeedback.notes && (
                      <p className="mt-1 text-xs text-gray-500 italic">
                        You have unsaved changes
                      </p>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Footer Actions */}
            {!isDemoMode && (
              <div className="sticky bottom-0 bg-gray-50 border-t border-gray-200 px-6 py-4 flex items-center justify-between">
                <button
                  onClick={() => setSelectedFeedback(null)}
                  className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900"
                >
                  Close
                </button>
                <button
                  onClick={() => deleteFeedback(selectedFeedback.feedback_id)}
                  disabled={deletingFeedback}
                  className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-lg text-white bg-red-600 hover:bg-red-700 disabled:bg-red-400 disabled:cursor-not-allowed transition-colors shadow-sm"
                >
                  {deletingFeedback ? (
                    <>
                      <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Deleting...
                    </>
                  ) : (
                    <>
                      <svg className="-ml-1 mr-2 h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                      Delete Feedback
                    </>
                  )}
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
