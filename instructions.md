# Deployment Instructions - LLM Wiki Agent

This document provides step-by-step instructions to deploy the LLM Wiki Agent to Google Cloud Vertex AI Agent Runtime.

## Prerequisites

1.  **Google Cloud Project**: You need an active GCP project.
2.  **Google Cloud SDK (gcloud)**: Installed and authenticated.
3.  **Python & `uv`**: Ensure Python 3.11+ and `uv` are installed.
4.  **`agents-cli`**: Installed via `uv tool install google-agents-cli`.

## Environment Variables

The agent can be configured using the following environment variables:

-   `WIKI_BUCKET_NAME`: The name of the GCS bucket used for storing the wiki content. Defaults to `agentwiki-adk-wiki-sg` if not set.
-   `LOGS_BUCKET_NAME`: The name of the GCS bucket used for storing telemetry logs and artifacts.

You can set these in a `.env` file in the project root for local development:

```env
WIKI_BUCKET_NAME=your-custom-wiki-bucket
LOGS_BUCKET_NAME=your-custom-logs-bucket
```

## 1. Enable Required APIs

Enable the necessary Google Cloud APIs for the project. This command is important because the agent relies on Vertex AI (Agent Runtime) and Cloud Storage to function.

```bash
gcloud services enable \
    aiplatform.googleapis.com \
    storage.googleapis.com
```
- **`aiplatform.googleapis.com`**: Required for Vertex AI Agent Runtime, where the agent is deployed.
- **`storage.googleapis.com`**: Required for Google Cloud Storage, where the wiki content and manifest are stored.

## 2. Configure GCS Buckets

The agent relies on GCS buckets. Ensure they exist and you have access to them:

-   **Wiki Bucket**: `[YOUR_WIKI_BUCKET_NAME]` (Stores the wiki pages, schema, index, and log). You can override this by setting `WIKI_BUCKET_NAME`.
-   **Manifest Bucket**: `[YOUR_MANIFEST_BUCKET_NAME]` (Stores the `rag_manifest.json`).

If they do not exist, create them:

```bash
gcloud storage buckets create gs://[YOUR_WIKI_BUCKET_NAME]
gcloud storage buckets create gs://[YOUR_MANIFEST_BUCKET_NAME]
```
- **`gcloud storage buckets create`**: This command creates the specified buckets in your project. They are necessary to hold the agent's knowledge base and configuration.

Upload the initial files (if not already done):

```bash
gcloud storage cp schema.md log.md index.md gs://[YOUR_WIKI_BUCKET_NAME]/
gcloud storage cp rag_manifest.json gs://[YOUR_MANIFEST_BUCKET_NAME]/
```
- **`gcloud storage cp`**: This command copies local files to the specified GCS bucket. This is important to initialize the wiki with the schema, an empty index, and the log file so the agent has a starting point.

## 3. IAM Permissions

### User Permissions

To deploy the agent, your user account (or the account running the deployment) needs the following roles on the project:
-   **Vertex AI Administrator** (`roles/aiplatform.admin`)
-   **Storage Admin** (`roles/storage.admin`) (to create buckets and upload files)

### Agent Service Account Permissions

When you deploy the agent to Vertex AI Agent Runtime, it will run as a service account created by Vertex AI. You need to grant this service account access to the GCS buckets so it can read and write files.

1.  Find the service account email. It usually looks like: `service-<PROJECT_NUMBER>@gcp-sa-aiplatform-re.iam.gserviceaccount.com`. You can see it in the deployment output or in the IAM console after the first deployment attempt.
2.  Grant this service account the **Storage Object Admin** role on both the wiki and manifest buckets:

```bash
gcloud storage buckets add-iam-policy-binding gs://[YOUR_WIKI_BUCKET_NAME] \
    --member="serviceAccount:service-[YOUR_PROJECT_NUMBER]@gcp-sa-aiplatform-re.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"

gcloud storage buckets add-iam-policy-binding gs://[YOUR_MANIFEST_BUCKET_NAME] \
    --member="serviceAccount:service-[YOUR_PROJECT_NUMBER]@gcp-sa-aiplatform-re.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"
```
- **`gcloud storage buckets add-iam-policy-binding`**: This command adds an IAM policy binding to a bucket. It is critical because it gives the agent's service account permission to read, write, and delete objects in the specified buckets. Without this, the agent will not be able to maintain the wiki.

## 4. Deployment Steps

Navigate to the project root directory:

```bash
cd /Users/sgardezi/work/projects/agentwiki-adk
```

Deploy the agent using `agents-cli`:

```bash
agents-cli deploy
```

This command will:
-   Introspect your application.
-   Package the code.
-   Deploy it to Vertex AI Agent Runtime.
- **`agents-cli deploy`**: This command automates the deployment process to Vertex AI Agent Runtime. It is the final step to make your agent available in the cloud.

## 5. Verification

Once deployed, you will receive a Playground URL in the output. You can use it to test the agent in the Cloud Console.

Alternatively, you can test locally using:

```bash
agents-cli playground
## 6. Deploying the Wiki Web UI to Cloud Run

The UI is located in the `frontend` directory and is built as a Next.js application.

### Prerequisites for UI Deployment

1.  **Artifact Registry**: You need a repository to store the Docker image.
2.  **Cloud Run**: Enabled in your project.

### Step-by-Step Deployment

1.  **Create Artifact Registry Repository** (if you don't have one):

```bash
gcloud artifacts repositories create agentwiki-repo \
    --repository-format=docker \
    --location=us-central1 \
    --description="Docker repository for AgentWiki"
```

2.  **Build and Push the Docker Image**:

Navigate to the `frontend` directory:
```bash
cd frontend
```

Build the image using Cloud Build (recommended for simplicity):
```bash
gcloud builds submit --tag us-central1-docker.pkg.dev/[YOUR_PROJECT_ID]/agentwiki-repo/wiki-ui:latest .
```
Replace `[YOUR_PROJECT_ID]` with your actual GCP project ID.

3.  **Deploy to Cloud Run**:

```bash
gcloud run deploy wiki-ui \
    --image us-central1-docker.pkg.dev/[YOUR_PROJECT_ID]/agentwiki-repo/wiki-ui:latest \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --set-env-vars WIKI_BUCKET_NAME=[YOUR_WIKI_BUCKET_NAME]
```
Replace `[YOUR_PROJECT_ID]` and `[YOUR_WIKI_BUCKET_NAME]` with your specific values.

### IAM Permissions for Cloud Run

The Cloud Run service needs permission to read from the GCS wiki bucket.

1.  Find the service account used by the Cloud Run service. By default, it uses the default compute service account or a specific one if you configured it.
2.  Grant it **Storage Object Viewer** (`roles/storage.objectViewer`) on the wiki bucket:

```bash
gcloud storage buckets add-iam-policy-binding gs://[YOUR_WIKI_BUCKET_NAME] \
    --member="serviceAccount:[CLOUD_RUN_SERVICE_ACCOUNT_EMAIL]" \
    --role="roles/storage.objectViewer"
```

This ensures the UI can read the markdown files and generate the graph.

