# S01 — Asphalt Project Workspace Manager

## 1. Purpose

Create and maintain one normalized local workspace for a paving project. This is infrastructure, not an AI mega-agent.

## 2. User / scenario

**User:** estimator, project manager, foreman, purchaser.  
**Scenario:** a new job arrives with any mixture of plan PDFs, specifications, quotes, photos, tickets and supplier documents.

## 3. Inputs

- project name
- project location
- customer/project ID (optional)
- unit system
- files/folders
- optional supplier/contractor names

## 4. Outputs

```text
project.json
file_manifest.json
source_index.json
audit.log
```

## 5. Requirements

### P0

- create standard folder tree;
- recursively inventory files;
- compute SHA-256 hash, size, timestamp, file type;
- classify files into plans/specs/quotes/tickets/photos/other;
- preserve original paths;
- create stable document IDs;
- support re-run without duplicating documents;
- maintain processing state.

### P1

- detect revised plan sets;
- identify likely superseded files;
- maintain project versions;
- generate a project manifest dashboard.

## 6. Project JSON contract

```json
{
  "project_id": "PROJECT-001",
  "name": "ABC Parking Lot",
  "location": null,
  "units": "US",
  "documents": [],
  "takeoffs": [],
  "specifications": [],
  "quotes": [],
  "tickets": [],
  "supplier_prices": [],
  "photos": [],
  "weather_runs": [],
  "calculation_runs": []
}
```

## 7. Rules

- never overwrite source files;
- never delete a source file automatically;
- derived files live in `working/` or `output/`;
- every downstream script receives `project.json` + relevant source IDs.

## 8. Acceptance tests

1. Import 100 mixed files → all are uniquely indexed.
2. Re-run import → zero duplicate documents.
3. Replace one revised PDF → new hash/version, old source retained.
4. Export manifest → all files traceable to physical path + hash.
