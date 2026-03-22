import { http, HttpResponse } from 'msw';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const handlers = [
  // =========================================================================
  // Dashboard Stats - GET /api/stats/:userId
  // Must match DashboardStatsSchema (all fields have .default(0))
  // =========================================================================
  http.get(`${API_BASE}/api/stats/:userId`, () => {
    return HttpResponse.json({
      posts_generated: 15,
      credits_remaining: 35,
      posts_published: 8,
      posts_published_this_month: 3,
      posts_scheduled: 2,
      posts_this_month: 5,
      posts_this_week: 2,
      posts_last_week: 1,
      growth_percentage: 12.5,
      draft_posts: 4
    });
  }),

  // =========================================================================
  // Posts History - GET /api/posts/:userId
  // Must match PostsResponseSchema -> { posts: DashboardPostSchema[] }
  // =========================================================================
  http.get(`${API_BASE}/api/posts/:userId`, () => {
    return HttpResponse.json({
      posts: [
        {
          id: 'test-post-1',
          content: 'Just pushed a major update to PostBot! 🚀',
          status: 'published',
          context: { type: 'push', repo: 'postbot' },
          created_at: Date.now() / 1000,
          published_at: Date.now() / 1000,
        },
        {
          id: 'test-post-2',
          content: 'Working on new AI features for automated posting.',
          status: 'draft',
          context: { type: 'generic' },
          created_at: Date.now() / 1000,
        }
      ]
    });
  }),

  // =========================================================================
  // Usage Data - GET /api/usage/:userId
  // Must match UsageResponseSchema -> { usage: UsageDataSchema } | UsageDataSchema
  // =========================================================================
  http.get(`${API_BASE}/api/usage/:userId`, () => {
    return HttpResponse.json({
      usage: {
        tier: 'free',
        posts_today: 2,
        posts_limit: 5,
        posts_remaining: 3,
        scheduled_count: 1,
        scheduled_limit: 3,
        scheduled_remaining: 2,
        resets_in_seconds: 43200,
        resets_at: null
      }
    });
  }),

  // =========================================================================
  // Templates - GET /api/templates
  // Must match TemplatesResponseSchema -> { templates: TemplateSchema[] }
  // TemplateSchema requires: id, name, description, icon, value
  // =========================================================================
  http.get(`${API_BASE}/api/templates`, () => {
    return HttpResponse.json({
      templates: [
        {
          id: 'standard',
          name: 'Standard Post',
          description: 'A professional LinkedIn post',
          icon: '📝',
          value: 'standard'
        },
        {
          id: 'announcement',
          name: 'Announcement',
          description: 'Share exciting news',
          icon: '📢',
          value: 'announcement'
        }
      ]
    });
  }),

  // =========================================================================
  // GitHub Activity - GET /api/github/activity/:username
  // Must match GitHubActivityResponseSchema -> { activities: GitHubActivitySchema[] }
  // GitHubActivitySchema requires: id, type, icon, title, description, time_ago, repo, context
  // =========================================================================
  http.get(`${API_BASE}/api/github/activity/:username`, () => {
    return HttpResponse.json({
      activities: [
        {
          id: 'act-1',
          type: 'PushEvent',
          icon: '🚀',
          title: 'Pushed 3 commits',
          description: 'Pushed 3 commits to main branch',
          time_ago: '2 hours ago',
          repo: 'postbot/web',
          context: {
            type: 'push',
            commits: 3,
            total_commits: 142,
            repo: 'web',
            full_repo: 'postbot/web',
            date: '2 hours ago'
          }
        },
        {
          id: 'act-2',
          type: 'CreateEvent',
          icon: '✨',
          title: 'Created repository',
          description: 'Created a new repository',
          time_ago: '1 day ago',
          repo: 'postbot/api',
          context: {
            type: 'new_repo',
            repo: 'api',
            full_repo: 'postbot/api'
          }
        }
      ]
    });
  }),

  // =========================================================================
  // User Settings - GET /api/settings/:userId
  // Must match UserSettingsResponseSchema (catchall)
  // =========================================================================
  http.get(`${API_BASE}/api/settings/:userId`, () => {
    return HttpResponse.json({
      github_username: 'testuser',
      persona: {
        bio: 'A developer sharing coding journeys',
        tone: 'professional',
        topics: ['tech', 'AI', 'web development']
      }
    });
  }),

  // =========================================================================
  // Generate Preview - POST /api/post/generate-preview
  // Must match GeneratePreviewResponseSchema
  // =========================================================================
  http.post(`${API_BASE}/api/post/generate-preview`, async () => {
    return HttpResponse.json({
      post: '🚀 Just shipped a major update to PostBot!\n\nAfter 142 commits and countless cups of coffee, the new AI-powered post generation is live.\n\nKey improvements:\n• 3x faster generation\n• Better context awareness\n• Natural-sounding posts\n\nBuilding in public has taught me so much about persistence and iteration.\n\nWhat projects are you working on? Drop a comment! 👇\n\n#BuildInPublic #Developer #AI',
      provider: 'groq',
      was_downgraded: false
    });
  }),

  // =========================================================================
  // Publish Post - POST /api/post/publish
  // Must match PublishPostResponseSchema
  // =========================================================================
  http.post(`${API_BASE}/api/post/publish`, async () => {
    return HttpResponse.json({
      success: true,
      post_url: 'https://linkedin.com/feed/update/urn:li:share:mock123'
    });
  }),

  // =========================================================================
  // Schedule Post - POST /api/scheduled
  // Must match SchedulePostResponseSchema
  // =========================================================================
  http.post(`${API_BASE}/api/scheduled`, async () => {
    return HttpResponse.json({
      success: true,
      scheduled_id: 'sched-mock-123'
    });
  }),

  // =========================================================================
  // Auth Refresh - POST /auth/refresh
  // Used by dashboard.tsx checkAuthentication
  // =========================================================================
  http.post(`${API_BASE}/auth/refresh`, async () => {
    return HttpResponse.json({
      authenticated: true,
      access_token: 'mock_access_token'
    });
  }),
];
