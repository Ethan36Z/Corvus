# A3.4b — Safe Public Fetch Foundation

Date: 2026-09-15

Status:

**CHECKPOINT**

Project:

**Corvus — Persistent Personal AI on Consumer Hardware**

Stage:

**A3.4 — Web v1 / Read-Only Internet Grounding**

Substage:

**A3.4b — Safe Public Fetch Foundation**

---

## 1. Goal

A3.4b gives Corvus its first controlled ability to retrieve public
Internet resources.

This stage does not yet connect Web access to the LLM or conversation
runtime.

Its purpose is to build and validate the transport layer beneath future
Web search and citation features.

Core rule:

**READ THE WEB, NEVER ACT ON THE WEB.**

The network client must remain a narrow read-only information channel.

---

## 2. Security Dependency

A3.4b builds on the permanent security boundary established in:

`A3.4a — Web Security Boundary Foundation`

That layer defines:

- public HTTP(S) only;
- default ports only;
- no URL credentials;
- no localhost;
- no LAN;
- no link-local addresses;
- no metadata endpoints;
- bounded redirects;
- bounded response size;
- bounded timeouts;
- external content as untrusted evidence.

A3.4b must not bypass that policy.

---

## 3. Safe Fetch Module

Implementation:

`app/web_fetch.py`

Contract tests:

`tests/test_web_fetch.py`

The public fetch API is:

`fetch_public_page(url)`

The caller cannot provide:

- arbitrary request headers;
- Authorization;
- cookies;
- credentials;
- request bodies;
- POST methods;
- custom sockets;
- proxy configuration.

The normal production path issues GET requests only.

---

## 4. DNS Resolution Model

For each fetch attempt:

hostname
→ DNS resolution
→ validate every returned address
→ select a validated public numeric IP
→ connect directly to that IP.

All DNS answers must satisfy the public-address policy.

If one DNS answer contains a blocked/private address, the request is
rejected.

This prevents mixed public/private resolution from silently crossing
the Corvus network boundary.

---

## 5. DNS Rebinding Protection

A3.4b intentionally avoids this unsafe sequence:

validate hostname resolution
→ pass hostname to generic HTTP client
→ client performs a second DNS resolution.

Instead, after DNS validation the socket receives only the already
validated numeric IP address.

Therefore the transport connection cannot silently resolve the hostname
again.

This closes the primary DNS-rebinding gap identified during A3.4a.

---

## 6. HTTPS Identity Preservation

Pinning the TCP transport to a numeric IP does not disable normal HTTPS
identity verification.

For HTTPS:

TCP destination:

validated numeric IP

TLS SNI:

original hostname

TLS certificate verification:

original hostname

HTTP Host header:

original hostname.

Therefore Corvus retains normal HTTPS certificate validation while also
preventing a second DNS resolution.

TLS verification is not disabled or weakened.

---

## 7. Redirect Handling

Automatic redirect behavior from generic HTTP clients is not used.

Redirects are followed manually.

For every redirect:

1. resolve relative Location against the current URL;
2. validate the new URL;
3. enforce scheme and port policy;
4. reject localhost/private destinations;
5. perform fresh DNS resolution;
6. validate all DNS answers;
7. connect to a newly validated numeric address.

Current redirect limit:

`MAX_REDIRECTS = 3`

A safe initial public URL cannot redirect into a private destination.

---

## 8. Response Boundaries

The fetcher accepts only textual/public-information media types.

Examples include:

- `text/*`
- `application/json`
- XHTML
- XML
- RSS
- Atom.

Binary media such as images are rejected by this Web text-fetch path.

Current maximum response size:

2 MiB.

Both declared Content-Length and streamed bytes are checked.

Oversized responses are rejected.

---

## 9. Content Encoding Policy

Web v1 currently requests:

`Accept-Encoding: identity`

Compressed or transformed responses are rejected by the foundation.

This intentionally keeps byte limits simple and auditable.

