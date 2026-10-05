---
layout: default
title: "S04 — Asphalt Specification Reader & Conflict Checker"
---

# S04 — Asphalt Specification Reader & Conflict Checker

## 1. Purpose

Read paving specifications and convert requirements into structured project constraints; compare them with plans and bids.

## 2. User / scenario

**User:** estimator / PM / project engineer.  
**Scenario:** a 100+ page specification contains asphalt mix, thickness, density, tack coat, base, compaction and testing requirements.

## 3. Inputs

- specification PDFs
- addenda
- plan notes (optional)
- existing takeoff (optional)

## 4. Outputs

```text
spec_requirements.json
spec_summary.md
conflicts.json
review_queue.json
```

## 5. Extract fields

- mix designation
- course type
- thickness
- density/compaction requirement
- PG/binder information
- aggregate requirements
- base material
- tack coat
- temperature requirements
- testing requirements
- acceptance criteria
- special notes

## 6. AI extraction requirements

Every extracted field must include:

```text
value
unit
source page
quoted context <= necessary excerpt
confidence
state
```

The AI must distinguish:

```text
REQUIRED
RECOMMENDED
OPTIONAL
EXAMPLE
REFERENCE ONLY
```

## 7. Conflict detection

Compare:

```text
PLAN vs SPEC
SPEC vs ADDENDUM
PLAN vs BID
SPEC vs BID
```

Example:

```text
Drawing: 2.5 in HMA
Specification: 3.0 in HMA
Status: REVIEW REQUIRED
```

## 8. Rules

- latest addendum does not automatically erase older text without version evidence;
- conflicting requirements are surfaced, not resolved by AI guesswork;
- the tool must cite source pages.

## 9. Acceptance tests

- extract known requirements from fixture specs;
- preserve page references;
- detect thickness mismatch;
- detect addendum changes;
- never label a planning note as a contract requirement unless source language supports it.
