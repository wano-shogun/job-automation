# ApplyPilot agent design

## Principle

Use small, bounded workers for interpretation. Give one coordinator ownership of
job state and one browser worker ownership of the active page. Independent job
search and ranking can run concurrently. Browser actions for one application
run in order, because later questions depend on earlier answers.

## Stage contracts

| Worker | Input | Output and evidence |
| --- | --- | --- |
| Discovery | Search query, location, board | Canonical job identity, title, direct application URL, source |
| Ranking | Job, candidate preferences | Score, reasons, hard filters |
| Inspector | Browser page | Visible controls, labels, options, required state, validation messages, step identity |
| Answer planner | Field snapshot, confirmed profile facts | Proposed value, fact source, confidence, unresolved questions |
| Browser executor | Approved field plan | Observed value after each action, upload and choice state |
| Verifier | Updated page | Remaining required fields, validation errors, next-step or final-review state |
| Confirmation checker | Submission attempt | Site receipt evidence or an unknown outcome |

The coordinator accepts a stage result only after its evidence is recorded. An
answer planner may say `needs_review`; it must not invent work history,
authorization, location, or compensation facts.

## Browser loop

1. Observe the current page and discover fields, including conditional fields.
2. Map known fields to facts and saved answers. Mark unknown or ambiguous fields
   for review.
3. Fill one field or one small group, then read the value back from the page.
4. Reobserve after any action that changes the form. Stop when the step cannot
   be verified.
5. Show the completed application in visible Chrome before a final submission.
6. Record a confirmed application only when the site returns clear receipt
   evidence. An uncertain click is never automatically repeated.

## Durable execution

The current implementation records `ranked`, `filling`, `ready_for_review`,
`needs_review`, and `failed` stages in SQLite, without copying personal answers
into the journal. Each run has an ID, and `agent status` shows recent attempts.
This is an audit trail, not yet a recovery queue.

A production recovery queue should use one row per candidate account, ATS, and
canonical job ID. It needs an atomic claim, lease expiry, attempt count, and
an append-only evidence trail. On restart, it can repeat discovery, inspection,
and field verification. A final submit attempt with an unknown outcome must
pause for human investigation before any retry.

## Current boundaries

- Public Ashby board search returns direct application URLs.
- The browser worker fills native controls, verifies entered values, and
  reinspects required fields revealed during filling.
- A human can review a visible form before the explicit final click.
- Multiple application steps, embedded frames, custom dropdowns, and login
  flows need dedicated browser inspection and ATS adapters.
- Headless preparation is supported. Final submission currently requires a
  visible review session.
