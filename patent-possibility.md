# Patent Possibility Report: LLM Wiki Agent

_Research conducted: 2026-05-10_

---

## Executive Summary

**Patentability Likelihood: Low-to-Moderate overall, with 1-2 narrow claims potentially viable.**

The research found a crowded and rapidly evolving landscape. The core pattern — an LLM agent that writes and maintains a markdown wiki using index-based navigation instead of vector search — was publicly formalized by Andrej Karpathy in an April 2026 GitHub Gist that went viral (5,000+ stars), followed within weeks by at least 7 open-source implementations. That constitutes significant public prior art for the general architecture.

**Critical timing question**: Was this project designed and substantially documented _before_ April 2026? If yes, some claims remain viable. If after, the Karpathy Gist and its derivatives are invalidating prior art for the core method.

---

## Key Distinguishing Features (Ranked by Novelty)

### 1. Schema-Adaptive Agent Behavior via Runtime-Read `schema.md` — MOST NOVEL

No prior art was found for an LLM agent that reads a user-modifiable schema file _at runtime_ to govern its own organizational behavior — allowing the schema to evolve and be versioned independently of agent code. This is the strongest candidate for a patent claim.

### 2. Explicit Typed YAML Relationship Declarations — MODERATELY NOVEL

Most implementations use informal `[[wikilinks]]`. This project declares structured YAML frontmatter with `relationship_type` and natural-language `description` fields — forming a typed, described graph without a graph database. Distinguishable from competitors.

### 3. Append-Only `log.md` as Provenance Record — NARROW NOVELTY

Not found as a distinct feature in competing implementations. A narrow novelty argument exists as an accountability/audit mechanism for autonomous knowledge modification.

### 4. GCS + Google ADK Stack — WEAK (Obvious Combination)

The specific technology stack (GCS + Gemini + ADK) is not found in other patents. However, USPTO examiners would likely argue this is an obvious combination of known components.

### 5. Index-Based Navigation Without Vector Search — ANTICIPATED

Directly anticipated by Corpus2Skill (arxiv, Apr 2026) and PageIndex by VectifyAI (Feb 2026). No longer novel.

### 6. LLM-as-Writer of Knowledge Base — FULLY ANTICIPATED

Established explicitly by the Karpathy Gist: _"You read it; the LLM writes it."_ Multiple open-source forks implement this. Not patentable as a standalone concept.

---

## Prior Art Found

### Patents

| Patent | What It Covers | Gap vs. This Project |
|--------|---------------|----------------------|
| [WO2024211308A1](https://patents.google.com/patent/WO2024211308A1/en) | LLM-generated knowledge graph | Uses dedicated graph DB, not flat files |
| [US12412138B1](https://patents.google.com/patent/US12412138B1/en) | Agentic orchestration with knowledge repository | No KG synthesis or schema adaptation |
| [US20250053793A1](https://patents.google.com/patent/US20250053793A1/en) | LLM agent orchestration | No knowledge base writing |

No patent was found that claims the specific combination: LLM agent + autonomous markdown wiki writing + schema-adaptive behavior + object storage + hierarchical index navigation + typed YAML relationship frontmatter.

### Academic Prior Art

- **[Karpathy LLM Wiki Gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)** — April 2026. The single most important prior art document. Establishes LLM-as-writer, no-RAG, index navigation.
- **[Agentic Deep Graph Reasoning (MIT/arxiv)](https://arxiv.org/abs/2502.13025)** — February 2025. Autonomous LLM agent builds self-organizing knowledge graph. Uses graph structures not flat files, but establishes the agentic self-organization concept.
- **[Corpus2Skill (arxiv)](https://arxiv.org/abs/2604.14572)** — April 2026. Formalizes hierarchical index navigation as a RAG replacement.

### Commercial Prior Art

| System | Overlap | Gap |
|--------|---------|-----|
| [WeKnora (Tencent)](https://github.com/Tencent/WeKnora) | LLM writes markdown wiki, cloud storage, self-maintaining | No schema.md adaptation, no typed YAML relationships |
| [Synthadoc](https://github.com/axoviq-ai/synthadoc) | Structured wikis, cross-references, no RAG | No cloud deployment, no schema adaptation |
| [nashsu/llm_wiki](https://github.com/nashsu/llm_wiki) | Karpathy pattern desktop implementation | No GCS, no typed YAML frontmatter |
| [PageIndex (VectifyAI)](https://github.com/VectifyAI/PageIndex) | Vectorless tree-index navigation | No knowledge writing, no synthesis |

---

## Recommended Patent Claims

Narrowed to what the prior art does _not_ cover.

### Strongest Independent Claim (Method)

> A computer-implemented method for autonomously maintaining a knowledge base comprising:
> receiving, by an LLM agent at runtime, a schema document specifying organizational conventions, wherein the schema document is user-modifiable independently of the agent code;
> reading a hierarchical index file from cloud object storage to identify relevant existing knowledge files;
> generating structured markdown files comprising YAML frontmatter with typed, described relationship declarations to other files;
> integrating new content by merging or updating existing files consistent with the current schema;
> updating the index and appending a record to an append-only provenance log;
> **wherein navigation is performed exclusively via the hierarchical index without embedding vectors or vector similarity search.**

### Dependent Claims

- Wherein the schema document may itself be updated by the LLM agent based on emergent organizational patterns observed during ingestion.
- Wherein each typed relationship declaration comprises a target file path, a relationship type field, and a natural-language description field.
- Wherein the cloud object storage is a flat-file bucket with no graph database backend.

---

## Risks

| Risk | Severity |
|------|----------|
| Karpathy Gist (Apr 2026) as prior art | High — if project postdates this |
| Rapid open-source proliferation | High — field saturated within weeks of the Gist |
| Alice / §101 software eligibility | Medium — must frame as technical improvement, not abstract information organization |
| "Obvious combination" argument | Medium — each component is individually well-known |
| Tencent WeKnora potential patent filings | Medium — watch USPTO/WIPO for Tencent filings |

---

## Recommended Next Steps

1. **Establish priority date immediately** — If the project predates April 2026, file a US provisional application (~$1,600 small entity) within days to lock in priority before more prior art accumulates.

2. **Focus claims on the schema-adaptive mechanism** — This is the strongest novel element. Draft claims around the runtime-read, user-modifiable schema governing LLM agent behavior independently of agent code.

3. **Commission a Freedom-to-Operate (FTO) analysis** — Have a registered patent attorney review WO2024211308A1, US12412138B1, and any pending Tencent (WeKnora) or VectifyAI (PageIndex) applications.

4. **Frame as a technical improvement, not information organization** — Under current USPTO AI guidance (August 2025), claims must demonstrate a specific technical improvement to computer functionality. Recommended framing: _"eliminates vector database infrastructure overhead, reduces latency, and provides deterministic interpretable navigation."_ Generic "organizes knowledge better" framing will fail §101.

5. **Consider trade secret protection as an alternative** — Given how crowded the landscape is, keeping the synthesis prompts, schema design, and GCS integration as trade secrets may be more defensible than a patent that requires full public disclosure.

6. **Monitor Tencent's filings** — WeKnora is open source but Tencent may be filing patents on the underlying method. Watch WIPO and USPTO for filings from _Shenzhen Tencent Computer Systems_ in 2025–2026.

---

## Bottom Line

The **schema-adaptive behavior mechanism** and the **typed YAML relationship structure** are the only aspects with a credible novelty argument. Everything else has been publicly disclosed. If this project predates April 2026, file a provisional application immediately and work with a patent attorney to craft narrow claims around those two features.
