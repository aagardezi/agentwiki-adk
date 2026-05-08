# LLM Wiki Agent

This project implements an ADK-based agent that builds and maintains a persistent knowledge base (wiki) in Google Cloud Storage (GCS), following the "LLM Wiki" pattern. It avoids traditional RAG (Retrieval-Augmented Generation) and vector search, relying instead on the LLM to actively synthesize and organize knowledge into interlinked markdown files, guided by an index. It also features a rich Web UI with an interactive graph view.

## Core Concept

Unlike traditional RAG systems that retrieve raw document chunks at query time and synthesize answers from scratch every time, this agent:
1.  **Incrementally builds** a structured, interlinked collection of markdown files (the Wiki).
2.  **Maintains consistency** and cross-references as new sources are added.
3.  **Uses an index file** (`index.md`) to navigate the wiki, avoiding the need for vector databases.
4.  **Captures Explicit Relationships**: Defines typed connections (e.g., "regulated_by") in page frontmatter.
5.  **Organizes with Tags**: Assigns tags to pages for structured discovery.
6.  **Dynamic Multi-Layer Hierarchy**: Organizes files into logical directories and subdirectories based on domain, growing dynamically as needed.



## Architecture & Design

The system consists of four main layers:
-   **Raw Sources**: Files or URLs provided by the user (immutable).
-   **The Wiki**: A directory of LLM-generated markdown files stored in GCS (`agentwiki-adk-wiki-sg`).
-   **The Schema**: `schema.md` (also in GCS) defining rules and conventions for the agent.
-   **The Web UI**: A Next.js application providing:
    -   **Tree View Sidebar**: Dynamically generated navigation supporting arbitrary depth.
    -   **Interactive Graph View**: Visualizes links, explicit relationships, and tag clusters.
    -   **Perspective Rendering**: Filters graph to show only selected node and its neighbors.

![Wiki Web UI](frontend_screenshot.png)



### Agent Design

The agent is built using the Google Agent Development Kit (ADK) and uses the `gemini-3-flash-preview` model. It operates in a ReAct (Reasoning + Acting) loop, using the following tools:


-   **GCS IO Tools**: Read, write, and list files in the GCS wiki bucket.
-   **Extractor Tools**: Extract text content from URLs and files (including PDFs).

### Interaction Flow

```mermaid
graph TD
    User([User]) -->|Query/Ingest| Agent[LLM Wiki Agent]
    User -->|Browse/Visualize| UI[Wiki Web UI]
    Agent -->|Read/Write| GCS[(GCS Wiki Bucket)]
    UI -->|Read/Generate Graph| GCS
    Agent -->|Extract Content| Ext[Extractor Tools]
    Ext -->|Fetch| Web[External URL]
    Ext -->|Read| File[Local File]
    
    subgraph GCS Bucket
        schema[schema.md]
        index[index.md]
        log[log.md]
        folders[Hierarchical Folders...]
        sources[sources/]
    end
    
    Agent -.->|Follows Rules| schema
    Agent -.->|Navigates via| index
    Agent -.->|Logs Actions to| log
    
    subgraph Knowledge Graph Features
        Tags[Tags]
        Rels[Explicit Relationships]
    end
    
    UI -.->|Visualizes| Knowledge Graph Features
```



## Project Structure

```
agentwiki-adk/
├── app/
│   ├── __init__.py
│   ├── agent.py          # Defines the ADK agent and instructions
│   ├── agent_runtime_app.py # Entry point for Agent Runtime
│   └── tools/
│       ├── __init__.py
│       ├── gcs_io.py     # Tools for reading/writing to GCS
│       └── extractor.py  # Tools for content extraction
├── frontend/             # Next.js Web UI
│   ├── app/              # App router pages and API routes
│   ├── components/       # React components (Graph, Sidebar, etc.)
│   └── ...
├── pyproject.toml        # Dependencies and project metadata
├── schema.md             # Initial schema (uploaded to GCS)
├── index.md              # Initial index (uploaded to GCS)
├── log.md                # Initial log (uploaded to GCS)
├── rag_manifest.json     # Initial manifest (uploaded to GCS)
└── README.md             # This file
```


## Getting Started

### Prerequisites

-   `uv` installed.
-   `agents-cli` installed (`uv tool install google-agents-cli`).
-   Google Cloud SDK installed and configured.

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

For detailed deployment instructions, including required APIs, IAM permissions, and how to set up direct Identity-Aware Proxy (IAP) for secure access, see [instructions.md](file:///Users/sgardezi/work/projects/agentwiki-adk/instructions.md).
