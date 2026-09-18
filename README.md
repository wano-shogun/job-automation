# Job Application Autofill & Tracker

A Python CLI for finding jobs on public ATS boards, ranking them against a local profile, and filling application forms in Chrome for review. Coverage varies by site and by employer form.

## Verified agent workflow

Search a public Ashby board and prepare one application in visible Chrome:

```powershell
python -m job_automation.cli agent run "Full Stack Developer" --ashby-board super.com --max-jobs 1
```

Add `--headless` to run without a window, and `--resume path/to/resume.pdf` to attach a resume where the form asks for one. Repeat `--ashby-board` to search more boards. The command displays the profile name and email it will use before opening an application. It fills fields and reports questions that need review; it does not send an application.

The agent currently requires an Ashby board name because its public jobs feed supplies direct application URLs. The older Indeed discovery scraper returns listing links and is not yet connected to a reliable application navigation flow. A final application is recorded only after the site shows a submission confirmation.

## Features

- 🤖 **Smart Form Autofill**: Intelligently detects form fields and auto-fills them from your profile
- 📊 **Application Tracking**: Track the status of all your applications in one place
- 🔍 **Job Board Detection**: Automatically detects which job board you're on
- 📋 **Form Parsing**: Parses complex forms with text inputs, dropdowns, textareas, checkboxes, and more
- 🛡️ **Review Before Submit**: Agent runs stop for review; the separate `apply fill --submit` command requires explicit confirmation
- 🤖 **Claude Integration** (planned): Use Claude API to help answer screening questions intelligently

## Supported Job Boards

- Ashby public job boards: direct application discovery and site-specific form labels
- Other sites: generic native HTML form filling when given a direct application URL

## Installation

### Prerequisites

- Python 3.11+
- Chrome browser (for Selenium)

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd job-automation
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -e .
pip install -e ".[dev]"  # For development/testing
```

4. Set up your profile and answers:
```bash
# Copy the example configs
cp config/profile.json.example ~/.job-automation/profile.json
cp config/answers.json.example ~/.job-automation/answers.json

# Edit them with your actual information
nano ~/.job-automation/profile.json
nano ~/.job-automation/answers.json
```

5. (Optional) Set up environment variables:
```bash
cp .env.example .env
# Edit .env as needed
```

## Usage

### Application Tracking

Track all your job applications:

```bash
# Add a new application
job-automation add "Google" "Senior Software Engineer" \
  --url "https://careers.google.com/jobs/..." \
  --notes "Found on LinkedIn"

# List all applications
job-automation list

# List applications by status
job-automation list --status applied
job-automation list --status interviewing

# Update application status
job-automation update-status 1 interviewing
job-automation update-status 1 offer
```

### Form Autofill (Planned)

```bash
# Open a job board and navigate to an application form
# Then run:
job-automation autofill

