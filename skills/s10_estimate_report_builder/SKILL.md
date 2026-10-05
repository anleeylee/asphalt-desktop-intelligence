# SKILL: S10 Asphalt Estimate Report Builder

## Role
Generate a reproducible project estimate/report from already structured and validated data.

## Inputs
project.json, takeoff, specifications, quotes, supplier prices, delivery tickets, optional weather/photos.

## Do not do
Do not discover new facts, silently fill missing values, or choose a contractor.

## Output
Markdown, JSON, CSV, XLSX and/or PDF.

## Required sections
Project Summary, Takeoff, Pavement Sections, Material Quantities, Order Quantities, Truckloads, Cost Basis, Supplier Evidence, Quote Comparison, Delivery Reconciliation, Weather Notes, Risk/Review Flags, Source Register, Calculation Register.

## Auditability
Every important value must trace to a source or named deterministic calculation run.

## Statuses
INFO, REVIEW, WARNING, MISMATCH, MISSING DATA.
