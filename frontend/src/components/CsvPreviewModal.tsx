import React, { useEffect, useMemo, useState, useCallback } from 'react';
import { Download, X, ExternalLink } from 'lucide-react';
import { apiService } from '@/services/api';

export type CsvPreviewModalProps = {
  url: string;
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  cacheKey?: string;
  maxRowsToParse?: number;
};

// Simple in-memory cache for parsed CSVs
const csvCache = new Map<string, { 
  headers: string[]; 
  rows: string[][];
  total_rows: number;
}>();

function useCsvData(url: string | null, cacheKey?: string) {
  const [headers, setHeaders] = useState<string[] | null>(null);
  const [rows, setRows] = useState<string[][] | null>(null);
  const [totalRows, setTotalRows] = useState<number>(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);

  const key = useMemo(() => (cacheKey ? cacheKey : url || ''), [url, cacheKey]);

  const loadMoreRows = useCallback(async (offset: number, limit: number = 100) => {
    if (!url) return;

    try {
      setLoadingMore(true);
      const data = await apiService.getCsvPreview(url, offset, limit);
      
      setRows(prevRows => {
        const newRows = prevRows ? [...prevRows, ...data.rows] : data.rows;
        // Update cache
        if (headers) {
          csvCache.set(key, { 
            headers, 
            rows: newRows,
            total_rows: data.total_rows
          });
        }
        return newRows;
      });
      
      setLoadingMore(false);
      return data.has_more;
    } catch (e: unknown) {
      setLoadingMore(false);
      throw e;
    }
  }, [url, key, headers]);

  useEffect(() => {
    if (!url) return;

    const cached = csvCache.get(key);
    if (cached) {
      setHeaders(cached.headers);
      setRows(cached.rows);
      setTotalRows(cached.total_rows);
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);
    setHeaders(null);
    setRows(null);

    // Fetch initial batch from backend
    apiService.getCsvPreview(url, 0, 100)
      .then(data => {
        if (cancelled) return;
        
        setHeaders(data.headers);
        setRows(data.rows);
        setTotalRows(data.total_rows);
        setLoading(false);
        
        // Cache the data
        csvCache.set(key, { 
          headers: data.headers, 
          rows: data.rows,
          total_rows: data.total_rows
        });
      })
      .catch(err => {
        if (!cancelled) {
          setError(err.message || 'Failed to fetch CSV');
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [url, key]);

  return { headers, rows, totalRows, loading, error, loadingMore, loadMoreRows };
}

// Helper functions for detecting special data types
function isUrl(str: string): boolean {
  try {
    const trimmed = str.trim();
    return trimmed.startsWith('http://') || trimmed.startsWith('https://') || trimmed.startsWith('www.');
  } catch {
    return false;
  }
}

function isFormattedList(str: string): boolean {
  const trimmed = str.trim();
  
  // Pattern 1: Check for structured data in parentheses format
  // like (value1; value2; value3; ...) - these should be mini-tables
  const parenthesesWithSemicolonPattern = /\([^)]+;[^)]+\)/;
  if (parenthesesWithSemicolonPattern.test(trimmed)) {
    return true; // This is structured data for mini-table
  }
  
  // Pattern 2: Simple semicolon-separated list of platform/tool names
  // e.g., "Google Ad Manager; Magnite DV+; OpenX" or with parentheses like "Xandr - Monetize SSP (AppNexus)"
  const parts = trimmed.split(';').map(p => p.trim()).filter(p => p.length > 0);
  
  if (parts.length >= 2) {
    // Check if it looks like platform/tool names or IDs (not sentences)
    const looksLikePlatforms = parts.every(part => {
      // Platform names are typically 1-6 words, may contain special chars and parentheses
      // Remove content in parentheses for word count check
      const withoutParentheses = part.replace(/\([^)]*\)/g, '').trim();
      const wordCount = withoutParentheses.split(/\s+/).filter(w => w.length > 0).length;
      return wordCount <= 6 && 
             !part.includes(':') && // No colons (not key:value pairs)
             part.length <= 60; // Reasonably short (increased for names with parentheses)
    });
    
    if (looksLikePlatforms) {
      return true;
    }
  }
  
  return false;
}

function parseFormattedList(str: string): Array<string[]> {
  const trimmed = str.trim();
  const items: Array<string[]> = [];
  
  // Check if this has structured data in parentheses (with semicolons inside)
  const hasStructuredParentheses = /\([^)]+;[^)]+\)/.test(trimmed);
  
  if (hasStructuredParentheses) {
    // Parse structured data from parentheses
    const segmentMatches = trimmed.match(/\([^)]+;[^)]+\)/g);
    if (segmentMatches) {
      segmentMatches.forEach((segmentMatch) => {
        const cleanSegment = segmentMatch.replace(/^\(|\)$/g, '');
        const fields = cleanSegment.split(';').map(field => field.trim());
        if (fields.length > 0) {
          items.push(fields);
        }
      });
    }
  } else {
    // Simple semicolon-separated list (may include items with parentheses like "Xandr (AppNexus)")
    const fields = trimmed.split(';').map(field => field.trim()).filter(f => f.length > 0);
    if (fields.length >= 1) {
      items.push(fields);
    }
  }
  
  return items;
}