Future compression support may be added only with explicit limits on
decompressed output.

---

## 10. Request Authority

The fetcher constructs its own fixed request headers.

The model or caller cannot supply arbitrary headers.

The request contains no:

- Authorization header;
- Cookie header;
- authenticated session;
- caller-provided credentials.

This ensures read-only Web retrieval cannot silently become access to
private user accounts.

---

## 11. Timeout Policy

Current Web foundation uses:

connect timeout:

3 seconds

read timeout:

8 seconds.

Timeouts are treated as controlled Web fetch failure.

Network failure does not grant fallback access to a less restricted
transport path.

---

## 12. Live Public Internet Acceptance

A real public HTTPS request was executed against:

`https://example.com/`

Observed result:

- HTTP status: 200
- media type: `text/html`
- real public DNS resolution
- bounded HTML response read
- no redirects required.

Result:

**LIVE_PUBLIC_HTTPS_FETCH = PASS**

This was the first validated real public Internet fetch through the
Corvus Web security boundary.

---

## 13. Live Negative Acceptance

Real fetch attempts were also made against blocked destinations.

Validated blocked examples:

`http://127.0.0.1/`

and:

`http://169.254.169.254/latest/meta-data/`

Both were rejected with:

`WEB_ADDRESS_BLOCKED`

before any allowed public fetch path could proceed.

Result:

**LIVE_PRIVATE_DESTINATION_BLOCK = PASS**

---

## 14. Contract Validation

A3.4b validates:

- pinned-IP transport;
- no second hostname resolution in the socket layer;
- original hostname preserved for TLS;
- original hostname preserved for HTTP Host;
- mixed public/private DNS rejection;
- redirect revalidation;
- redirect-to-localhost rejection;
- redirect limit;
- binary content rejection;
- transformed/compressed response rejection;
- Content-Length size rejection;
- streamed size rejection;
- non-success HTTP rejection;
- absence of Authorization;
- absence of Cookie;
- GET-only request contract.

Regression validation also confirms all A3.4a security contracts remain
passing.

Validated result:

**WEB PINNED-IP FETCH CONTRACT OK**

**WEB DNS REBINDING BOUNDARY CONTRACT OK**

**WEB REDIRECT REVALIDATION CONTRACT OK**

**WEB CONTENT BOUNDARY CONTRACT OK**

**WEB RESPONSE SIZE CONTRACT OK**

**WEB READ-ONLY REQUEST CONTRACT OK**

**LIVE_PUBLIC_HTTPS_FETCH = PASS**

**LIVE_PRIVATE_DESTINATION_BLOCK = PASS**

---

## 15. Architecture Invariant

The important abstraction is:

search provider
→ safe result identifiers
→ Corvus safe fetcher
→ bounded external evidence.

Search providers must not become alternate unrestricted network paths.

Changing Brave, Bing, Google, SearXNG, or another discovery engine must
not change the Web transport security boundary.

Principle:

**Search engines are replaceable.**

**The Corvus network boundary is not.**

---

## 16. Current Limitations

A3.4b does not yet provide:

- Web search;
- HTML extraction;
- source registry;
- citations;
- model tool routing;
- automatic decision to browse;
- conversation runtime integration;
- external evidence injection.

It provides only the safe public fetch transport foundation.

This separation is intentional.

---

## 17. Next Step

The next stage should build Web discovery above this transport layer.

Expected direction:

search query
→ search provider
→ normalized SearchResult records
→ stable result IDs
→ source registry
→ safe fetch by selected result
→ text extraction
→ untrusted external evidence
→ model context
→ citations.

The LLM should not receive arbitrary URL-fetch authority.

Where possible, page fetching should operate through server-controlled
search-result identifiers rather than unrestricted model-supplied URLs.

---

## 18. Status

Corvus now has a validated, read-only, SSRF-resistant public Web fetch
foundation.

This is the first real public network capability in Corvus.

Status:

**A3.4b Safe Public Fetch Foundation — CHECKPOINT**
