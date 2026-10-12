"use client";

import { useState, useEffect, useCallback, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import {
  Sliders,
  Building2,
  RefreshCw,
  Save,
  CheckCircle2,
  AlertCircle,
  Database,
  Users,
  BookOpen,
  HardDrive,
  Sparkles,
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
}

interface TenantDetails {
  tenant: PlatformTenant;
  entitlements: {
    plan: string;
    quotas: {
      max_students: number;
      max_staff: number;
      max_batches: number;
      storage_mb: number;
    };
    features: Record<string, boolean>;
    usage: {
      students: number;
      staff: number;
      batches: number;
    };
  };
}

function PlatformQuotasContent() {
  const { t } = useLanguage();
  const searchParams = useSearchParams();
  const initialTenantId = searchParams.get("tenantId") || "";

  const [tenants, setTenants] = useState<PlatformTenant[]>([]);
  const [selectedTenantId, setSelectedTenantId] = useState<string>(initialTenantId);
  const [details, setDetails] = useState<TenantDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Form states
  const [maxStudents, setMaxStudents] = useState<number>(100);
  const [maxStaff, setMaxStaff] = useState<number>(5);
  const [maxBatches, setMaxBatches] = useState<number>(5);
  const [storageMb, setStorageMb] = useState<number>(1024);
  const [features, setFeatures] = useState<Record<string, boolean>>({});

  const fetchTenants = useCallback(async () => {
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
    }
  }, [selectedTenantId]);

  const fetchDetails = useCallback(async (tenantId: string) => {
    if (!tenantId) return;
    setLoading(true);
    try {
      const res = await fetch(`/api/proxy/platform/tenants/${tenantId}`, {
        headers: authHeaders(),
      });
      if (!res.ok) throw new Error("Failed to load tenant quota details");
      const data: TenantDetails = await res.json();
      setDetails(data);
      setMaxStudents(data.entitlements.quotas.max_students);
      setMaxStaff(data.entitlements.quotas.max_staff);
      setMaxBatches(data.entitlements.quotas.max_batches);
      setStorageMb(data.entitlements.quotas.storage_mb);
      setFeatures(data.entitlements.features || {});
    } catch (err: any) {
      toast.error(err.message || "Failed to load quota details");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTenants();
  }, [fetchTenants]);

  useEffect(() => {
    if (selectedTenantId) {
      fetchDetails(selectedTenantId);
    }
  }, [selectedTenantId, fetchDetails]);

  const handleSaveOverrides = async () => {
    if (!selectedTenantId) return;
    setSaving(true);
    try {
      const payload = {
        max_students: Number(maxStudents),
        max_staff: Number(maxStaff),
        max_batches: Number(maxBatches),
        storage_mb: Number(storageMb),
        features: features,
      };

      const res = await fetch(`/api/proxy/platform/tenants/${selectedTenantId}/quotas`, {
        method: "PATCH",
        headers: authHeaders(),
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.message || data.detail || "Failed to update quotas");
      toast.success(data.message || "Custom quota overrides saved successfully");
      fetchDetails(selectedTenantId);
    } catch (err: any) {
      toast.error(err.message || "Failed to save quota overrides");
    } finally {
      setSaving(false);
    }
  };

  const toggleFeature = (key: string) => {
    setFeatures((prev) => ({
      ...prev,
      [key]: !prev[key],
    }));
  };

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="rounded-md bg-violet-600/10 p-1.5 text-violet-600 dark:text-violet-400">
              <Sliders className="h-5 w-5" />
            </span>
            <h1 className="text-2xl font-bold tracking-tight">Usage & Enterprise Quotas</h1>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Configure custom enterprise capacity limits, storage allowances, and granular feature flags per tenant.
          </p>
        </div>

        <button
          onClick={() => selectedTenantId && fetchDetails(selectedTenantId)}
          disabled={loading}
          className="flex items-center gap-1.5 rounded-xl border bg-background px-3.5 py-2 text-xs font-semibold hover:bg-accent transition-colors shadow-xs"
        >
          <RefreshCw className={cn("h-3.5 w-3.5 text-muted-foreground", loading && "animate-spin")} />
          Refresh
        </button>
      </div>

      {/* Tenant Selector */}
      <div className="rounded-2xl border bg-card p-4 shadow-xs">
        <label className="text-xs font-semibold text-foreground block mb-1.5">Select Institute to Configure</label>
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

      {details && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Current Usage Telemetry */}
          <div className="rounded-2xl border bg-card p-6 shadow-xs space-y-4">
            <h2 className="font-bold text-base tracking-tight flex items-center gap-2">
              <Building2 className="h-4 w-4 text-violet-600" /> Live Database Usage
            </h2>
            <div className="space-y-3 text-xs">
              <div className="flex justify-between items-center py-2 border-b">
                <span className="text-muted-foreground">Institute Name</span>
                <span className="font-bold text-foreground">{details.tenant.name}</span>
              </div>
              <div className="flex justify-between items-center py-2 border-b">
                <span className="text-muted-foreground">Active Plan</span>
                <span className="font-bold uppercase text-violet-600">{details.entitlements.plan}</span>
              </div>
              <div className="flex justify-between items-center py-2 border-b">
                <span className="text-muted-foreground">Active Enrolled Students</span>
                <span className="font-bold text-foreground">
                  {details.entitlements.usage.students} / {details.entitlements.quotas.max_students}
                </span>
              </div>
              <div className="flex justify-between items-center py-2 border-b">
                <span className="text-muted-foreground">Staff & Faculty Logins</span>
                <span className="font-bold text-foreground">
                  {details.entitlements.usage.staff} / {details.entitlements.quotas.max_staff}
                </span>
              </div>
              <div className="flex justify-between items-center py-2">
                <span className="text-muted-foreground">Active Scheduled Batches</span>
                <span className="font-bold text-foreground">
                  {details.entitlements.usage.batches} / {details.entitlements.quotas.max_batches}
                </span>
              </div>
            </div>
          </div>

          {/* Quota & Feature Overrides Form */}
          <div className="lg:col-span-2 rounded-2xl border bg-card p-6 shadow-xs space-y-5">
            <div className="flex items-center justify-between border-b pb-3">
              <div>
                <h2 className="font-bold text-base tracking-tight">Custom Enterprise Overrides</h2>
                <p className="text-xs text-muted-foreground">
                  These limits override default plan definitions without modifying canonical plan tiers.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-semibold text-foreground block mb-1">Max Students Limit</label>
                <input
                  type="number"
                  value={maxStudents}
                  onChange={(e) => setMaxStudents(Number(e.target.value))}
                  min={1}
                  className="h-9 w-full rounded-xl border bg-background px-3 text-xs focus:outline-none focus:ring-1 focus:ring-violet-500"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-foreground block mb-1">Max Staff Limit</label>
                <input
                  type="number"
                  value={maxStaff}
                  onChange={(e) => setMaxStaff(Number(e.target.value))}
                  min={1}
                  className="h-9 w-full rounded-xl border bg-background px-3 text-xs focus:outline-none focus:ring-1 focus:ring-violet-500"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-foreground block mb-1">Max Batches Limit</label>
                <input
                  type="number"
                  value={maxBatches}
                  onChange={(e) => setMaxBatches(Number(e.target.value))}
                  min={1}
                  className="h-9 w-full rounded-xl border bg-background px-3 text-xs focus:outline-none focus:ring-1 focus:ring-violet-500"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-foreground block mb-1">Storage Allocation (MB)</label>
                <input
                  type="number"
                  value={storageMb}
                  onChange={(e) => setStorageMb(Number(e.target.value))}
                  min={100}
                  className="h-9 w-full rounded-xl border bg-background px-3 text-xs focus:outline-none focus:ring-1 focus:ring-violet-500"
                />
              </div>
            </div>

            {/* Feature Flags Toggle */}
            <div className="border-t pt-4 space-y-3">
              <span className="text-xs font-bold text-foreground block">Feature Entitlement Overrides</span>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                {[
                  { key: "ai_copilot_enabled", label: "AI Copilot Engine" },
                  { key: "custom_roles_enabled", label: "Custom RBAC & Roles" },
                  { key: "custom_fields_enabled", label: "Custom Fields System" },
                  { key: "advanced_analytics_enabled", label: "Advanced Analytics & Reports" },
                  { key: "whatsapp_notifications_enabled", label: "WhatsApp & SMS Automation" },
                ].map((feat) => {
                  const active = Boolean(features[feat.key]);
                  return (
                    <button
                      type="button"
                      key={feat.key}
                      onClick={() => toggleFeature(feat.key)}
                      className={cn(
                        "flex items-center justify-between p-3 rounded-xl border text-xs font-medium transition-all text-left",
                        active
                          ? "bg-violet-500/10 border-violet-500/30 text-violet-700 dark:text-violet-300"
                          : "bg-muted/30 border-border text-muted-foreground hover:bg-accent"
                      )}
                    >
                      <span>{feat.label}</span>
                      {active ? (
                        <CheckCircle2 className="h-4 w-4 text-violet-600 shrink-0" />
                      ) : (
                        <span className="text-[10px] uppercase font-bold text-muted-foreground">Disabled</span>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="flex justify-end pt-3">
              <button
                onClick={handleSaveOverrides}
                disabled={saving}
                className="flex items-center gap-2 rounded-xl bg-violet-600 px-5 py-2.5 text-xs font-semibold text-white hover:bg-violet-700 transition-colors shadow-xs"
              >
                <Save className="h-4 w-4" />
                {saving ? "Saving Overrides..." : "Save Quota Overrides"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function PlatformQuotasPage() {
  return (
    <Suspense fallback={<div className="p-6 text-xs text-muted-foreground animate-pulse">Loading quota controls...</div>}>
      <PlatformQuotasContent />
    </Suspense>
  );
}
