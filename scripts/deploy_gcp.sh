#!/usr/bin/env bash
# One-shot Google Cloud deployment for VyaparVaani AI (run in Cloud Shell or any shell with gcloud).
#
#   1. Cloud Run      - backend API + Gemini Live voice WebSocket + React app (single container)
#   2. Agent Engine   - VyaparVaani Owner Agent (Google ADK)
#   3. Gemini Enterprise - registers the Owner Agent in your Gemini Enterprise app
#
# Usage:
#   export PROJECT_ID=my-project GE_APP_ID=my-gemini-enterprise-app-id
#   export GEMINI_API_KEY=...        # optional: omit to use Vertex AI for Gemini Live too
#   bash scripts/deploy_gcp.sh [all|backend|agent|register]
#
# GE_APP_ID: Cloud console > Gemini Enterprise > Apps > your app > the "ID" column.
set -euo pipefail

STEP="${1:-all}"
PROJECT_ID="${PROJECT_ID:?set PROJECT_ID}"
RUN_REGION="${RUN_REGION:-asia-south1}"          # Mumbai: lowest latency for Indian shops
AGENT_REGION="${AGENT_REGION:-us-central1}"      # Agent Engine region (global GE app accepts any)
GE_LOCATION="${GE_LOCATION:-global}"             # Gemini Enterprise app location: global | us | eu
SERVICE="${SERVICE:-vyaparvaani}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STATE="$ROOT/.deploy_state"; mkdir -p "$STATE"

gcloud config set project "$PROJECT_ID" >/dev/null

ensure_secret() {  # name value
  if ! gcloud secrets describe "$1" >/dev/null 2>&1; then
    printf '%s' "$2" | gcloud secrets create "$1" --data-file=- --replication-policy=automatic
  fi
}

agent_token() {
  if ! gcloud secrets describe ENTERPRISE_AGENT_TOKEN >/dev/null 2>&1; then
    ensure_secret ENTERPRISE_AGENT_TOKEN "$(python3 -c 'import secrets;print(secrets.token_urlsafe(32))')"
  fi
  gcloud secrets versions access latest --secret=ENTERPRISE_AGENT_TOKEN
}

deploy_backend() {
  echo "==> Enabling APIs"
  gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
    secretmanager.googleapis.com aiplatform.googleapis.com discoveryengine.googleapis.com

  agent_token >/dev/null
  local sa num
  num="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
  sa="${num}-compute@developer.gserviceaccount.com"
  gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$sa" \
    --role=roles/secretmanager.secretAccessor --condition=None >/dev/null
  gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$sa" \
    --role=roles/aiplatform.user --condition=None >/dev/null

  local secrets="ENTERPRISE_AGENT_TOKEN=ENTERPRISE_AGENT_TOKEN:latest"
  local envs="ENVIRONMENT=production,DEBUG=False,GEMINI_LIVE_MODEL=${GEMINI_LIVE_MODEL:-gemini-3.8-live}"
  if [[ -n "${GEMINI_API_KEY:-}" ]]; then
    ensure_secret GEMINI_API_KEY "$GEMINI_API_KEY"
    secrets+=",GEMINI_API_KEY=GEMINI_API_KEY:latest"
  else
    envs+=",GOOGLE_GENAI_USE_VERTEXAI=True,GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GOOGLE_CLOUD_LOCATION=$AGENT_REGION"
  fi

  echo "==> Deploying Cloud Run service '$SERVICE' to $RUN_REGION"
  # --max-instances 1: the approval event bus (counter <-> owner) is in-process.
  gcloud run deploy "$SERVICE" --source "$ROOT" --region "$RUN_REGION" --allow-unauthenticated \
    --timeout 3600 --session-affinity --min-instances 1 --max-instances 1 --memory 1Gi \
    --set-env-vars "$envs" --set-secrets "$secrets"

  gcloud run services describe "$SERVICE" --region "$RUN_REGION" --format='value(status.url)' > "$STATE/backend_url"
  echo "==> Backend: $(cat "$STATE/backend_url")"
}

