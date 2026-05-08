# Deployment Instructions - LLM Wiki Agent

This document provides step-by-step instructions to deploy the LLM Wiki Agent to Google Cloud Vertex AI Agent Runtime.

## Prerequisites
 
 1.  **Google Cloud Project**: You need an active GCP project.
 2.  **Google Cloud SDK (gcloud)**: Installed and authenticated.
 3.  **Python & `uv`**: Ensure Python 3.11+ and `uv` are installed.
 4.  **`agents-cli`**: Installed via `uv tool install google-agents-cli`.
 5.  **Node.js & npm**: (Required for Web UI) Ensure Node.js (v18+) and npm are installed for local testing and building the frontend.


## Environment Variables

The agent can be configured using the following environment variables:

-   `WIKI_BUCKET_NAME`: The name of the GCS bucket used for storing the wiki content. Defaults to `agentwiki-adk-wiki-sg` if not set.
-   `LOGS_BUCKET_NAME`: The name of the GCS bucket used for storing telemetry logs and artifacts.

You can set these in a `.env` file in the project root for local development:

```env
WIKI_BUCKET_NAME=your-custom-wiki-bucket
LOGS_BUCKET_NAME=your-custom-logs-bucket
```

## 1. Set Project and Enable Required APIs

First, ensure you have set the correct Google Cloud project:

```bash
gcloud config set project [YOUR_PROJECT_ID]
```

Then, enable the necessary Google Cloud APIs for the project. This command is important because the agent relies on Vertex AI (Agent Runtime) and Cloud Storage, and the UI relies on Artifact Registry, Cloud Build, and Cloud Run.

```bash
gcloud services enable \
    aiplatform.googleapis.com \
    storage.googleapis.com \
    artifactregistry.googleapis.com \
    run.googleapis.com \
    cloudbuild.googleapis.com
```
- **`aiplatform.googleapis.com`**: Required for Vertex AI Agent Runtime, where the agent is deployed.
- **`storage.googleapis.com`**: Required for Google Cloud Storage, where the wiki content and manifest are stored.
- **`artifactregistry.googleapis.com`**: Required for storing the UI Docker image.
- **`run.googleapis.com`**: Required for deploying the UI to Cloud Run.
- **`cloudbuild.googleapis.com`**: Required for building the UI Docker image in the cloud.


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
## 6. Running the Wiki Web UI Locally

You can run the frontend locally to test the UI and the graph visualization.

### Prerequisites

1.  **Node.js**: Ensure you have Node.js installed (v18+ recommended).
2.  **Application Default Credentials**: The frontend needs to access GCS. Ensure you have set up Application Default Credentials:
    ```bash
    gcloud auth application-default login
    ```

### Steps

1.  Navigate to the `frontend` directory:
    ```bash
    cd frontend
    ```

2.  Install dependencies:
    ```bash
    npm install
    ```

3.  Set the `WIKI_BUCKET_NAME` environment variable and start the development server:
    ```bash
    # On macOS/Linux
    WIKI_BUCKET_NAME=[YOUR_WIKI_BUCKET_NAME] npm run dev
    
    # On Windows (PowerShell)
    $env:WIKI_BUCKET_NAME="[YOUR_WIKI_BUCKET_NAME]"; npm run dev
    ```
    Replace `[YOUR_WIKI_BUCKET_NAME]` with your specific bucket name (e.g., `agentwiki-adk-wiki-sg`).

4.  Open [http://localhost:3000](http://localhost:3000) in your browser.

> [!NOTE]
> If port 3000 is already in use, Next.js might fail to start or try to use another port. You can specify a port using `npm run dev -- -p [PORT_NUMBER]`.


## 7. Deploying the Wiki Web UI to Cloud Run with IAP

The UI is located in the `frontend` directory and is built as a Next.js application. These instructions cover deploying it with direct Identity-Aware Proxy (IAP) integration.

### Prerequisites for UI Deployment

1.  **Artifact Registry**: You need a repository to store the Docker image.
2.  **Cloud Run**: Enabled in your project.
3.  **IAP**: Enabled in your project.

### Step-by-Step Deployment

1.  **Enable Required APIs**:
    ```bash
    gcloud services enable iap.googleapis.com run.googleapis.com
    ```

2.  **Create Artifact Registry Repository** (if you don't have one):
    ```bash
    gcloud artifacts repositories create agentwiki-repo \
        --repository-format=docker \
        --location=us-central1 \
        --description="Docker repository for AgentWiki"
    ```

3.  **Build and Push the Docker Image**:
    Navigate to the `frontend` directory:
    ```bash
    cd frontend
    ```
    Build the image using Cloud Build:
    ```bash
    gcloud builds submit --tag us-central1-docker.pkg.dev/[YOUR_PROJECT_ID]/agentwiki-repo/wiki-ui:latest .
    ```
    Replace `[YOUR_PROJECT_ID]` with your actual GCP project ID.

4.  **Deploy to Cloud Run with IAP**:
    ```bash
    gcloud run deploy wiki-ui \
        --image us-central1-docker.pkg.dev/[YOUR_PROJECT_ID]/agentwiki-repo/wiki-ui:latest \
        --platform managed \
        --region us-central1 \
        --no-allow-unauthenticated \
        --iap \
        --set-env-vars WIKI_BUCKET_NAME=[YOUR_WIKI_BUCKET_NAME]
    ```
    Replace `[YOUR_PROJECT_ID]` and `[YOUR_WIKI_BUCKET_NAME]` with your specific values.
    *   `--no-allow-unauthenticated`: Restricts public access.
    *   `--iap`: Enables direct IAP integration.

5.  **Grant Invoker Permission to IAP Service Agent**:
    IAP needs permission to invoke the Cloud Run service.
    ```bash
    gcloud run services add-iam-policy-binding wiki-ui \
        --region=us-central1 \
        --member=serviceAccount:service-[YOUR_PROJECT_NUMBER]@gcp-sa-iap.iam.gserviceaccount.com \
        --role=roles/run.invoker
    ```
    Replace `[YOUR_PROJECT_NUMBER]` with your actual GCP project number.

6.  **Grant Access to Users**:
    Grant the "IAP-secured Web App User" role to the users who should have access.
    ```bash
    gcloud iap web add-iam-policy-binding \
        --member=user:[USER_EMAIL] \
        --role=roles/iap.httpsResourceAccessor \
        --region=us-central1 \
        --resource-type=cloud-run \
        --service=wiki-ui
    ```
    Replace `[USER_EMAIL]` with the email of the user (e.g., `user@example.com`).

### IAM Permissions for Cloud Run to access GCS

The Cloud Run service needs permission to read from the GCS wiki bucket.

1.  Grant the Cloud Run service account **Storage Object Viewer** (`roles/storage.objectViewer`) on the wiki bucket. By default, Cloud Run uses the default compute service account:
    ```bash
    gcloud storage buckets add-iam-policy-binding gs://[YOUR_WIKI_BUCKET_NAME] \
        --member="serviceAccount:[YOUR_PROJECT_NUMBER]-compute@developer.gserviceaccount.com" \
        --role="roles/storage.objectViewer"
    ```
    Replace `[YOUR_PROJECT_NUMBER]` and `[YOUR_WIKI_BUCKET_NAME]` with your specific values.


