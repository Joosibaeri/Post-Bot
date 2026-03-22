import { z } from 'zod';

// ============================================================================
// Core Domain Schemas
// ============================================================================

export const GitHubActivitySchema = z.object({
    id: z.string(),
    type: z.string(),
    icon: z.string(),
    title: z.string(),
    description: z.string(),
    time_ago: z.string(),
    repo: z.string(),
    context: z.record(z.string(), z.unknown())
});

export const PostContextSchema = z.object({
    type: z.string(),
    commits: z.number().optional(),
    total_commits: z.number().optional(),
    repo: z.string().optional(),
    full_repo: z.string().optional(),
    date: z.string().optional(),
}).catchall(z.unknown()); // Allow other properties

export const DashboardPostSchema = z.object({
    id: z.union([z.string(), z.number()]),
    content: z.string().optional(),
    post_content: z.string().optional(), // from PostHistory
    image_url: z.string().optional().nullable(),
    status: z.enum(['draft', 'published', 'scheduled']).or(z.string()),
    activity: GitHubActivitySchema.optional().nullable(),
    post_type: z.string().optional(),
    context: z.record(z.string(), z.unknown()).optional(),
    linkedin_post_id: z.string().optional().nullable(),
    engagement: z.record(z.string(), z.unknown()).optional(),
    created_at: z.number().optional(),
    published_at: z.number().optional().nullable(),
});

export const TemplateSchema = z.object({
    id: z.string(),
    name: z.string(),
    description: z.string(),
    icon: z.string(),
    value: z.string()
});

export const DashboardStatsSchema = z.object({
    posts_generated: z.number().default(0),
    credits_remaining: z.number().default(0),
    posts_published: z.number().default(0),
    posts_published_this_month: z.number().default(0),
    posts_scheduled: z.number().default(0),
    posts_this_month: z.number().default(0),
    posts_this_week: z.number().default(0),
    posts_last_week: z.number().default(0),
    growth_percentage: z.number().default(0),
    draft_posts: z.number().default(0)
});

export const UsageDataSchema = z.object({
    tier: z.string(),
    posts_today: z.number(),
    posts_limit: z.number(),
    posts_remaining: z.number(),
    scheduled_count: z.number(),
    scheduled_limit: z.number(),
    scheduled_remaining: z.number(),
    resets_in_seconds: z.number(),
    resets_at: z.string().nullable()
});

// ============================================================================
// API Response Schemas
// ============================================================================

export const GeneratePreviewResponseSchema = z.object({
    post: z.string(),
    provider: z.string().optional(),
    was_downgraded: z.boolean().optional(),
});

export const PublishPostResponseSchema = z.object({
    success: z.boolean().optional(),
    error: z.string().optional(),
    post_url: z.string().optional(),
    post: z.string().optional(),
});

export const SchedulePostResponseSchema = z.object({
    success: z.boolean().optional(),
    error: z.string().optional(),
    scheduled_id: z.string().optional(),
});

// GET /api/stats/{user_id}
export const StatsResponseSchema = DashboardStatsSchema;

// GET /api/posts/{user_id}
export const PostsResponseSchema = z.object({
    posts: z.array(DashboardPostSchema).default([])
});

// GET /api/usage/{user_id}
export const UsageResponseSchema = z.object({
    usage: UsageDataSchema
}).or(UsageDataSchema); // Handle both formats as seen in useDashboardData

// GET /api/templates
export const TemplatesResponseSchema = z.object({
    templates: z.array(TemplateSchema).default([])
});

// GET /api/github/activity/{username}
export const GitHubActivityResponseSchema = z.object({
    activities: z.array(GitHubActivitySchema).default([])
});

// GET /api/settings/{user_id}
export const UserSettingsResponseSchema = z.object({
    github_username: z.string().optional(),
    persona: z.record(z.string(), z.unknown()).optional()
}).catchall(z.unknown());
