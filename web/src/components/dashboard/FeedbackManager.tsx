import React, { useState, useEffect } from 'react';
import dynamic from 'next/dynamic';

const FeedbackModal = dynamic(() => import('@/components/modals/FeedbackModal'));

interface FeedbackManagerProps {
    publishCount: number;
    userId: string;
    getToken: () => Promise<string | null>;
}

export const FeedbackManager: React.FC<FeedbackManagerProps> = ({ publishCount, userId, getToken }) => {
    const [showFeedback, setShowFeedback] = useState(false);
    const [feedbackAutoTriggered, setFeedbackAutoTriggered] = useState(false);

    // Auto-trigger on 2nd publish
    useEffect(() => {
        if (publishCount === 2) {
            const hasSubmitted = localStorage.getItem('hasSubmittedFeedback') === 'true';
            const hasDismissed = localStorage.getItem('feedbackDismissed') === 'true';

            if (!hasSubmitted && !hasDismissed) {
                setFeedbackAutoTriggered(true);
                setShowFeedback(true);
            }
        }
    }, [publishCount]);

    return (
        <>
            <button
                onClick={() => {
                    setFeedbackAutoTriggered(false);
                    setShowFeedback(true);
                }}
                className="px-4 py-2 bg-gradient-to-r from-purple-500/10 to-pink-500/10 border-2 border-purple-300 dark:border-purple-500/30 text-purple-700 dark:text-purple-300 rounded-lg hover:from-purple-500/20 hover:to-pink-500/20 transition-all flex items-center"
                aria-label="Give feedback"
            >
                <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
                Feedback
            </button>

            {showFeedback && (
                <FeedbackModal
                    isOpen={showFeedback}
                    onClose={() => {
                        setShowFeedback(false);
                        if (feedbackAutoTriggered) {
                            localStorage.setItem('feedbackDismissed', 'true');
                        }
                        setFeedbackAutoTriggered(false);
                    }}
                    userId={userId}
                    getToken={getToken}
                    autoTriggered={feedbackAutoTriggered}
                    autoDismissSeconds={35}
                />
            )}
        </>
    );
};
