"""Run ApplyPilot's browser filler against a URL or the included local form.

The default only fills fields and leaves the browser open for review.  Passing
``--submit`` requires an additional typed confirmation before it can send a
real application.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from job_automation.apply import JobSubmitter
from job_automation.browser.driver import BrowserDriver
from job_automation.profile.loader import ProfileLoader


def main() -> None:
    parser = argparse.ArgumentParser(description="Fill a job application in Chrome.")
    parser.add_argument(
        "url",
        nargs="?",
        default=(Path(__file__).with_name("test_form.html").resolve().as_uri()),
        help="Application URL. Defaults to the local safe test form.",
    )
    parser.add_argument("--resume", help="Path to resume PDF or DOCX.")
    parser.add_argument("--submit", action="store_true", help="Click the final submit button.")
    args = parser.parse_args()

    if args.submit:
        confirmation = input("This will submit a real application. Type SUBMIT to continue: ")
        if confirmation != "SUBMIT":
            raise SystemExit("Submission cancelled.")

    browser = BrowserDriver()
    browser.start()
    try:
        submitter = JobSubmitter(browser.get_driver(), ProfileLoader())
        result = submitter.submit_application(args.url, args.resume, submit=args.submit)
        print(f"Status: {result.status}")
        print(f"Fields filled: {len(result.fields_filled)}")
        if result.required_fields_needing_review:
            print("Required fields needing review:")
            for field in result.required_fields_needing_review:
                print(f"- {field}")
        if result.notes:
            print(result.notes)
        print("Browser is open for review. Press Ctrl+C here to close it.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Closing browser.")
    finally:
        browser.stop()


if __name__ == "__main__":
    main()