// List Modal Component
function ListModal({ items, isOpen, onClose, title }: { items: string[], isOpen: boolean, onClose: () => void, title: string }) {
  if (!isOpen) return null;
  
  return (
    <div className="fixed inset-0 bg-black/50 z-[60] flex items-center justify-center" onClick={onClose}>
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full max-h-[60vh] overflow-hidden" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
          <h4 className="font-semibold text-sm text-gray-900">{title}</h4>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="p-4 overflow-y-auto max-h-[50vh]">
          {items.length === 0 ? (
            <p className="text-sm text-gray-500">No items to display</p>
          ) : (
            <ul className="space-y-1">
              {items.map((item, index) => (
                <li key={index} className="text-sm text-gray-700 py-1 px-2 hover:bg-gray-50 rounded">
                  <span className="text-gray-400 mr-2">{index + 1}.</span>
                  {isUrl(item) ? (
                    <a href={item} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                      {item}
                    </a>
                  ) : (
                    item
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}

// Cell renderer component
function TableCell({ value }: { value: string }) {
  // Check for URLs
  if (isUrl(value)) {
    return (
      <div className="px-3 py-2">
        <a 
          href={value.startsWith('www.') ? `https://${value}` : value}
          target="_blank"
          rel="noopener noreferrer"
          className="text-blue-600 hover:underline inline-flex items-center gap-1 text-xs"
          title={value}
        >
          <span className="truncate max-w-[200px]">{value}</span>
          <ExternalLink className="h-3 w-3 flex-shrink-0" />
        </a>
      </div>
    );
  }

  // Check if this is likely an anomaly description FIRST
  // (contains semicolons and descriptive text with keywords)
  const isAnomalyText = value.includes(';') && 
                        (value.includes('Missing') || 
                         value.includes('exclusions') || 
                         value.includes('not set') ||
                         value.includes('should be') ||
                         value.includes('expected') ||
                         value.includes('Safeguards') ||
                         value.includes('required') ||
                         value.includes('disabled') ||
                         (value.includes(':') && (value.includes('Issues') || value.includes('Mismatch'))));
  
  if (isAnomalyText) {
    // Split by semicolon and display as a list of issues
    const issues = value.split(';').map(s => s.trim()).filter(s => s.length > 0);
    return (
      <div className="px-3 py-2 text-xs text-gray-700">
        {issues.length === 1 ? (
          <span title={value}>{issues[0]}</span>
        ) : (
          <ul className="space-y-1">
            {issues.map((issue, idx) => (
              <li key={idx} className="flex items-start">
                <span className="text-gray-400 mr-1">•</span>
                <span className="break-words">{issue}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    );
  }
  
  // Check for formatted lists (semicolon-separated)
  if (isFormattedList(value)) {
    const items = parseFormattedList(value);
    // Check if this is structured data with semicolons inside parentheses
    const hasStructuredParentheses = /\([^)]+;[^)]+\)/.test(value);
    
    if (hasStructuredParentheses && items.length > 0) {
      // Grouped lists - show as mini-table
      return (
        <div className="p-2">
          <div className="overflow-x-auto">
            <table className="text-xs border border-gray-200 rounded">
              <tbody>
                {items.map((item, idx) => (
                  <tr key={idx} className={idx > 0 ? "border-t border-gray-100" : ""}>
                    {item.map((field, fieldIdx) => (
                      <td key={fieldIdx} className="px-2 py-1 text-gray-700 whitespace-nowrap">
                        {field || <span className="italic text-gray-400">-</span>}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      );
    } else if (items.length === 1) {
      // Simple lists - show as chips
      return (
        <div className="p-2">
          <div className="flex flex-wrap gap-1">
            {items[0].map((val, idx) => (
              <span 
                key={idx}
                className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 border border-blue-200"
                title={val}
              >
                {val}
              </span>
            ))}
          </div>
        </div>
      );
    }
  }
  
  // Regular cell
  return (
    <div className="px-3 py-2 truncate text-xs text-gray-700" title={value}>
      {value || <span className="italic text-gray-400">empty</span>}
    </div>
  );
}

export default function CsvPreviewModal({ 
  url, 
  isOpen, 
  onClose, 
  title = 'Data table preview', 
  cacheKey, 
}: CsvPreviewModalProps) {
  const [listModalData, setListModalData] = useState<{ items: string[], title: string } | null>(null);
  
  const { headers, rows, totalRows, loading, error, loadingMore, loadMoreRows } = useCsvData(
    isOpen ? url : null, 
    cacheKey
  );

  // Extract filename from URL
  const downloadFilename = useMemo(() => {
    if (!url) return 'data.csv';
    try {
      const urlObj = new URL(url);
      const pathname = urlObj.pathname;
      const filename = pathname.split('/').pop() || 'data.csv';
      return filename.endsWith('.csv') ? filename : `${filename}.csv`;
    } catch {
      return 'data.csv';
    }
  }, [url]);

  // Handle scroll to load more rows from backend
  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    const element = e.currentTarget;
    const threshold = 200;
    
    // Check if user scrolled near bottom and we have more data to load
    if (element.scrollHeight - element.scrollTop - element.clientHeight < threshold) {
      if (rows && rows.length < totalRows && !loadingMore) {
        // Load more data from backend
        loadMoreRows(rows.length, 100).catch(err => {
          console.error('Failed to load more rows:', err);
        });
      }
    }
  }, [rows, totalRows, loadingMore, loadMoreRows]);

  if (!isOpen) return null;

  return (
    <>
      <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" onClick={onClose}>
        <div className="bg-white text-gray-900 rounded-lg shadow-xl w-full max-w-[95vw] h-[85vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
            <h3 className="font-semibold text-lg text-gray-900">{title}</h3>
            <div className="flex items-center space-x-3">
              <a
                href={url}
                download={downloadFilename}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center text-sm px-4 py-2 rounded-md text-white transition-colors bg-teal-500 hover:bg-teal-600"
                title={`Download ${downloadFilename}`}
              >
                <Download className="h-4 w-4 mr-2" />
                Download CSV
              </a>
              <button 
                onClick={onClose} 
                className="inline-flex items-center text-sm text-gray-600 hover:text-gray-900 p-2 rounded-md hover:bg-gray-100 transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-hidden flex flex-col p-6">
            {loading && (
              <div className="flex items-center justify-center h-full">
                <div className="text-gray-500">Loading data...</div>
              </div>
            )}
            
            {error && (
              <div className="flex items-center justify-center h-full">
                <div className="text-red-500">Error: {error}</div>
              </div>
            )}
            
            {!loading && !error && headers && rows && (
              <div className="flex-1 overflow-auto border border-gray-200 rounded-lg" onScroll={handleScroll}>
                <table className="w-full">
                  <thead className="sticky top-0 bg-gray-50 z-10">
                    <tr>
                      {headers.map((header, idx) => (
                        <th 
                          key={idx} 
                          className="px-3 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-200 bg-gray-50"
                          style={{ minWidth: '150px' }}
                        >
                          {header}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-100">
                    {rows.map((row, rowIdx) => (
                      <tr key={rowIdx} className="hover:bg-gray-50 transition-colors">
                        {row.map((cell, cellIdx) => (
                          <td 
                            key={cellIdx} 
                            className="border-r border-gray-100 last:border-r-0"
                            style={{ minWidth: '150px', maxWidth: '400px' }}
                          >
                            <TableCell value={cell} />
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
                
                {loadingMore && (
                  <div className="text-center py-4 bg-gray-50 border-t border-gray-200">
                    <div className="text-sm text-gray-500">Loading more rows...</div>
                  </div>
                )}
                
                {!loadingMore && rows.length < totalRows && (
                  <div className="text-center py-4 bg-gray-50 border-t border-gray-200">
                    <div className="text-sm text-gray-600">
                      Scroll down to load more rows ({rows.length} of {totalRows} loaded)
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="px-6 py-3 border-t border-gray-200 bg-gray-50">
            <div className="flex items-center justify-between">
              <div className="text-sm text-gray-600">
                {rows && headers && (
                  <span>
                    {rows.length} of {totalRows} rows × {headers.length} columns loaded
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
      
      {/* List Modal */}
      {listModalData && (
        <ListModal 
          items={listModalData.items}
          isOpen={true}
          onClose={() => setListModalData(null)}
          title={listModalData.title}
        />
      )}
    </>
  );
}