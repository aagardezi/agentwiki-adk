# LLM Wiki Schema

This document defines the structure, conventions, and workflows for the LLM Wiki stored in GCS.

## Directory Structure

The wiki is stored in the GCS bucket `your-wiki-bucket-name`. The structure is **dynamic and multi-layered**. The agent should organize files into logical directories and subdirectories based on domain and topic.

Special files at the root:
- `index.md`: Content-oriented catalog of all pages.
- `log.md`: Chronological record of operations.
- `schema.md`: This file.
- `sources/`: Directory for summaries of raw sources (keep flat).

Example of a logical hierarchy (the agent is encouraged to create new branches as needed):
- `compliance/`
  - `regulators/` (e.g., `fca.md`, `pra.md`)
  - `frameworks/` (e.g., `smcr.md`, `mifid-iii.md`)
  - `concepts/` (e.g., `compliance.md`, `kyc.md`)
- `technology/`
  - `ai/`
    - `platforms/` (e.g., `vertex-ai.md`)
    - `models/` (e.g., `gemini.md`)
  - `defi/` (e.g., `de-fi.md`)
- `agents/`
  - `frameworks/` (e.g., `google-adk-framework.md`)
  - `implementations/` (e.g., `global-kyc-compliance-agent.md`)



## Page Format

All markdown files in the wiki (except special files like `index.md` and `log.md`) MUST have YAML frontmatter at the top.

Example:
```markdown
---
title: Document Title
created_at: 2026-05-07
updated_at: 2026-05-07
sources: [source_id_1, source_id_2]
tags: [tag1, tag2]
relationships:
  - target: "concepts/concept_name.md"
    type: "relates_to"
  - target: "entities/entity_name.md"
    type: "regulated_by"
---

# Content

Content goes here...
```

## Conventions

- **Links**: Use relative markdown links to reference other pages (e.g., `[Link Text](../concepts/concept_name.md)` or `[Link Text](entity_name.md)` if in the same directory). These represent general connections.
- **Explicit Relationships**: Use the `relationships` field in the frontmatter to define high-value, typed connections. This supercharges the graph view and helps models understand the domain better.
- **Traceability**: Every claim or piece of information should be traceable to a source listed in the frontmatter or cited inline.
- **Contradictions**: If a new source contradicts existing information, do not delete the old information. Instead, document the contradiction, citing both sources.

## Workflows

### Ingest

When a new source is provided:
1. Read the source content.
2. Create a summary page in `sources/`.
3. Identify relevant entities, concepts, technologies, protocols, and organizations. Be thorough in extracting new terms.
4. Update existing pages or create new ones in a logically determined hierarchical directory.
   - Concrete agent implementations MUST go into `agents/implementations/`.
   - Agent frameworks MUST go into `agents/frameworks/`.
   - New technologies, protocols (like MCP), and platforms MUST go into appropriate subdirectories under `technology/` (e.g., `technology/protocols/`, `technology/platforms/`).
   - You are encouraged to create new subdirectories or even top-level domains if the topic warrants it.


5. **Identify Relationships**: Actively look for specific relationships between the new/updated pages and existing pages. Add them to the `relationships` frontmatter.
6. **Add Tags**: Assign relevant tags to the page in the frontmatter to facilitate discovery and filtering.
7. Update `index.md` with links to new/updated pages.
8. Append an entry to `log.md`.



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

