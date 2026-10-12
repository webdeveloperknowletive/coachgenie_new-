"use client";

import { useState, useEffect, useCallback } from "react";
import {
  CheckSquare,
  Building2,
  RefreshCw,
  CheckCircle2,
  XCircle,
  Sparkles,
  Layers,
  Sliders,
  ShieldCheck,
  AlertCircle,
  ArrowRight,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { authHeaders } from "@/lib/auth-headers";
import { useLanguage } from "@/components/providers/LanguageProvider";

interface PlatformTenant {
  id: string;
  name: string;
  subdomain: string;
  plan: string;
  is_active: boolean;
  settings?: Record<string, any>;
}

interface TenantDetails {
  tenant: PlatformTenant;
  entitlements: {
    plan: string;
    quotas: Record<string, number>;
    features: Record<string, boolean>;
    usage: Record<string, number>;
  };
}

const FEATURE_CATALOG = [
  { key: "ai_copilot_enabled", label: "AI Copilot Engine", desc: "Automated doubt resolution and analytical copilot" },
  { key: "custom_roles_enabled", label: "Custom RBAC & Roles", desc: "Dynamic role creation and granular capability grants" },
  { key: "custom_fields_enabled", label: "Custom Fields System", desc: "Schema extensions on students, leads, and batches" },
  { key: "advanced_analytics_enabled", label: "Advanced Analytics", desc: "Cohort retention analysis and revenue forecasts" },
  { key: "whatsapp_notifications_enabled", label: "WhatsApp & SMS Automation", desc: "Automated alerts for parents and students" },
];

export default function PlatformEntitlementsPage() {
  const { t } = useLanguage();
  const [tenants, setTenants] = useState<PlatformTenant[]>([]);
  const [selectedTenantId, setSelectedTenantId] = useState<string>("");
  const [tenantDetails, setTenantDetails] = useState<TenantDetails | null>(null);
  const [globalFlags, setGlobalFlags] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(true);

  const fetchTenantsAndFlags = useCallback(async () => {
    setLoading(true);
    try {
      const [tRes, fRes] = await Promise.all([
        fetch("/api/proxy/platform/tenants?limit=100", { headers: authHeaders() })
          .then((r) => (r.ok ? r.json() : { items: [] })),
        fetch("/api/proxy/platform/feature-flags", { headers: authHeaders() })
          .then((r) => (r.ok ? r.json() : { features: {} })),
      ]);

      const items: PlatformTenant[] = tRes.items ?? [];
      setTenants(items);
      setGlobalFlags(fRes.features ?? {});

      if (items.length > 0 && !selectedTenantId) {
        setSelectedTenantId(items[0].id);
      }
    } catch (err: any) {
      toast.error(err.message || "Failed to load entitlements baseline");
    } finally {
      setLoading(false);
    }
  }, [selectedTenantId]);

  const fetchTenantDetails = useCallback(async (id: string) => {
    if (!id) return;
    try {
      const res = await fetch(`/api/proxy/platform/tenants/${id}`, {
        headers: authHeaders(),
      });
      if (!res.ok) throw new Error("Failed to load tenant entitlements");
      const data = await res.json();
      setTenantDetails(data);
    } catch (err: any) {
      toast.error("Failed to load tenant details");
    }
  }, []);

  useEffect(() => {
    fetchTenantsAndFlags();
  }, [fetchTenantsAndFlags]);

  useEffect(() => {
    if (selectedTenantId) {
      fetchTenantDetails(selectedTenantId);
    }
  }, [selectedTenantId, fetchTenantDetails]);

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="rounded-md bg-violet-600/10 p-1.5 text-violet-600 dark:text-violet-400">
              <CheckSquare className="h-5 w-5" />
            </span>
            <h1 className="text-2xl font-bold tracking-tight">Entitlement & Resolution Center</h1>
            <span className="rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-xs font-semibold text-emerald-600">
              Phase 2 Entitlement Engine
            </span>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Real-time multi-tenant capability evaluation resolving Platform Flags + Base Plan Defaults + Custom Overrides.
          </p>
        </div>

        <button
          onClick={() => {
            fetchTenantsAndFlags();
            if (selectedTenantId) fetchTenantDetails(selectedTenantId);
          }}
          disabled={loading}
          className="flex items-center gap-1.5 rounded-xl border bg-background px-3.5 py-2 text-xs font-semibold hover:bg-accent transition-colors shadow-xs"
        >
          <RefreshCw className={cn("h-3.5 w-3.5 text-muted-foreground", loading && "animate-spin")} />
          Refresh
        </button>
      </div>

      {/* Selector */}
      <div className="rounded-2xl border bg-card p-4 shadow-xs">
        <label className="text-xs font-semibold text-foreground block mb-1.5">Select Institute to Evaluate</label>
        <select
          value={selectedTenantId}
          onChange={(e) => setSelectedTenantId(e.target.value)}
          className="h-10 w-full max-w-xl rounded-xl border bg-background px-3 text-xs focus:outline-none focus:ring-1 focus:ring-violet-500 font-medium"
        >
          {tenants.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name} ({t.subdomain}) — Plan: {t.plan.toUpperCase()}
            </option>
          ))}
        </select>
      </div>

      {/* Resolution Logic Formula Card */}
      <div className="rounded-2xl border bg-muted/20 p-5 shadow-xs">
        <h2 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-2">
          Canonical Entitlement Resolution Engine
        </h2>
        <div className="flex flex-wrap items-center gap-3 text-xs font-mono">
          <span className="rounded-lg bg-card px-3 py-1.5 border font-semibold">1. Platform Flag (Global)</span>
          <span className="text-muted-foreground font-bold">✕</span>
          <span className="rounded-lg bg-card px-3 py-1.5 border font-semibold">2. Base Plan Default</span>
          <span className="text-muted-foreground font-bold">+</span>
          <span className="rounded-lg bg-card px-3 py-1.5 border font-semibold">3. Tenant Custom Override</span>
          <span className="text-muted-foreground font-bold">⟹</span>
          <span className="rounded-lg bg-violet-600 text-white px-3.5 py-1.5 font-bold shadow-xs">
            Effective Capability
          </span>
        </div>
      </div>

      {/* Feature Resolution Table */}
      {tenantDetails && (
        <div className="rounded-2xl border bg-card shadow-xs overflow-hidden">
          <div className="p-5 border-b flex items-center justify-between">
            <div>
              <h2 className="font-bold text-base">
                Effective Capabilities for {tenantDetails.tenant.name}
              </h2>
              <span className="text-xs text-muted-foreground">
                Subscription Tier: <strong className="uppercase text-violet-600">{tenantDetails.entitlements.plan}</strong>
              </span>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b bg-muted/40 text-muted-foreground font-medium">
                <tr>
                  <th className="py-3 px-4">Feature Name</th>
                  <th className="py-3 px-4 text-center">Platform Global Flag</th>
                  <th className="py-3 px-4 text-center">Plan Default</th>
                  <th className="py-3 px-4 text-center">Tenant Override</th>
                  <th className="py-3 px-4 text-right">Effective State</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {FEATURE_CATALOG.map((feat) => {
                  const isEffective = Boolean(tenantDetails.entitlements.features[feat.key]);
                  const isGlobal = globalFlags[feat.key] ?? true;

                  return (
                    <tr key={feat.key} className="hover:bg-muted/20 transition-colors">
                      <td className="py-3.5 px-4">
                        <div>
                          <span className="font-bold text-foreground block">{feat.label}</span>
                          <span className="text-[11px] text-muted-foreground">{feat.desc}</span>
                        </div>
                      </td>
                      <td className="py-3.5 px-4 text-center">
                        {isGlobal ? (
                          <span className="inline-flex items-center gap-1 text-emerald-600 font-semibold">
                            <CheckCircle2 className="h-3.5 w-3.5" /> ON
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-rose-600 font-semibold">
                            <XCircle className="h-3.5 w-3.5" /> OFF
                          </span>
                        )}
                      </td>
                      <td className="py-3.5 px-4 text-center font-medium capitalize">
                        {tenantDetails.entitlements.plan === "enterprise" ||
                        (tenantDetails.entitlements.plan === "growth" && feat.key !== "custom_roles_rbac")
                          ? "Enabled in Plan"
                          : feat.key === "custom_fields_enabled"
                          ? "Enabled in Starter"
                          : "Locked in Starter"}
                      </td>
                      <td className="py-3.5 px-4 text-center font-mono text-[11px]">
                        {tenantDetails.tenant.settings?.plan_overrides?.features?.[feat.key] !== undefined
                          ? tenantDetails.tenant.settings?.plan_overrides?.features?.[feat.key]
                            ? "Override: ON"
                            : "Override: OFF"
                          : "No Override (Inherited)"}
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        {isEffective ? (
                          <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-3 py-1 text-xs font-bold text-emerald-600">
                            <CheckCircle2 className="h-4 w-4" /> ENABLED
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1.5 rounded-full bg-muted px-3 py-1 text-xs font-bold text-muted-foreground">
                            <XCircle className="h-4 w-4" /> DISABLED
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
