# Job Discovery Module - Phase 1

## Overview

The Job Discovery module is Phase 1 of the ApplyPilot feature roadmap. It provides a suite of web scrapers for discovering job listings across multiple job boards:

- **Indeed** - Indeed.com
- **LinkedIn** - LinkedIn.com
- **Glassdoor** - Glassdoor.com
- **ZipRecruiter** - ZipRecruiter.com
- **Google Jobs** - Google Jobs (aggregator)

## Architecture

### Core Components

```
src/job_automation/discovery/
├── __init__.py              # Module exports
├── scraper_base.py          # BaseScraper abstract class
├── indeed.py                # Indeed scraper
├── linkedin.py              # LinkedIn scraper
├── glassdoor.py             # Glassdoor scraper
├── ziprecruiter.py          # ZipRecruiter scraper
└── google_jobs.py           # Google Jobs scraper
```

### Database Schema

```sql
CREATE TABLE jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,           -- "indeed", "linkedin", etc
    job_id TEXT UNIQUE NOT NULL,    -- Unique ID from source
    title TEXT NOT NULL,             -- Job title
    company TEXT NOT NULL,           -- Company name
    location TEXT NOT NULL,          -- Job location
    salary TEXT,                     -- Salary info (optional)
    description TEXT,                -- Job description (optional)
    url TEXT NOT NULL,              -- Link to job posting
    posted_date TEXT,               -- Original posting date (optional)
    discovered_date TEXT NOT NULL,  -- When we found it
    scraped_at TEXT NOT NULL        -- When we scraped it
);

CREATE TABLE scraper_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL UNIQUE,    -- Scraper source name
    last_run TEXT,                  -- Last execution time
    last_success TEXT,              -- Last successful run
    error_count INTEGER DEFAULT 0,  -- Error counter
    error_message TEXT              -- Last error message
);
```

## Usage

### Command-Line Interface

#### Search for Jobs

```bash
# Search across all job boards
job-automation discover search "Python Developer" --location "San Francisco"

# Search on a specific job board
job-automation discover search "Data Scientist" --source indeed

# Limit results
job-automation discover search "JavaScript" --limit 5
```

#### List Discovered Jobs

```bash
# List all discovered jobs
job-automation discover list

# List jobs from a specific source
job-automation discover list --source linkedin --limit 50

# Use pagination
job-automation discover list --limit 20 --offset 20
```

#### Search Database

```bash
# Search by title, company, or location
job-automation discover search-jobs "Python"
job-automation discover search-jobs "San Francisco"
job-automation discover search-jobs "Google"
```

#### View Statistics

```bash
# See jobs per source and scraper status
job-automation discover stats
```

#### Clean Up Old Jobs

```bash
# Delete jobs older than 30 days
job-automation discover clean --days 30
```

## Implementation Details

### BaseScraper Class

All scrapers inherit from `BaseScraper`, which provides:

- **Rate Limiting**: Configurable delays between requests
- **Retry Logic**: Exponential backoff for failed requests
- **Session Management**: Proper headers and session handling
- **HTML Parsing**: BeautifulSoup integration
- **Job Creation**: Utility methods for creating Job objects

```python
class BaseScraper(ABC):
    def __init__(
        self,
        source: str,
        base_url: str,
        delay_between_requests: float = 1.0,
        timeout: int = 10,
        max_retries: int = 3,
    ):
        ...

    @abstractmethod
    def search(self, query: str, location: str = "", page: int = 1) -> list[Job]:
        """Search for jobs"""
        pass

    @abstractmethod
    def scrape_job_details(self, job_url: str) -> Job | None:
        """Get full job details"""
        pass
```

### Scraper Implementation

Each scraper implements the abstract methods:

```python
class IndeedScraper(BaseScraper):
    def __init__(self):
        super().__init__(
            source="indeed",
            base_url="https://www.indeed.com",
            delay_between_requests=2.0,  # Be respectful
        )

    def search(self, query: str, location: str = "", page: int = 1) -> list[Job]:
        # Scrape job listings
        pass

    def scrape_job_details(self, job_url: str) -> Job | None:
        # Get full job description
        pass
```

