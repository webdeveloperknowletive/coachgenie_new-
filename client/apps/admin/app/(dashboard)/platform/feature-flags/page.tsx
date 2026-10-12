"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Flag,
  ShieldCheck,
  RefreshCw,
  Save,
  CheckCircle2,
  XCircle,
  Sparkles,
  Sliders,
  Radio,
  Zap,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { authHeaders } from "@/lib/auth-headers";
import { useLanguage } from "@/components/providers/LanguageProvider";

interface FeatureFlagsResponse {
  features: Record<string, boolean>;
}

const FEATURE_DEFINITIONS = [
  {
    key: "ai_copilot_enabled",
    label: "Global AI Copilot & Doubt Solving",
    desc: "Master switch governing LLM inference availability across student & faculty portals.",
    category: "AI & ML",
  },
  {
    key: "whatsapp_notifications",
    label: "WhatsApp & SMS Gateway Dispatch",
    desc: "Governs Meta Cloud API & Twilio outbound automated message delivery.",
    category: "Communications",
  },
  {
    key: "advanced_analytics",
    label: "Advanced Analytics & Forecasting",
    desc: "Enables multi-dimensional student performance cohorts and revenue predictive models.",
    category: "Analytics",
  },
  {
    key: "web_push_alerts",
    label: "Browser Web Push Notifications",
    desc: "Permits browser service worker push subscriptions for real-time alerts.",
    category: "Communications",
  },
  {
    key: "custom_roles_rbac",
    label: "Dynamic Custom Roles & RBAC Engine",
    desc: "Allows institutes to create bespoke organizational roles beyond default tutor/counselor.",
    category: "Security",
  },
  {
    key: "beta_features_access",
    label: "Beta & Experimental Modules Access",
    desc: "Gates experimental platform capabilities undergoing internal staging validation.",
    category: "Experimental",
  },
];

export default function PlatformFeatureFlagsPage() {
  const { t } = useLanguage();
  const [flags, setFlags] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const fetchFlags = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/proxy/platform/feature-flags", {
        headers: authHeaders(),
      });
      if (!res.ok) throw new Error("Failed to load feature flags");
      const data: FeatureFlagsResponse = await res.json();
      setFlags(data.features || {});
    } catch (err: any) {
      toast.error(err.message || "Failed to load platform feature flags");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchFlags();
  }, [fetchFlags]);

  const handleToggle = (key: string) => {
    setFlags((prev) => ({
      ...prev,
      [key]: !prev[key],
    }));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const res = await fetch("/api/proxy/platform/feature-flags", {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ features: flags }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.message || data.detail || "Failed to save feature flags");
      toast.success(data.message || "Platform feature flags saved successfully");
      fetchFlags();
    } catch (err: any) {
      toast.error(err.message || "Failed to update feature flags");
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
              <Flag className="h-5 w-5" />
            </span>
            <h1 className="text-2xl font-bold tracking-tight">Platform Global Feature Flags</h1>
            <span className="rounded-full bg-violet-500/10 px-2.5 py-0.5 text-xs font-semibold text-violet-600">
              Control Plane Master Toggles
            </span>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Global operational switches affecting all tenants. Disabling a flag here deactivates the capability across all subscriptions.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => fetchFlags()}
            disabled={loading}
            className="flex items-center gap-1.5 rounded-xl border bg-background px-3.5 py-2 text-xs font-semibold hover:bg-accent transition-colors shadow-xs"
          >
            <RefreshCw className={cn("h-3.5 w-3.5 text-muted-foreground", loading && "animate-spin")} />
            Refresh
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-1.5 rounded-xl bg-violet-600 px-4 py-2 text-xs font-semibold text-white hover:bg-violet-700 transition-colors shadow-xs"
          >
            <Save className="h-3.5 w-3.5" />
            {saving ? "Saving..." : "Save Feature Flags"}
          </button>
        </div>
      </div>

      {/* Feature Flags Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {FEATURE_DEFINITIONS.map((feat) => {
          const active = Boolean(flags[feat.key]);

          return (
            <div
              key={feat.key}
              onClick={() => handleToggle(feat.key)}
              className={cn(
                "p-5 rounded-2xl border transition-all cursor-pointer shadow-xs flex flex-col justify-between space-y-3",
                active
                  ? "bg-card border-violet-500/40 hover:border-violet-500"
                  : "bg-muted/30 border-border opacity-70 hover:opacity-100"
              )}
            >
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                    {feat.category}
                  </span>
                  <div
                    className={cn(
                      "h-5 w-9 rounded-full transition-colors relative flex items-center p-0.5",
                      active ? "bg-violet-600" : "bg-muted border"
                    )}
                  >
                    <div
                      className={cn(
                        "h-4 w-4 rounded-full bg-white transition-transform shadow-xs",
                        active ? "translate-x-4" : "translate-x-0"
                      )}
                    />
                  </div>
                </div>

                <h3 className="font-bold text-sm text-foreground">{feat.label}</h3>
                <p className="text-xs text-muted-foreground">{feat.desc}</p>
              </div>

              <div className="pt-2 border-t flex items-center justify-between text-xs">
                <span className="text-muted-foreground font-mono text-[11px]">{feat.key}</span>
                {active ? (
                  <span className="inline-flex items-center gap-1 text-emerald-600 font-semibold text-[11px]">
                    <CheckCircle2 className="h-3.5 w-3.5" /> Globally Active
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-muted-foreground font-semibold text-[11px]">
                    <XCircle className="h-3.5 w-3.5" /> Globally Disabled
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