# This will:
# 1. Detect which job board you're on
# 2. Parse all form fields
# 3. Match fields to your profile/answers
# 4. Show you the fill plan for review
# 5. After review, fill the form (you still click Submit)
```

## Project Structure

```
job-automation/
├── src/job_automation/
│   ├── __init__.py
│   ├── cli.py                 # Command-line interface
│   ├── models.py              # Pydantic models for Application data
│   ├── db.py                  # SQLite database layer
│   │
│   ├── browser/               # Browser automation
│   │   ├── driver.py          # Selenium WebDriver management
│   │   └── detectors.py       # Job board detection
│   │
│   ├── forms/                 # Form parsing and matching
│   │   ├── parser.py          # BeautifulSoup form parsing
│   │   └── matcher.py         # Match fields to profile/answers
│   │
│   ├── profile/               # User profile management
│   │   ├── models.py          # Pydantic models for Profile/Answers
│   │   └── loader.py          # Load profile.json and answers.json
│   │
│   └── autofill/              # Main autofill engine
│       └── engine.py          # Orchestration logic
│
├── tests/                     # Unit tests
├── config/
│   ├── profile.json.example   # Profile template
│   └── answers.json.example   # Answers template
├── .gitignore
├── .env.example               # Environment variables template
├── pyproject.toml             # Project configuration
└── README.md                  # This file
```

## Configuration

### profile.json

Your personal and professional information:

```json
{
  "name": "Your Name",
  "firstName": "First",
  "lastName": "Last",
  "email": "your@email.com",
  "phone": "555-123-4567",
  "linkedIn": "https://linkedin.com/in/yourprofile",
  "github": "https://github.com/yourprofile",
  "portfolio": "https://yoursite.com",
  "address": "123 Main St",
  "city": "San Francisco",
  "state": "CA",
  "zip": "94105",
  "country": "United States",
  "resume": "/path/to/resume.pdf"
}
```

### answers.json

Pre-written answers to common job application questions:

```json
{
  "whyInterested": "Your answer here...",
  "whyCompany": "Your answer here...",
  "experience": "Your answer here...",
  "availability": "2 weeks",
  "workAuthorization": "Yes, I'm a US citizen",
  "sponsorship": "No"
}
```

You can add custom fields for any question you frequently encounter.

## How It Works

### Autofill Flow

1. **Detection**: Detects which job board you're on by analyzing the current URL
2. **Parsing**: Uses BeautifulSoup to parse the form and extract all fillable fields
3. **Matching**: Uses your profile.json and answers.json to intelligently match fields
4. **Planning**: Creates a fill plan with confidence scores (only fills high-confidence matches)
5. **Review**: Shows you exactly what will be filled before proceeding
6. **Execution**: Fills the form fields (you always review and click Submit manually)

### Form Field Types

The tool intelligently handles:
- Text inputs (name, email, etc.)
- Email fields
- Phone fields
- Textareas (cover letters, experiences)
- Select dropdowns
- Checkboxes
- Radio buttons

### Matching Algorithm

Fields are matched based on:
- Field name analysis (e.g., "firstName" matches "first_name")
- Field label text analysis
- Field type (email fields match to your email, phone fields to your phone, etc.)
- Confidence scoring to avoid incorrect matches

## Development

### Running Tests

```bash
pytest
pytest -v  # Verbose
pytest --cov  # With coverage
```

### Code Style

This project follows PEP 8. Format code with:
```bash
pip install black
black src/
```

### Adding Support for New Job Boards

1. Update `JobBoard` enum in `src/job_automation/browser/detectors.py`
2. Add detection logic in `detect_job_board_from_url()`
3. (Optional) Add board-specific form parsing in a new module

## Roadmap

- [ ] Web UI for easier management
- [ ] Claude API integration for intelligent answer generation
- [ ] Resume upload automation
- [ ] Email integration for application confirmations
- [ ] More job boards (AngelList, Built.in, etc.)
- [ ] Advanced form field matching with ML
- [ ] Application statistics and analytics
- [ ] Scheduled autofill for saved drafts

## Limitations

- **Never auto-submits**: You must manually review and click Submit
- **Requires manual browser control**: You navigate to job posts; the tool helps with form filling
- **Profile-based only**: Doesn't make up answers or use AI unless explicitly integrated

## Privacy & Security

- All data (profile, answers, applications) is stored locally
- No data is sent to external services without your explicit action
- Resume file paths must be set manually; the tool doesn't upload files
- Future Claude API integration will be optional and explicit

## Troubleshooting

### "Profile file not found"
Make sure you've copied and filled out `~/.job-automation/profile.json`:
```bash
cp config/profile.json.example ~/.job-automation/profile.json
```

### Chrome driver errors
Make sure you have Chrome installed. The tool uses Selenium's built-in ChromeDriver:
```bash
# Update WebDriver dependencies
pip install --upgrade selenium webdriver-manager
```

### Form fields not detected
Some job boards use JavaScript to dynamically render forms. Try:
1. Waiting a few seconds after the page loads
2. Making sure you're on the actual job application form
3. Opening an issue with the page URL

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes (`git commit -am 'Add my feature'`)
4. Push to the branch (`git push origin feature/my-feature`)
5. Open a Pull Request

## License

MIT License - see LICENSE file for details

## Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check existing documentation
- Review the codebase for examples

## Disclaimer

This tool is designed to help you efficiently fill out job applications. Always review all information before submitting applications. The tool does not have access to external services and relies entirely on your local profile data.
