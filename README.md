# Active Knowledge Agent Wiki

This project implements an ADK-based agent that builds and maintains a persistent knowledge base (wiki) in Google Cloud Storage (GCS), following the "Active Knowledge Agent Wiki" pattern. It avoids traditional RAG (Retrieval-Augmented Generation) and vector search, relying instead on the LLM to actively synthesize and organize knowledge into interlinked markdown files, guided by an index. It also features a rich Web UI with an interactive graph view.

## Core Concept

Unlike traditional RAG systems that retrieve raw document chunks at query time and synthesize answers from scratch every time, this agent:
1.  **Incrementally builds** a structured, interlinked collection of markdown files (the Wiki).
2.  **Maintains consistency** and cross-references as new sources are added.
3.  **Uses an index file** (`index.md`) to navigate the wiki, avoiding the need for vector databases.
4.  **Captures Explicit Relationships**: Defines typed connections (e.g., "regulated_by") in page frontmatter.
5.  **Organizes with Tags**: Assigns tags to pages for structured discovery.
6.  **Dynamic Multi-Layer Hierarchy**: Organizes files into logical directories and subdirectories based on domain, growing dynamically as needed.



## Architecture & Design

The system consists of five main layers:
-   **Raw Sources**: Files or URLs provided by the user (immutable).
-   **GCS Raw Data**: Unmodified raw files stored in GCS under the `raw_data/` folder (acting as the source of truth).
-   **The Wiki**: A directory of LLM-generated markdown files stored in GCS (configured via `WIKI_BUCKET_NAME` environment variable).
-   **The Schema**: `schema.md` (also in GCS) defining rules and conventions for the agent.
-   **The Web UI**: A Next.js application providing:
    -   **Tree View Sidebar**: Dynamically generated navigation supporting arbitrary depth.
    -   **Interactive Graph View**: Visualizes links, explicit relationships, and tag clusters.
    -   **Perspective Rendering**: Filters graph to show only selected node and its neighbors.

![Wiki Web UI](frontend_screenshot.png)



### Multi-Agent Architecture Design

The system is powered by a **hierarchical multi-agent orchestration system** built on top of the Google Agent Development Kit (ADK). Rather than a single agent attempting to execute all reasoning, verification, and compilation steps sequentially, tasks are delegated to specialized, autonomous sub-agents collaborating through a central orchestrator.