## Features

### ✅ Implemented

- [x] Base scraper framework with rate limiting
- [x] Scraper implementations for 5 job boards
- [x] Database schema for storing jobs
- [x] CLI commands for job discovery
- [x] Job search and listing
- [x] Scraper status tracking
- [x] Pagination support
- [x] Search by title/company/location
- [x] Job cleanup (delete old jobs)
- [x] Unit and integration tests

### 🔄 Future Enhancements

- [ ] Selenium/Playwright support for JS-heavy sites
- [ ] Proxy rotation for high-volume scraping
- [ ] Distributed scraping (parallel job board crawling)
- [ ] Advanced filtering (salary ranges, posting date)
- [ ] Resume scoring with Phase 2
- [ ] Export to CSV/JSON
- [ ] Scheduled background scraping

## Rate Limiting

Each scraper has configurable rate limiting:

- **Indeed**: 2 seconds between requests
- **LinkedIn**: 3 seconds between requests (stricter)
- **Glassdoor**: 2.5 seconds between requests
- **ZipRecruiter**: 2 seconds between requests
- **Google Jobs**: 2 seconds between requests

This respects the job boards' Terms of Service and avoids IP blocking.

## Error Handling

All scrapers implement:

- Retry logic with exponential backoff
- Graceful degradation on failures
- Error tracking in database
- User-friendly error messages

## Testing

Run tests with pytest:

```bash
# All discovery tests
pytest tests/test_discovery.py -v
pytest tests/test_discovery_db.py -v

# Run specific test
pytest tests/test_discovery.py::TestIndeedScraper -v
```

## Limitations & Known Issues

### Current Limitations

1. **JavaScript Rendering**: Most job boards use JavaScript to load content. Current implementation uses BeautifulSoup only.
   - Solution: Selenium/Playwright support planned for Phase 1.5

2. **Dynamic Selectors**: Job boards frequently change their HTML structure.
   - Solution: Implement selector fallbacks and update regularly

3. **CAPTCHA/Bot Detection**: Some boards block requests from bots.
   - Solution: Implement proxy rotation and realistic user-agent rotation

4. **Authentication**: LinkedIn and some others require authentication for full data.
   - Solution: Optional Selenium driver with real browser automation

### Workarounds

For best results with JavaScript-heavy sites:

```python
from selenium import webdriver

# Use Selenium driver directly
driver = webdriver.Chrome()
driver.get(url)
html = driver.page_source

# Then parse with BeautifulSoup
from bs4 import BeautifulSoup
soup = BeautifulSoup(html, "html.parser")
```

## Contributing

To add a new scraper:

1. Create a new file: `src/job_automation/discovery/newsource.py`
2. Implement the scraper class:

```python
from job_automation.discovery.scraper_base import BaseScraper

class NewsourceScraper(BaseScraper):
    def __init__(self):
        super().__init__(
            source="newsource",
            base_url="https://newsource.com",
            delay_between_requests=2.0,
        )

    def search(self, query: str, location: str = "", page: int = 1) -> list[Job]:
        # Implement search
        pass

    def scrape_job_details(self, job_url: str) -> Job | None:
        # Implement details scraping
        pass
```

3. Add to exports in `__init__.py`
4. Add CLI integration
5. Add tests

## Next Phase

Phase 2 will implement:

- **Job Scoring**: Match jobs to user profile (see `SCORING.md` - to be created)
- Claude API integration for intelligent scoring
- Heuristic fallbacks

See `BUILD_PLAN.md` for the full roadmap.

## Resources

- [BUILD_PLAN.md](BUILD_PLAN.md) - Full ApplyPilot roadmap
- [README.md](README.md) - Main project documentation
- Tests: `tests/test_discovery.py`, `tests/test_discovery_db.py`

## Related Modules

- `src/job_automation/db.py` - Database layer
- `src/job_automation/models.py` - Data models (Job, Application)
- `src/job_automation/cli.py` - Command-line interface