deploy_agent() {
  local url="${BACKEND_URL:-$(cat "$STATE/backend_url" 2>/dev/null || true)}"
  [[ -n "$url" ]] || { echo "Backend URL unknown: run the backend step or export BACKEND_URL"; exit 1; }

  echo "==> Writing Owner Agent runtime config"
  cat > "$ROOT/enterprise_agent/vyaparvaani_owner/.env" <<EOF
GOOGLE_GENAI_USE_VERTEXAI=True
GOOGLE_CLOUD_PROJECT=$PROJECT_ID
GOOGLE_CLOUD_LOCATION=$AGENT_REGION
OWNER_AGENT_MODEL=${OWNER_AGENT_MODEL:-gemini-3.5-flash}
VYAPARVAANI_API_URL=$url
VYAPARVAANI_AGENT_TOKEN=$(agent_token)
EOF

  echo "==> Deploying Owner Agent to Vertex AI Agent Engine ($AGENT_REGION)"
  cd "$ROOT/enterprise_agent"
  [[ -d .venv ]] || { python3 -m venv .venv; .venv/bin/pip install -q -r requirements.txt; }
  local adk=".venv/bin/adk"; [[ -x "$adk" ]] || adk=".venv/Scripts/adk"
  local args=(--project "$PROJECT_ID" --region "$AGENT_REGION" --display_name "VyaparVaani Owner Agent"
              --description "Owner back-office agent: briefing, credit approvals, udhaar, restock, voice audit"
              --otel_to_cloud)
  [[ -s "$STATE/agent_engine_id" ]] && args+=(--agent_engine_id "$(cat "$STATE/agent_engine_id")")
  "$adk" deploy agent_engine "${args[@]}" vyaparvaani_owner | tee "$STATE/agent_deploy.log"

  grep -oE 'reasoningEngines/[0-9]+' "$STATE/agent_deploy.log" | tail -1 | cut -d/ -f2 > "$STATE/agent_engine_id" || true
  [[ -s "$STATE/agent_engine_id" ]] || { echo "Could not parse the Agent Engine ID from the log; set it in $STATE/agent_engine_id"; exit 1; }
  echo "==> Agent Engine: projects/$PROJECT_ID/locations/$AGENT_REGION/reasoningEngines/$(cat "$STATE/agent_engine_id")"
}

register_agent() {
  local app="${GE_APP_ID:?set GE_APP_ID (Gemini Enterprise app ID)}"
  local engine_id; engine_id="$(cat "$STATE/agent_engine_id")"
  local host="https://${GE_LOCATION}-discoveryengine.googleapis.com"

  echo "==> Registering Owner Agent in Gemini Enterprise app '$app'"
  curl -sS -X POST \
    -H "Authorization: Bearer $(gcloud auth print-access-token)" \
    -H "Content-Type: application/json" -H "X-Goog-User-Project: $PROJECT_ID" \
    "$host/v1alpha/projects/$PROJECT_ID/locations/$GE_LOCATION/collections/default_collection/engines/$app/assistants/default_assistant/agents" \
    -d @- <<EOF | tee "$STATE/ge_register.json"
{
  "displayName": "VyaparVaani Owner Agent",
  "description": "For the shop owner: today's shop briefing; approve or reject credit orders escalated by the VyaparVaani counter voice agent (decision is announced at the counter); udhaar / khata balances and payment reminders; low-stock reorder and restock; audit of every voice transaction. Use for any question about the kirana shop, its customers, khata, stock or sales.",
  "adkAgentDefinition": {
    "provisionedReasoningEngine": {
      "reasoningEngine": "projects/$PROJECT_ID/locations/$AGENT_REGION/reasoningEngines/$engine_id"
    }
  }
}
EOF
  echo
  echo "==> Done. Open Gemini Enterprise > Agents > 'VyaparVaani Owner Agent'."
  echo "    If this call fails, register in the console: Gemini Enterprise > your app > Agents > Add agent >"
  echo "    'Custom agent via Agent Runtime' > resource: projects/$PROJECT_ID/locations/$AGENT_REGION/reasoningEngines/$engine_id"
}

case "$STEP" in
  backend)  deploy_backend ;;
  agent)    deploy_agent ;;
  register) register_agent ;;
  all)      deploy_backend; deploy_agent; register_agent ;;
  *) echo "usage: $0 [all|backend|agent|register]"; exit 1 ;;
esac
