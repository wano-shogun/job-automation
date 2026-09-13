# ApplyPilot Feature Build Plan

## Status: Phase 1 COMPLETE ✅ | Phases 2-6 IN PROGRESS

**Goal**: Expand job-automation to include all ApplyPilot features (job discovery, scoring, resume tailoring, cover letters, auto-submit)

**Timeline**: 9-10 weeks parallel development  
**Phase 1 Completion**: 2026-09-12 ✅

---

## Phase 1: Job Discovery (Week 1-2) ✅ COMPLETE

### Modules to Create:
- `src/job_automation/discovery/`
  - `scraper_base.py` - Abstract base class
  - `indeed.py` - Indeed scraper
  - `linkedin.py` - LinkedIn scraper
  - `glassdoor.py` - Glassdoor scraper
  - `ziprecruiter.py` - ZipRecruiter scraper
  - `google_jobs.py` - Google Jobs scraper

### Features:
- [x] Parse job listings
- [x] Extract job details (title, company, location, salary, description)
- [x] Handle pagination
- [x] Store in database
- [x] Rate limiting/delays to avoid blocking
- [x] 5 job board scrapers (Indeed, LinkedIn, Glassdoor, ZipRecruiter, Google Jobs)
- [x] CLI commands for searching and listing jobs
- [x] Comprehensive testing suite
- [x] Error tracking and recovery

### Database Schema:
```sql
CREATE TABLE jobs (
    id INTEGER PRIMARY KEY,
    source TEXT,  -- indeed, linkedin, etc
    job_id TEXT UNIQUE,
    title TEXT,
    company TEXT,
    location TEXT,
    salary TEXT,
    description TEXT,
    url TEXT,
    posted_date DATE,
    discovered_date DATE,
    scraped_at TIMESTAMP
);
```

---

## Phase 2: Job Scoring (Week 2-3)

### Modules:
- `src/job_automation/scoring/`
  - `matcher.py` - Match job to profile
  - `ranker.py` - Score and rank jobs

### Features:
- [ ] Extract job requirements
- [ ] Compare to user skills/experience
- [ ] AI scoring (Claude API for quality)
- [ ] Simple heuristic scoring (backup)
- [ ] Score 1-10 rating
- [ ] Filter by threshold

---

## Phase 3: Resume Handling (Week 3-4)

### Modules:
- `src/job_automation/resume/`
  - `parser.py` - Parse PDF/DOCX resume
  - `tailor.py` - Generate job-specific versions
  - `generator.py` - Generate from profile

### Features:
- [ ] Parse existing resume (PDF, DOCX)
- [ ] Extract sections (skills, experience, education)
- [ ] Tailor per job using Claude
- [ ] Preserve factual accuracy
- [ ] Generate PDF versions
- [ ] Store variants

---

## Phase 4: Cover Letters (Week 4)

### Modules:
- `src/job_automation/cover_letter/`
  - `generator.py` - Generate cover letters

### Features:
- [ ] Research company (web search)
- [ ] Generate personalized letter
- [ ] Use Claude for quality content
- [ ] Save as PDF/TXT
- [ ] Include in applications

---

## Phase 5: Auto-Submit (Week 5-6)

### Modules:
- `src/job_automation/apply/`
  - `submitter.py` - Form submission logic
  - `screening.py` - Answer screening questions
  - `captcha.py` - CAPTCHA handling (optional)

### Features:
- [ ] Navigate job application pages
- [ ] Fill forms (use existing form filler)
- [ ] Upload resume
- [ ] Upload cover letter
- [ ] Answer screening questions (Claude)
- [ ] Submit applications
- [ ] Handle errors/retries
- [ ] Track submissions

---

## Phase 6: Orchestration & Dashboard (Week 6+)

### Modules:
- `src/job_automation/orchestrator.py` - Master controller
- `src/job_automation/dashboard/` - Live UI
  - `app.py` - FastAPI/Streamlit dashboard
  - `templates/` - HTML templates

### Features:
- [ ] Discover jobs in background
- [ ] Score jobs continuously
- [ ] Apply to matching jobs
- [ ] Live progress dashboard
- [ ] Email notifications
- [ ] Application history
- [ ] Settings management

---

## Dependencies to Add

```
selenium>=4.15
beautifulsoup4>=4.12
requests>=2.31
python-docx>=0.8.11
PyPDF2>=3.0
anthropic>=0.25
fastapi>=0.104
uvicorn>=0.24
streamlit>=1.28
aiohttp>=3.9  # async requests
playwright>=1.40  # alternative to selenium
```

---

## Next Steps

1. Create discovery module structure
2. Build Indeed scraper (proof of concept)
3. Build LinkedIn scraper
4. Build scoring system
5. Build resume parser/tailor
6. Build cover letter generator
7. Build auto-submit logic
8. Build dashboard
9. Integration testing
10. Polish & deploy

---

## Architecture Notes

- **Async-first**: Use asyncio for parallel scraping/applying
- **Modular**: Each job board is independent
- **Error handling**: Graceful degradation on failures
- **Rate limiting**: Respect job boards' terms of service
- **Local-first**: Minimal API dependencies (Claude optional)
- **User control**: Always show plan before applying

---

## Database Updates

Add to models.py:
- Job model (scraped listings)
- JobApplication model (our applications)
- Resume model (stored versions)
- CoverLetter model (generated letters)
- Submission model (what we applied to)

---

**Status**: Phase 1 Complete ✅
**Current**: Ready to start Phase 2 (Job Scoring)
**Phase 1 Deliverables**:
- 6 scraper implementations (indeed.py, linkedin.py, glassdoor.py, ziprecruiter.py, google_jobs.py, scraper_base.py)
- Extended database schema (jobs table, scraper_status table)
- JobDiscoveryRepository with full CRUD operations
- 5 CLI commands in discover group (search, list, search-jobs, stats, clean)
- 20+ unit tests for discovery module and database layer
- Comprehensive documentation (DISCOVERY.md, PHASE1_COMPLETION.md)
