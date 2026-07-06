# Wiki Graph Traversal and GCS Raw File Citation Guidelines

To answer queries, you must systematically traverse the wiki structure and locate grounding facts in the original source documents.

## Guidelines
1. Always start by reading the central index file `index.md` and the update log `log.md`.
2. Map conceptual topics to specific markdown pages under directory categories (e.g. `concepts/`, `entities/`, `technologies/`).
3. Follow markdown page link references (e.g. `[Other Page](../concepts/other.md)`) to expand your research graph.
4. Scan the frontmatter or inline links of wiki pages to locate source summary files (usually stored under `sources/`, e.g. `sources/source_document.md`).
5. From the source summary, follow the direct citation link to retrieve the original raw file (stored in GCS under the `raw_data/` prefix, e.g. `raw_data/original_file.pdf`).
6. Rely on raw data file contents as the ultimate source of truth to verify details and formulate answers.
7. Any fact asserted in your draft response MUST list its corresponding wiki page, source summary, and raw GCS file path (e.g. `raw_data/filename`) as explicit citations.
