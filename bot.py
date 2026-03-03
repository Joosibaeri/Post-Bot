import requests
import json
import logging
import random
import re
import datetime
import os
import sys
import time
from typing import Any, Dict, List, Optional
from dateutil import parser as dateutil_parser
from groq import Groq
try:
    from mistralai import Mistral
    MISTRAL_AVAILABLE = True
except ImportError:
    Mistral = None
    MISTRAL_AVAILABLE = False
try:
    import tweepy
    TWITTER_AVAILABLE = True
except ImportError:
    tweepy = None
    TWITTER_AVAILABLE = False
from urllib.parse import quote

# --- LOGGING SETUP ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("postbot")

# Load .env file for local development
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, will use system environment variables

# --- CONFIGURATION (Load from environment variables for security) ---
LINKEDIN_ACCESS_TOKEN: str = os.getenv('LINKEDIN_ACCESS_TOKEN', '')
LINKEDIN_USER_URN: str = os.getenv('LINKEDIN_USER_URN', '')
GITHUB_USERNAME: str = os.getenv('MY_GITHUB_USERNAME') or os.getenv('GITHUB_USERNAME') or ''
GITHUB_TOKEN: Optional[str] = os.getenv('MY_GITHUB_TOKEN') or os.getenv('GITHUB_TOKEN') or None
MAX_POSTS: int = int(os.getenv('MAX_POSTS', '999'))
POST_DELAY_SECONDS: int = int(os.getenv('POST_DELAY_SECONDS', '3600'))
GROQ_API_KEY: str = os.getenv('GROQ_API_KEY', '')
MISTRAL_API_KEY: str = os.getenv('MISTRAL_API_KEY', '')
UNSPLASH_ACCESS_KEY: str = os.getenv('UNSPLASH_ACCESS_KEY', '')

# Twitter/X API credentials
TWITTER_API_KEY: str = os.getenv('TWITTER_API_KEY', '')
TWITTER_API_SECRET: str = os.getenv('TWITTER_API_SECRET', '')
TWITTER_ACCESS_TOKEN: str = os.getenv('TWITTER_ACCESS_TOKEN', '')
TWITTER_ACCESS_TOKEN_SECRET: str = os.getenv('TWITTER_ACCESS_TOKEN_SECRET', '')


def validate_credentials(*, require_linkedin: bool = True) -> bool:
    """Validate that required credentials are set. Returns True if valid."""
    missing: List[str] = []
    if not GROQ_API_KEY:
        missing.append("GROQ_API_KEY")
    if not GITHUB_USERNAME:
        missing.append("GITHUB_USERNAME (or MY_GITHUB_USERNAME)")
    if require_linkedin:
        if not LINKEDIN_ACCESS_TOKEN:
            missing.append("LINKEDIN_ACCESS_TOKEN")
        if not LINKEDIN_USER_URN:
            missing.append("LINKEDIN_USER_URN")
    if missing:
        logger.error("Missing required credentials: %s", ", ".join(missing))
        logger.error("Set environment variables or create a .env file in the project directory")
        return False
    return True


# Initialize AI clients (lazy — checked at runtime)
groq_client: Optional[Groq] = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
mistral_client = Mistral(api_key=MISTRAL_API_KEY) if MISTRAL_AVAILABLE and MISTRAL_API_KEY else None

# Initialize Twitter client
twitter_client = None
if TWITTER_AVAILABLE and TWITTER_API_KEY and TWITTER_ACCESS_TOKEN:
    try:
        twitter_client = tweepy.Client(
            consumer_key=TWITTER_API_KEY,
            consumer_secret=TWITTER_API_SECRET,
            access_token=TWITTER_ACCESS_TOKEN,
            access_token_secret=TWITTER_ACCESS_TOKEN_SECRET
        )
        logger.info("Twitter client initialized")
    except Exception as e:
        logger.warning("Twitter client initialization failed: %s", e)


# =============================================================================
# SHARED HELPERS
# =============================================================================

def _github_headers() -> Dict[str, str]:
    """Return auth headers for GitHub API calls."""
    headers: Dict[str, str] = {}
    if GITHUB_TOKEN:
        headers['Authorization'] = f'token {GITHUB_TOKEN}'
    return headers


def _retry_request(
    method: str,
    url: str,
    *,
    retries: int = 3,
    backoff: float = 1.0,
    timeout: int = 10,
    **kwargs,
) -> Optional[requests.Response]:
    """Make an HTTP request with automatic retries on transient failures.

    Retries on connection errors, timeouts, and 5xx status codes.
    Returns the Response on success, or None after exhausting retries.
    """
    for attempt in range(1, retries + 1):
        try:
            resp = requests.request(method, url, timeout=timeout, **kwargs)
            if resp.status_code < 500:
                return resp  # Success or client error — don't retry
            logger.warning("Server error %d for %s (attempt %d/%d)", resp.status_code, url, attempt, retries)
        except (requests.ConnectionError, requests.Timeout) as exc:
            logger.warning("Request failed for %s: %s (attempt %d/%d)", url, exc, attempt, retries)
        if attempt < retries:
            time.sleep(backoff * attempt)
    logger.error("All %d retries exhausted for %s", retries, url)
    return None


def _github_get(url: str, **kwargs) -> Optional[requests.Response]:
    """GET from GitHub API with auth headers, token-fallback, and retry."""
    headers = _github_headers()
    resp = _retry_request("GET", url, headers=headers, **kwargs)
    # If token gives 401, retry without it (public API)
    if resp is not None and resp.status_code == 401 and headers.get('Authorization'):
        logger.warning("GitHub token unauthorized — retrying without token")
        resp = _retry_request("GET", url, **kwargs)
    return resp


