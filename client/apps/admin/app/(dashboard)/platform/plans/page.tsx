"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Layers,
  Sparkles,
  Zap,
  Building2,
  Crown,
  CheckCircle2,
  XCircle,
  RefreshCw,
  ArrowRight,
  ShieldCheck,
  Search,
  Database,
  Users,
  BookOpen,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { authHeaders } from "@/lib/auth-headers";
import { useLanguage } from "@/components/providers/LanguageProvider";

const CANONICAL_PLANS = [
  {
    id: "starter",
    name: "Starter",
    icon: Zap,
    color: "text-blue-600",
    bg: "bg-blue-500/10",
    border: "border-blue-200 dark:border-blue-900",
    description: "For individual tutors and emerging coaching centers",
    quotas: {
      max_students: 100,
      max_staff: 5,
      max_batches: 5,
      storage_mb: 1024,
    },
    features: [
      { name: "Custom Fields", enabled: true },
      { name: "AI Copilot", enabled: false },
      { name: "Custom Roles & RBAC", enabled: false },
      { name: "Advanced Analytics", enabled: false },
      { name: "WhatsApp Notifications", enabled: false },
    ],
  },
  {
    id: "growth",
    name: "Growth",
    icon: Building2,
    color: "text-violet-600",
    bg: "bg-violet-500/10",
    border: "border-violet-300 dark:border-violet-800",
    description: "For expanding institutes requiring multi-batch management and automation",
    quotas: {
      max_students: 500,
      max_staff: 20,
      max_batches: 25,
      storage_mb: 5120,
    },
    features: [
      { name: "Custom Fields", enabled: true },
      { name: "AI Copilot", enabled: true },
      { name: "Custom Roles & RBAC", enabled: true },
      { name: "Advanced Analytics", enabled: true },
      { name: "WhatsApp Notifications", enabled: true },
    ],
  },
  {
    id: "enterprise",
    name: "Enterprise",
    icon: Crown,
    color: "text-amber-600",
    bg: "bg-amber-500/10",
    border: "border-amber-300 dark:border-amber-800",
    description: "For large multi-branch coaching institutes with enterprise scale",
    quotas: {
      max_students: 5000,
      max_staff: 100,
      max_batches: 200,
      storage_mb: 51200,
    },
    features: [
      { name: "Custom Fields", enabled: true },
      { name: "AI Copilot", enabled: true },
      { name: "Custom Roles & RBAC", enabled: true },
      { name: "Advanced Analytics", enabled: true },
      { name: "WhatsApp Notifications", enabled: true },
    ],
  },
];

interface PlatformTenant {
  id: string;
  name: string;
  subdomain: string;
  plan: string;
  is_active: boolean;
}

