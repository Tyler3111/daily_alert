# constants/string_constants.py
"""Centralized string constants for the job discovery system."""

# ============= SELECTORS =============
JOB_SELECTORS = [
    'div[class*="job"]',
    'li[class*="job"]',
    'div[class*="position"]',
    'a[href*="job"]',
    'div[class*="career"]',
    '[data-job-id]',
    '.job-listing',
    '.job-item',
    '.job-card',
    '.job-posting',
    '.open-position',
    '.role-listing',
    'a[href*="career"]',
    'a[href*="position"]',
    'a[href*="apply"]'
]

# ============= USER AGENTS =============
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15'
]

# ============= EXPERIENCE LEVELS =============
SENIOR_INDICATORS = ['senior', 'lead', 'principal', 'staff', 'manager', 'director', 'head of']
JUNIOR_INDICATORS = ['junior', 'entry', 'entry-level', 'associate', 'graduate', 'intern', 'trainee', 'apprentice']

# ============= LANGUAGE INDICATORS =============
LANGUAGE_INDICATORS = {
    'english': ['english', 'eng', 'english-speaking', 'fluent english'],
    'mandarin': ['mandarin', 'chinese', '中文', '普通话', 'putonghua', '国语'],
    'cantonese': ['cantonese', 'canton', '粤语', '廣東話', 'guangdong', '粤语']
}

# ============= QUEUE NAMES =============
QUEUE_NAMES = {
    'task_queue': 'scrape_tasks',
    'result_queue': 'scrape_results',
    'failure_queue': 'scrape_failures',
    'discovery_queue': 'discovery_tasks'
}

# ============= STATUSES =============
URL_STATUSES = {
    'PENDING': 'pending',
    'ACTIVE': 'active',
    'FAILED': 'failed',
    'DEPRECATED': 'deprecated',
    'DISCOVERED': 'discovered'
}

# ============= SCRAPER CONFIG =============
SCRAPER_CONFIG = {
    'viewport_width': 1280,
    'viewport_height': 720,
    'locale': 'en-US',
    'timezone': 'Asia/Hong_Kong',
    'navigation_timeout': 30000,
    'wait_timeout': 10000,
    'poll_interval': 5,  # seconds
    'max_retries': 3
}