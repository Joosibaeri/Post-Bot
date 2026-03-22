/**
 * Integration Tests for PostBot Dashboard
 *
 * Tests the core user flows with MSW mocking the backend API:
 * 1. Dashboard data loading (useDashboardData hook)
 * 2. Post generation flow (generatePreview API)
 * 3. Post publishing flow (publishPost API)
 * 4. Post scheduling flow (schedulePost API)
 * 5. Error handling (API failures, network errors)
 */
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { http, HttpResponse } from 'msw';
import { server } from '@/mocks/server';
import { useDashboardData } from '@/hooks/useDashboardData';
import { generatePreview, publishPost, schedulePost } from '@/lib/api';

// ============================================================================
// TEST UTILITIES
// ============================================================================

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
}

function TestWrapper({ children }: { children: React.ReactNode }) {
  const queryClient = createTestQueryClient();
  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}

// ============================================================================
// 1. DASHBOARD DATA LOADING TESTS
// ============================================================================

describe('Dashboard Data Loading', () => {
  // Helper component that exposes hook data
  function DashboardTestComponent() {
    const data = useDashboardData({ userId: 'test_user_id' });
    
    if (data.isLoading) return <div data-testid="loading">Loading...</div>;
    
    return (
      <div>
        <div data-testid="posts-generated">{data.stats.posts_generated}</div>
        <div data-testid="posts-published">{data.stats.posts_published}</div>
        <div data-testid="credits-remaining">{data.stats.credits_remaining}</div>
        <div data-testid="growth">{data.stats.growth_percentage}</div>
        <div data-testid="post-count">{data.posts.length}</div>
        <div data-testid="tier">{data.usage?.tier || 'none'}</div>
        <div data-testid="posts-remaining">{data.usage?.posts_remaining ?? 'none'}</div>
        <div data-testid="github-username">{data.githubUsername}</div>
        <div data-testid="github-activities">{data.githubActivities.length}</div>
        <div data-testid="templates">{data.templates.length}</div>
        <div data-testid="persona-complete">{String(data.personaComplete)}</div>
        {data.isError && <div data-testid="error">Error occurred</div>}
      </div>
    );
  }

  it('should load dashboard stats correctly', async () => {
    render(<DashboardTestComponent />, { wrapper: TestWrapper });
    
    expect(screen.getByTestId('loading')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByTestId('posts-generated')).toHaveTextContent('15');
    });
    expect(screen.getByTestId('posts-published')).toHaveTextContent('8');
    expect(screen.getByTestId('credits-remaining')).toHaveTextContent('35');
    expect(screen.getByTestId('growth')).toHaveTextContent('12.5');
  });

  it('should load post history', async () => {
    render(<DashboardTestComponent />, { wrapper: TestWrapper });
    
    await waitFor(() => {
      expect(screen.getByTestId('post-count')).toHaveTextContent('2');
    });
  });

  it('should load usage data with tier info', async () => {
    render(<DashboardTestComponent />, { wrapper: TestWrapper });
    
    await waitFor(() => {
      expect(screen.getByTestId('tier')).toHaveTextContent('free');
    });
    expect(screen.getByTestId('posts-remaining')).toHaveTextContent('3');
  });

  it('should load templates', async () => {
    render(<DashboardTestComponent />, { wrapper: TestWrapper });
    
    await waitFor(() => {
      expect(screen.getByTestId('templates')).toHaveTextContent('2');
    });
  });

  it('should load GitHub activities and auto-detect username', async () => {
    render(<DashboardTestComponent />, { wrapper: TestWrapper });
    
    await waitFor(() => {
      expect(screen.getByTestId('github-username')).toHaveTextContent('testuser');
    });
    
    await waitFor(() => {
      expect(screen.getByTestId('github-activities')).toHaveTextContent('2');
    });
  });

  it('should evaluate persona completeness', async () => {
    render(<DashboardTestComponent />, { wrapper: TestWrapper });
    
    await waitFor(() => {
      expect(screen.getByTestId('persona-complete')).toHaveTextContent('true');
    });
  });

  it('should show error state when stats API fails', async () => {
    server.use(
      http.get(`${API_BASE}/api/stats/:userId`, () => {
        return new HttpResponse(null, { status: 500 });
      })
    );
    
    render(<DashboardTestComponent />, { wrapper: TestWrapper });
    
    await waitFor(() => {
      expect(screen.getByTestId('error')).toBeInTheDocument();
    });
  });

  it('should fallback to defaults when stats return empty object', async () => {
    server.use(
      http.get(`${API_BASE}/api/stats/:userId`, () => {
        return HttpResponse.json({});
      })
    );
    
    render(<DashboardTestComponent />, { wrapper: TestWrapper });
    
    await waitFor(() => {
      // DashboardStatsSchema uses .default(0) for all fields
      expect(screen.getByTestId('posts-generated')).toHaveTextContent('0');
    });
  });
});

