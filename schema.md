# LLM Wiki Schema

This document defines the structure, conventions, and workflows for the LLM Wiki stored in GCS.

## Directory Structure

The wiki is stored in the GCS bucket `knowldge-graph-jack-sg`. The structure is **dynamic and multi-layered**. The agent should organize files into logical directories and subdirectories based on domain and topic.

Special files at the root:
- `index.md`: Content-oriented catalog of all pages.
- `log.md`: Chronological record of operations.
- `schema.md`: This file.
- `gaps.md`: Auto-maintained list of stub pages (knowledge gaps detected during ingest).
- `schema_proposals.md`: Proposals for schema evolution filed by the Librarian Agent.
- `sources/`: Directory for summaries of raw sources (keep flat).
- `raw_data/`: Directory storing unmodified raw source files in GCS (the immutable ground truth).

Example of a logical hierarchy (the agent is encouraged to create new branches as needed):
- `regulations/`
  - `uk_crr/` (UK Capital Requirements Regulation articles and rules)
  - `supervisory_statements/` (PRA Supervisory Statements like SS10/13, SS3/24, etc.)
  - `policy_statements/` (PRA Policy Statements like PS14/26)
- `capital_and_liquidity/`
  - `own_funds/` (Common Equity Tier 1, Additional Tier 1, Tier 2 capital)
  - `capital_buffers/` (Capital conservation buffer, countercyclical buffer, G-SII/O-SII buffers)
  - `leverage_ratio/` (UK leverage ratio framework)
  - `liquidity_and_nsfr/` (Liquidity coverage ratio (LCR), Net stable funding ratio (NSFR))
- `risk_measurement/`
  - `credit_risk/` (Standardised approach, IRB approach, definition of default)
  - `counterparty_credit_risk/` (CCR, exposure methods)
  - `market_risk/` (Standardised approach, internal model approach)
  - `operational_risk/` (Operational risk capital requirements)
  - `securitisation/` (Securitisation framework, significant risk transfer)
  - `credit_valuation_adjustment/` (CVA risk)
- `reporting_and_disclosure/`
  - `corep/` (Common Reporting templates and instructions)
- `glossary/` (Definitions and key terms from UKCRR and PRA Handbook)



## Page Format

All markdown files in the wiki (except special files like `index.md`, `log.md`, `gaps.md`, and `schema_proposals.md`) MUST have YAML frontmatter at the top.

Example:
```markdown
---
title: Document Title
created_at: 2026-05-07
updated_at: 2026-05-07
sources: [source_id_1, source_id_2]
tags: [tag1, tag2]
status: active          # active | stub | contested
confidence: 0.85        # 0.0–1.0, see Confidence Scoring below
evidence_count: 2       # number of independent sources supporting this page
contested: false        # true if a contradiction has been detected
relationships:
  - target: "concepts/concept_name.md"
    type: "relates_to"
    description: "Both address the same regulatory domain"
  - target: "entities/entity_name.md"
    type: "regulated_by"
    description: "Subject to oversight by this regulator"
---

# Content

Content goes here...
```

## Relationship Type Ontology

All `relationships` entries MUST use one of the following controlled types. Using an undefined type is a schema violation.

| Type | Meaning |
|------|---------|
| `implements` | Concrete realization of an abstract concept or specification |
| `extends` | Builds upon and adds to another concept or system |
| `regulated_by` | Subject to governance or oversight by |
| `contradicts` | Contains claims that conflict with another page |
| `supersedes` | Replaces or deprecates a prior version or approach |
| `uses` | Depends on or employs another technology or concept |
| `relates_to` | General conceptual connection (use sparingly — prefer specific types) |
| `part_of` | A component or subset of a larger whole |

Each relationship entry must include a `description` field explaining why the relationship exists.

## Confidence Scoring

Every knowledge page MUST include a `confidence` score (0.0–1.0) reflecting the reliability of its claims.

| Range | Meaning |
|-------|---------|
| 0.9–1.0 | Official documentation, primary standards, peer-reviewed sources |
| 0.7–0.9 | Reputable secondary sources, established industry publications |
| 0.5–0.7 | Blogs, third-party write-ups, single unverified accounts |
| 0.0–0.5 | Speculative, conflicting, or stub content |

- `evidence_count` increments each time an independent source corroborates this page's claims.
- `contested: true` is set automatically by the Reviewer Agent when a contradiction is detected. Revert to `false` only after the contradiction is resolved and documented.
- Stub pages always start with `confidence: 0.0` and `status: stub`.

## Conventions

- **Links**: Use relative markdown links to reference other pages (e.g., `[Link Text](../concepts/concept_name.md)` or `[Link Text](entity_name.md)` if in the same directory). These represent general connections.
- **Explicit Relationships**: Use the `relationships` field in the frontmatter to define high-value, typed connections. This supercharges the graph view and helps models understand the domain better.
- **Traceability**: Every claim or piece of information should be traceable to a source listed in the frontmatter or cited inline.
- **Contradictions**: If a new source contradicts existing information, do not delete the old information. Instead, document the contradiction, citing both sources.

## Workflows

### Ingest

When a new source is provided:
1. Upload the unmodified original file to GCS under `raw_data/`.
2. Extract the source content from the file/url.
3. Create a summary page in `sources/`. In this summary page, link to the raw data file using the relative format: `[Original File](../raw_data/<filename>)`.
4. Identify relevant entities, concepts, technologies, protocols, and organizations. Be thorough in extracting new terms.
5. Update existing pages or create new ones in a logically determined hierarchical directory.
   - Regulations (articles, rules, supervisory/policy statements) MUST go under `regulations/`.
   - Structural capital, buffers, and leverage framework details MUST go under `capital_and_liquidity/`.
   - Domain-specific risk details (credit risk, market risk, counterparty credit risk, operational risk, CVA, etc.) MUST go under `risk_measurement/`.
   - Common reporting (COREP) and templates MUST go under `reporting_and_disclosure/`.
   - General definitions and terms MUST go under `glossary/`.
   - You are encouraged to create new subdirectories or even top-level domains if the topic warrants it.


6. **Identify Relationships**: Actively look for specific relationships between the new/updated pages and existing pages. Add them to the `relationships` frontmatter.
7. **Add Tags**: Assign relevant tags to the page in the frontmatter to facilitate discovery and filtering.
8. Update `index.md` with links to new/updated pages.
9. Append an entry to `log.md`.



### Query

When answering a question:
1. Consult `index.md` to find relevant pages.
2. Read the relevant pages, paying attention to both inline links and explicit relationships in the frontmatter.
3. Synthesize an answer, citing the pages used.
4. If the synthesis is valuable, consider saving it as a new page in `concepts/` and updating `index.md`.

### Lint

Periodically check the wiki for:
- Broken links.
- Orphan pages (pages with no inbound links).
- Missing frontmatter or malformed relationships.
- Stale claims or unresolved contradictions.

