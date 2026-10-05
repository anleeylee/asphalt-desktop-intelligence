---
layout: default
title: "S09 — Asphalt Field Photo Condition Analyzer"
---

# S09 — Asphalt Field Photo Condition Analyzer

## 1. Purpose

Screen site photographs for visible pavement distress and field conditions that may affect further investigation, repair planning or estimating.

## 2. Users

Foreman, estimator, property manager, homeowner.

## 3. Inputs

- JPG/PNG/HEIC photos
- optional GPS metadata
- optional project area label
- optional reference object/scale

## 4. Detection classes

P0:

- pothole
- longitudinal cracking
- transverse cracking
- interconnected/alligator-like cracking
- rutting/visible deformation
- edge deterioration
- patching
- standing water / visible ponding
- surface segregation/texture anomaly (visual only)

## 5. Output

```json
{
  "photo_id": "IMG-001",
  "observations": [
    {"class":"pothole","confidence":0.94}
  ],
  "severity": "screening_only",
  "notes": [],
  "human_review_required": true
}
```

## 6. AI boundary

This is **visual screening**, not structural pavement diagnosis.

AI must not claim to know:

- pavement layer strength;
- exact CBR;
- remaining structural life;
- exact repair depth;
- engineering cause of cracking from one photo.

## 7. Optional measurement mode

With a known reference dimension, the tool may produce approximate:

- crack length;
- pothole width/length;
- visible patch area.

All such measurements are marked `APPROXIMATE` until verified.

## 8. Acceptance tests

- fixture images with known visible distress;
- low-light/blurry images routed to review;
- no photo-only output is marked “engineering diagnosis”.
