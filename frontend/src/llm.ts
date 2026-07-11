// Bring-your-own-key config, held only in the browser (localStorage). It is sent to
// the backend as per-request X-LLM-* headers and used only for that call — never
// persisted or logged server-side. With no key set, the app grades offline.
export interface LlmConfig {
  baseUrl: string;
  apiKey: string;
  model: string;
}

const KEYS = { baseUrl: "gm-llm-base", apiKey: "gm-llm-key", model: "gm-llm-model" } as const;

export const EMPTY_CONFIG: LlmConfig = { baseUrl: "", apiKey: "", model: "" };

// Provider presets. The backend adapter speaks OpenAI-compatible Chat Completions
// against ANY of these base URLs, so a single interface reaches essentially every
// model on the market: the OpenAI-compatible vendors below directly, plus every other
// model (Anthropic Claude, Google Gemini, Meta Llama, 300+ more) through the OpenRouter
// gateway. "Custom" accepts any other OpenAI-compatible endpoint, including local
// runtimes reached over a public HTTPS tunnel (Ollama / LM Studio / vLLM).
export interface Provider {
  id: string;
  label: string;
  baseUrl: string;
  modelHint: string;
}

export const PROVIDERS: Provider[] = [
  { id: "openrouter", label: "OpenRouter — any model", baseUrl: "https://openrouter.ai/api/v1", modelHint: "anthropic/claude-3.5-sonnet" },
  { id: "openai", label: "OpenAI", baseUrl: "https://api.openai.com/v1", modelHint: "gpt-4o-mini" },
  { id: "qwen", label: "Alibaba Qwen (DashScope)", baseUrl: "https://dashscope-intl.aliyuncs.com/compatible-mode/v1", modelHint: "qwen-plus" },
  { id: "groq", label: "Groq", baseUrl: "https://api.groq.com/openai/v1", modelHint: "llama-3.3-70b-versatile" },
  { id: "deepseek", label: "DeepSeek", baseUrl: "https://api.deepseek.com/v1", modelHint: "deepseek-chat" },
  { id: "mistral", label: "Mistral", baseUrl: "https://api.mistral.ai/v1", modelHint: "mistral-large-latest" },
  { id: "together", label: "Together AI", baseUrl: "https://api.together.xyz/v1", modelHint: "meta-llama/Llama-3.3-70B-Instruct-Turbo" },
  { id: "custom", label: "Custom…", baseUrl: "", modelHint: "model-id" },
];

export function providerIdFor(baseUrl: string): string {
  const hit = PROVIDERS.find((p) => p.baseUrl && p.baseUrl === baseUrl.trim());
  return hit ? hit.id : "custom";
}

export function loadLlmConfig(): LlmConfig {
  try {
    return {
      baseUrl: localStorage.getItem(KEYS.baseUrl) ?? "",
      apiKey: localStorage.getItem(KEYS.apiKey) ?? "",
      model: localStorage.getItem(KEYS.model) ?? "",
    };
  } catch {
    return { ...EMPTY_CONFIG };
  }
}

export function saveLlmConfig(cfg: LlmConfig): void {
  try {
    for (const k of Object.keys(KEYS) as (keyof LlmConfig)[]) {
      const v = cfg[k].trim();
      if (v) localStorage.setItem(KEYS[k], v);
      else localStorage.removeItem(KEYS[k]);
    }
  } catch {
    /* storage unavailable — config stays in-memory for this session only */
  }
}

// Only send headers that are actually set, so an empty field falls back to any
// operator env default rather than overriding it with a blank.
export function llmHeaders(): Record<string, string> {
  const c = loadLlmConfig();
  const h: Record<string, string> = {};
  if (c.baseUrl.trim()) h["X-LLM-Base-Url"] = c.baseUrl.trim();
  if (c.apiKey.trim()) h["X-LLM-Api-Key"] = c.apiKey.trim();
  if (c.model.trim()) h["X-LLM-Model"] = c.model.trim();
  return h;
}
