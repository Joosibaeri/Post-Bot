import React, { useEffect, useState } from 'react';
import { useFocusTrap } from '@/hooks/useFocusTrap';

interface FeedbackModalProps {
    isOpen: boolean;
    onClose: () => void;
    defaultEmail?: string;
    userId?: string;
    getToken?: () => Promise<string | null>;
    autoTriggered?: boolean;
    autoDismissSeconds?: number;
}

export function FeedbackModal({ isOpen, onClose, defaultEmail = '' }: FeedbackModalProps) {
    const [bugTitle, setBugTitle] = useState('');
    const [bugDescription, setBugDescription] = useState('');
    const [userEmail, setUserEmail] = useState(defaultEmail);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [successMessage, setSuccessMessage] = useState('');
    const [errorMessage, setErrorMessage] = useState('');
    const trapRef = useFocusTrap<HTMLDivElement>(isOpen);

    useEffect(() => {
        if (isOpen) {
            setUserEmail(defaultEmail);
            setSuccessMessage('');
            setErrorMessage('');
        }
    }, [isOpen, defaultEmail]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setSuccessMessage('');
        setErrorMessage('');

        setIsSubmitting(true);
        try {
            const payload = {
                bug_title: bugTitle,
                bug_description: bugDescription,
                user_email: userEmail,
            };

            const apiBase = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '') || '';
            const endpointCandidates = [
                apiBase ? `${apiBase}/api/feedback` : '',
                '/api/backend/api/feedback',
            ];

            let response: Response | null = null;

            for (const endpoint of endpointCandidates) {
                if (!endpoint || endpoint === '/api/feedback') continue;
                try {
                    const candidateResponse = await fetch(endpoint, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(payload),
                    });

                    response = candidateResponse;
                    if (candidateResponse.status === 201) break;
                    if (candidateResponse.status !== 404) break;
                } catch {
                    // Try next candidate endpoint.
                }
            }

            if (response?.status === 201) {
                setSuccessMessage('Bug report sent. Thank you for helping improve PostBot.');
                setBugTitle('');
                setBugDescription('');
                setUserEmail(defaultEmail);
            } else {
                const errorPayload = await response?.json().catch(() => ({} as any));
                const statusCode = response?.status || 0;
                if (statusCode === 404) {
                    setErrorMessage('Bug endpoint not found. Restart backend and confirm NEXT_PUBLIC_API_URL is set to your API server.');
                } else {
                    setErrorMessage(errorPayload?.detail || errorPayload?.message || 'Could not submit bug report. Please try again.');
                }
            }
        } catch (error) {
            setErrorMessage('Network error while submitting bug report. Please try again.');
        } finally {
            setIsSubmitting(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" ref={trapRef}>
            <button
                type="button"
                aria-label="Close report bug modal"
                className="absolute inset-0 bg-black/60 backdrop-blur-sm"
                onClick={onClose}
            />

            <div
                role="dialog"
                aria-modal="true"
                aria-labelledby="report-bug-title"
                className="relative w-full max-w-xl rounded-2xl border border-white/10 bg-gray-900 text-white shadow-2xl"
            >
                <div className="flex items-center justify-between border-b border-white/10 px-5 py-4">
                    <div>
                        <h2 id="report-bug-title" className="text-lg font-semibold">Report a Bug</h2>
                        <p className="text-sm text-gray-300">Share what happened and we will investigate quickly.</p>
                    </div>
                    <button
                        type="button"
                        onClick={onClose}
                        className="rounded-md p-2 text-gray-300 hover:bg-white/10 hover:text-white"
                        aria-label="Close"
                    >
                        <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="space-y-4 px-5 py-5">
                    <div>
                        <label htmlFor="bug_title" className="mb-1 block text-sm font-medium text-gray-200">Bug title</label>
                        <input
                            id="bug_title"
                            type="text"
                            value={bugTitle}
                            onChange={(e) => setBugTitle(e.target.value)}
                            required
                            className="w-full rounded-lg border border-white/15 bg-white/5 px-3 py-2 text-sm text-white placeholder-gray-400 focus:border-blue-400 focus:outline-none"
                            placeholder="Short summary of the issue"
                        />
                    </div>

                    <div>
                        <label htmlFor="bug_description" className="mb-1 block text-sm font-medium text-gray-200">Bug description</label>
                        <textarea
                            id="bug_description"
                            value={bugDescription}
                            onChange={(e) => setBugDescription(e.target.value)}
                            required
                            rows={5}
                            className="w-full rounded-lg border border-white/15 bg-white/5 px-3 py-2 text-sm text-white placeholder-gray-400 focus:border-blue-400 focus:outline-none"
                            placeholder="What were you trying to do, and what happened instead?"
                        />
                    </div>

                    <div>
                        <label htmlFor="user_email" className="mb-1 block text-sm font-medium text-gray-200">Email</label>
                        <input
                            id="user_email"
                            type="email"
                            value={userEmail}
                            onChange={(e) => setUserEmail(e.target.value)}
                            required
                            className="w-full rounded-lg border border-white/15 bg-white/5 px-3 py-2 text-sm text-white placeholder-gray-400 focus:border-blue-400 focus:outline-none"
                            placeholder="you@example.com"
                        />
                    </div>

                    {successMessage && (
                        <p className="rounded-md border border-emerald-400/40 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-200">{successMessage}</p>
                    )}
                    {errorMessage && (
                        <p className="rounded-md border border-red-400/40 bg-red-500/10 px-3 py-2 text-sm text-red-200">{errorMessage}</p>
                    )}

                    <div className="flex justify-end gap-3 pt-1">
                        <button
                            type="button"
                            onClick={onClose}
                            className="rounded-lg border border-white/20 px-4 py-2 text-sm font-medium text-gray-200 hover:bg-white/10"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            disabled={isSubmitting}
                            className="inline-flex items-center rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-70"
                        >
                            {isSubmitting ? 'Submitting...' : 'Submit Bug'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}

export default FeedbackModal;
