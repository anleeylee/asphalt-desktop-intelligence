---
layout: default
title: "S03 — CAD / DWG / DXF Paving Takeoff Skill"
---

# S03 — CAD / DWG / DXF Paving Takeoff Skill

## 1. Purpose

Extract measurable paving geometry from CAD files without turning the script into a general CAD platform.

## 2. Primary user

Professional estimator / engineer / CAD-aware PM.

## 3. Supported inputs

P0:

- DXF
- CAD files converted to DXF by the user

P1:

- DWG through a supported licensed/installed conversion path

## 4. Core workflow

```text
CAD
↓
layer inventory
↓
entity inventory
↓
unit detection
↓
semantic layer classification
↓
closed polyline detection
↓
area calculation
↓
quantity mapping
↓
validation
```

## 5. AI role

AI maps project-specific layers to semantic classes:

```text
ASPHALT
BASE
MILL
CURB
SIDEWALK
STRIPING
```

It may suggest mappings but must preserve the original layer name and require confirmation for uncertain mappings.

## 6. Required outputs

```json
{
  "layer": "PAV-ASPH",
  "semantic_type": "HMA",
  "entity_count": 14,
  "area_sq_ft": 84200,
  "closed_entities": 12,
  "open_entities": 2,
  "confidence": 0.97
}
```

## 7. Validation

- model units must be known;
- detect open polylines;
- detect self-intersections;
- detect nested islands/holes;
- detect duplicate geometry;
- compare CAD area against plan notes when possible.

## 8. Do not do

- do not auto-edit source CAD;
- do not infer engineering thickness from geometry alone;
- do not treat a layer named `ASPHALT` as proof of material specification.

## 9. Acceptance tests

Use 10 fixture DXF files with known areas. Output area error must be <0.1% for valid closed geometry.