def humanize_delta(ts: datetime.datetime, now_utc: Optional[datetime.datetime] = None) -> str:
    """Return a human-readable time string like '3 hours ago'."""
    if now_utc is None:
        now_utc = datetime.datetime.now(datetime.timezone.utc)
    delta = now_utc - ts
    total_seconds = delta.total_seconds()
    hours = int(total_seconds // 3600)
    if hours < 1:
        minutes = max(1, int(total_seconds // 60))
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    return f"{hours} hour{'s' if hours != 1 else ''} ago"


def sanitize_for_prompt(text: str) -> str:
    """Sanitize user-supplied text before embedding in an AI prompt.

    Strips characters that could be used for prompt injection.
    """
    # Allow only alphanumeric, hyphens, underscores, dots, slashes, spaces
    return re.sub(r'[^\w\s\-./]', '', text)


def _get_repo_total_commits(full_repo: str) -> int:
    """Fetch total commit count for a repository using the GitHub API.

    Uses the commits endpoint with per_page=1 and reads the 'last' page
    number from the Link header. Returns 0 only if the API call fails.
    """
    commits_url = f"https://api.github.com/repos/{full_repo}/commits?per_page=1"
    resp = _github_get(commits_url)
    if resp is None or resp.status_code != 200:
        logger.warning("Could not fetch commit count for %s (status=%s)",
                       full_repo, resp.status_code if resp else 'None')
        return 0
    link_header = resp.headers.get('Link', '')
    # Parse: <https://...?per_page=1&page=139>; rel="last"
    match = re.search(r'[&?]page=(\d+)>; rel="last"', link_header)
    if match:
        total = int(match.group(1))
        logger.info("Repo %s has %d total commits", full_repo, total)
        return total
    # No Link header means everything fits on 1 page (≤1 commit)
    data = resp.json()
    total = len(data) if isinstance(data, list) else 1
    logger.info("Repo %s has %d total commits (single page)", full_repo, total)
    return total

# --- LINKEDIN PERSONA (AI Personality) ---
LINKEDIN_PERSONA = """You are writing LinkedIn posts for Clifford (Darko) Opoku-Sarkodie.

HEADLINE: Creative Technologist | Backend Software Engineer | DevSecOps | Building Secure Fintech & AI Solutions | CS Student @ UoPeople

ABOUT THE VOICE:
- Backend-focused engineer passionate about building secure, scalable systems
- DevSecOps mindset - security is not an afterthought, it's built-in
- Fintech & AI specialist - building real solutions that matter
- CS student at University of the People - learning never stops
- Creative technologist who bridges innovative ideas with solid engineering
- Community-focused and open to collaboration
- Growing professional navigating the tech industry

LINKEDIN POST STRUCTURE:
1. Hook (1-2 sentences): Relatable question, observation, or story
   - CRITICAL: NEVER start with "As I", "As a", "I just", "Just", "Today I", "Recently", "So I", "Ever had"
   - MUST use one of these hook STARTERS (pick RANDOMLY using the timestamp seed):
     * A bold statement: "Most developers get this wrong..." / "Hot take:" / "Unpopular opinion:"
     * A confession: "I'll admit it—" / "Confession:" / "I used to think..."
     * A number: "After 100 commits..." / "3 things I learned..." / "Day 57:"
     * A scene: "It was 2am. My code wasn't working." / "Picture this:" / "There I was..."
     * A contradiction: "Everyone says X. I disagree." / "They said it couldn't be done."
     * A challenge: "Who else has struggled with..." / "The hardest part of..."
   - EVERY post opening MUST be COMPLETELY DIFFERENT from the last one
   - If you've used a question hook before, use a statement this time
2. Body (3-5 sentences): Develop the idea with a specific example or experience
3. Insight (1-2 sentences): What you learned and why it matters
4. Call to Action (1 sentence): Engage your network
5. Hashtags: 8-12 relevant hashtags (new line)

WORD COUNT & FORMAT:
- Target: 200-300 words (1,300-1,600 characters) - LinkedIn's optimal length
- FORMATTING "BRO-ETRY" STYLE:
  - 1-2 sentence paragraphs MAX.
  - Double line break between every paragraph.
  - NO big blocks of text.
- Conversational, authentic, like talking to peers
- Include 3-4 emojis naturally (🔐 🚀 💡 ✨ 🔥 💻 🎯 ⚡ 🧠 🏦)
- NO markdown formatting (no **bold**), NO code blocks, NO bullet points
- Keep it punchy and engaging

TONE:
- Genuine and relatable
- Technically confident but approachable
- Security-conscious - always thinking about the "what could go wrong"
- Growth-minded learner
- Problem-solver with engineering mindset

TOPICS:
- Backend engineering wins and lessons (APIs, databases, architecture)
- DevSecOps practices and security insights
- Fintech challenges and solutions
- AI/ML integration in real applications
- Learning moments as a CS student @ UoPeople
- Building scalable, secure systems
- Tech career navigation
- Open source contributions

MANDATORY:
- Include 8-12 hashtags on a new line
- Posts must feel COMPLETE - no cutting off mid-sentence
- Balance technical depth with accessibility
- Share learning, not just achievements"""

# Anti-patterns: Banned LinkedIn clichés that make posts feel generic
ANTI_PATTERNS = """
NEVER USE THESE PHRASES (they make posts feel generic and inauthentic):
- "Excited to announce..." / "Thrilled to share..."
- "I'm humbled to..." / "Honored to..."
- "Game-changer" / "Revolutionary" / "Cutting-edge"
- "Leveraging" / "Synergy" / "Paradigm shift"
- "In this fast-paced world..." / "In today's digital age..."
- "Thought leadership" / "Value proposition"
- "Passionate about..." (show don't tell)
- "At the end of the day..."
- "Let's unpack this..." / "Deep dive"
- "Moving the needle" / "Low-hanging fruit"
- "Circle back" / "Touch base"
- "It goes without saying..."

INSTEAD: Use specific, concrete language. Show enthusiasm through details, not buzzwords.
"""

# --- SENSOR 2: GITHUB STATS CHECKER ---
def get_github_stats() -> Optional[Dict[str, Any]]:
    """Fetch GitHub user stats for inspirational posts."""
    logger.info("Fetching GitHub stats for %s...", GITHUB_USERNAME)
    url = f"https://api.github.com/users/{GITHUB_USERNAME}"
    resp = _github_get(url)
    if resp is None or resp.status_code != 200:
        logger.warning("Could not fetch GitHub user info.")
        return None
    data = resp.json()
    return {
        'public_repos': data.get('public_repos', 0),
        'followers': data.get('followers', 0),
        'location': data.get('location'),
        'html_url': data.get('html_url'),
        'login': data.get('login'),
    }


def get_latest_github_activity(max_items: Optional[int] = None) -> List[Dict[str, Any]]:
    """Fetch recent GitHub user events (last 24h).

    Returns a list (possibly empty). Each item has keys: type, repo, full_repo, date,
    and optional commits/action.
    """
    if max_items is None:
        max_items = MAX_POSTS

    logger.info("Checking GitHub activity for %s (up to %d)...", GITHUB_USERNAME, max_items)
    activities: List[Dict[str, Any]] = []

    url = f"https://api.github.com/users/{GITHUB_USERNAME}/events"
    resp = _github_get(url)
    if resp is None or resp.status_code != 200:
        logger.info("No GitHub activity found or API error.")
        return activities

    events = resp.json()
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    cutoff = now_utc - datetime.timedelta(hours=24)

    for event in events:
        if len(activities) >= max_items:
            break
        try:
            event_time = dateutil_parser.isoparse(event.get('created_at'))
        except Exception:
            continue
        if event_time.tzinfo is None:
            event_time = event_time.replace(tzinfo=datetime.timezone.utc)
        if event_time < cutoff:
            continue
        when_text = humanize_delta(event_time, now_utc)

        etype = event.get('type')
        repo_name = event.get('repo', {}).get('name', '')
        clean_repo_name = repo_name.split('/')[-1] if repo_name else ''

        if etype == 'PushEvent':
            # payload.size is the true commit count; payload.commits may be truncated to 20
            commit_count = event.get('payload', {}).get('size') or len(event.get('payload', {}).get('commits', []))
            total_commits = _get_repo_total_commits(repo_name)
            activities.append({
                'type': 'push',
                'repo': clean_repo_name,
                'full_repo': repo_name,
                'commits': commit_count,
                'total_commits': total_commits,
                'date': when_text,
            })
        elif etype == 'PullRequestEvent':
            action = event.get('payload', {}).get('action', 'updated')
            total_commits = _get_repo_total_commits(repo_name)
            activities.append({
                'type': 'pull_request',
                'action': action,
                'repo': clean_repo_name,
                'full_repo': repo_name,
                'total_commits': total_commits,
                'date': when_text,
            })
        elif etype == 'CreateEvent':
            ref_type = event.get('payload', {}).get('ref_type', 'repo')
            if ref_type == 'repository':
                total_commits = _get_repo_total_commits(repo_name)
                activities.append({
                    'type': 'new_repo',
                    'repo': clean_repo_name,
                    'full_repo': repo_name,
                    'total_commits': total_commits,
                    'date': when_text,
                })

    if not activities:
        logger.info("No GitHub activity found in the last 24 hours.")
    else:
        logger.info("Found %d recent event(s)", len(activities))
    return activities


def get_recent_repo_updates() -> Optional[List[Dict[str, Any]]]:
    """Scan user's repositories and return recent updates (pushed_at) within 24h."""
    logger.info("Scanning repos for recent pushes for %s...", GITHUB_USERNAME)
    url = f"https://api.github.com/users/{GITHUB_USERNAME}/repos?per_page=100&type=owner"
    resp = _github_get(url)
    if resp is None or resp.status_code != 200:
        return None

    repos = resp.json()
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    cutoff = now_utc - datetime.timedelta(hours=24)

    recent: List[Dict[str, Any]] = []
    for r in repos:
        pushed = r.get('pushed_at')
        if not pushed:
            continue
        pushed_dt = dateutil_parser.isoparse(pushed)
        if pushed_dt.tzinfo is None:
            pushed_dt = pushed_dt.replace(tzinfo=datetime.timezone.utc)
        if pushed_dt < cutoff:
            continue

        repo_name = r.get('name')
        full_repo = r.get('full_name')
        # Try to get the actual latest commit time
        commit_url = f"https://api.github.com/repos/{full_repo}/commits?per_page=1"
        c_resp = _github_get(commit_url)
        if c_resp is not None and c_resp.status_code == 200:
            commits = c_resp.json()
            if commits:
                commit_time = commits[0].get('commit', {}).get('author', {}).get('date')
                commit_dt = dateutil_parser.isoparse(commit_time)
                if commit_dt.tzinfo is None:
                    commit_dt = commit_dt.replace(tzinfo=datetime.timezone.utc)
                when_text = humanize_delta(commit_dt, now_utc)
                total_commits = _get_repo_total_commits(full_repo)
                recent.append({
                    'type': 'push', 'repo': repo_name, 'full_repo': full_repo,
                    'commits': 1, 'total_commits': total_commits,
                    'date': when_text, '_ts': commit_dt,
                })
                continue
        # Fallback: use pushed_at time
        when_text = humanize_delta(pushed_dt, now_utc)
        total_commits = _get_repo_total_commits(full_repo)
        recent.append({
            'type': 'push', 'repo': repo_name, 'full_repo': full_repo,
            'commits': 1, 'total_commits': total_commits,
            'date': when_text, '_ts': pushed_dt,
        })

    # Sort by actual timestamp descending (most recent first)
    recent.sort(key=lambda x: x.get('_ts', datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)), reverse=True)
    # Remove internal _ts key before returning
    for item in recent:
        item.pop('_ts', None)
    return recent or None

# --- AI BRAIN: GENERATE DYNAMIC CONTENT WITH GROQ/MISTRAL ---
# Hook starters for guaranteed variety
HOOK_STARTERS = [
    "Hot take:",
    "Unpopular opinion:",
    "Most developers get this wrong:",
    "Confession:",
    "I used to think",
    "3 things I learned",
    "Here's what nobody tells you about",
    "It was 2am.",
    "Picture this:",
    "There I was,",
    "They said it couldn't be done.",
    "The hardest part of",
    "What if I told you",
    "Stop doing this:",
    "The secret to",
    "I almost gave up on",
    "Day 57 of",
    "Real talk:",
    "Plot twist:",
    "You know that feeling when",
]

_LAST_HOOK_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".last_hook")

def get_random_hook() -> str:
    """Get a random hook starter, guaranteed different from the last one used."""
    last_hook = ""
    try:
        if os.path.exists(_LAST_HOOK_FILE):
            with open(_LAST_HOOK_FILE, "r", encoding="utf-8") as f:
                last_hook = f.read().strip()
    except OSError:
        pass

    candidates = [h for h in HOOK_STARTERS if h != last_hook]
    if not candidates:
        candidates = HOOK_STARTERS  # safety fallback
    chosen = random.choice(candidates)

    try:
        with open(_LAST_HOOK_FILE, "w", encoding="utf-8") as f:
            f.write(chosen)
    except OSError:
        pass

    logger.info("Hook chosen: '%s' (previous was '%s')", chosen, last_hook or 'none')
    return chosen

def generate_post_with_ai(context_data: Dict[str, Any]) -> Optional[str]:
    """Use Groq/Mistral AI to draft a LinkedIn post based on context."""
    logger.info("AI is thinking and drafting your post...")
    
    try:
        # Get a random hook for this post
        random_hook = get_random_hook()
        
        # Build context prompt based on what triggered the post
        # Sanitize any user-supplied values before embedding in the prompt
        if isinstance(context_data, dict) and context_data.get('type') == 'push':
            safe_repo = sanitize_for_prompt(context_data.get('repo', ''))
            safe_full_repo = sanitize_for_prompt(context_data.get('full_repo', ''))
            push_count = context_data.get('commits', 0)
            total = context_data.get('total_commits') or 'many'
            # Describe the push naturally — never say "0 commits"
            if push_count and push_count > 1:
                push_desc = f"User just pushed {push_count} commits to repo '{safe_repo}'"
            else:
                push_desc = f"User just pushed new code to repo '{safe_repo}'"
            context_prompt = f"""
GitHub Activity: {push_desc} {context_data['date']}.
The repo now has {total} total commits across its history.
Repo: https://github.com/{safe_full_repo}

IMPORTANT: Do NOT mention '0 commits'. Focus on the total commit count ({total}) and the repo's journey.

WRITE A COMPLETE LINKEDIN POST - MUST INCLUDE EVERYTHING BELOW:

MANDATORY HOOK STARTER (use this exact opening): "{random_hook}"

Structure (250-350 words total):
1. Hook (1-2 sentences) - START WITH: "{random_hook}" then continue with a relatable moment about coding/building
2. Story (3-4 sentences) - what this code work involved and what you learned  
3. Value (1-2 sentences) - why it matters or insight gained
4. Question (1 sentence) - ask your network something and tag relevant people/topics
5. HASHTAGS (MANDATORY FINAL LINE: exactly 15-20 hashtags space-separated)

CRITICAL REQUIREMENTS:
- Write the COMPLETE post - output MUST end with the hashtags line
- POST MUST END with a question followed by a blank line then hashtags
- Do NOT include @mentions or @tags of any kind
- MANDATORY FINAL LINE: exactly 15-20 diverse hashtags covering topic, tech stack, community, career
  (example: #WebDev #JavaScript #React #NodeJS #Code #Design #Tech #Frontend #Backend #UI #UX #Learning #DevCommunity #Growth #Innovation #100DaysOfCode #Coding #Programming #TechCareer #OpenSource)
- Explicitly include this repo link: https://github.com/{safe_full_repo}
- Include 3-4 emojis naturally: 🎨 🚀 💡 ✨
- Length: 250-350 words TOTAL including hashtags
- DO NOT stop mid-sentence or before hashtags

{LINKEDIN_PERSONA}
"""
        
        elif isinstance(context_data, dict) and context_data.get('type') == 'pull_request':
            safe_repo = sanitize_for_prompt(context_data.get('repo', ''))
            safe_full_repo = sanitize_for_prompt(context_data.get('full_repo', ''))
            context_prompt = f"""
GitHub Activity: User just {context_data['action'].upper()} a pull request on '{safe_repo}' {context_data['date']}.
Repo: https://github.com/{safe_full_repo}

WRITE A COMPLETE LINKEDIN POST - MUST INCLUDE EVERYTHING BELOW:

Structure (200-300 words total):
1. Hook (1-2 sentences) - relatable moment about collaboration or code review
2. Story (3-4 sentences) - what the PR involved and what surprised/excited you
3. Lesson (1-2 sentences) - what you learned about teamwork or design
4. Question (1 sentence) - engage your network
5. HASHTAGS (8-12 hashtags on separate line, space-separated)

Requirements:
- Write the FULL post, do NOT cut off early
- ALWAYS end with hashtags
- Explicitly include this repo link once in the body: https://github.com/{safe_full_repo}
- Vary the hook/story wording each run; avoid repeating phrasing or metaphors from prior posts
- Include 3-4 emojis naturally: 🎨 🚀 💡 ✨
- Make it conversational and authentic
- FINISH THE ENTIRE POST before stopping

{LINKEDIN_PERSONA}
"""
        
        elif isinstance(context_data, dict) and context_data.get('type') == 'new_repo':
            safe_repo = sanitize_for_prompt(context_data.get('repo', ''))
            safe_full_repo = sanitize_for_prompt(context_data.get('full_repo', ''))
            context_prompt = f"""
GitHub Activity: User just created a new repository called '{safe_repo}' {context_data['date']}.
Repo: https://github.com/{safe_full_repo}

WRITE A COMPLETE LINKEDIN POST - MUST INCLUDE EVERYTHING BELOW:

Structure (200-300 words total):
1. Hook (1-2 sentences) - why you created this project
2. Story (3-4 sentences) - the problem, inspiration, or challenge
3. Vision (1-2 sentences) - what's the potential or purpose
4. Invite (1 sentence) - call for collaboration or feedback
5. HASHTAGS (8-12 hashtags on separate line, space-separated)

Requirements:
- Write the FULL post, do NOT cut off early
- ALWAYS end with hashtags
- Explicitly include this repo link once in the body: https://github.com/{safe_full_repo}
- Vary the hook/story wording each run; avoid repeating phrasing or metaphors from prior posts
- Include 3-4 emojis naturally: 🎨 🚀 💡 ✨
- Make it conversational and authentic
- FINISH THE ENTIRE POST before stopping

{LINKEDIN_PERSONA}
"""
        
        elif isinstance(context_data, dict) and context_data.get('type') == 'milestone':
            stats = context_data
            context_prompt = f"""
GitHub Milestone: 
- {stats['public_repos']} public repositories
- {stats['followers']} followers
- Location: {stats.get('location', 'Unknown')}
GitHub profile: https://github.com/{GITHUB_USERNAME}

Write a COMPLETE LinkedIn post that MUST include ALL of these:
1. Reflection (1-2 sentences) - moment of pride/reflection
2. Journey (3-4 sentences) - key milestones, lessons, growth
3. Community (1-2 sentences) - thank people who helped
4. Future (1 sentence) - what's next
5. CRITICAL: End with EXACTLY 8-12 HASHTAGS on a new line, separated by spaces
6. Include 3-4 emojis (🎨 🚀 💡 ✨) naturally throughout

Make it 200-300 words. Do NOT cut off mid-sentence.

{LINKEDIN_PERSONA}
"""
        
        else:
            context_prompt = f"""Write a COMPLETE LINKEDIN POST - MUST INCLUDE EVERYTHING BELOW:

Structure (200-300 words total):
1. Hook (1-2 sentences) - relatable observation about web dev/tech
2. Insight (3-4 sentences) - share a lesson or perspective
3. Value (1-2 sentences) - why it matters to others
4. Question (1 sentence) - engage your network
5. HASHTAGS (8-12 hashtags on separate line, space-separated)

Requirements:
- Write the FULL post, do NOT cut off early
- ALWAYS end with hashtags
- Vary the hook/story wording each run; avoid repeating phrasing or metaphors from prior posts
- Include 3-4 emojis naturally: 🎨 🚀 💡 ✨
- Make it conversational and authentic
- FINISH THE ENTIRE POST before stopping

{LINKEDIN_PERSONA}

{ANTI_PATTERNS}
"""
        
        # Randomly select between available AI models for variety
        system_message = "You are a LinkedIn post writer. You MUST complete every post you write. Every post MUST end with exactly 8-12 hashtags on the final line. NEVER stop mid-sentence or before adding the hashtags. NEVER use markdown formatting — no **bold**, *italic*, ## headers, bullet points, or code blocks. Write plain text only. NEVER include @mentions — no @username or @company tags."
        
        # Select AI model — prefer Mistral (70%) for variety
        if mistral_client and random.random() < 0.7:
            selected_model = "mistral"
        else:
            selected_model = "groq"
        
        if selected_model == "mistral" and mistral_client:
            logger.info("Using Mistral AI for this post...")
            response = mistral_client.chat.complete(
                model="mistral-large-latest",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": context_prompt}
                ],
                temperature=0.7,
                max_tokens=4000,
            )
            post_content = response.choices[0].message.content.strip()
        else:
            logger.info("Using Groq (Llama 3.3) for this post...")
            response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": context_prompt}
                ],
                temperature=0.7,
                max_tokens=4000,
            )
            post_content = response.choices[0].message.content.strip()

        # Ensure the model didn't cut off mid-sentence or omit required hashtags
        def _looks_complete(text: str) -> bool:
            if not text or len(text.strip()) < 150:
                return False
            lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
            if not lines:
                return False
            last = lines[-1]
            # MUST have hashtags line with 8-20 hashtags
            tags = [w for w in last.split() if w.startswith('#')]
            if 8 <= len(tags) <= 20:
                return True
            # If no hashtags, it's incomplete
            return False

        def _attempt_finish(current_text: str, tries: int = 2) -> str:
            for attempt in range(tries):
                try:
                    # Check if we just need hashtags or a full continuation
                    lines = [l.strip() for l in current_text.strip().splitlines() if l.strip()]
                    last_line = lines[-1] if lines else ""
                    has_hashtags = any(w.startswith('#') for w in last_line.split())
                    
                    if has_hashtags:
                        # Already has hashtags line, might just need more hashtags
                        tags = [w for w in last_line.split() if w.startswith('#')]
                        if len(tags) >= 8:
                            return current_text  # Already complete
                    
                    # Determine what's missing
                    if not has_hashtags and current_text.strip().endswith(('.', '!', '?')):
                        # Complete sentence but no hashtags - just add hashtags
                        cont_prompt = (
                            "The LinkedIn post below is complete but missing the required hashtags. "
                            "Output ONLY a line with exactly 8-12 relevant diverse hashtags (space-separated). "
                            "Include hashtags for: topic, tech stack, community tags, career tags. "
                            "Format: #Tag1 #Tag2 #Tag3 etc.\n\nPOST:\n" + current_text
                        )
                    else:
                        # Incomplete - need to finish the thought AND add hashtags
                        cont_prompt = (
                            "The LinkedIn post below is incomplete. Continue it briefly (1-2 sentences max), "
                            "then on a NEW LINE add exactly 8-12 relevant diverse hashtags.\n\nPOST SO FAR:\n" + current_text
                        )
                    
                    resp = groq_client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": cont_prompt}],
                        temperature=0.6,
                        max_tokens=500,
                    )
                    addition = resp.choices[0].message.content.strip()
                    
                    # Smart merge - check if addition already has the full post
                    if len(addition) > len(current_text) * 0.8:
                        # Model repeated the whole post, use it directly
                        current_text = addition
                    else:
                        # Append the continuation
                        current_text = current_text.rstrip() + "\n\n" + addition
                    
                    if _looks_complete(current_text):
                        return current_text
                except Exception as e:
                    logger.warning("Error attempting to finish truncated post: %s", e)
                    continue
            # Last resort: force add synthesized hashtags
            logger.warning("Using fallback hashtags generator...")
            if not current_text.strip().endswith(('.', '!', '?')):
                current_text = current_text.rstrip() + '.'
            # Use our synthesized hashtags (same module, no import needed)
            hashtags_line = synthesize_hashtags(current_text, desired=10)
            current_text = current_text.rstrip() + "\n\n" + hashtags_line
            return current_text

        if not _looks_complete(post_content):
            logger.warning("Generated post appears incomplete — requesting continuation...")
            post_content = _attempt_finish(post_content, tries=2)

        # Strip any markdown formatting the AI may have included
        post_content = strip_markdown(post_content)

        return post_content
        
    except Exception as e:
        logger.error("Error generating post with AI: %s", e)
        logger.info("Tip: Make sure your API keys are valid (GROQ_API_KEY / MISTRAL_API_KEY)")
        return None

