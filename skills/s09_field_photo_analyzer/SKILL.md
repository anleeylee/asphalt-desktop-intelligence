# SKILL: S09 Asphalt Field Photo Analyzer

## Role
Screen photos for visible pavement distress and field observations.

## Inputs
JPG/PNG/HEIC; optional known reference dimension and project area.

## Detect
potholes, longitudinal/transverse/interconnected cracking, rutting/deformation, edge deterioration, patching, standing water, visible surface anomalies.

## AI rules
- Photo analysis is visual screening only.
- Never infer CBR, structural capacity, remaining life, or exact repair depth from a photo alone.
- Poor-quality images go to review.

## Optional measurement
Approximate crack length/patch area/pothole dimensions only when a valid scale reference exists. Mark `APPROXIMATE` until verified.

## Output
`photo_analysis.json`, `photo_summary.md`, `review_queue.json`.
