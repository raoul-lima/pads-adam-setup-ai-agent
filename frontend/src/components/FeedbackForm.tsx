import { useState } from 'react';
import { ThumbsUp, ThumbsDown, Send, Loader2 } from 'lucide-react';
import { apiService } from '@/services/api';

interface FeedbackFormProps {
  message: {
    user_query: string;
    ai_response: string;
  };
  partnerName: string;
  onFeedbackSent: () => void;
}

const FeedbackForm = ({ message, partnerName, onFeedbackSent }: FeedbackFormProps) => {
  const [feedback, setFeedback] = useState('');
  const [sentiment, setSentiment] = useState<'positive' | 'negative' | null>(null);
  const [showInput, setShowInput] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleIconClick = (type: 'positive' | 'negative') => {
    setSentiment(type);
    setShowInput(true);
  };

  const handleFeedbackSubmit = async () => {
    if (feedback.trim() && sentiment && !isLoading) {
      setIsLoading(true);
      try {
        await apiService.sendFeedback({
          ...message,
          feedback: feedback,
          partner_name: partnerName,
          sentiment: sentiment,
        });
        onFeedbackSent(); // Notify parent component
        // Reset state for next feedback
        setFeedback('');
        setShowInput(false);
        setSentiment(null);
      } catch (error) {
        console.error('Failed to send feedback:', error);
      } finally {
        setIsLoading(false);
      }
    }
  };

  return (
    <div className="mt-2 flex items-start space-x-2">
      {!showInput && !isLoading && (
         <div className="flex space-x-2 items-center">
           <button 
             onClick={() => handleIconClick('positive')}
             title="Send positive feedback"
             className="p-1.5 rounded-full hover:bg-[var(--ai-bubble-background)] text-[var(--text-secondary)] hover:text-green-500 transition-colors"
           >
             <ThumbsUp className="h-4 w-4" />
           </button>
           <button 
             onClick={() => handleIconClick('negative')}
             title="Send negative / improvement feedback"
             className="p-1.5 rounded-full hover:bg-[var(--ai-bubble-background)] text-[var(--text-secondary)] hover:text-red-500 transition-colors"
           >
             <ThumbsDown className="h-4 w-4" />
           </button>
         </div>
      )}

      {showInput && (
        <div className="flex items-center space-x-2 w-full max-w-2xl">
          <textarea
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            placeholder={"Commentaire :\nReponse parfaite :\nScore / 100"}
            className="w-full px-3 py-2 text-sm bg-white text-gray-900 border border-gray-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-indigo-500 min-h-[120px] resize-none"
            rows={6}
            disabled={isLoading}
          />
          <button 
            onClick={handleFeedbackSubmit} 
            className="text-indigo-600 hover:text-indigo-800 self-start mt-2 disabled:opacity-50 disabled:cursor-not-allowed"
            disabled={isLoading}
          >
            {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          </button>
        </div>
      )}
    </div>
  );
};

export default FeedbackForm; 