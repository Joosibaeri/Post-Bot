import '@/styles/globals.css'
import type { AppProps } from 'next/app'
import { useRouter } from 'next/router'
import { useState } from 'react'
import { Toaster } from 'react-hot-toast'
import { QueryClient, QueryClientProvider, QueryCache } from '@tanstack/react-query'
import { ThemeProvider } from '@/components/ThemeProvider'
import { showToast } from '@/lib/toast'
import ErrorBoundary from '@/components/ErrorBoundary'
import SkipToContent from '@/components/SkipToContent'
import AnimatedBackground from '@/components/ui/AnimatedBackground'
import { Inter } from 'next/font/google'

import { ClerkProvider } from '@clerk/nextjs'

// Configure Inter font with next/font for zero layout shift
const inter = Inter({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-inter',
})

export default function App({ Component, pageProps }: AppProps) {
  const router = useRouter();
  const isOnboarding = router.pathname === '/onboarding';

  // Initialize QueryClient with useState to prevent recreation on re-renders
  // This ensures the cache persists across component updates
  const [queryClient] = useState(() => new QueryClient({
    queryCache: new QueryCache({
      onError: (error: any) => {
        // Suppress toast for expected/handled error types:
        // 1. HTTP errors from our api client (e.g. "Failed to fetch /api/stats: Unauthorized")
        // 2. Zod validation errors (schema mismatches)
        // 3. Abort/timeout errors
        // 4. Network errors when backend is unreachable
        // These are already surfaced via each query's isError state.
        const message = error?.message || '';
        const isHttpError = message.startsWith('Failed to fetch') || message.startsWith('Failed to post');
        const isZodError = error?.name === 'ZodError';
        const isAbortError = error?.name === 'AbortError';
        const isNetworkError = message === 'Failed to fetch' || message.includes('NetworkError');

        if (isHttpError || isZodError || isAbortError || isNetworkError) {
          console.warn('Query Error (suppressed toast):', message);
          return;
        }

        console.error('Query Error:', error);
        showToast.error('An unexpected data error occurred. Please try refreshing.');
      },
    }),
    defaultOptions: {
      queries: {
        staleTime: 1000 * 60 * 5, // 5 minutes
        gcTime: 1000 * 60 * 30, // 30 minutes (formerly cacheTime)
        refetchOnWindowFocus: false, // Disable auto-refetch on focus for better UX
        retry: 1, // Only retry failed requests once
      },
    },
  }));

  return (
    <ClerkProvider {...pageProps}>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider>
          <ErrorBoundary>
            {/* Apply Inter font to entire app with zero layout shift */}
            <div className={`${inter.variable} font-sans`}>
              {/* Global animated background - Interactive particle theme on all pages EXCEPT onboarding */}
              {!isOnboarding && (
                <AnimatedBackground intensity="subtle" variant="interactive" fixed={true} />
              )}
              <SkipToContent />
              {/* Page transition: fade-in on route change */}
              <div key={router.pathname} className="page-transition">
                <Component {...pageProps} />
              </div>
              <Toaster />
            </div>
          </ErrorBoundary>
        </ThemeProvider>
      </QueryClientProvider>
    </ClerkProvider>
  )
}