# --- POST CLEANUP ---

def strip_markdown(text: str) -> str:
    """Remove markdown formatting that AI models may include.
    LinkedIn renders plain text, so **bold** would appear literally."""
    # Remove bold: **text** or __text__
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    # Remove italic: *text* or _text_ (but not inside hashtags or URLs)
    text = re.sub(r'(?<!\w)\*(.+?)\*(?!\w)', r'\1', text)
    # Remove headers: ## Header
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    # Remove code blocks: ```code```
    text = re.sub(r'```[\s\S]*?```', '', text)
    # Remove inline code: `code`
    text = re.sub(r'`(.+?)`', r'\1', text)
    # Remove bullet points: - item or * item at line start
    text = re.sub(r'^[\-\*]\s+', '', text, flags=re.MULTILINE)
    # Remove numbered list markers: 1. item
    text = re.sub(r'^\d+\.\s+', '', text, flags=re.MULTILINE)
    return text.strip()

# --- IMAGE FUNCTIONS ---

def _extract_image_keywords(post_content: str) -> str:
    """Use AI to extract a dev-focused Unsplash search query from post content.

    Returns a short search string guaranteed to produce software/dev imagery.
    Falls back to curated dev-related queries if AI is unavailable.
    """
    # Curated pool of guaranteed-good dev image queries
    _DEV_IMAGE_QUERIES = [
        'code on laptop screen dark',
        'programmer typing code laptop',
        'software developer computer screen',
        'dark code editor terminal',
        'laptop programming code',
        'coding setup desk dark',
        'web development code screen',
        'developer workspace monitors code',
        'github code laptop programming',
        'python code terminal dark',
        'javascript code editor screen',
        'cybersecurity code dark screen',
        'API code development laptop',
        'software engineering workspace',
        'coding on MacBook dark',
    ]

    try:
        prompt = (
            "I need an Unsplash image search query for a LinkedIn post about software development.\n\n"
            "Post excerpt:\n" + post_content[:400] + "\n\n"
            "Return ONLY a 3-4 word Unsplash search query. "
            "The query MUST be about software, coding, or computers. "
            "Good examples: 'code laptop dark screen', 'developer typing code', 'programming terminal dark', "
            "'software engineer workspace', 'code editor dark mode'.\n"
            "Bad examples (NEVER use): 'pipeline factory', 'hardware circuit', 'industrial', 'microchip', "
            "'oil', 'machinery', 'robot', 'abstract technology'.\n\n"
            "Return ONLY the search query words, nothing else."
        )
        if groq_client:
            resp = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=20,
            )
            keywords = resp.choices[0].message.content.strip().strip('"\'')
            words = keywords.split()
            # Validate: must be 2-5 words, no long sentences, must contain a dev-ish word
            dev_signals = {'code', 'coding', 'developer', 'programming', 'software', 'laptop',
                           'terminal', 'screen', 'computer', 'workspace', 'editor', 'tech',
                           'web', 'api', 'data', 'python', 'javascript', 'dark', 'typing',
                           'keyboard', 'monitor', 'setup', 'github', 'devops', 'cloud'}
            if (2 <= len(words) <= 5
                    and all(len(w) < 20 for w in words)
                    and any(w.lower() in dev_signals for w in words)):
                logger.info("AI image query: '%s'", keywords)
                return keywords
            else:
                logger.info("AI returned non-dev query '%s', using curated fallback", keywords)
    except Exception as e:
        logger.debug("AI keyword extraction failed: %s", e)

    # Fallback: pick from curated list based on post content hints
    content_lower = post_content.lower()
    topic_picks = [
        (['security', 'devsecops', 'encrypt', 'auth'], 'cybersecurity code dark screen'),
        (['api', 'backend', 'database', 'server', 'flask', 'django', 'fastapi'], 'API code development laptop'),
        (['frontend', 'react', 'css', 'html', 'ui'], 'web development code screen'),
        (['python', 'pip', 'django', 'flask'], 'python code terminal dark'),
        (['javascript', 'typescript', 'node', 'react', 'next'], 'javascript code editor screen'),
        (['github', 'commit', 'repo', 'open source', 'git'], 'github code laptop programming'),
        (['deploy', 'docker', 'cloud', 'aws', 'devops'], 'software engineering workspace'),
    ]
    for keywords, query in topic_picks:
        if any(kw in content_lower for kw in keywords):
            logger.info("Fallback image query (topic match): '%s'", query)
            return query

    choice = random.choice(_DEV_IMAGE_QUERIES)
    logger.info("Fallback image query (random dev): '%s'", choice)
    return choice


