"""
Scheduler Worker - Background task for publishing scheduled posts

This module provides a background task that:
- Checks for due posts every 60 seconds
- Publishes them via LinkedIn API
- Updates post status to 'published' or 'failed'
"""

import asyncio
import logging

# Import from centralized services package - errors caught at module load
from services import post_to_linkedin, get_token_by_user_id
from services.scheduled_posts import get_due_posts, update_post_status

logger = logging.getLogger(__name__)

# Background task reference
_scheduler_task = None


async def process_due_posts():
    """
    Check for and publish all due posts.
    
    Returns:
        Number of posts processed
    """
    try:
        due_posts = await get_due_posts()
    except Exception as e:
        logger.error(f"Error getting due posts: {e}")
        return 0
    
    if not due_posts:
        return 0
    
    logger.info(f"📅 Processing {len(due_posts)} due posts...")
    processed = 0
    
    for post in due_posts:
        try:
            # Get user's LinkedIn tokens
            tokens = await get_token_by_user_id(post['user_id'])
            
            if not tokens or not tokens.get('access_token'):
                await update_post_status(
                    post['id'],
                    'failed',
                    'LinkedIn not connected or token expired'
                )
                logger.warning(f"No LinkedIn token for user {post['user_id']}")
                processed += 1
                continue
            
            # Publish to LinkedIn
            # NOTE: post_to_linkedin (from linkedin_service) is sync and uses requests
            # Run in thread to avoid blocking the async event loop
            result = await asyncio.to_thread(
                post_to_linkedin,
                message_text=post['post_content'],
                access_token=tokens['access_token'],
                linkedin_user_urn=tokens.get('linkedin_user_urn'),
            )
            
            # Handle both bool and dict returns from post_to_linkedin
            success = result.get('success') if isinstance(result, dict) else bool(result)
            
            if success:
                await update_post_status(post['id'], 'published')
                logger.info(f"Successfully published scheduled post {post['id']}")
            else:
                error_msg = result.get('error', 'Unknown error') if isinstance(result, dict) else 'Publishing returned failure'
                await update_post_status(
                    post['id'],
                    'failed',
                    error_msg
                )
                logger.error(f"Failed to publish post {post['id']}: {error_msg}")
            
            processed += 1
            
        except Exception as e:
            await update_post_status(post['id'], 'failed', str(e))
            logger.error(f"Error processing scheduled post {post['id']}: {e}", exc_info=True)
            processed += 1
    
    return processed


async def scheduler_loop():
    """
    Background loop that checks for due posts every 60 seconds.
    """
    logger.info("📅 Scheduler worker started - checking every 60 seconds")
    
    while True:
        try:
            count = await process_due_posts()
            if count > 0:
                logger.info(f"📅 Scheduler processed {count} posts")
        except Exception as e:
            logger.error(f"Scheduler error: {e}", exc_info=True)
        
        # Wait 60 seconds before next check
        await asyncio.sleep(60)


def start_scheduler():
    """
    Start the background scheduler worker.
    Call this on app startup after the event loop is running.
    """
    global _scheduler_task
    
    if _scheduler_task is not None:
        logger.warning("Scheduler already running")
        return
    
    try:
        loop = asyncio.get_event_loop()
        _scheduler_task = loop.create_task(scheduler_loop())
        logger.info("📅 Scheduler worker initialized")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")


async def start_scheduler_async():
    """
    Async version of start_scheduler for use in FastAPI lifespan.
    """
    global _scheduler_task
    
    if _scheduler_task is not None:
        logger.warning("Scheduler already running")
        return
    
    _scheduler_task = asyncio.create_task(scheduler_loop())
    logger.info("📅 Scheduler worker initialized")


def stop_scheduler():
    """
    Stop the background scheduler worker.
    Call this on app shutdown.
    """
    global _scheduler_task
    
    if _scheduler_task is not None:
        _scheduler_task.cancel()
        _scheduler_task = None
        logger.info("📅 Scheduler worker stopped")