export default function PlatformPlansPage() {
  const { t } = useLanguage();
  const [tenants, setTenants] = useState<PlatformTenant[]>([]);
  const [loading, setLoading] = useState(true);
  const [updatingId, setUpdatingId] = useState<string | null>(null);
  const [selectedTenantId, setSelectedTenantId] = useState<string>("");
  const [newPlan, setNewPlan] = useState<string>("growth");

  const fetchTenants = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/proxy/platform/tenants?limit=100", {
        headers: authHeaders(),
      });
      if (!res.ok) throw new Error("Failed to load tenants");
      const data = await res.json();
      setTenants(data.items ?? []);
      if (data.items && data.items.length > 0 && !selectedTenantId) {
        setSelectedTenantId(data.items[0].id);
      }
    } catch (err: any) {
      toast.error(err.message || "Failed to load tenants");
    } finally {
      setLoading(false);
    }
  }, [selectedTenantId]);

  useEffect(() => {
    fetchTenants();
  }, [fetchTenants]);

  const handleUpdatePlan = async () => {
    if (!selectedTenantId) return;
    setUpdatingId(selectedTenantId);
    try {
      const res = await fetch(`/api/proxy/platform/tenants/${selectedTenantId}/plan`, {
        method: "PATCH",
        headers: authHeaders(),
        body: JSON.stringify({ plan: newPlan }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.message || data.detail || "Failed to update plan");
      toast.success(data.message || `Plan updated to ${newPlan}`);
      fetchTenants();
    } catch (err: any) {
      toast.error(err.message || "Failed to update tenant plan");
    } finally {
      setUpdatingId(null);
    }
  };

  const selectedTenant = tenants.find((t) => t.id === selectedTenantId);

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="rounded-md bg-violet-600/10 p-1.5 text-violet-600 dark:text-violet-400">
              <Layers className="h-5 w-5" />
            </span>
            <h1 className="text-2xl font-bold tracking-tight">Plans & Entitlements</h1>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Canonical platform tier definitions, quota limits, feature flags, and tenant tier assignments.
          </p>
        </div>

        <button
          onClick={() => fetchTenants()}
          disabled={loading}
          className="flex items-center gap-1.5 rounded-xl border bg-background px-3.5 py-2 text-xs font-semibold hover:bg-accent transition-colors shadow-xs"
        >
          <RefreshCw className={cn("h-3.5 w-3.5 text-muted-foreground", loading && "animate-spin")} />
          Refresh
        </button>
      </div>

      {/* 3 Tier Grid */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {CANONICAL_PLANS.map((plan) => {
          const Icon = plan.icon;
          const assignedCount = tenants.filter((t) => t.plan.toLowerCase() === plan.id).length;

          return (
            <div
              key={plan.id}
              className={cn("rounded-2xl border bg-card p-6 shadow-xs flex flex-col justify-between", plan.border)}
            >
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={cn("rounded-xl p-2.5", plan.bg, plan.color)}>
                      <Icon className="h-5 w-5" />
                    </div>
                    <div>
                      <h2 className="font-bold text-lg">{plan.name} Tier</h2>
                      <span className="text-xs text-muted-foreground">{assignedCount} institutes active</span>
                    </div>
                  </div>
                </div>

                <p className="text-xs text-muted-foreground">{plan.description}</p>

                {/* Quotas */}
                <div className="rounded-xl bg-muted/40 p-3.5 space-y-2 border text-xs">
                  <div className="font-semibold text-foreground text-[11px] uppercase tracking-wider">
                    Base Quotas
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <span className="text-muted-foreground block text-[11px]">Max Students</span>
                      <span className="font-bold text-foreground">{plan.quotas.max_students.toLocaleString()}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground block text-[11px]">Max Staff</span>
                      <span className="font-bold text-foreground">{plan.quotas.max_staff}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground block text-[11px]">Max Batches</span>
                      <span className="font-bold text-foreground">{plan.quotas.max_batches}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground block text-[11px]">Storage</span>
                      <span className="font-bold text-foreground">{plan.quotas.storage_mb / 1024} GB</span>
                    </div>
                  </div>
                </div>

                {/* Features */}
                <div className="space-y-2 text-xs">
                  <div className="font-semibold text-foreground text-[11px] uppercase tracking-wider">
                    Entitled Features
                  </div>
                  <div className="space-y-1.5">
                    {plan.features.map((feat) => (
                      <div key={feat.name} className="flex items-center justify-between text-xs">
                        <span className="text-muted-foreground">{feat.name}</span>
                        {feat.enabled ? (
                          <span className="inline-flex items-center gap-1 text-emerald-600 font-medium text-[11px]">
                            <CheckCircle2 className="h-3.5 w-3.5" /> Enabled
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-muted-foreground/60 text-[11px]">
                            <XCircle className="h-3.5 w-3.5" /> Locked
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Plan Assignment Tool */}
      <div className="rounded-2xl border bg-card p-6 shadow-xs space-y-4">
        <h2 className="text-base font-bold tracking-tight flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-violet-600" /> Change Institute Subscription Plan
        </h2>
        <p className="text-xs text-muted-foreground">
          Instantly upgrade or downgrade an institute's canonical subscription plan. Changes take effect immediately.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
          <div>
            <label className="text-xs font-semibold text-foreground block mb-1.5">Select Institute</label>
            <select
              value={selectedTenantId}
              onChange={(e) => setSelectedTenantId(e.target.value)}
              className="h-10 w-full rounded-xl border bg-background px-3 text-xs focus:outline-none focus:ring-1 focus:ring-violet-500"
            >
              {tenants.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name} ({t.subdomain}) — Current: {t.plan.toUpperCase()}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs font-semibold text-foreground block mb-1.5">New Subscription Plan</label>
            <select
              value={newPlan}
              onChange={(e) => setNewPlan(e.target.value)}
              className="h-10 w-full rounded-xl border bg-background px-3 text-xs focus:outline-none focus:ring-1 focus:ring-violet-500"
            >
              <option value="starter">Starter Plan (Up to 100 students)</option>
              <option value="growth">Growth Plan (Up to 500 students, AI Copilot)</option>
              <option value="enterprise">Enterprise Plan (Up to 5000 students, Multi-branch)</option>
            </select>
          </div>

          <div className="flex items-end">
            <button
              onClick={handleUpdatePlan}
              disabled={updatingId === selectedTenantId || !selectedTenantId}
              className="h-10 w-full rounded-xl bg-violet-600 text-xs font-semibold text-white hover:bg-violet-700 transition-colors shadow-xs flex items-center justify-center gap-2"
            >
              {updatingId === selectedTenantId ? "Applying..." : "Apply Plan Update"}
              <ArrowRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
