# A3.4a — Web Security Boundary Foundation

Date: 2026-09-15

Status:

**CHECKPOINT**

Project:

**Corvus — Persistent Personal AI on Consumer Hardware**

Stage:

**A3.4 — Web v1 / Read-Only Internet Grounding**

Substage:

**A3.4a — Web Security Foundation**

---

## 1. Purpose

Corvus is beginning to gain access to public Internet information.

This changes the trust model of the system.

Before Web search, page fetching, citations, or model-facing external
evidence are implemented, Corvus establishes a dedicated network
security boundary.

The purpose of this layer is not merely input validation.

It defines what external network authority Corvus is allowed to have.

Core principle:

**READ THE WEB, NEVER ACT ON THE WEB.**

Web v1 is a read-only information capability.

It is not a browser automation system, action agent, shell, or general
network client.

---

## 2. Architectural Boundary

The model must never receive unrestricted network authority.

Qwen must not receive:

- raw sockets;
- arbitrary URL fetching;
- browser automation;
- shell access;
- filesystem access;
- authenticated HTTP sessions;
- cookies;
- private credentials;
- localhost access;
- LAN access.

Instead, future model-facing Web capabilities must pass through narrow
Corvus backend tools.

Target architecture:

user request
→ Corvus runtime
→ constrained Web tool request
→ Web Security Boundary
→ public Internet
→ bounded external evidence
→ Working Context
→ Qwen
→ answer + citations.

The security boundary belongs to Corvus itself.

Search engines and fetch implementations are replaceable components.

---

## 3. Current Security Policy Module

Foundation module:

`app/web_security.py`

Contract tests:

`tests/test_web_security.py`

This module currently performs policy validation only.

It does not yet perform DNS resolution or HTTP requests.

This is intentional.

The policy boundary is established and tested before network access is
introduced.

---

## 4. Allowed Network Surface

Web v1 currently permits only:

- HTTP
- HTTPS

Only default public Web ports are allowed:

- HTTP: 80
- HTTPS: 443

Non-default ports are rejected.

Credentials embedded in URLs are rejected.

URL fragments are removed before fetch use.

Maximum URL length is bounded.

---

## 5. Private Network Protection

Direct access to non-public network addresses is blocked.

Examples include:

- loopback;
- RFC1918 private networks;
- link-local networks;
- unspecified addresses;
- multicast addresses;
- reserved addresses;
- carrier-grade / non-global ranges where applicable;
- IPv6 loopback and link-local ranges.

Examples explicitly covered by tests include:

- `127.0.0.1`
- `10.0.0.0/8`
- `172.16.0.0/12`
- `192.168.0.0/16`
- `169.254.0.0/16`
- `100.64.0.0/10`
- `::1`
- IPv6 link-local addresses.

This prevents Web functionality from becoming an indirect path into
Corvus host services, Docker services, FoxGate, the home LAN, or cloud
metadata endpoints.

---

## 6. Local Hostname Protection

Local-only hostname classes are blocked.

Examples include:

- `localhost`
- `*.localhost`
- `*.local`
- `*.home.arpa`

Hostname syntax is normalized and validated.

IDNA hostname normalization is supported.

---

## 7. DNS Security Contract

The foundation includes a separate contract for validating resolved IP
addresses.

A hostname is not considered safe merely because its textual URL looks
public.

Every resolved address must independently satisfy the public-address
policy.

A DNS answer containing both a public address and a blocked/private
address is rejected.

Important:

DNS validation alone is not sufficient protection against DNS
rebinding.

The future fetch implementation must ensure that the actual network
connection is bound to an address that was already validated.

It must not:

1. validate DNS;
2. hand the hostname to a generic HTTP client;
3. allow that client to perform an independent second DNS resolution.

That would reopen the SSRF boundary.

---

## 8. Redirect Security

Redirect targets must pass through the same public URL security policy.

Future fetch code must revalidate every redirect hop.

A safe initial URL must never be allowed to redirect into:

