'use client';

import { useState, useEffect, useRef } from 'react';
import Image from 'next/image';
import { apiService } from '@/services/api';
import { Message } from '@/types/api';
import { Send, User, RotateCcw, Download, Table } from 'lucide-react';
import CsvPreviewModal from './CsvPreviewModal';
import MarkdownRenderer from './MarkdownRenderer';
import FeedbackForm from './FeedbackForm';

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [loadingText, setLoadingText] = useState('Thinking...');
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [feedbackSent, setFeedbackSent] = useState<{[messageIndex: number]: boolean}>({});
  const [isBetaPopoverVisible, setIsBetaPopoverVisible] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const loadingTimerRef = useRef<NodeJS.Timeout | null>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    if (messagesContainerRef.current && messagesEndRef.current) {
      // Use manual scroll instead of scrollIntoView to prevent propagation
      const container = messagesContainerRef.current;
      const scrollTop = messagesEndRef.current.offsetTop - container.offsetTop;
      container.scrollTo({ top: scrollTop, behavior: 'smooth' });
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    loadConversationHistory();
    setTimeout(() => {
      inputRef.current?.focus();
    }, 100);
  }, []);

  // Comprehensive scroll propagation prevention
  useEffect(() => {
    const messagesContainer = messagesContainerRef.current;
    if (!messagesContainer) return;

    // Prevent all wheel events from propagating beyond this container
    const handleWheel = (e: WheelEvent) => {
      e.stopPropagation();
      
      const { scrollTop, scrollHeight, clientHeight } = messagesContainer;
      const isAtTop = scrollTop === 0;
      const isAtBottom = scrollTop + clientHeight >= scrollHeight - 1;

      // Only prevent default at boundaries to stop propagation completely
      if ((isAtTop && e.deltaY < 0) || (isAtBottom && e.deltaY > 0)) {
        e.preventDefault();
      }
    };

    // Prevent touch scroll propagation
    const handleTouchMove = (e: TouchEvent) => {
      e.stopPropagation();
    };

    // Prevent other scroll events
    const handleScroll = (e: Event) => {
      e.stopPropagation();
    };

    // Add event listeners with explicit options
    messagesContainer.addEventListener('wheel', handleWheel, { passive: false, capture: true });
    messagesContainer.addEventListener('touchmove', handleTouchMove, { passive: false, capture: true });
    messagesContainer.addEventListener('scroll', handleScroll, { passive: true, capture: true });
    
    return () => {
      messagesContainer.removeEventListener('wheel', handleWheel);
      messagesContainer.removeEventListener('touchmove', handleTouchMove);
      messagesContainer.removeEventListener('scroll', handleScroll);
    };
  }, []);

  const loadConversationHistory = async () => {
    try {
      const history = await apiService.getConversationHistory();
      setMessages(history.messages);
      setConversationId(history.conversation_id);
    } catch (error) {
      console.error('Failed to load conversation history:', error);
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim() || isLoading) return;

    const userMessage: Message = {
      type: 'human',
      content: inputMessage,
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    const currentInput = inputMessage;
    setInputMessage('');
    setIsLoading(true);
    setLoadingText('Thinking...');

    if (loadingTimerRef.current) {
      clearTimeout(loadingTimerRef.current);
    }

    loadingTimerRef.current = setTimeout(() => {
      setLoadingText('Analysing...');
    }, 10000);

    try {
      const response = await apiService.sendMessage(currentInput);
      
      const aiMessage: Message = {
        type: 'ai',
        content: response.response,
        timestamp: response.timestamp,
        download_links: response.download_links,
      };

      setMessages(prev => [...prev, aiMessage]);
      setConversationId(response.conversation_id);
    } catch (error: unknown) {
      const errorMessage: Message = {
        type: 'ai',
        content: `Error: ${error instanceof Error ? error.message : 'Failed to send message. Please try again.'}`,
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      if (loadingTimerRef.current) {
        clearTimeout(loadingTimerRef.current);
      }
      setTimeout(() => {
        inputRef.current?.focus();
      }, 100);
    }
  };

  const handleResetConversation = async () => {
    try {
      await apiService.resetConversation();
      setMessages([]);
      setConversationId(null);
      setFeedbackSent({});
    } catch (error) {
      console.error('Failed to reset conversation:', error);
    }
  };

  const handleFeedbackSent = (messageIndex: number) => {
    setFeedbackSent(prev => ({ ...prev, [messageIndex]: true }));
    setTimeout(() => {
      setFeedbackSent(prev => ({ ...prev, [messageIndex]: false }));
    }, 3000); // Hide message after 3 seconds
  };

  const suggestedQuestions = [

    "Review the viewability settings for Line Item [Name/ID] to ensure it's optimized.",
    "Analyze the settings for Campaign [Name/ID] for invalid traffic and brand safety.",
    "Check the targeting settings for Campaign [Name/ID].",
    "Analyze the budget pacing for Insertion Order [Name/ID].",
    "Review the quality settings for Line Item [Name/ID].",
    "I would like to create a new partner on Adsecura, can you help me?",
    "How are advertisers assigned to an user on Adsecura?",
    "Help me to trigger the verification for a partner in the AdKeeper tool on Adsecura.",
    "Guide me to set up a Brand Lift measurement in DV360.",
    "How do I access the 'BudgetKeeper' application from 'Adsecura'?",
    "What are the procedures to modify a partner on Adsecura?",
    "How to export the list of partners from the Adsecura site?",
    "How to modify an user's license on Adsecura.",
    "How to create a campaign in CM360?"
  ];

  return (
    <div className="flex flex-col h-screen bg-[var(--background)]" style={{ overscrollBehavior: 'contain' }}>
      {/* Header */}
      <header className="bg-[var(--card-background)] border-b border-[var(--border-color)] px-6 py-4">
        <div className="flex items-center space-x-3 min-h-[60px]">
          <div className="h-10 w-10 relative">
            <Image src="/adsecura_logo.png" alt="Adsecura Logo" layout="fill" objectFit="contain" />
          </div>
          <div>
            <div className="flex items-center space-x-2 relative">
              <h1 className="text-xl font-semibold text-[var(--text-primary)]">Adam Setup Agent</h1>
              <div 
                className="relative"
                onMouseEnter={() => setIsBetaPopoverVisible(true)}
                onMouseLeave={() => setIsBetaPopoverVisible(false)}
              >
                <span className="cursor-pointer px-2 py-1 text-xs font-semibold text-green-800 bg-green-200 bg-opacity-50 rounded-md border border-green-300 backdrop-blur-sm">
                  Beta | v0.2.1
                </span>
                {isBetaPopoverVisible && (
                  <div className="absolute top-full right-0 mt-2 w-64 bg-[var(--card-background)] border border-[var(--border-color)] rounded-lg shadow-lg p-3 z-50">
                    <h4 className="font-bold text-sm mb-2 text-[var(--text-primary)]">Key Features:</h4>
                    <ul className="list-disc list-inside text-xs text-[var(--text-secondary)] space-y-1">
                      <li><strong>DV360 Data Analysis:</strong> Analyze campaigns and line items using natural language.</li>
                      <li><strong>Automated Audits:</strong> Check naming conventions, brand safety, and targeting.</li>
                      <li><strong>Multi-Platform Expertise:</strong> Get expert support for Adsecura platform, and Google, Amazon & Microsoft advertising platforms.</li>
                      <li><strong>Downloadable Results:</strong> Export your analysis results.</li>
                      <li><strong>Multi-Lingual & Secure:</strong> Converse securely in English, French, Spanish, Dutch, and Polish.</li>
                    </ul>
                  </div>
                )}
              </div>
            </div>
            <p className="text-sm text-[var(--text-secondary)]">
              {conversationId ? `Conversation: ${conversationId.slice(0, 8)}...` : 'New conversation'}
            </p>
          </div>
        </div>
      </header>

      {/* Persistent Disclaimer */}
      <div className="bg-[var(--card-background)] border-b border-[var(--border-color)] px-6 py-1">
        <p className="text-xs text-[var(--text-secondary)] opacity-60">
          📅 Working with yesterday&apos;s data (refreshed daily) not live data from current DV360 UI.
        </p>
      </div>

      {/* Messages */}
      <main ref={messagesContainerRef} className="flex-1 overflow-y-auto px-6 py-4 space-y-4 bg-[var(--card-background)]" style={{ overscrollBehavior: 'contain', scrollBehavior: 'smooth' }}>
        {messages.length === 0 ? (
          <div className="text-center py-12">
            <div className="h-16 w-16 relative mx-auto mb-4">
              <Image src="/adsecura_logo.png" alt="Adsecura Logo" layout="fill" objectFit="contain" />
            </div>
            <h3 className="text-lg font-medium text-[var(--text-primary)] mb-2">
              Welcome to Adam Setup Agent
            </h3>
            <p className="text-[var(--text-secondary)] mb-6">
              Ask me anything about your DV360 campaigns and data analysis.
            </p>
            <div className="bg-[var(--card-background)] border border-[var(--border-color)] rounded-lg p-3 mb-6 max-w-2xl mx-auto">
              <p className="text-xs text-[var(--text-secondary)] opacity-75">
                <span className="inline-block mb-1">⚠️ Adam Setup Agent can make mistakes - verify important information and share feedback to help improve.</span>
                <br />
                <span>📅 Using yesterday&apos;s DV360 data snapshot (refreshed daily) - not live data from current DV360 UI.</span>
              </p>
            </div>
            <div className="max-w-2xl mx-auto">
              <h4 className="text-sm font-medium text-[var(--text-primary)] mb-3">Try asking:</h4>
              <div className="grid gap-2">
                {suggestedQuestions.map((question, index) => (
                  <button
                    key={index}
                    onClick={() => setInputMessage(question)}
                    className="text-left p-3 bg-[var(--card-background)] border border-[var(--border-color)] rounded-lg text-[var(--text-primary)] hover:bg-gray-100 transition-colors text-sm"
                  >
                    {question}
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          messages.map((message, index) => (
            <div
              key={index}
              className={`flex items-start space-x-4 ${message.type === 'human' ? 'justify-end' : 'justify-start'}`}
            >
              {/* Message Bubble */}
              <div
                className={`flex max-w-3xl ${
                  message.type === 'human' ? 'flex-row-reverse space-x-reverse' : 'flex-row'
                } space-x-3`}
              >
                <div
                  className={`flex-shrink-0 h-8 w-8 rounded-full flex items-center justify-center relative ${
                    message.type === 'human'
                      ? 'bg-[var(--user-bubble-background)] text-[var(--user-bubble-text)]'
                      : 'bg-[var(--ai-bubble-background)] text-[var(--ai-bubble-text)]'
                  }`}
                >
                  {message.type === 'human' ? (
                    <User className="h-4 w-4" />
                  ) : (
                    <div className="h-5 w-5 relative">
                      <Image src="/adsecura_logo.png" alt="Adsecura Logo" layout="fill" objectFit="contain" />
                    </div>
                  )}
                </div>
                <div
                  className={`px-4 py-3 rounded-lg ${
                    message.type === 'human'
                      ? 'bg-[var(--user-bubble-background)] text-[var(--user-bubble-text)]'
                      : 'bg-[var(--ai-bubble-background)] border border-[var(--border-color)] text-[var(--ai-bubble-text)]'
                  } ${message.type === 'ai' ? 'ai-message' : ''}`}
                >
                  <div className="prose prose-sm max-w-none">
                    <MarkdownRenderer 
                      content={message.content} 
                      isAI={message.type === 'ai'} 
                    />
                  </div>
                  {message.download_links && message.download_links.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-[var(--border-color)]">
                      <h4 className="text-xs font-semibold mb-2 text-[var(--text-secondary)]">Downloadable contents:</h4>
                      <div className="flex flex-col space-y-2">
                        {message.download_links.map((link, i) => (
                          <div key={i} className="flex items-center space-x-2">
                            {/* Preview button with label */}
                            <button
                              type="button"
                              onClick={() => setPreviewUrl(link.url)}
                              className="inline-flex items-center text-sm px-3 py-1.5 rounded-md border border-gray-300 text-gray-700 hover:bg-blue-50 hover:text-blue-700 hover:border-blue-300 hover:shadow-sm transition-all duration-200 transform hover:scale-[1.02]"
                              title="Preview data table"
                            >
                              <Table className="h-4 w-4 mr-2 transition-transform group-hover:scale-110" />
                              <span>{link.label}</span>
                            </button>
                            {/* Download button */}
                            <a
                              href={link.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center text-xs px-2.5 py-1 rounded-md bg-blue-500 text-white hover:bg-blue-600 transition-colors"
                              title="Download"
                            >
                              <Download size={14} className="mr-1" />
                              Download
                            </a>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  <div
                    className={`text-xs mt-2 ${
                      message.type === 'human' ? 'text-teal-200' : 'text-[var(--text-secondary)]'
                    }`}
                  >
                    {new Date(message.timestamp).toLocaleTimeString()}
                  </div>
                </div>
              </div>

              {/* Feedback Form (for AI messages) */}
              {message.type === 'ai' && (
                <div className="flex-shrink-0">
                  <FeedbackForm
                    message={{
                      user_query: messages[index - 1]?.content || '',
                      ai_response: message.content,
                    }}
                    partnerName={"partner"} // This needs to be sourced from URL now
                    onFeedbackSent={() => handleFeedbackSent(index)}
                  />
                  {feedbackSent[index] && (
                    <p className="text-xs text-green-500 mt-2">Feedback received!</p>
                  )}
                </div>
              )}
            </div>
          ))
        )}
        
        {isLoading && (
          <div className="flex justify-start">
            <div className="flex items-center space-x-3 max-w-3xl">
              <div className="flex-shrink-0 h-8 w-8 relative">
                <Image 
                  src="/adsecura_logo.png" 
                  alt="Adsecura Logo" 
                  layout="fill" 
                  objectFit="contain" 
                  className="animate-spin"
                />
              </div>
              <div className="bg-transparent rounded-lg px-4 py-3">
                <p className="text-[var(--text-secondary)] animate-pulse">{loadingText}</p>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </main>

      {/* CSV Preview Modal */}
      <CsvPreviewModal
        url={previewUrl || ''}
        isOpen={Boolean(previewUrl)}
        onClose={() => setPreviewUrl(null)}
        title="Data table preview"
      />

      {/* Input */}
      <footer className="bg-[var(--card-background)] border-t border-[var(--border-color)] px-6 py-4">
        <form onSubmit={handleSendMessage} className="flex items-center space-x-4">
          <button
              type="button"
              onClick={handleResetConversation}
              title="Reset conversation"
              className="p-3 text-green-600 bg-green-500/10 hover:bg-green-500/20 rounded-full focus:outline-none focus:ring-2 focus:ring-green-500 transition-colors"
              aria-label="Reset conversation"
          >
              <RotateCcw className="h-5 w-5" />
          </button>
          <div className="flex-1">
            <input
              ref={inputRef}
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSendMessage(e);
                }
              }}
              placeholder="Ask me anything..."
              className="w-full px-4 py-3 border border-[var(--border-color)] rounded-lg focus:outline-none focus:ring-2 focus:ring-[var(--brand-teal)] text-[var(--text-primary)] placeholder-[var(--text-secondary)] bg-[var(--input-background)]"
              disabled={isLoading}
            />
          </div>
          <button
            type="submit"
            disabled={isLoading || !inputMessage.trim()}
            title="Send message to Adam"
            className="px-6 py-3 bg-[var(--brand-teal)] text-[var(--text-light)] rounded-lg hover:bg-[var(--brand-teal-hover)] focus:outline-none focus:ring-2 focus:ring-[var(--brand-teal)] focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Send className="h-5 w-5" />
          </button>
        </form>
        <p className="text-xs text-center text-[var(--text-secondary)] mt-2">
          Adam Setup Agent can make mistakes, verify important information and give your feedback as much as possible to help us improve its capabilities.
        </p>
      </footer>
    </div>
  );
} 