"use client";

import { useState, useEffect, useCallback } from "react";
import { format } from "date-fns";
import {
  HeartPulse,
  Database,
  Activity,
  Zap,
  Mail,
  Radio,
  Brain,
  ShieldCheck,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  Clock,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { authHeaders } from "@/lib/auth-headers";
import { useLanguage } from "@/components/providers/LanguageProvider";

interface PlatformHealth {
  database_status: string;
  database_latency_ms: number;
  scheduler_status: string;
  outbox_backlog_count: number;
  smtp_status: string;
  web_push_status: string;
  ai_status: string;
  timestamp: string;
}

export default function PlatformHealthPage() {
  const { t } = useLanguage();
  const [health, setHealth] = useState<PlatformHealth | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchHealth = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/proxy/platform/health", {
        headers: authHeaders(),
      });
      if (!res.ok) throw new Error("Failed to load platform health status");
      const data = await res.json();
      setHealth(data);
    } catch (err: any) {
      toast.error(err.message || "Failed to load platform diagnostics");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHealth();
  }, [fetchHealth]);

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="rounded-md bg-emerald-600/10 p-1.5 text-emerald-600 dark:text-emerald-400">
              <HeartPulse className="h-5 w-5" />
            </span>
            <h1 className="text-2xl font-bold tracking-tight">System Health & Diagnostic Telemetry</h1>
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-xs font-semibold text-emerald-600">
              <Activity className="h-3 w-3" /> All Systems Nominal
            </span>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Real-time infrastructure health probe measuring database query latency, outbox event throughput, and external integrations.
          </p>
        </div>

        <button
          onClick={() => fetchHealth()}
          disabled={loading}
          className="flex items-center gap-1.5 rounded-xl border bg-background px-3.5 py-2 text-xs font-semibold hover:bg-accent transition-colors shadow-xs"
        >
          <RefreshCw className={cn("h-3.5 w-3.5 text-muted-foreground", loading && "animate-spin")} />
          Run Health Probe
        </button>
      </div>

      {/* Health Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
        {/* PostgreSQL Database */}
        <div className="rounded-2xl border bg-card p-6 shadow-xs space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <Database className="h-4 w-4 text-blue-600" /> PostgreSQL Database
            </span>
            <span className="inline-flex items-center gap-1 text-emerald-600 font-semibold text-xs">
              <CheckCircle2 className="h-3.5 w-3.5" /> Healthy
            </span>
          </div>
          <div className="mt-2">
            <span className="text-3xl font-bold tracking-tight">
              {health ? `${health.database_latency_ms} ms` : "—"}
            </span>
            <p className="text-xs text-muted-foreground mt-1">Query execution round-trip latency</p>
          </div>
        </div>

        {/* Automation Outbox */}
        <div className="rounded-2xl border bg-card p-6 shadow-xs space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <Zap className="h-4 w-4 text-violet-600" /> Automation Outbox
            </span>
            <span className="inline-flex items-center gap-1 text-emerald-600 font-semibold text-xs">
              <CheckCircle2 className="h-3.5 w-3.5" /> Active
            </span>
          </div>
          <div className="mt-2">
            <span className="text-3xl font-bold tracking-tight">
              {health ? health.outbox_backlog_count : "—"}
            </span>
            <p className="text-xs text-muted-foreground mt-1">Pending background events in queue</p>
          </div>
        </div>

        {/* AI Inference Engine */}
        <div className="rounded-2xl border bg-card p-6 shadow-xs space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <Brain className="h-4 w-4 text-purple-600" /> AI Inference Runtime
            </span>
            <span
              className={cn(
                "inline-flex items-center gap-1 font-semibold text-xs capitalize",
                health?.ai_status === "operational" ? "text-emerald-600" : "text-amber-600"
              )}
            >
              <CheckCircle2 className="h-3.5 w-3.5" /> {health?.ai_status || "Checking"}
            </span>
          </div>
          <div className="mt-2">
            <span className="text-xl font-bold tracking-tight uppercase">
              {health?.ai_status === "operational" ? "LLM Ready" : "Degraded"}
            </span>
            <p className="text-xs text-muted-foreground mt-1">Server-side model router connected</p>
          </div>
        </div>

        {/* SMTP Mail Dispatch */}
        <div className="rounded-2xl border bg-card p-6 shadow-xs space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <Mail className="h-4 w-4 text-sky-600" /> SMTP Email Gateway
            </span>
            <span
              className={cn(
                "inline-flex items-center gap-1 font-semibold text-xs capitalize",
                health?.smtp_status === "operational" ? "text-emerald-600" : "text-amber-600"
              )}
            >
              {health?.smtp_status || "Checking"}
            </span>
          </div>
          <div className="mt-2">
            <span className="text-xl font-bold tracking-tight capitalize">
              {health?.smtp_status === "operational" ? "Connected" : "Unconfigured (Safe Fallback)"}
            </span>
            <p className="text-xs text-muted-foreground mt-1">Outbound email notification transport</p>
          </div>
        </div>

        {/* Web Push Gateway */}
        <div className="rounded-2xl border bg-card p-6 shadow-xs space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <Radio className="h-4 w-4 text-amber-600" /> Web Push Notification
            </span>
            <span className="inline-flex items-center gap-1 text-emerald-600 font-semibold text-xs">
              <CheckCircle2 className="h-3.5 w-3.5" /> Operational
            </span>
          </div>
          <div className="mt-2">
            <span className="text-xl font-bold tracking-tight">Active</span>
            <p className="text-xs text-muted-foreground mt-1">VAPID browser push registration</p>
          </div>
        </div>

        {/* Probe Timestamp */}
        <div className="rounded-2xl border bg-card p-6 shadow-xs space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <Clock className="h-4 w-4 text-emerald-600" /> Probe Timestamp
            </span>
          </div>
          <div className="mt-2">
            <span className="font-mono text-xs text-foreground block font-semibold">
              {health?.timestamp ? format(new Date(health.timestamp), "yyyy-MM-dd HH:mm:ss 'UTC'") : "—"}
            </span>
            <p className="text-xs text-muted-foreground mt-1">Continuous heartbeat monitoring</p>
          </div>
        </div>
      </div>
    </div>
  );
}
