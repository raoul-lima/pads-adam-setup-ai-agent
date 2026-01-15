'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

interface EvaluationStatus {
  adam_api_available: boolean;
  credentials_configured: boolean;
  ready: boolean;
  timestamp: string;
  error?: string;
}

interface EvaluationProgress {
  status: 'idle' | 'ongoing' | 'completed' | 'failed';
  current_test_case: number;
  total_test_cases: number;
  percentage: number;
  current_step: string;
  start_time: string | null;
  end_time: string | null;
  elapsed_seconds: number | null;
  error_message: string | null;
  user_email: string | null;
  partner: string | null;
  preview_only: boolean;
  dry_run: boolean;
}

export default function EvaluationPage() {
  const router = useRouter();
  const [status, setStatus] = useState<EvaluationStatus | null>(null);
  const [progress, setProgress] = useState<EvaluationProgress | null>(null);
  const [running, setRunning] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Use evaluation API URL if set, otherwise fall back to regular backend URL
  const evaluationBackendUrl = process.env.NEXT_PUBLIC_EVALUATION_BACKEND_URL || 
                                process.env.NEXT_PUBLIC_BACKEND_URL || 
                                'http://localhost:8001';

  const checkStatus = async () => {
    try {
      setError(null);
      
      const response = await fetch(`${evaluationBackendUrl}/evaluation/status`);
      
      if (!response.ok) {
        throw new Error(`Failed to check status: ${response.statusText}`);
      }
      
      const data: EvaluationStatus = await response.json();
      setStatus(data);
      
    } catch (err) {
      console.error('Failed to check evaluation status:', err);
      setError(err instanceof Error ? err.message : 'Failed to check status');
    }
  };

  const checkProgress = async () => {
    try {
      const response = await fetch(`${evaluationBackendUrl}/evaluation/progress`);
      
      if (!response.ok) {
        throw new Error(`Failed to check progress: ${response.statusText}`);
      }
      
      const data: EvaluationProgress = await response.json();
      setProgress(data);
      
      // If evaluation has started (status is ongoing), we can stop the "running" state
      // The progress status will handle the rest
      if (data.status === 'ongoing') {
        setRunning(false);
      }
      
    } catch (err) {
      console.error('Failed to check evaluation progress:', err);
    }
  };

  useEffect(() => {
    checkStatus();
    checkProgress();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Poll progress every 5 seconds when evaluation is ongoing or when running (to catch initial state)
  useEffect(() => {
    if (progress?.status === 'ongoing' || running) {
      // Start polling - use shorter interval initially if running, then 5 seconds
      const interval = setInterval(() => {
        checkProgress();
      }, running ? 2000 : 5000); // Poll every 2 seconds when starting, then 5 seconds
      
      // Cleanup function - stops polling when status changes or component unmounts
      return () => {
        clearInterval(interval);
      };
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [progress?.status, running]);

  const runEvaluation = async () => {
    try {
      setRunning(true);
      setError(null);
      setMessage(null);
      
      const response = await fetch(`${evaluationBackendUrl}/evaluation/run`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(errorData.detail || `Failed to run evaluation: ${response.statusText}`);
      }
      
      const data = await response.json();
      setMessage(data.message || 'Evaluation started successfully!');
      
      // Wait a moment for the evaluation to start, then check progress
      // This gives the background thread time to initialize
      setTimeout(async () => {
        await checkProgress();
        // Check again after a short delay to catch the initial progress update
        setTimeout(async () => {
          await checkProgress();
          // Once we confirm evaluation has started, we can set running to false
          // The progress status will handle the rest
          const updatedProgress = await fetch(`${evaluationBackendUrl}/evaluation/progress`)
            .then(res => res.ok ? res.json() : null)
            .catch(() => null);
          if (updatedProgress && updatedProgress.status === 'ongoing') {
            setRunning(false);
          }
        }, 1000);
      }, 500);
      
    } catch (err) {
      console.error('Failed to run evaluation:', err);
      setError(err instanceof Error ? err.message : 'Failed to run evaluation');
      setRunning(false);
    }
  };

  const handleBackToDashboard = () => {
    router.push('/dashboard');
  };

  const handleLogout = () => {
    document.cookie = 'admin-session=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT;';
    router.push('/login');
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">ADAM Evaluation</h1>
              <p className="mt-1 text-sm text-gray-500">
                Run and monitor ADAM agent evaluations
              </p>
            </div>
            <div className="flex space-x-3">
              <button
                onClick={handleBackToDashboard}
                className="bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded-md text-sm font-medium"
              >
                ← Back to Dashboard
              </button>
              <button
                onClick={handleLogout}
                className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-md text-sm font-medium"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        {/* Status Card */}
        <div className="mb-8 bg-white shadow rounded-lg p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold text-gray-900">System Status</h2>
            <button
              onClick={checkStatus}
              className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded-md text-sm font-medium"
            >
              Refresh Status
            </button>
          </div>

          {status ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className={`p-4 rounded-lg ${status.adam_api_available ? 'bg-green-50' : 'bg-red-50'}`}>
                <div className="flex items-center">
                  <div className={`h-3 w-3 rounded-full ${status.adam_api_available ? 'bg-green-500' : 'bg-red-500'}`}></div>
                  <span className="ml-2 text-sm font-medium text-gray-900">ADAM API</span>
                </div>
                <p className="mt-1 text-xs text-gray-500">
                  {status.adam_api_available ? 'Connected' : 'Disconnected'}
                </p>
                <p className="mt-0.5 text-xs text-gray-400">
                  {status.adam_api_available ? 'Ready to process requests' : 'Cannot reach ADAM API'}
                </p>
              </div>

              <div className={`p-4 rounded-lg ${status.credentials_configured ? 'bg-green-50' : 'bg-yellow-50'}`}>
                <div className="flex items-center">
                  <div className={`h-3 w-3 rounded-full ${status.credentials_configured ? 'bg-green-500' : 'bg-yellow-500'}`}></div>
                  <span className="ml-2 text-sm font-medium text-gray-900">Credentials</span>
                </div>
                <p className="mt-1 text-xs text-gray-500">
                  Application Default Credentials
                </p>
                <p className="mt-0.5 text-xs text-gray-400">
                  {status.credentials_configured ? 'Available' : 'Not configured'}
                </p>
              </div>

              <div className={`p-4 rounded-lg ${status.ready ? 'bg-green-50' : 'bg-yellow-50'}`}>
                <div className="flex items-center">
                  <div className={`h-3 w-3 rounded-full ${status.ready ? 'bg-green-500' : 'bg-yellow-500'}`}></div>
                  <span className="ml-2 text-sm font-medium text-gray-900">System Ready</span>
                </div>
                <p className="mt-1 text-xs text-gray-500">
                  {status.ready ? 'Ready to run' : 'Setup required'}
                </p>
              </div>
            </div>
          ) : (
            <div className="text-center py-4">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mx-auto"></div>
              <p className="mt-2 text-sm text-gray-500">Checking system status...</p>
            </div>
          )}

          {status?.error && (
            <div className="mt-4 p-3 bg-red-50 rounded-md">
              <p className="text-sm text-red-800">{status.error}</p>
            </div>
          )}
        </div>

        {/* Run Evaluation Card */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Run Evaluation</h2>
          
          <div className="space-y-4">
            <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
              <h3 className="text-sm font-medium text-blue-900 mb-2">What This Does:</h3>
              <ul className="list-disc list-inside text-sm text-blue-800 space-y-1">
                <li>Reads test cases from the Google Sheet (GOLDEN SET - EVAL tab)</li>
                <li>Runs ADAM agent on each reference input</li>
                <li>Evaluates responses using Gemini LLM-as-a-judge</li>
                <li>Writes results back to the sheet (scores and feedback)</li>
              </ul>
            </div>

            <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4">
              <h3 className="text-sm font-medium text-yellow-900 mb-2">Before You Run:</h3>
              <ul className="list-disc list-inside text-sm text-yellow-800 space-y-1">
                <li>Ensure your Google Sheet has test cases with &quot;USE FOR EVALS&quot; = YES</li>
                <li>Verify Google Application Default Credentials are configured</li>
                <li>Verify GEMINI_API_KEY is set in backend environment</li>
                <li>This process may take several minutes depending on test case count</li>
              </ul>
            </div>

            {message && (
              <div className="bg-green-50 border border-green-200 rounded-md p-4">
                <div className="flex">
                  <svg className="h-5 w-5 text-green-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  <div className="ml-3">
                    <p className="text-sm text-green-800">{message}</p>
                    <p className="mt-2 text-xs text-green-700">Check the backend logs for real-time progress. Results will appear in the Google Sheet when complete.</p>
                  </div>
                </div>
              </div>
            )}

            {error && (
              <div className="bg-red-50 border border-red-200 rounded-md p-4">
                <div className="flex">
                  <svg className="h-5 w-5 text-red-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                  <div className="ml-3">
                    <p className="text-sm text-red-800">{error}</p>
                  </div>
                </div>
              </div>
            )}

            {/* Progress Bar */}
            {(progress && progress.status !== 'idle') || running ? (
              <div className="bg-white border border-gray-200 rounded-md p-4">
                <div className="flex justify-between items-center mb-2">
                  <h3 className="text-sm font-medium text-gray-900">
                    {!progress || progress.status === 'idle' ? 'Starting Evaluation...' :
                     progress.status === 'ongoing' ? 'Evaluation in Progress' :
                     progress.status === 'completed' ? 'Evaluation Completed' :
                     'Evaluation Failed'}
                  </h3>
                  {progress && progress.elapsed_seconds !== null && (
                    <span className="text-xs text-gray-500">
                      {Math.floor(progress.elapsed_seconds / 60)}m {Math.floor(progress.elapsed_seconds % 60)}s
                    </span>
                  )}
                </div>
                
                {(!progress || progress.status === 'idle') && running && (
                  <>
                    <div className="w-full bg-gray-200 rounded-full h-2.5 mb-2">
                      <div
                        className="bg-indigo-600 h-2.5 rounded-full animate-pulse"
                        style={{ width: '10%' }}
                      ></div>
                    </div>
                    <div className="text-xs text-gray-600">
                      Initializing evaluation...
                    </div>
                  </>
                )}
                
                {progress && progress.status === 'ongoing' && (
                  <>
                    <div className="w-full bg-gray-200 rounded-full h-2.5 mb-2">
                      <div
                        className="bg-indigo-600 h-2.5 rounded-full transition-all duration-300"
                        style={{ width: `${Math.min(Math.max(progress.percentage || 0, 0), 100)}%` }}
                      ></div>
                    </div>
                    <div className="flex justify-between items-center text-xs text-gray-600">
                      <span>
                        {progress.total_test_cases > 0 ? (
                          <>Test case {progress.current_test_case || 0} of {progress.total_test_cases} ({(progress.percentage || 0).toFixed(1)}%)</>
                        ) : (
                          <>Preparing test cases...</>
                        )}
                      </span>
                      <span className="text-indigo-600 font-medium">{progress.current_step || 'Initializing...'}</span>
                    </div>
                  </>
                )}
                
                {progress && progress.status === 'completed' && (
                  <div className="text-sm text-green-700">
                    ✅ Completed {progress.total_test_cases} test cases successfully
                  </div>
                )}
                
                {progress && progress.status === 'failed' && (
                  <div className="text-sm text-red-700">
                    ❌ {progress.error_message || 'Evaluation failed'}
                  </div>
                )}
              </div>
            ) : null}

            <div className="flex justify-center">
              <button
                onClick={runEvaluation}
                disabled={running || progress?.status === 'ongoing' || !status?.ready}
                className="bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400 disabled:cursor-not-allowed text-white px-8 py-3 rounded-md text-base font-medium flex items-center transition-all"
              >
                {running ? (
                  <>
                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Starting Evaluation...
                  </>
                ) : progress?.status === 'ongoing' ? (
                  <>
                    <svg className="animate-pulse -ml-1 mr-2 h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    Evaluation Running...
                  </>
                ) : (
                  <>
                    <svg className="-ml-1 mr-2 h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                    </svg>
                    Run Evaluation
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Documentation Link */}
        <div className="mt-8 bg-white shadow rounded-lg p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Documentation</h2>
          <div className="space-y-3">
            <div>
              <h3 className="text-sm font-medium text-gray-700">Google Sheet</h3>
              <a
                href="https://docs.google.com/spreadsheets/d/1zKQqEHnUzLTH3WAZFj3bGON53Jp_JWiXQ_NN4Wlp_wE/edit"
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-indigo-600 hover:text-indigo-500"
              >
                Open Evaluation Sheet (GOLDEN SET - EVAL) →
              </a>
            </div>
            <div>
              <h3 className="text-sm font-medium text-gray-700">Evaluation API URL</h3>
              <p className="text-sm text-gray-600">{evaluationBackendUrl}</p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