- **Orchestrator Agent** ([agent.py](file:///Users/sgardezi/work/projects/agentwiki-adk/app/agent.py)): The root agent that receives input, initializes the workflow pipeline, coordinates sub-agent tasks, and returns progress reports to the user.
- **Wiki Researcher Agent** ([wiki_researcher_agent.py](file:///Users/sgardezi/work/projects/agentwiki-adk/app/agents/wiki_researcher_agent.py)): An agent that executes the retrieval/Q&A pipeline, analyzing the central index to locate relevant paths, reading wiki pages, source summaries, and raw files under `raw_data/` to answer queries.
- **Synthesizer Agent** ([synthesizer_agent.py](file:///Users/sgardezi/work/projects/agentwiki-adk/app/agents/synthesizer_agent.py)): The core processor that digests extracted source text, identifies concepts, creates/modifies dynamic markdown files in GCS, and defines explicitly typed frontmatter relationships.
- **Reviewer Agent** ([reviewer_agent.py](file:///Users/sgardezi/work/projects/agentwiki-adk/app/agents/reviewer_agent.py)): An independent auditor that scans modified knowledge pages, ensures strict schema compliance, cross-checks claims for contradictions, and flags pages as `contested` if conflicts are found.
- **Librarian Agent** ([librarian_agent.py](file:///Users/sgardezi/work/projects/agentwiki-adk/app/agents/librarian_agent.py)): A bookkeeping agent responsible for maintaining catalog files, compiling `index.md`, recording chronological actions in `log.md`, and tracking stub references in `gaps.md`.
- **Schema Manager Agent** ([schema_manager_agent.py](file:///Users/sgardezi/work/projects/agentwiki-adk/app/agents/schema_manager_agent.py)): An administrative agent that checks for pending directory conventions in `schema_proposals.md` and interactively processes them, merging approved definitions into the live `schema.md` governance file.

### Multi-Agent Topology

```mermaid
graph TD
    User([User]) -->|1. Ingest / Query Request| Orch[Orchestrator Agent]
    User -->|Browse & Audit| UI[Wiki Web UI]

    subgraph multi_agent ["Hierarchical Multi-Agent System"]
        Orch -->|2. Write Content| Synth[Synthesizer Agent]
        Orch -->|3. Verify Factual Integrity| Rev[Reviewer Agent]
        Orch -->|4. Re-Index & Log| Lib[Librarian Agent]
        Orch -->|5. Manage Schema Proposals| SchemaMgr[Schema Manager Agent]
        Orch -->|6. Query / Q&A| Res[Wiki Researcher Agent]
    end

    Orch -->|Extract & Upload| ExtTools[Extractor Tools]
    ExtTools -->|Upload Raw| GCS[(GCS Wiki Bucket)]
    Synth -->|Read/Write Pages| GCS
    Rev -->|Factual Audit| GCS
    Lib -->|Maintain Index & Gaps| GCS
    SchemaMgr -->|Read/Merge Proposals| GCS
    Res -->|Read Index, Logs & Pages| GCS
    
    UI -->|Fetch Graph/Tree| GCS

    subgraph gcs_bucket ["GCS Bucket Layout"]
        schema[schema.md]
        index[index.md]
        log[log.md]
        gaps[gaps.md]
        proposals[schema_proposals.md]
        raw_data[raw_data/]
        hierarchy[Dynamic Hierarchical Folders...]
    end

    GCS --- gcs_bucket
```

### Core Multi-Agent Workflows

#### Ingestion Pipeline

The sequence below illustrates how the Orchestrator coordinates the ingestion of new resources, ensuring uncompromised data extraction, active cross-referencing, validation auditing, and automated directory registration:

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Orchestrator as Orchestrator Agent
    participant Extractor as Extractor Node / Tool
    participant Synthesizer as Synthesizer Agent
    participant Reviewer as Reviewer Agent
    participant Librarian as Librarian Agent
    participant GCS as GCS Storage Bucket

    User->>Orchestrator: Ingest Request (Source URL/File)
    Orchestrator->>Extractor: Extract content & upload
    Extractor->>GCS: Upload original file to raw_data/
    Extractor->>Orchestrator: Extracted source text
    Orchestrator->>Synthesizer: Write wiki pages
    Synthesizer->>GCS: Read existing pages & write updates
    Synthesizer->>Orchestrator: Manifest of modified pages
    Orchestrator->>Reviewer: Verify factual integrity
    Reviewer->>GCS: Cross-check claims & verify directory schema
    Reviewer->>Orchestrator: Factual audit & contradiction review report
    Orchestrator->>Librarian: Re-index & Log
    Librarian->>GCS: Update index.md, log.md, gaps.md & proposals
    Librarian->>Orchestrator: Confirmation
    Orchestrator->>User: Final ingestion summary & health delta
```

#### Schema Evolution Pipeline

When new domains emerge from digested source documents, the system records proposed directory schemas in `schema_proposals.md`. The Orchestrator manages this schema evolution pipeline interactively via the Schema Manager Agent:

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Orchestrator as Orchestrator Agent
    participant SchemaMgr as Schema Manager Agent
    participant GCS as GCS Storage Bucket

    User->>Orchestrator: Schema Manage/Review Request
    Orchestrator->>SchemaMgr: Check schema proposals
    SchemaMgr->>GCS: Read schema_proposals.md
    alt No pending proposals
        SchemaMgr-->>User: No pending schema proposals found
    else Pending proposals exist
        SchemaMgr->>User: Present proposals for interactive approval
        User->>SchemaMgr: Approve/Reject proposal selections
        SchemaMgr->>GCS: Merge approved definitions into schema.md
        SchemaMgr->>GCS: Clear approved entries from schema_proposals.md
        SchemaMgr-->>User: Merge and update confirmation
    end
```


#### Retrieval & Q&A Pipeline

When a user asks a question to retrieve or summarize information from the wiki (e.g., "Summarize the compliance frameworks for IAP"), the system bypasses traditional vector retrieval databases. Instead, the Orchestrator uses the central index file to locate highly relevant, hand-grounded documents and files:

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Orchestrator as Orchestrator Agent
    participant Researcher as Wiki Researcher Agent
    participant GCS as GCS Storage Bucket

    User->>Orchestrator: Q&A/Summary Request (e.g., "Summarize frameworks for IAP")
    Orchestrator->>Researcher: Delegate query to researcher
    Researcher->>GCS: read_wiki_file("index.md") & "log.md"
    GCS-->>Researcher: Index structure & chronological log
    Note over Researcher: Identify relevant page paths<br/>based on index & log
    Researcher->>GCS: read_wiki_file("technology/iap.md")
    GCS-->>Researcher: Target page text & metadata
    Note over Researcher: Identify referenced source summaries
    Researcher->>GCS: read_wiki_file("sources/src_iap.md")
    GCS-->>Researcher: Source summary content with raw link
    Note over Researcher: Locate and retrieve original raw file
    Researcher->>GCS: read_wiki_file("raw_data/iap_doc.pdf")
    GCS-->>Researcher: Original raw file contents
    Note over Researcher: Synthesize citation-backed response<br/>directly from verified data
    Researcher-->>Orchestrator: Grounded response
    Orchestrator-->>User: Fully grounded answer with citations
```


---

## The Active Knowledge Agent Wiki Pattern vs. Traditional RAG

To fully appreciate the benefits of this active, compounding knowledge base, it is helpful to compare it directly with traditional Retrieval-Augmented Generation (RAG).

| Feature | Traditional RAG | Active Knowledge Agent Wiki Pattern |
| :--- | :--- | :--- |
| **State & Memory** | **Stateless**. Retrieves chunks on-the-fly for each query. Forgets what it synthesized last time. | **Stateful**. Actively integrates new information into an evolving, structured knowledge base. |
| **Precision & Links** | **Fuzzy Similarity**. Relies on vector distance, which can retrieve out-of-context or irrelevant text. | **High-Precision Graph**. Uses hard, semantic relationships (`regulated_by`, `contradicts`) and tags defined by the LLM in page frontmatter. |
| **Auditability** | **Black Box**. Vector store contains binary embeddings. Extremely difficult for humans to audit or manually correct. | **Transparent**. Made of clean, human-readable Markdown files in GCS. Humans can directly read and edit the agent's memory. |
| **Infrastructure** | **High Complexity**. Requires running a vector database, embedding APIs, chunking algorithms, and tuning parameters. | **Zero Vector Cost**. Relies entirely on standard cloud storage (GCS) and file system structures. No vector database needed. |
| **Temporal Validity** | **Time Blind**. Vector search cannot separate overlapping historical document versions, retrieving conflicting text from multiple years (e.g., 2024 vs. 2025 booklet chunks). | **Time Aware**. Pages are organized in versioned directories and tagged with validity dates in frontmatter, enabling the Orchestrator to query precise historical policy contexts. |

---

## Beneficial Use Cases

The Active Knowledge Agent Wiki architecture shines in complex, long-form knowledge environments where information is **dynamic**, **highly interlinked**, and **requires human-in-the-loop verification**.

### 📋 1. Insurance Claim Lifecycle & Claims Auditing
*   **The Challenge**: An insurance claims handler faces an influx of 100+ documents per claim—including police reports, medical bills, mechanic estimates, photos, and email exchanges. The claim evolves over weeks or months, and the handler needs to understand the chronological timeline, identify inconsistencies (e.g., medical treatments mismatching the police report), and build a final audit trail.
*   **Why Traditional RAG Fails**: RAG retrieves disconnected fragments of text (e.g., a page from a medical report, a sentence from a policy). It cannot synthesize a cohesive timeline or recognize that a fact retrieved today directly contradicts a fact retrieved two weeks ago because it does not keep state.
*   **The Active Knowledge Agent Wiki Solution**: The agent ingests incoming claim documents and actively maintains a compounding claim wiki. 
    *   It builds a structured timeline (e.g., `/claims/CLAIM-123/timeline.md`), updating it chronologically.
    *   It maps explicit relationships, such as tying `/claims/CLAIM-123/injury-report.md` to the `/claims/CLAIM-123/medical-provider.md` via `treated_by`.
    *   The claims handler can review the resulting claims graph in the Web UI, instantly audit the LLM's synthesis, and correct any errors in the markdown files directly, ensuring perfect factual alignment before final payout approval.

### ⚖️ 2. Regulatory & Compliance Intelligence
*   **The Challenge**: Compliance officers in financial services or healthcare must track hundreds of fast-changing regulatory updates, internal policies, and audit reports. They need to map how a new state law impacts existing corporate rules.
*   **The Active Knowledge Agent Wiki Solution**: The agent ingests new regulatory circulars and actively updates a corporate policy wiki. It creates tags for compliance areas and links policies directly to regulations (e.g., `policy.md` `-[implemented_for]->` `regulation.md`). This dynamic compliance graph lets officers immediately see the blast radius of any rule change.

### 🔬 3. Codebase & Technical Architecture Mapping
*   **The Challenge**: Developers or research teams trying to map out complex system architectures, codebase structures, or open-source protocols.
*   **The Active Knowledge Agent Wiki Solution**: The agent maps out repositories, creates structural directories, extracts and connects concepts (e.g., mapping how MCP servers interact with Agent Platforms), and visualizes these relationships dynamically, creating a self-documenting codebase.

---

## Project Structure

```
agentwiki-adk/
├── app/
│   ├── __init__.py
│   ├── agent.py             # Defines the ADK Orchestrator Agent and workflow
│   ├── agent_runtime_app.py # Entry point for Agent Runtime
│   ├── agents/              # Specialized sub-agents
│   │   ├── __init__.py
│   │   ├── wiki_researcher_agent.py # Retrieval and Q&A researcher agent
│   │   ├── synthesizer_agent.py # Wiki composition & GCS editing agent
│   │   ├── reviewer_agent.py  # Schema & contradiction auditing agent
│   │   ├── librarian_agent.py # Bookkeeping, indexing, & gaps logging agent
│   │   └── schema_manager_agent.py # Automated schema evolution manager agent
│   └── tools/
│       ├── __init__.py
│       ├── gcs_io.py        # Tools for reading/writing to GCS
│       ├── extractor.py     # Tools for content extraction
│       └── health.py        # Quantitative wiki health calculation tool
├── frontend/                # Next.js Web UI
│   ├── app/                 # App router pages and API routes
│   ├── components/          # React components (Graph, Sidebar, etc.)
│   └── ...
├── pyproject.toml           # Dependencies and project metadata
├── schema.md                # Initial schema (uploaded to GCS)
├── index.md                 # Initial index (uploaded to GCS)
├── log.md                   # Initial log (uploaded to GCS)
└── README.md                # This file

```


## Getting Started

### Prerequisites

-   `uv` installed.
-   `agents-cli` installed (`uv tool install google-agents-cli`).
-   Google Cloud SDK installed and configured.

### Environment Configuration

Before running the agent or the Web UI, you must configure the GCS bucket where the wiki will be stored.

For local development, create a `.env` file in the project root **and** in the `frontend/` directory to define the GCS bucket name:

```env
WIKI_BUCKET_NAME=your-unique-gcs-bucket-name
```

*(Note: `.env` files are already configured in `.gitignore` and will not be committed.)*

### Installation

```bash
agents-cli install
```

### Local Development

To test the agent locally using the playground:

```bash
agents-cli playground
```

## Deployment

> [!IMPORTANT]
> Detailed step-by-step instructions for deploying this project to Google Cloud Platform (GCP) with secure **direct Identity-Aware Proxy (IAP) integration** are maintained in [instructions.md](./instructions.md). 
> 
> Please refer to [instructions.md](./instructions.md) for:
> - Required GCP APIs and IAM Role configurations
> - Cloud Run service setup with `--iap` flag
> - GCS Bucket permission binding
> - Multi-stage Docker builds and Artifact Registry push commands
