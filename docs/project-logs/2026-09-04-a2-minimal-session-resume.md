# Stage A2 Checkpoint — Minimal Session Resume

## Context

The A2 backend can already accept persistent chat turns over HTTP.

A daily-use client also needs to recover canonical conversation history after
a browser refresh, API restart, or later return to a session.

## Research / Engineering Question

What is the smallest session surface required before the existing UI can
integrate with the persistent Corvus backend?

## Starting Hypothesis

Corvus does not need a separate session store or conversation manager.

The canonical SQLite Evidence Log should remain authoritative.

A minimal API only needs to:

- list known session IDs;
- expose basic session metadata;
- load canonical messages for one session.

## What We Did

Added:

`GET /api/sessions`

It returns session metadata derived directly from canonical messages:

- session ID;
- message count;
- first and last message IDs;
- created timestamp;
- updated timestamp.

Added:

`GET /api/sessions/{session_id}`

It returns canonical session messages in chronological order.

The response also reports:

- total message count;
- returned message count;
- whether additional older messages exist.

Missing sessions return HTTP 404.

## Evidence / Results

Route validation passed:

`session_list_route=PASS`

`session_detail_route=PASS`

The real A2 HTTP validation session was found:

`a2-http-live`

Its canonical transcript contained:

- `#29` user
- `#30` assistant

Validation passed:

`session_list_contains_live_session=PASS`

`canonical_session_resume=PASS`

`canonical_message_ids_preserved=PASS`

`chronological_session_messages=PASS`

Missing-session behavior passed:

`missing_session_404=PASS`

## Interpretation

The backend now exposes enough canonical session state for a browser client to
reload and continue an existing conversation.

No second session database, generated title system, summary layer, or session
manager is required for the A2 baseline.

## Decision

ADOPT the minimal SQLite-derived session API.

DEFER:

- automatic titles;
- renaming;
- deletion;
- generated summaries;
- conversation folders;
- advanced session management.

## Architecture Impact

SQLite Evidence Log
→ session metadata
→ canonical transcript
→ UI resume

The Evidence Log remains the single source of truth.

## Next Step

Run the final A2 backend daily-use acceptance across HTTP, restart, session
resume, and continued conversation.

Then stop at the UI integration boundary.