def get_relevant_image(post_content: str) -> Optional[bytes]:
    """Fetch a relevant image from Unsplash based on post content."""
    if not UNSPLASH_ACCESS_KEY:
        logger.info("No Unsplash API key set, skipping image fetch")
        return None
    
    search_term = _extract_image_keywords(post_content)
    
    logger.info("Searching for image: '%s'...", search_term)
    
    try:
        url = f"https://api.unsplash.com/photos/random?query={quote(search_term)}&orientation=landscape&content_filter=high"
        headers = {'Authorization': f'Client-ID {UNSPLASH_ACCESS_KEY}'}
        resp = _retry_request("GET", url, headers=headers)
        
        if resp is not None and resp.status_code == 200:
            data = resp.json()
            image_download_url = data['urls']['regular']
            image_description = data.get('alt_description', 'No description')
            logger.info("Found image: %s", image_description)
            
            img_resp = _retry_request("GET", image_download_url)
            if img_resp is not None and img_resp.status_code == 200:
                logger.info("Image downloaded (%d bytes)", len(img_resp.content))
                return img_resp.content
            else:
                logger.warning("Failed to download image")
                return None
        else:
            status = resp.status_code if resp else 'no response'
            logger.warning("Unsplash API error: %s", status)
            return None
    except Exception as e:
        logger.warning("Error fetching image: %s", e)
        return None


