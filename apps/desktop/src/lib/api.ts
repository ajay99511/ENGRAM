/**
 * PersonalAssist API Client
 *
 * Type-safe HTTP client for all PersonalAssist backend endpoints.
 * Uses environment overrides when available and keeps the current desktop
 * default of localhost:8000 for compatibility.
 */

const DEFAULT_API_BASE = "http://127.0.0.1:8000";

function resolveApiBase(): string {
  const explicitBase = import.meta.env.VITE_API_BASE_URL?.trim();
  if (explicitBase) {
    return explicitBase.replace(/\/$/, "");
  }

  const explicitPort = import.meta.env.VITE_API_PORT?.trim();
  if (explicitPort) {
    return `http://127.0.0.1:${explicitPort}`;
  }

  return DEFAULT_API_BASE;
}

const API_BASE = resolveApiBase();
const API_TOKEN = import.meta.env.VITE_API_ACCESS_TOKEN?.trim() || "";

// ── Types ──────────────────────────────────────────────────────────

export interface ChatResponse {
  response: string;
  model_used: string;
  memory_used?: boolean;
  memories_extracted?: Record<string, unknown>;
  thread_id?: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  model_used?: string;
  memory_used: boolean;
  timestamp: string;
}

export interface ChatThread {
  id: string;
  title: string;
  updated_at: string;
}

export interface ChatThreadDetail extends ChatThread {
  messages: ChatMessage[];
}

export interface IngestErrorItem {
  file: string;
  error: string;
}

export interface IngestReport {
  total_files: number;
  processed_files: number;
  total_chunks: number;
  skipped_files: number;
  failed_files: number;
  errors: IngestErrorItem[];
  duration_seconds: number;
  files_processed: string[];
}

export interface ModelInfo {
  id: string;
  name: string;
  provider: string;
  is_local: boolean;
  is_active: boolean;
  size_gb?: number;
  parameter_size?: string;
  description?: string;
  context_window?: string;
  pricing_input?: string;
  pricing_output?: string;
  is_recommended?: boolean;
  api_key_set?: boolean;
  supports_tool_calls?: boolean;
  supports_reasoning?: boolean;
  supports_temperature?: boolean;
  requires_reasoning_echo?: boolean;
}

export interface Memory {
  id: string;
  memory: string;
  content?: string;
  score?: number;
  metadata?: Record<string, unknown>;
}

export interface TraceEvent {
  run_id: string;
  agent_name: string;
  event_type: string;
  content: string;
  timestamp: string;
  metadata: Record<string, unknown>;
}

export interface AgentResult {
  response: string;
  plan: string;
  research: string;
  model_used: string;
  run_id: string;
  tool_loop?: Record<string, unknown>;
}

export interface HealthResponse {
  status: string;
  version: string;
}

export interface PodcastRequest {
  topic: string;
  duration_minutes: number;
  level: "beginner" | "intermediate" | "advanced";
  model?: string;
}

export interface PodcastJob {
  job_id: string;
  topic: string;
  status: string;
  progress_pct: number;
  output_path?: string;
  error?: string;
  created_at: string;
  duration_minutes: number;
  level: string;
}

// ── Helpers ────────────────────────────────────────────────────────

function buildHeaders(includeJson: boolean, extra?: HeadersInit): Headers {
  const headers = new Headers(extra);
  if (includeJson && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (API_TOKEN) {
    headers.set("x-api-token", API_TOKEN);
  }
  return headers;
}

async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: buildHeaders(true, options?.headers),
  });
  if (!res.ok) {
    const err = await res.text().catch(() => "Unknown error");
    throw new Error(`API error ${res.status}: ${err}`);
  }
  return res.json() as Promise<T>;
}

// ── Health ──────────────────────────────────────────────────────────

export async function checkHealth(): Promise<HealthResponse> {
  return api<HealthResponse>("/health");
}

// ── Ingestion ──────────────────────────────────────────────────────

export async function ingestDocument(
  path: string,
  recursive: boolean = true,
  globPatterns?: string[]
): Promise<{ status: string; report: IngestReport }> {
  return api("/ingest", {
    method: "POST",
    body: JSON.stringify({
      path,
      recursive,
      glob_patterns: globPatterns,
    }),
  });
}

// ── Chat ───────────────────────────────────────────────────────────

export async function chatPlain(
  message: string,
  model: string = "local",
  threadId?: string
): Promise<ChatResponse> {
  return api<ChatResponse>("/chat", {
    method: "POST",
    body: JSON.stringify({ message, model, thread_id: threadId }),
  });
}

export async function chatSmart(
  message: string,
  model: string = "local",
  threadId?: string
): Promise<ChatResponse> {
  return api<ChatResponse>("/chat/smart", {
    method: "POST",
    body: JSON.stringify({ message, model, thread_id: threadId }),
  });
}

export async function* chatStream(
  message: string,
  model: string = "local",
  threadId?: string
): AsyncGenerator<string | { thread_id: string }, void, undefined> {
  const res = await fetch(`${API_BASE}/chat/stream`, {
    method: "POST",
    headers: buildHeaders(true),
    body: JSON.stringify({ message, model, thread_id: threadId }),
  });

  if (!res.ok) throw new Error(`Stream error: ${res.status}`);
  if (!res.body) throw new Error("No response body");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        const data = line.slice(6).trim();
        if (data === "[DONE]") return;
        try {
          const parsed = JSON.parse(data);
          if (parsed.thread_id) yield { thread_id: parsed.thread_id };
          if (parsed.text) yield parsed.text;
          if (parsed.error) throw new Error(parsed.error);
        } catch {
          // non-JSON data line, skip
        }
      }
    }
  }
}