// ============================================================================
// 2. POST GENERATION FLOW TESTS
// ============================================================================

describe('Post Generation Flow', () => {
  it('should generate a preview post', async () => {
    const result = await generatePreview({
      user_id: 'test_user_id',
      context: { type: 'push', commits: 3, repo: 'web', full_repo: 'postbot/web' },
      model: 'groq',
    }, 'mock_token');

    expect(result.post).toBeTruthy();
    expect(result.post.length).toBeGreaterThan(50);
    expect(result.provider).toBe('groq');
    expect(result.was_downgraded).toBe(false);
  });

  it('should handle generation failure gracefully', async () => {
    server.use(
      http.post(`${API_BASE}/api/post/generate-preview`, () => {
        return new HttpResponse(null, { status: 429, statusText: 'Rate Limited' });
      })
    );

    await expect(
      generatePreview({ user_id: 'test_user_id' }, 'mock_token')
    ).rejects.toThrow('Failed to generate preview');
  });

  it('should handle 500 server error on generation', async () => {
    server.use(
      http.post(`${API_BASE}/api/post/generate-preview`, () => {
        return new HttpResponse(null, { status: 500, statusText: 'Internal Server Error' });
      })
    );

    await expect(
      generatePreview({ user_id: 'test_user_id' }, 'mock_token')
    ).rejects.toThrow('Failed to generate preview');
  });
});

// ============================================================================
// 3. POST PUBLISHING FLOW TESTS
// ============================================================================

describe('Post Publishing Flow', () => {
  it('should publish a post successfully', async () => {
    const result = await publishPost({
      user_id: 'test_user_id',
      post_content: 'This is my LinkedIn post!',
      test_mode: false,
    }, 'mock_token');

    expect(result.success).toBe(true);
    expect(result.post_url).toContain('linkedin.com');
  });

  it('should publish in test mode', async () => {
    server.use(
      http.post(`${API_BASE}/api/post/publish`, async () => {
        return HttpResponse.json({
          success: true,
          post: 'Test mode: post content echoed back',
        });
      })
    );

    const result = await publishPost({
      user_id: 'test_user_id',
      post_content: 'Test post',
      test_mode: true,
    }, 'mock_token');

    expect(result.success).toBe(true);
    expect(result.post).toBeTruthy();
  });

  it('should handle publish failure with error detail', async () => {
    server.use(
      http.post(`${API_BASE}/api/post/publish`, () => {
        return HttpResponse.json(
          { detail: 'LinkedIn token expired. Please re-authenticate.' },
          { status: 401 }
        );
      })
    );

    await expect(
      publishPost({ user_id: 'test_user_id', post_content: 'test' }, 'mock_token')
    ).rejects.toThrow('LinkedIn token expired');
  });

  it('should include image_url when publishing with image', async () => {
    const result = await publishPost({
      user_id: 'test_user_id',
      post_content: 'Post with image!',
      image_url: 'https://images.unsplash.com/photo-123',
    }, 'mock_token');

    expect(result.success).toBe(true);
  });
});

// ============================================================================
// 4. POST SCHEDULING FLOW TESTS
// ============================================================================

describe('Post Scheduling Flow', () => {
  it('should schedule a post successfully', async () => {
    const result = await schedulePost({
      user_id: 'test_user_id',
      post_content: 'Scheduled post for tomorrow!',
      scheduled_time: Date.now() + 86400000, // Tomorrow
    }, 'mock_token');

    expect(result.success).toBe(true);
    expect(result.scheduled_id).toBe('sched-mock-123');
  });

  it('should handle scheduling failure', async () => {
    server.use(
      http.post(`${API_BASE}/api/scheduled`, () => {
        return new HttpResponse(null, { status: 400, statusText: 'Bad Request' });
      })
    );

    await expect(
      schedulePost({
        user_id: 'test_user_id',
        post_content: 'test',
        scheduled_time: Date.now() - 1000, // Past time
      }, 'mock_token')
    ).rejects.toThrow('Failed to schedule post');
  });
});