def synthesize_hashtags(post_content: str, desired: int = 18) -> str:
    """Create a fallback set of hashtags based on keywords in the post."""
    keywords_map = {
        'design': '#Design', 'ui': '#UI', 'ux': '#UX', 'frontend': '#Frontend',
        'react': '#React', 'javascript': '#JavaScript', 'python': '#Python', 'node': '#NodeJS',
        'automation': '#Automation', 'bot': '#Bot', 'ai': '#AI', 'ml': '#MachineLearning',
        'open source': '#OpenSource', 'opensource': '#OpenSource', 'web': '#WebDevelopment',
        'learning': '#Learning', 'student': '#Student', 'career': '#Career', 'product': '#Product',
        'backend': '#Backend', 'api': '#API', 'database': '#Database', 'cloud': '#Cloud',
        'github': '#GitHub', 'code': '#Code', 'coding': '#Coding', 'css': '#CSS', 'html': '#HTML'
    }
    text = post_content.lower()
    selected = []
    for k, tag in keywords_map.items():
        if k in text and tag not in selected:
            selected.append(tag)
    # Comprehensive defaults pool
    defaults = [
        '#WebDev', '#100DaysOfCode', '#Coding', '#Developer', '#Tech', '#Programming', 
        '#Growth', '#Creativity', '#DevCommunity', '#TechCareer', '#Innovation',
        '#BuildInPublic', '#LearnInPublic', '#SoftwareEngineering', '#CodeNewbie',
        '#TechTwitter', '#DeveloperLife', '#OpenSource', '#CodingLife', '#WebDesign'
    ]
    for d in defaults:
        if len(selected) >= desired:
            break
        if d not in selected:
            selected.append(d)
    # Ensure we have exactly `desired` hashtags
    if len(selected) > desired:
        selected = selected[:desired]
    return ' '.join(selected)

