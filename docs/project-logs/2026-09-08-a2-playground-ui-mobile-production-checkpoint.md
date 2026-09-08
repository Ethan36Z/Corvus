# A2 — Playground UI & Mobile Production Checkpoint

Date: 2026-09-08

## Context

Corvus has moved beyond a backend-only daily-use baseline.

The Memory Playground is now the primary interactive surface for both
the private Corvus deployment and the recruiter-facing Demo Corvus
deployment.

After the desktop chat experience stabilized, real use on mobile exposed
several product-level UI issues that were not obvious during desktop
development:

- conversation sessions were identified by opaque internal IDs,
- panel controls contained redundant close buttons,
- the theme control used platform-dependent emoji-style glyphs,
- mobile drawers could appear underneath the global top bar,
- the page could require viewport scrolling instead of behaving like an
  application shell,
- the composer was not consistently positioned at the bottom of the
  mobile viewport,
- iOS Safari could zoom or shift the page when focusing the textarea,
- the software keyboard changed the visual viewport independently of
  the CSS layout viewport.

This checkpoint records the stabilization of the Playground UI before
further personality or memory-capability work.

## Research/Engineering Question

How can the existing Corvus Playground be made usable as a production
desktop and mobile chat surface without redesigning the sealed A0/A1/A2
memory and conversation backend?

The implementation should:

- preserve the existing desktop experience,
- remain lightweight,
- avoid introducing a separate mobile application,
- keep private and demo deployments on the same frontend codebase,
- behave correctly on modern mobile browsers, including iOS Safari.

## Starting Hypothesis

The existing React application was already structurally sufficient.

The highest-value path was therefore not a frontend rewrite.

Instead, the Playground could reach a useful production checkpoint by
tightening several interaction and responsive-layout boundaries:

1. keep internal session IDs internal,
2. make panel controls stateful and visually consistent,
3. treat mobile as a fixed application viewport,
4. let the message region own scrolling,
5. keep the composer inside the visible viewport,
6. account explicitly for iOS VisualViewport behavior.

## What We Did

### 1. Human-readable conversation titles

The conversation list previously displayed session identifiers such as:

`chat-17885635965777`

The sessions API was extended to derive a readable title from the first
user message in each conversation.

The frontend now renders this title while preserving `session_id` as the
internal canonical identifier.

Checkpoint commit:

`716a2f0 Add readable conversation titles`

### 2. Unified panel controls

The left conversation toggle was converted from a static hamburger glyph
into an animated control:

`hamburger → X → hamburger`

The icon reflects whether the Conversations panel is open.

Redundant close buttons inside both the Conversations and Inspector
panels were removed.

The right-side textual `Inspect` button was replaced with a compact
right-panel line icon and a subtle active state.

The `CORVUS / Memory Playground` brand area was intentionally retained.

Checkpoint commit:

`bfb465f Polish Corvus panel toggle controls`

### 3. Mobile application shell

A final mobile layout authority was added for compact screens.

The mobile interface now uses the visible screen as an application shell
rather than allowing the browser document to become the primary
scrolling surface.

Key changes include:

- `100dvh`-based viewport sizing,
- independent message-region scrolling,
- horizontal overflow containment,
- centered mobile composer sizing,
- safe-area-aware bottom spacing,
- drawers positioned below the global top bar,
- compact panel sizing appropriate for phones.

### 4. Theme-control visual consistency

The previous sun/moon text glyphs could render as emoji depending on the
platform.

They were replaced with line-based SVG icons using the same visual
language as the Inspector control.

### 5. iOS textarea focus stability

The mobile textarea font size was raised to 16px.

This prevents iOS Safari from automatically zooming the page when the
composer receives focus.

### 6. iOS VisualViewport integration

CSS viewport units alone were not sufficient when the iOS software
keyboard opened.

Corvus now observes `window.visualViewport` and exposes the actual
visible height and vertical offset to CSS.

The mobile shell follows the visual viewport while the keyboard opens
and closes.

The viewport metadata was also updated with:

`viewport-fit=cover`

This allows safe-area handling on modern iPhones.

Checkpoint commit:

`210b716 Polish Corvus mobile chat experience`

## Evidence/Results

Frontend validation passed after the final mobile changes:

- TypeScript build: PASS
- Vite production build: PASS
- `git diff --check`: PASS

The final production bundle built successfully with Vite 8.2.2.

Real-device testing confirmed improvement of the observed mobile issues:

- textarea focus no longer triggers Safari auto-zoom,
- the composer follows the reduced visible area when the software
  keyboard appears,
- the mobile layout no longer depends on whole-page scrolling,
- panel controls remain accessible from the global top bar,
- theme and Inspector controls use a consistent line-icon style.

The frontend was rebuilt and recreated for both deployments.

Private Corvus:

- container: `corvus-web`
- health endpoint: `127.0.0.1:8097/healthz`
- result: `ok`

Demo Corvus:

- container: `corvus-demo-web`
- health endpoint: `127.0.0.1:8099/healthz`
- result: `ok`

Both frontend images were rebuilt from:

`playground/Dockerfile.production`

The API services, model runtime, and persistent memory data were not
recreated as part of this UI deployment.

## Interpretation

The major remaining Playground problems at this checkpoint were not
backend architecture problems.

They were application-shell and interaction-boundary problems.

The existing React frontend proved sufficient once desktop and mobile
viewport ownership were made explicit.

In particular, iOS software-keyboard behavior demonstrated that
`100vh` / `100dvh` alone cannot always represent the user's actual
visible workspace.

Using the browser VisualViewport API provides a small, targeted solution
without introducing a mobile-specific application architecture.

## Decision

The current Playground UI is accepted as a stable product checkpoint.

Corvus will continue using one shared responsive web frontend for:

- Private Corvus,
- Demo Corvus,
- desktop browsers,
- mobile browsers.

The project will not introduce a separate native mobile client at this
stage.

The following UI principles are retained:

- desktop behavior should not be casually disturbed by mobile fixes,
- mobile layout should behave like an application shell,
- internal identifiers should not dominate user-facing UI,
- controls should communicate state directly,
- platform-dependent emoji should not be used as primary UI icons when
  consistent vector controls are available.

## Architecture Impact

No memory architecture changed.

No retrieval architecture changed.

No session persistence semantics changed.

No model-runtime behavior changed.

The change is isolated to the Playground presentation layer and the
read-only session-list metadata returned for UI presentation.

Current high-level delivery path remains:

A0 retrieval foundation
→ A1 persistent conversation loop
→ A2 daily-use backend
→ Playground UI
→ Private / Demo deployment
→ real-world use and incremental product refinement

The same Playground build continues to serve both private and demo
environments.

## Open Questions

The current UI is intentionally treated as a checkpoint rather than a
final visual design.

Possible future improvements include:

- further small-screen refinement discovered through real use,
- accessibility review,
- richer mobile interaction controls,
- attachment / voice controls in the reserved composer footer,
- additional Inspector presentation work,
- later visual identity work for Corvus.

These are deferred until actual use demonstrates value.

No further UI expansion is required to close this checkpoint.

## Next Step

Return focus to normal Corvus use and the existing Delivery Roadmap.

Future UI changes should be driven by concrete usability problems rather
than continued polishing for its own sake.

The current deployed Playground should now be treated as the baseline
for subsequent product iterations.
