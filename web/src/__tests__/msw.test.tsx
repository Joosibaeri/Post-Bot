import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useDashboardData } from '@/hooks/useDashboardData';

// Wrapper for React Query
const createTestQueryClient = () => new QueryClient({
  defaultOptions: {
    queries: { retry: false },
  },
});

export function Wrapper({ children }: { children: React.ReactNode }) {
  const queryClient = createTestQueryClient();
  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}

function TestComponent() {
  const { stats, isLoading } = useDashboardData({ userId: 'test_user_id' });
  if (isLoading) return <div>Loading...</div>;
  return <div data-testid="generated-posts">{stats.posts_generated}</div>;
}

describe('MSW Setup', () => {
  it('should mock API calls with useDashboardData', async () => {
    render(<TestComponent />, { wrapper: Wrapper });
    expect(screen.getByText('Loading...')).toBeInTheDocument();
    
    // MSW should return 15 for stats.posts_generated
    await waitFor(() => {
      expect(screen.getByTestId('generated-posts')).toHaveTextContent('15');
    });
  });
});