def upload_image_to_linkedin(image_data: bytes) -> Optional[str]:
    """Upload an image to LinkedIn and return the asset URN."""
    logger.info("Uploading image to LinkedIn...")
    
    try:
        register_url = "https://api.linkedin.com/v2/assets?action=registerUpload"
        headers = {
            'Authorization': f'Bearer {LINKEDIN_ACCESS_TOKEN}',
            'Content-Type': 'application/json',
            'X-Restli-Protocol-Version': '2.0.0'
        }
        
        register_data = {
            "registerUploadRequest": {
                "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                "owner": f"urn:li:person:{LINKEDIN_USER_URN}",
                "serviceRelationships": [
                    {
                        "relationshipType": "OWNER",
                        "identifier": "urn:li:userGeneratedContent"
                    }
                ]
            }
        }
        
        response = _retry_request("POST", register_url, headers=headers, json=register_data)
        if response is None or response.status_code != 200:
            logger.error("Failed to register upload: %s", response.status_code if response else 'no response')
            return None
        
        register_response = response.json()
        asset_urn = register_response['value']['asset']
        upload_url = register_response['value']['uploadMechanism']['com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest']['uploadUrl']
        
        logger.info("Uploading binary data to LinkedIn...")
        upload_headers = {
            'Authorization': f'Bearer {LINKEDIN_ACCESS_TOKEN}',
        }
        upload_response = _retry_request("PUT", upload_url, headers=upload_headers, data=image_data)
        
        if upload_response is not None and upload_response.status_code in [200, 201]:
            logger.info("Image uploaded successfully: %s", asset_urn)
            return asset_urn
        else:
            logger.error("Failed to upload image: %s", upload_response.status_code if upload_response else 'no response')
            return None
            
    except Exception as e:
        logger.error("Error uploading image: %s", e)
        return None

