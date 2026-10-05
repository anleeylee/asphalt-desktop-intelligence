# SKILL: S04 Asphalt Specification Reader

## Role
Extract paving requirements from specifications/addenda and compare them with plans and bids.

## Core task
Turn long construction specifications into structured requirements with page-level evidence.

## Extract
- material/mix designation;
- course type;
- thickness;
- density/compaction;
- binder/PG;
- aggregate/base;
- tack coat;
- temperature;
- testing/acceptance;
- special notes.

## Classification
Every statement must be classified as REQUIRED, RECOMMENDED, OPTIONAL, EXAMPLE, or REFERENCE ONLY when evidence supports the classification.

## AI rules
- Preserve source page.
- Never resolve contradictory clauses by guessing.
- Latest addendum must be tracked as a version, not silently overwrite the original.

## Conflict modes
PLAN vs SPEC, SPEC vs ADDENDUM, PLAN vs BID, SPEC vs BID.

## Output
`spec_requirements.json`, `spec_summary.md`, `conflicts.json`, `review_queue.json`.

## Escalate
Any contractual conflict, missing section, unclear addendum precedence, or extracted field with low confidence.
