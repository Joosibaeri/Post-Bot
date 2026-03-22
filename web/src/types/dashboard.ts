/**
 * Dashboard Types
 * 
 * These types integrate with the auto-generated API contracts.
 * 
 * TO REGENERATE API TYPES:
 * 1. Ensure backend is running: cd backend && python app.py
 * 2. Run: npm run generate:types
 * 
 * The generated types are at: shared/contracts/index.d.ts
 */

// Re-export API types from shared contracts
// Note: These are generated from OpenAPI spec - do not modify directly
export type {
    components,
    paths,
    operations,
} from '@shared/contracts/index';

// Type aliases for commonly used schemas
import type { components } from '@shared/contracts/index';

/** Request body for saving a post */
export type SavePostRequest = components['schemas']['PostCreateRequest'];

/** Request body for batch post generation */
export type BatchGenerateRequest = components['schemas']['BatchGenerateRequest'];

/** Request body for publishing to LinkedIn */
export type FullPublishRequest = components['schemas']['PublishFullRequest'];

/** Request body for scanning GitHub activity */
export type ScanRequest = components['schemas']['ScanRequest'];

/** Request body for scheduling a post */
export type SchedulePostRequest = components['schemas']['ScheduleRequest'];

/** User settings request */
export type UserSettingsRequest = components['schemas']['SettingsRequest'];

/** Image preview request */
export type ImagePreviewRequest = components['schemas']['ImagePreviewRequest'];

import { z } from 'zod';
import * as schemas from '../lib/schemas';

// ============================================================================
// Frontend-only types (not in API spec)
// ============================================================================

/**
 * GitHub activity item from scan endpoint
 * Note: This is a frontend representation, the actual API returns generic objects
 */
export type GitHubActivity = z.infer<typeof schemas.GitHubActivitySchema>;

/**
 * Post item for the dashboard queue
 */
export type DashboardPost = z.infer<typeof schemas.DashboardPostSchema>;

/**
 * Template option for post generation styles
 */
export type Template = z.infer<typeof schemas.TemplateSchema>;

/**
 * User stats from analytics endpoint
 */
export interface UserStats {
    total_posts: number;
    published_posts: number;
    draft_posts: number;
    posts_this_month: number;
}

/**
 * Base properties shared by all context types
 */
interface BasePostContext {
    date?: string;
    commits?: number;
    total_commits?: number;
    repo?: string;
    full_repo?: string;
    pr_number?: number;
    [key: string]: any; // Use any instead of unknown to allow React Node evaluation
}

/**
 * Post context for AI generation
 * Uses a discriminated union based on the `type` field for precise typing.
 */
export type PostContext = 
    | ({ type: 'push' } & BasePostContext)
    | ({ type: 'pull_request' } & BasePostContext)
    | ({ type: 'new_repo' } & BasePostContext)
    | ({ type: 'repurpose', url?: string } & BasePostContext)
    | ({ type: string & {} } & BasePostContext); // Fallback for templates e.g. 'thought-leadership'

/**
 * Dashboard stats response
 */
export type DashboardStats = z.infer<typeof schemas.DashboardStatsSchema>;

/**
 * Usage data response
 */
export type UsageData = z.infer<typeof schemas.UsageDataSchema>;