# --- THE POSTING FUNCTION ---
def post_to_linkedin(message_text: str, image_asset_urn: Optional[str] = None) -> None:
    """Post to LinkedIn with optional image."""
    url = "https://api.linkedin.com/v2/ugcPosts"
    headers = {
        'Authorization': f'Bearer {LINKEDIN_ACCESS_TOKEN}',
        'Content-Type': 'application/json',
        'X-Restli-Protocol-Version': '2.0.0'
    }
    
    # Prepare post data based on whether we have an image
    if image_asset_urn:
        post_data = {
            "author": f"urn:li:person:{LINKEDIN_USER_URN}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": message_text},
                    "shareMediaCategory": "IMAGE",
                    "media": [
                        {
                            "status": "READY",
                            "media": image_asset_urn
                        }
                    ]
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
        }
    else:
        post_data = {
            "author": f"urn:li:person:{LINKEDIN_USER_URN}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": message_text},
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
        }
    
    logger.info("Posting to LinkedIn: '%s...'", message_text[:30])
    response = _retry_request("POST", url, headers=headers, json=post_data)
    if response is not None and response.status_code == 201:
        logger.info("SUCCESS! Post is live.")
    else:
        status = response.status_code if response else 'no response'
        logger.error("LinkedIn post FAILED: %s", status)

def generate_tweet_with_ai(context_data: Dict[str, Any], linkedin_post: Optional[str] = None) -> Optional[str]:
    """Generate a Twitter/X-native post using AI.

    Twitter posts are fundamentally different from LinkedIn:
    - Max 280 characters
    - Casual, punchy, emoji-heavy
    - 2-4 hashtags max (not 8-12)
    - Questions to spark replies
    - No long storytelling
    """
    logger.info("Generating Twitter-native post with AI...")

    # Build a context summary and repo link for the AI
    repo_link = ""
    if isinstance(context_data, dict) and context_data.get('type') == 'push':
        safe_repo = sanitize_for_prompt(context_data.get('repo', ''))
        safe_full_repo = sanitize_for_prompt(context_data.get('full_repo', ''))
        repo_link = f"https://github.com/{safe_full_repo}" if safe_full_repo else ""
        commits_text = context_data.get('commits', 0)
        total_text = context_data.get('total_commits') or 'many'
        # Never say "0 commits" — phrase it naturally
        if commits_text and int(commits_text) > 1:
            topic_hint = f"Just pushed {commits_text} commits to '{safe_repo}'. The repo has {total_text} total commits."
        else:
            topic_hint = f"Just pushed new code to '{safe_repo}'. The repo has {total_text} total commits."
    elif isinstance(context_data, dict) and context_data.get('type') == 'pull_request':
        safe_repo = sanitize_for_prompt(context_data.get('repo', ''))
        safe_full_repo = sanitize_for_prompt(context_data.get('full_repo', ''))
        repo_link = f"https://github.com/{safe_full_repo}" if safe_full_repo else ""
        total_text = context_data.get('total_commits') or 'many'
        topic_hint = f"Just {context_data.get('action', 'opened')} a pull request on '{safe_repo}' (repo has {total_text} total commits)."
    elif isinstance(context_data, dict) and context_data.get('type') == 'new_repo':
        safe_repo = sanitize_for_prompt(context_data.get('repo', ''))
        safe_full_repo = sanitize_for_prompt(context_data.get('full_repo', ''))
        repo_link = f"https://github.com/{safe_full_repo}" if safe_full_repo else ""
        total_text = context_data.get('total_commits') or 'many'
        topic_hint = f"Just created a new repository called '{safe_repo}' ({total_text} commits so far)."
    elif isinstance(context_data, dict) and context_data.get('type') == 'milestone':
        topic_hint = f"Reached a milestone: {context_data.get('public_repos', '?')} public repos, {context_data.get('followers', '?')} followers."
        repo_link = f"https://github.com/{GITHUB_USERNAME}" if GITHUB_USERNAME else ""
    else:
        topic_hint = "General dev/tech thought."
        repo_link = f"https://github.com/{GITHUB_USERNAME}" if GITHUB_USERNAME else ""

    # Optionally include the LinkedIn post as reference so the tweet covers the same topic
    reference = ""
    if linkedin_post:
        # Trim to avoid blowing up the prompt
        reference = f"\n\nFor reference, here is the LinkedIn post on the same topic (DO NOT copy it, write a completely different tweet):\n{linkedin_post[:600]}"

    link_instruction = ""
    if repo_link:
        link_instruction = f"\n- MUST include this link in the tweet: {repo_link}"

    tweet_prompt = f"""Write a single tweet (max 280 characters) for Twitter/X.

Context: {topic_hint}{reference}

TWITTER STYLE RULES:
- MAX 280 characters total including hashtags, emojis, and links
- Short, punchy, exciting — like texting a friend
- Use 2-4 emojis naturally (🚀 🔥 💡 ✨ 👨‍💻 💻 🎯 ⚡){link_instruction}
- End with a question OR a bold statement to get replies
- Include 2-3 hashtags INLINE (woven into the text or at the end)
- NO @mentions
- Casual tone — contractions, exclamations, slang are fine
- ONE short thought, not a mini-essay
- DO NOT use markdown formatting

EXAMPLES OF GOOD TWEETS:
"End of Month 2 in #ALX_BE, and I've started working with Django! 👨‍💻 Excited to build powerful backends using Python's top framework. 🚀💻\n\nWhat's your favorite Django feature? Let's chat! 💬👇 #ALX #Django"

"Just mass-refactored my entire auth system and nothing broke 🔐✨ Check it out: https://github.com/user/repo #DevSecOps #Coding"

"3am debugging session and I finally cracked it 🐛🔥 The feeling is unmatched. Who else has been there? #CodeLife #DevLife"

Output ONLY the tweet text, nothing else."""

    system_msg = "You are a Twitter/X post writer. Write short, punchy tweets under 280 characters. Use emojis and hashtags. Be casual and engaging. NEVER use markdown. Output ONLY the tweet text."

    try:
        if mistral_client and random.random() < 0.7:
            resp = mistral_client.chat.complete(
                model="mistral-large-latest",
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": tweet_prompt}
                ],
                temperature=0.8,
                max_tokens=300,
            )
            tweet = resp.choices[0].message.content.strip()
        elif groq_client:
            resp = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": tweet_prompt}
                ],
                temperature=0.8,
                max_tokens=300,
            )
            tweet = resp.choices[0].message.content.strip()
        else:
            logger.warning("No AI client available for tweet generation")
            return None

        # Clean up: remove quotes the AI may have wrapped around the tweet
        if tweet.startswith('"') and tweet.endswith('"'):
            tweet = tweet[1:-1]
        if tweet.startswith("'") and tweet.endswith("'"):
            tweet = tweet[1:-1]

        # Strip markdown just in case
        tweet = strip_markdown(tweet)

        # Hard enforce 280 char limit
        if len(tweet) > 280:
            # Try to cut at last complete sentence that fits
            truncated = tweet[:280]
            last_punc = max(truncated.rfind('.'), truncated.rfind('!'), truncated.rfind('?'))
            if last_punc > 80:
                tweet = truncated[:last_punc + 1]
            else:
                # Cut at last space to avoid mid-word
                last_space = truncated.rfind(' ')
                if last_space > 80:
                    tweet = truncated[:last_space]

        logger.info("Generated tweet (%d chars): %s", len(tweet), tweet[:80])
        return tweet

    except Exception as e:
        logger.error("Failed to generate tweet with AI: %s", e)
        return None


