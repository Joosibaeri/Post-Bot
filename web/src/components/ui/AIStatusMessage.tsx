/**
 * AIStatusMessage — Chat-bubble-style status messages from the bot
 *
 * Displays animated, typewriter-effect messages during AI operations
 * like scanning, generating, and publishing. Personalised with the user's name.
 *
 * Usage:
 *   const ai = useAIStatus();
 *   ai.show("Scanning your activity, Alex...");
 *   ai.update("Found 5 things to talk about...");
 *   ai.complete("All done! 5 posts ready.");
 *
 *   <AIStatusMessage {...ai} />
 */

import { useState, useEffect, useRef, useCallback } from 'react';

// ─── Types ────────────────────────────────────────────────────────────────────

export interface StatusMessage {
  id: number;
  text: string;
  type: 'thinking' | 'progress' | 'success' | 'error';
  timestamp: number;
}

export interface AIStatusState {
  messages: StatusMessage[];
  isActive: boolean;
}

export interface AIStatusActions {
  show: (message: string, type?: StatusMessage['type']) => void;
  update: (message: string, type?: StatusMessage['type']) => void;
  complete: (message: string) => void;
  error: (message: string) => void;
  dismiss: () => void;
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

let _msgId = 0;

export function useAIStatus(): AIStatusState & AIStatusActions {
  const [messages, setMessages] = useState<StatusMessage[]>([]);
  const [isActive, setIsActive] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearTimer = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const addMessage = useCallback((text: string, type: StatusMessage['type']) => {
    setMessages(prev => [
      ...prev,
      { id: ++_msgId, text, type, timestamp: Date.now() },
    ]);
  }, []);

  /** Start a new operation — clears previous messages */
  const show = useCallback((message: string, type: StatusMessage['type'] = 'thinking') => {
    clearTimer();
    setIsActive(true);
    setMessages([{ id: ++_msgId, text: message, type, timestamp: Date.now() }]);
  }, [clearTimer]);

  /** Add a progress update (appends to the conversation) */
  const update = useCallback((message: string, type: StatusMessage['type'] = 'progress') => {
    addMessage(message, type);
  }, [addMessage]);

  /** Mark the operation as complete — auto-dismiss after delay */
  const complete = useCallback((message: string) => {
    addMessage(message, 'success');
    clearTimer();
    timerRef.current = setTimeout(() => {
      setIsActive(false);
      setMessages([]);
    }, 4500);
  }, [addMessage, clearTimer]);

  /** Show an error — auto-dismiss after delay */
  const error = useCallback((message: string) => {
    addMessage(message, 'error');
    clearTimer();
    timerRef.current = setTimeout(() => {
      setIsActive(false);
      setMessages([]);
    }, 5500);
  }, [addMessage, clearTimer]);

  /** Immediately dismiss */
  const dismiss = useCallback(() => {
    clearTimer();
    setIsActive(false);
    setMessages([]);
  }, [clearTimer]);

  // Cleanup on unmount
  useEffect(() => () => clearTimer(), [clearTimer]);

  return { messages, isActive, show, update, complete, error, dismiss };
}

// ─── Typewriter Component ─────────────────────────────────────────────────────

function Typewriter({ text, speed = 18, onComplete }: { text: string; speed?: number; onComplete?: () => void }) {
  const [displayed, setDisplayed] = useState('');
  const indexRef = useRef(0);

  useEffect(() => {
    setDisplayed('');
    indexRef.current = 0;

    const interval = setInterval(() => {
      indexRef.current += 1;
      if (indexRef.current <= text.length) {
        setDisplayed(text.slice(0, indexRef.current));
      } else {
        clearInterval(interval);
        onComplete?.();
      }
    }, speed);

    return () => clearInterval(interval);
  }, [text, speed, onComplete]);

  return <>{displayed}</>;
}

// ─── Thinking Dots ────────────────────────────────────────────────────────────

function ThinkingDots() {
  return (
    <span className="inline-flex items-center gap-0.5 ml-1">
      <span className="w-1.5 h-1.5 bg-current rounded-full animate-bounce [animation-delay:0ms]" />
      <span className="w-1.5 h-1.5 bg-current rounded-full animate-bounce [animation-delay:150ms]" />
      <span className="w-1.5 h-1.5 bg-current rounded-full animate-bounce [animation-delay:300ms]" />
    </span>
  );
}

// ─── Icon by type ─────────────────────────────────────────────────────────────

function StatusIcon({ type }: { type: StatusMessage['type'] }) {
  switch (type) {
    case 'thinking':
      return (
        <div className="w-5 h-5 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
      );
    case 'progress':
      return <span className="text-sm">⚡</span>;
    case 'success':
      return <span className="text-sm">✅</span>;
    case 'error':
      return <span className="text-sm">❌</span>;
  }
}

// ─── Single Message Bubble ────────────────────────────────────────────────────

function MessageBubble({
  message,
  isLatest,
}: {
  message: StatusMessage;
  isLatest: boolean;
}) {
  const bgMap: Record<StatusMessage['type'], string> = {
    thinking:
      'bg-gradient-to-r from-blue-500/10 to-indigo-500/10 border-blue-200/50 dark:from-blue-500/20 dark:to-indigo-500/20 dark:border-blue-400/30',
    progress:
      'bg-gradient-to-r from-amber-500/10 to-orange-500/10 border-amber-200/50 dark:from-amber-500/20 dark:to-orange-500/20 dark:border-amber-400/30',
    success:
      'bg-gradient-to-r from-emerald-500/10 to-green-500/10 border-emerald-200/50 dark:from-emerald-500/20 dark:to-green-500/20 dark:border-emerald-400/30',
    error:
      'bg-gradient-to-r from-red-500/10 to-rose-500/10 border-red-200/50 dark:from-red-500/20 dark:to-rose-500/20 dark:border-red-400/30',
  };

  const textMap: Record<StatusMessage['type'], string> = {
    thinking: 'text-blue-700 dark:text-blue-300',
    progress: 'text-amber-700 dark:text-amber-300',
    success: 'text-emerald-700 dark:text-emerald-300',
    error: 'text-red-700 dark:text-red-300',
  };

  return (
    <div
      className={`
        flex items-start gap-2.5 px-4 py-3 rounded-2xl rounded-tl-sm border backdrop-blur-sm
        transition-all duration-500 ease-out
        ${bgMap[message.type]} ${textMap[message.type]}
        ${isLatest ? 'opacity-100 translate-y-0' : 'opacity-60 scale-[0.97]'}
      `}
      style={{
        animation: 'slideInUp 0.35s cubic-bezier(0.16, 1, 0.3, 1)',
      }}
    >
      <div className="flex-shrink-0 mt-0.5">
        <StatusIcon type={message.type} />
      </div>
      <p className="text-sm font-medium leading-relaxed flex-1">
        {isLatest ? (
          <>
            <Typewriter text={message.text} speed={16} />
            {message.type === 'thinking' && <ThinkingDots />}
          </>
        ) : (
          <>
            {message.text}
            {message.type === 'thinking' && <ThinkingDots />}
          </>
        )}
      </p>
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export function AIStatusMessage({
  messages,
  isActive,
  dismiss,
}: AIStatusState & Pick<AIStatusActions, 'dismiss'>) {
  if (!isActive || messages.length === 0) return null;

  // Show last 3 messages max
  const visibleMessages = messages.slice(-3);

  return (
    <>
      {/* Keyframes for slide-in animation */}
      <style jsx global>{`
        @keyframes slideInUp {
          from {
            opacity: 0;
            transform: translateY(8px) scale(0.97);
          }
          to {
            opacity: 1;
            transform: translateY(0) scale(1);
          }
        }
      `}</style>

      <div
        className="relative my-4 transition-all duration-300"
        role="status"
        aria-live="polite"
      >
        {/* Bot header */}
        <div className="flex items-center gap-2 mb-2">
          <div className="w-7 h-7 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center shadow-md shadow-blue-500/20">
            <span className="text-xs">🤖</span>
          </div>
          <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
            Post Bot
          </span>
          <button
            onClick={dismiss}
            className="ml-auto text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors p-1 rounded-md hover:bg-gray-100 dark:hover:bg-white/10"
            aria-label="Dismiss status messages"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Messages */}
        <div className="space-y-2 pl-9">
          {visibleMessages.map((msg, i) => (
            <MessageBubble
              key={msg.id}
              message={msg}
              isLatest={i === visibleMessages.length - 1}
            />
          ))}
        </div>
      </div>
    </>
  );
}

export default AIStatusMessage;
