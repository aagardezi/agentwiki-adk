# LLM Wiki Schema

This document defines the structure, conventions, and workflows for the LLM Wiki stored in GCS.

## Directory Structure

The wiki is stored in the GCS bucket `agentwiki-adk-wiki-sg` with the following structure:

- `index.md`: Content-oriented catalog of all pages.
- `log.md`: Chronological record of operations.
- `schema.md`: This file.
- `entities/`: Directory for pages about specific entities (people, places, projects, etc.).
- `concepts/`: Directory for pages about abstract concepts, ideas, or topics.
- `sources/`: Directory for summaries of raw sources.

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
---

# Content

Content goes here...
```

## Conventions

- **Links**: Use relative markdown links to reference other pages (e.g., `[Link Text](../concepts/concept_name.md)` or `[Link Text](entity_name.md)` if in the same directory).
- **Traceability**: Every claim or piece of information should be traceable to a source listed in the frontmatter or cited inline.
- **Contradictions**: If a new source contradicts existing information, do not delete the old information. Instead, document the contradiction, citing both sources.

## Workflows

### Ingest

When a new source is provided:
1. Read the source content.
2. Create a summary page in `sources/`.
3. Identify relevant entities and concepts.
4. Update existing pages in `entities/` and `concepts/` or create new ones if they don't exist.
5. Update `index.md` with links to new/updated pages.
6. Append an entry to `log.md`.

### Query

When answering a question:
1. Consult `index.md` to find relevant pages.
2. Read the relevant pages.
3. Synthesize an answer, citing the pages used.
4. If the synthesis is valuable, consider saving it as a new page in `concepts/` and updating `index.md`.

### Lint

Periodically check the wiki for:
- Broken links.
- Orphan pages (pages with no inbound links).
- Missing frontmatter.
- Stale claims or unresolved contradictions.