def post_to_twitter(
    context_data: Dict[str, Any],
    linkedin_post: Optional[str] = None,
) -> Optional[str]:
    """Generate a Twitter-native post and publish it.

    Args:
        context_data: The activity context (same dict passed to generate_post_with_ai)
        linkedin_post: The LinkedIn post for topic reference (tweet will NOT copy it)
    """
    if not twitter_client:
        logger.warning("Twitter client not available - skipping Twitter post")
        return None

    tweet_text = generate_tweet_with_ai(context_data, linkedin_post)
    if not tweet_text:
        logger.warning("Could not generate a tweet — skipping Twitter post")
        return None

    logger.info("Posting tweet: '%s'", tweet_text[:80])

    try:
        response = twitter_client.create_tweet(text=tweet_text)
        if response and response.data:
            tweet_id = response.data['id']
            logger.info("Tweet posted! ID: %s", tweet_id)
            logger.info("  https://twitter.com/i/status/%s", tweet_id)
            return tweet_id
        else:
            logger.warning("Tweet response was empty")
            return None
    except Exception as e:
        logger.error("Twitter post failed: %s", e)
        return None

# --- MAIN BRAIN ---
if __name__ == "__main__":
    # Set TEST_MODE = True to preview posts without posting to LinkedIn
    TEST_MODE = False  # Change to False when you're ready to post live
    
    logger.info("LinkedIn Post Bot Starting...")
    if TEST_MODE:
        logger.info("TEST MODE ENABLED - Posts will NOT go live on LinkedIn")
    
    # Validate credentials before doing any work
    if not validate_credentials(require_linkedin=not TEST_MODE):
        logger.error("Aborting: fix missing credentials and try again.")
        sys.exit(1)
    
    # Priority 1: Check for today's GitHub activity (may return multiple)
    logger.info("Step 1: Checking GitHub activity...")
    github_activities = get_latest_github_activity()

    posts_to_publish: List[Dict[str, Any]] = []

    if github_activities:
        logger.info("Found %d GitHub activity(ies)!", len(github_activities))
        posts_to_publish.extend(github_activities)
    else:
        # Fallback: check repo-level pushes (covers updates not visible in user events)
        logger.info("Step 1b: No direct user events found — scanning repos for recent pushes...")
        repo_activities = get_recent_repo_updates()
        if repo_activities:
            logger.info("Found %d repo-level recent update(s)!", len(repo_activities))
            posts_to_publish.extend(repo_activities)
        else:
            # Priority 2: Check for GitHub stats/milestones
            logger.info("Step 2: Checking GitHub milestones...")
            github_stats = get_github_stats()

            if github_stats and (github_stats['public_repos'] % 5 == 0 or github_stats['followers'] % 10 == 0):
                logger.info("Found a milestone! Generating post...")
                posts_to_publish.append(github_stats)
            else:
                # Priority 3: Use AI to generate generic dev content
                logger.info("Step 3: Generating AI-powered generic post...")
                generic_context: Dict[str, Any] = {
                    'type': 'generic'
                }
                posts_to_publish.append(generic_context)
    
    # Post multiple items (one post per activity)
    if posts_to_publish:
        with open("last_generated_post.txt", "w", encoding="utf-8") as f:
            f.write("")

        for idx, ctx in enumerate(posts_to_publish):
            logger.info("--- Generating post %d/%d ---", idx + 1, len(posts_to_publish))
            post_content = generate_post_with_ai(ctx)
            
            # Final fallback: if the model output seems truncated, append synthesized hashtags
            def _looks_complete_local(text: str) -> bool:
                if not text or len(text.strip()) < 150:
                    return False
                lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
                if not lines:
                    return False
                last = lines[-1]
                tags = [w for w in last.split() if w.startswith('#')]
                return 8 <= len(tags) <= 20

            if post_content and not _looks_complete_local(post_content):
                logger.warning("Post missing proper hashtags line — applying fallback completion.")
                if not post_content.strip().endswith(('.', '!', '?')):
                    post_content = post_content.rstrip()
                    if post_content and post_content[-1].isalnum():
                        post_content += '.'
                hashtags_line = synthesize_hashtags(post_content, desired=18)
                post_content = post_content.rstrip() + '\n\n' + hashtags_line
            if not post_content:
                logger.error("Failed to generate post content for activity; skipping.")
                continue

            with open("last_generated_post.txt", "a", encoding="utf-8") as f:
                f.write("\n" + "="*60 + "\n")
                f.write(post_content + "\n")
                f.write("="*60 + "\n")

            logger.info("GENERATED POST PREVIEW (saved to last_generated_post.txt):")
            print(post_content)  # Print full post to stdout for preview

            if TEST_MODE:
                image_data = get_relevant_image(post_content)
                if image_data:
                    logger.info("Image downloaded (%d bytes — would be used in live mode)", len(image_data))
                else:
                    logger.info("No image for this post")
            else:
                image_data = get_relevant_image(post_content)
                image_asset_urn = None
                if image_data:
                    image_asset_urn = upload_image_to_linkedin(image_data)
                    if image_asset_urn:
                        logger.info("Post will include an image!")

                post_to_linkedin(post_content, image_asset_urn)
                if twitter_client:
                    post_to_twitter(ctx, linkedin_post=post_content)
                if idx < (len(posts_to_publish) - 1):
                    delay_minutes = POST_DELAY_SECONDS / 60
                    logger.info("Sleeping %.0f minutes before next post...", delay_minutes)
                    time.sleep(POST_DELAY_SECONDS)
        logger.info("All posts processed. Previews saved to last_generated_post.txt")
    else:
        logger.warning("No activities to generate posts from.")