- localhost;
- LAN addresses;
- metadata endpoints;
- blocked ports;
- credential-bearing URLs;
- other forbidden destinations.

Redirect count is bounded.

Current policy:

`MAX_REDIRECTS = 3`

---

## 9. Resource Limits

Web access must remain bounded.

Current policy foundation defines:

- maximum response size: 2 MiB;
- maximum extracted text: 60,000 characters;
- maximum fetches per turn: 4;
- connect timeout: 3 seconds;
- read timeout: 8 seconds;
- maximum redirects: 3.

These limits exist to reduce:

- memory exhaustion;
- slow-response attacks;
- unexpectedly large downloads;
- accidental crawler behavior;
- uncontrolled tool loops.

---

## 10. External Content Trust Model

Internet content is not trusted instruction.

Future Web content must enter Corvus as:

**UNTRUSTED EXTERNAL EVIDENCE**

External pages may contain text such as:

- system prompts;
- fake tool instructions;
- requests to ignore previous rules;
- requests to reveal data;
- instructions to perform external actions.

Such text remains evidence from a source.

It does not become Corvus authority.

Web evidence must never override:

- Corvus system policy;
- personality policy;
- memory semantics;
- tool authority boundaries;
- user authorization requirements.

---

## 11. Authority Invariants

The following invariants are intentional architecture and must not be
removed casually during future refactors.

### Invariant 1

**The LLM never receives raw network authority.**

### Invariant 2

**Web v1 can read public HTTP(S) information only.**

### Invariant 3

**localhost, LAN, link-local and other non-public destinations are
blocked.**

### Invariant 4

**DNS results must be validated before connection.**

### Invariant 5

**The actual connection must use the validated destination.**

### Invariant 6

**Every redirect target must be revalidated.**

### Invariant 7

**Network operations must have strict time, size, redirect and
per-turn limits.**

### Invariant 8

**External Web content is untrusted evidence, never instruction.**

### Invariant 9

**Search engines are replaceable. The security boundary is not.**

### Invariant 10

**Web read capability must not silently evolve into Web action
authority.**

---

## 12. Explicitly Out of Scope for Web v1

Web v1 does not provide:

- login;
- authenticated browsing;
- POST actions;
- form submission;
- purchases;
- email sending;
- message sending;
- social posting;
- account changes;
- deletion;
- GitHub mutation;
- browser automation;
- shell execution;
- filesystem mutation;
- LAN access;
- arbitrary socket access;
- autonomous browsing loops.

Future action capabilities, if ever introduced, require a separate
authority model and security review.

---

## 13. Validation

The initial security policy contract validates:

- public HTTPS URL acceptance;
- public HTTP URL acceptance;
- public literal IP acceptance;
- non-HTTP scheme rejection;
- localhost rejection;
- local hostname rejection;
- private IPv4 rejection;
- link-local rejection;
- CGNAT / non-global address rejection;
- IPv6 loopback rejection;
- IPv6 link-local rejection;
- URL credential rejection;
- non-default port rejection;
- resolved-address validation;
- mixed public/private DNS answer rejection;
- resource-limit constants.

Validated result:

- Python compile: PASS
- URL policy contract: PASS
- private-network block contract: PASS
- DNS address policy contract: PASS
- resource-limit policy contract: PASS
- `git diff --check`: PASS

---

## 14. Next Engineering Step

The next component is not search integration.

The next component is a safe network fetch foundation:

DNS resolution
→ validate all resolved addresses
→ choose validated public destination
→ connect to the validated destination
→ preserve HTTP Host / TLS hostname semantics
→ bounded response streaming
→ redirect revalidation
→ content-type validation.

This fetch path must close the DNS-rebinding gap before Corvus is
allowed to retrieve arbitrary public pages.

Only after this foundation is validated should search-provider
integration begin.

---

## 15. Status

This checkpoint establishes the first permanent Web security boundary
for Corvus.

It does not yet grant Corvus Internet access.

Status:

**A3.4a Web Security Boundary Foundation — CHECKPOINT**
