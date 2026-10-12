"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Brain,
  Cpu,
  Zap,
  ShieldCheck,
  RefreshCw,
  Save,
  CheckCircle2,
  AlertCircle,
  Activity,
  Sliders,
  Sparkles,
  Bot,
  Lock,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { authHeaders } from "@/lib/auth-headers";
import { useLanguage } from "@/components/providers/LanguageProvider";

interface AIConfig {
  enabled: boolean;
  active_provider: string;
  available_providers: string[];
  model_routing: {
    copilot_model: string;
    doubt_solver_model: string;
    career_guidance_model: string;
    analytics_assistant_model: string;
  };
  last_health_check?: string;
  average_latency_ms: number;
}

export default function PlatformAIPage() {
  const { t } = useLanguage();
  const [config, setConfig] = useState<AIConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Form states
  const [enabled, setEnabled] = useState(true);
  const [activeProvider, setActiveProvider] = useState("groq");
  const [copilotModel, setCopilotModel] = useState("llama3-70b-8192");
  const [doubtSolverModel, setDoubtSolverModel] = useState("llama3-70b-8192");
  const [careerModel, setCareerModel] = useState("llama3-8b-8192");
  const [analyticsModel, setAnalyticsModel] = useState("llama3-70b-8192");

  const fetchAIConfig = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/proxy/platform/ai/config", {
        headers: authHeaders(),
      });
      if (!res.ok) throw new Error("Failed to load AI platform configuration");
      const data: AIConfig = await res.json();
      setConfig(data);
      setEnabled(data.enabled);
      setActiveProvider(data.active_provider);
      setCopilotModel(data.model_routing.copilot_model);
      setDoubtSolverModel(data.model_routing.doubt_solver_model);
      setCareerModel(data.model_routing.career_guidance_model);
      setAnalyticsModel(data.model_routing.analytics_assistant_model);
    } catch (err: any) {
      toast.error(err.message || "Failed to load AI control settings");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAIConfig();
  }, [fetchAIConfig]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = {
        enabled,
        active_provider: activeProvider,
        available_providers: config?.available_providers ?? ["groq", "openai-compatible", "render-copilot"],
        model_routing: {
          copilot_model: copilotModel,
          doubt_solver_model: doubtSolverModel,
          career_guidance_model: careerModel,
          analytics_assistant_model: analyticsModel,
        },
        average_latency_ms: config?.average_latency_ms ?? 240.0,
      };

      const res = await fetch("/api/proxy/platform/ai/config", {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.message || data.detail || "Failed to update AI configuration");
      toast.success(data.message || "AI Model routing updated successfully");
      fetchAIConfig();
    } catch (err: any) {
      toast.error(err.message || "Failed to save AI configuration");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="rounded-md bg-violet-600/10 p-1.5 text-violet-600 dark:text-violet-400">
              <Brain className="h-5 w-5" />
            </span>
            <h1 className="text-2xl font-bold tracking-tight">AI & LLM Platform Control Center</h1>
            <span className="rounded-full bg-violet-500/10 px-2.5 py-0.5 text-xs font-semibold text-violet-600">
              Server-Side Secure Routing
            </span>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Global inference provider management, per-feature model routing, latency monitoring, and zero-leak security controls.
          </p>
        </div>

        <button
          onClick={() => fetchAIConfig()}
          disabled={loading}
          className="flex items-center gap-1.5 rounded-xl border bg-background px-3.5 py-2 text-xs font-semibold hover:bg-accent transition-colors shadow-xs"
        >
          <RefreshCw className={cn("h-3.5 w-3.5 text-muted-foreground", loading && "animate-spin")} />
          Refresh
        </button>
      </div>

      {/* Security & Health Row */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-2xl border bg-card p-5 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Provider Engine
            </span>
            <div className="rounded-xl bg-violet-500/10 p-2 text-violet-600">
              <Cpu className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold tracking-tight uppercase">{activeProvider}</span>
            <span className="text-xs font-medium text-emerald-600">Active</span>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">Inference runtime backend</p>
        </div>

        <div className="rounded-2xl border bg-card p-5 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Average Latency
            </span>
            <div className="rounded-xl bg-emerald-500/10 p-2 text-emerald-600">
              <Activity className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold tracking-tight">
              {config ? `${config.average_latency_ms} ms` : "—"}
            </span>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">Token generation response</p>
        </div>

        <div className="rounded-2xl border bg-card p-5 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Security Boundary
            </span>
            <div className="rounded-xl bg-blue-500/10 p-2 text-blue-600">
              <Lock className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-lg font-bold tracking-tight text-emerald-600 flex items-center gap-1">
              <ShieldCheck className="h-5 w-5" /> 100% Server-Side
            </span>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">API Keys never touch client</p>
        </div>
      </div>

      {/* Model Routing Form */}
      <form onSubmit={handleSave} className="rounded-2xl border bg-card p-6 shadow-xs space-y-6">
        <div className="flex items-center justify-between border-b pb-4">
          <div>
            <h2 className="text-base font-bold tracking-tight">Model Routing by Feature</h2>
            <p className="text-xs text-muted-foreground">
              Assign high-throughput vs reasoning models across student doubt solvers, copilot chat, and analytics.
            </p>
          </div>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={enabled}
              onChange={(e) => setEnabled(e.target.checked)}
              className="h-4 w-4 rounded border-border text-violet-600 focus:ring-violet-500"
            />
            <span className="text-xs font-semibold">{enabled ? "AI Engine Online" : "AI Engine Suspended"}</span>
          </label>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 text-xs">
          <div>
            <label className="font-semibold block mb-1.5">Active LLM Provider Runtime</label>
            <select
              value={activeProvider}
              onChange={(e) => setActiveProvider(e.target.value)}
              className="h-10 w-full rounded-xl border bg-background px-3 text-xs focus:outline-none focus:ring-1 focus:ring-violet-500 font-medium"
            >
              <option value="groq">Groq LPU Acceleration (Ultra Low Latency)</option>
              <option value="openai-compatible">OpenAI-Compatible Generic Proxy</option>
              <option value="render-copilot">Render Hosted Copilot Engine</option>
            </select>
          </div>

          <div>
            <label className="font-semibold block mb-1.5">AI Copilot & Faculty Assistant Model</label>
            <select
              value={copilotModel}
              onChange={(e) => setCopilotModel(e.target.value)}
              className="h-10 w-full rounded-xl border bg-background px-3 text-xs focus:outline-none focus:ring-1 focus:ring-violet-500 font-medium"
            >
              <option value="llama3-70b-8192">LLaMA 3 70B (High Reasoning)</option>
              <option value="llama3-8b-8192">LLaMA 3 8B (Fast Response)</option>
              <option value="mixtral-8x7b-32768">Mixtral 8x7B 32k (Long Context)</option>
            </select>
          </div>

          <div>
            <label className="font-semibold block mb-1.5">Student Academic Doubt Solver Model</label>
            <select
              value={doubtSolverModel}
              onChange={(e) => setDoubtSolverModel(e.target.value)}
              className="h-10 w-full rounded-xl border bg-background px-3 text-xs focus:outline-none focus:ring-1 focus:ring-violet-500 font-medium"
            >
              <option value="llama3-70b-8192">LLaMA 3 70B (Step-by-step Math & Science)</option>
              <option value="llama3-8b-8192">LLaMA 3 8B (Instant Answers)</option>
            </select>
          </div>

          <div>
            <label className="font-semibold block mb-1.5">Career Guidance & Counseling Roleplay Model</label>
            <select
              value={careerModel}
              onChange={(e) => setCareerModel(e.target.value)}
              className="h-10 w-full rounded-xl border bg-background px-3 text-xs focus:outline-none focus:ring-1 focus:ring-violet-500 font-medium"
            >
              <option value="llama3-8b-8192">LLaMA 3 8B (Conversational Persona)</option>
              <option value="llama3-70b-8192">LLaMA 3 70B (Deep Psychometric Analysis)</option>
            </select>
          </div>

          <div>
            <label className="font-semibold block mb-1.5">Institute Executive Analytics AI Assistant</label>
            <select
              value={analyticsModel}
              onChange={(e) => setAnalyticsModel(e.target.value)}
              className="h-10 w-full rounded-xl border bg-background px-3 text-xs focus:outline-none focus:ring-1 focus:ring-violet-500 font-medium"
            >
              <option value="llama3-70b-8192">LLaMA 3 70B (Statistical Inferences & KPIs)</option>
              <option value="mixtral-8x7b-32768">Mixtral 8x7B (Large Spreadsheet Ingestion)</option>
            </select>
          </div>
        </div>

        <div className="flex justify-end pt-3 border-t">
          <button
            type="submit"
            disabled={saving}
            className="flex items-center gap-2 rounded-xl bg-violet-600 px-5 py-2.5 text-xs font-semibold text-white hover:bg-violet-700 transition-colors shadow-xs"
          >
            <Save className="h-4 w-4" />
            {saving ? "Saving Configuration..." : "Save AI Routing & Policies"}
          </button>
        </div>
      </form>
    </div>
  );
}