export async function* chatSmartStream(
  message: string,
  model: string = "local",
  threadId?: string
): AsyncGenerator<string | { thread_id: string; memory_used?: boolean }, void, undefined> {
  const res = await fetch(`${API_BASE}/chat/smart/stream`, {
    method: "POST",
    headers: buildHeaders(true),
    body: JSON.stringify({ message, model, thread_id: threadId }),
  });

  if (!res.ok) throw new Error(`Smart stream error: ${res.status}`);
  if (!res.body) throw new Error("No response body");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        const data = line.slice(6).trim();
        if (data === "[DONE]") return;
        try {
          const parsed = JSON.parse(data);
          if (parsed.thread_id) yield { thread_id: parsed.thread_id, memory_used: parsed.memory_used };
          if (parsed.text) yield parsed.text;
          if (parsed.error) throw new Error(parsed.error);
        } catch {
          // non-JSON data line, skip
        }
      }
    }
  }
}

export async function getChatThreads(): Promise<{ threads: ChatThread[] }> {
  return api("/chat/threads");
}

export async function getChatThread(threadId: string): Promise<ChatThreadDetail> {
  return api(`/chat/threads/${encodeURIComponent(threadId)}`);
}

export async function deleteChatThread(threadId: string): Promise<{ status: string }> {
  return api(`/chat/threads/${encodeURIComponent(threadId)}`, { method: "DELETE" });
}

// ── Memory ─────────────────────────────────────────────────────────

export async function getAllMemories(
  userId: string = "default"
): Promise<{ memories: Memory[]; count: number }> {
  return api(`/memory/all?user_id=${encodeURIComponent(userId)}`);
}

export async function forgetMemory(
  memoryId: string
): Promise<{ status: string }> {
  return api("/memory/forget", {
    method: "POST",
    body: JSON.stringify({ memory_id: memoryId }),
  });
}

export async function consolidateMemories(
  userId: string = "default"
): Promise<Record<string, unknown>> {
  return api(`/memory/consolidate?user_id=${encodeURIComponent(userId)}`, {
    method: "POST",
  });
}

export async function checkMemoryHealth(): Promise<{
  status: string;
  qdrant: string;
}> {
  return api("/memory/health");
}

// ── Models ─────────────────────────────────────────────────────────

export async function listModels(): Promise<{ models: ModelInfo[] }> {
  return api("/models");
}

export async function getActiveModel(): Promise<{
  active_model: string;
  model_info: ModelInfo | null;
}> {
  return api("/models/active");
}

export async function switchModel(
  model: string
): Promise<{ status: string; active_model: string }> {
  return api("/models/switch", {
    method: "POST",
    body: JSON.stringify({ model }),
  });
}

// ── Agents ─────────────────────────────────────────────────────────

export async function runAgent(
  message: string,
  model: string = "local"
): Promise<AgentResult> {
  return api("/agents/run", {
    method: "POST",
    body: JSON.stringify({ message, model }),
  });
}

export async function* streamTrace(
  runId: string
): AsyncGenerator<TraceEvent, void, undefined> {
  const res = await fetch(`${API_BASE}/agents/trace/${runId}`, {
    headers: buildHeaders(false),
  });
  if (!res.ok) throw new Error(`Trace error: ${res.status}`);
  if (!res.body) throw new Error("No response body");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        const data = line.slice(6).trim();
        try {
          yield JSON.parse(data) as TraceEvent;
        } catch {
          // non-JSON line
        }
      }
    }
  }
}

// ── Podcast ────────────────────────────────────────────────────────

export async function generatePodcast(
  req: PodcastRequest
): Promise<{ job_id: string; status_url: string }> {
  return api("/api/podcast/generate", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export async function getPodcastStatus(
  jobId: string
): Promise<PodcastJob> {
  return api(`/api/podcast/status/${jobId}`);
}

export async function listPodcastJobs(): Promise<{ jobs: PodcastJob[]; count: number }> {
  return api("/api/podcast/jobs");
}

export function getPodcastDownloadUrl(jobId: string): string {
  return `${API_BASE}/api/podcast/download/${jobId}`;
}

export async function* streamPodcastProgress(
  jobId: string
): AsyncGenerator<PodcastJob, void, undefined> {
  const res = await fetch(`${API_BASE}/api/podcast/status/${jobId}/stream`, {
    headers: buildHeaders(false),
  });
  if (!res.ok) throw new Error(`Podcast stream error: ${res.status}`);
  if (!res.body) throw new Error("No response body");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        const data = line.slice(6).trim();
        try {
          yield JSON.parse(data) as PodcastJob;
        } catch {
          // non-JSON line
        }
      }
    }
  }
}

// ── Context Sensing ────────────────────────────────────────────────

export async function getActiveContext(): Promise<any> {
  return api("/context/active");
}

export async function clearActiveContext(): Promise<any> {
  return api("/context/clear", { method: "POST" });
}