// ============================================================================
// 5. FULL DRAFT → GENERATE → PUBLISH FLOW
// ============================================================================

describe('Draft → Generate → Publish (E2E Flow)', () => {
  it('should complete the full post creation lifecycle', async () => {
    // Step 1: Generate preview
    const preview = await generatePreview({
      user_id: 'test_user_id',
      context: { type: 'push', commits: 3, repo: 'web', full_repo: 'postbot/web' },
      model: 'groq',
    }, 'mock_token');

    expect(preview.post).toBeTruthy();
    expect(preview.post.length).toBeGreaterThan(0);

    // Step 2: Publish the generated post
    const publishResult = await publishPost({
      user_id: 'test_user_id',
      post_content: preview.post,
      test_mode: false,
    }, 'mock_token');

    expect(publishResult.success).toBe(true);
    expect(publishResult.post_url).toBeTruthy();
  });

  it('should complete generate → edit → publish flow', async () => {
    // Step 1: Generate
    const preview = await generatePreview({
      user_id: 'test_user_id',
      context: { type: 'push', commits: 5, repo: 'api', full_repo: 'postbot/api' },
    }, 'mock_token');

    // Step 2: Simulate editing (user modifies the text)
    const editedPost = preview.post + '\n\nEdited by the user ✏️';

    // Step 3: Publish edited version
    const result = await publishPost({
      user_id: 'test_user_id',
      post_content: editedPost,
    }, 'mock_token');

    expect(result.success).toBe(true);
  });

  it('should complete generate → schedule flow', async () => {
    // Step 1: Generate
    const preview = await generatePreview({
      user_id: 'test_user_id',
      context: { type: 'push', commits: 2, repo: 'cli', full_repo: 'postbot/cli' },
    }, 'mock_token');

    // Step 2: Schedule for tomorrow at 9 AM
    const tomorrow9am = new Date();
    tomorrow9am.setDate(tomorrow9am.getDate() + 1);
    tomorrow9am.setHours(9, 0, 0, 0);

    const result = await schedulePost({
      user_id: 'test_user_id',
      post_content: preview.post,
      scheduled_time: tomorrow9am.getTime(),
    }, 'mock_token');

    expect(result.success).toBe(true);
    expect(result.scheduled_id).toBeTruthy();
  });
});

// ============================================================================
// 6. NETWORK & ERROR RESILIENCE TESTS
// ============================================================================

describe('Network Resilience', () => {
  it('should handle network failure on API calls', async () => {
    server.use(
      http.post(`${API_BASE}/api/post/generate-preview`, () => {
        return HttpResponse.error();
      })
    );

    await expect(
      generatePreview({ user_id: 'test_user_id' }, 'mock_token')
    ).rejects.toThrow();
  });

  it('should handle malformed JSON response', async () => {
    server.use(
      http.get(`${API_BASE}/api/stats/:userId`, () => {
        return new HttpResponse('not json at all', {
          headers: { 'Content-Type': 'text/html' }
        });
      })
    );

    // This should cause a Zod parse error when useDashboardData tries to parse
    function BrokenStatsComponent() {
      const data = useDashboardData({ userId: 'test_user_id' });
      if (data.isLoading) return <div>Loading...</div>;
      if (data.errors.stats) return <div data-testid="stats-error">Stats failed</div>;
      return <div data-testid="stats-ok">OK</div>;
    }

    render(<BrokenStatsComponent />, { wrapper: TestWrapper });

    await waitFor(() => {
      expect(screen.getByTestId('stats-error')).toBeInTheDocument();
    });
  });

  it('should handle 401 Unauthorized gracefully', async () => {
    server.use(
      http.get(`${API_BASE}/api/posts/:userId`, () => {
        return HttpResponse.json(
          { detail: 'Authentication required' },
          { status: 401 }
        );
      })
    );

    function AuthTestComponent() {
      const data = useDashboardData({ userId: 'test_user_id' });
      if (data.isLoading) return <div>Loading...</div>;
      if (data.errors.posts) return <div data-testid="auth-error">Auth failed</div>;
      return <div data-testid="posts-ok">{data.posts.length} posts</div>;
    }

    render(<AuthTestComponent />, { wrapper: TestWrapper });

    await waitFor(() => {
      expect(screen.getByTestId('auth-error')).toBeInTheDocument();
    });
  });
});
