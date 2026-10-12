"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  Building2,
  Users,
  ShieldCheck,
  Zap,
  TrendingUp,
  Activity,
  AlertCircle,
  CheckCircle2,
  ArrowUpRight,
  Sparkles,
  CreditCard,
  Settings,
  BookOpen,
  Eye,
  RefreshCw,
  Search,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { authHeaders } from "@/lib/auth-headers";
import { useLanguage } from "@/components/providers/LanguageProvider";

interface PlatformMetrics {
  total_tenants: number;
  active_tenants: number;
  suspended_tenants: number;
  total_students: number;
  total_staff: number;
  plan_distribution: Record<string, number>;
  total_invoiced_amount: number;
  total_collected_revenue: number;
}

interface PlatformTenant {
  id: string;
  name: string;
  subdomain: string;
  plan: string;
  is_active: boolean;
  created_at: string;
  student_count?: number;
  staff_count?: number;
}

export function SuperAdminDashboard() {
  const { t } = useLanguage();
  const [metrics, setMetrics] = useState<PlatformMetrics | null>(null);
  const [tenants, setTenants] = useState<PlatformTenant[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [generatingTokenFor, setGeneratingTokenFor] = useState<string | null>(null);

  const fetchPlatformData = useCallback(async () => {
    setLoading(true);
    try {
      const [mRes, tRes] = await Promise.all([
        fetch("/api/proxy/platform/metrics", { headers: authHeaders() })
          .then((r) => (r.ok ? r.json() : null))
          .catch(() => null),
        fetch("/api/proxy/platform/tenants?limit=20", { headers: authHeaders() })
          .then((r) => (r.ok ? r.json() : null))
          .catch(() => null),
      ]);

      if (mRes) setMetrics(mRes);
      if (tRes) setTenants(tRes.items ?? tRes.data ?? (Array.isArray(tRes) ? tRes : []));
    } catch (err) {
      console.error("Failed to load platform data:", err);
      toast.error("Failed to load platform metrics.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPlatformData();
  }, [fetchPlatformData]);

  const handleGenerateDiagnosticToken = async (tenantId: string, subdomain: string) => {
    setGeneratingTokenFor(tenantId);
    try {
      const res = await fetch(`/api/proxy/platform/tenants/${tenantId}/diagnostic-token`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ reason: "Super Admin routine system verification" }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.message || data.detail || "Failed to generate token");

      toast.success(`Diagnostic Token Generated for ${subdomain}. Read-Only expires in 15 mins.`);
    } catch (err: any) {
      toast.error(err.message || "Failed to initiate diagnostic mode");
    } finally {
      setGeneratingTokenFor(null);
    }
  };

  const filteredTenants = tenants.filter(
    (t) =>
      t.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      t.subdomain.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6 max-w-7xl">
      {/* 🛡️ Platform Executive Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="rounded-md bg-violet-600/10 p-1.5 text-violet-600 dark:text-violet-400">
              <ShieldCheck className="h-5 w-5" />
            </span>
            <h1 className="text-2xl font-bold tracking-tight">
              {t("Super Admin Platform Control")}
            </h1>
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-xs font-semibold text-emerald-600">
              <Activity className="h-3 w-3" /> Platform Master
            </span>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Global multi-tenant governance, subscription quotas, and real-time cross-institute telemetry.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => fetchPlatformData()}
            disabled={loading}
            className="flex items-center gap-1.5 rounded-xl border bg-background px-3.5 py-2 text-xs font-semibold hover:bg-accent transition-colors shadow-xs"
          >
            <RefreshCw className={cn("h-3.5 w-3.5 text-muted-foreground", loading && "animate-spin")} />
            {t("Refresh Telemetry")}
          </button>
          <Link
            href="/settings/billing"
            className="flex items-center gap-1.5 rounded-xl bg-violet-600 px-3.5 py-2 text-xs font-semibold text-white hover:bg-violet-700 transition-colors shadow-xs shadow-violet-500/20"
          >
            <CreditCard className="h-3.5 w-3.5" />
            {t("Plan Entitlements")}
          </Link>
        </div>
      </div>

      {/* 📊 Global Platform KPI Metric Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {/* Total Institutes */}
        <div className="rounded-2xl border bg-card p-5 shadow-xs transition-all hover:border-violet-500/30">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Total Institutes
            </span>
            <div className="rounded-xl bg-blue-500/10 p-2 text-blue-600">
              <Building2 className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold tracking-tight">
              {metrics ? metrics.total_tenants : "—"}
            </span>
            <span className="text-xs font-medium text-emerald-600">
              {metrics ? `${metrics.active_tenants} active` : ""}
            </span>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            {metrics?.suspended_tenants ? `${metrics.suspended_tenants} suspended` : "0 suspended"}
          </p>
        </div>

        {/* Global Students */}
        <div className="rounded-2xl border bg-card p-5 shadow-xs transition-all hover:border-violet-500/30">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Platform Students
            </span>
            <div className="rounded-xl bg-violet-500/10 p-2 text-violet-600">
              <Users className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold tracking-tight">
              {metrics ? metrics.total_students : "—"}
            </span>
            <span className="text-xs text-muted-foreground">across all institutes</span>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">Active enrolled profiles</p>
        </div>

        {/* Global Staff & Tutors */}
        <div className="rounded-2xl border bg-card p-5 shadow-xs transition-all hover:border-violet-500/30">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Platform Staff
            </span>
            <div className="rounded-xl bg-amber-500/10 p-2 text-amber-600">
              <Zap className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold tracking-tight">
              {metrics ? metrics.total_staff : "—"}
            </span>
            <span className="text-xs text-muted-foreground">tutors & counselors</span>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">Institute operators</p>
        </div>

        {/* Platform Revenue */}
        <div className="rounded-2xl border bg-card p-5 shadow-xs transition-all hover:border-violet-500/30">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Collected Revenue
            </span>
            <div className="rounded-xl bg-emerald-500/10 p-2 text-emerald-600">
              <TrendingUp className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold tracking-tight">
              {metrics ? `₹${metrics.total_collected_revenue.toLocaleString("en-IN")}` : "—"}
            </span>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            Invoiced: ₹{metrics ? metrics.total_invoiced_amount.toLocaleString("en-IN") : "0"}
          </p>
        </div>
      </div>

      {/* 🏢 Plan Distribution & Tenant Explorer */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Plan Distribution Breakdown */}
        <div className="rounded-2xl border bg-card p-6 shadow-xs">
          <h2 className="text-base font-bold tracking-tight flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-violet-600" />
            Subscription Distribution
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Institutes segmented by active subscription tier.
          </p>

          <div className="mt-5 space-y-3">
            {metrics && Object.keys(metrics.plan_distribution).length > 0 ? (
              Object.entries(metrics.plan_distribution).map(([plan, count]) => {
                const percent = metrics.total_tenants > 0 ? Math.round((count / metrics.total_tenants) * 100) : 0;
                return (
                  <div key={plan} className="space-y-1.5">
                    <div className="flex justify-between text-xs font-medium">
                      <span className="capitalize">{plan} Plan</span>
                      <span>
                        {count} institutes ({percent}%)
                      </span>
                    </div>
                    <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
                      <div
                        className="h-full rounded-full bg-violet-600 transition-all duration-500"
                        style={{ width: `${percent}%` }}
                      />
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="py-8 text-center text-xs text-muted-foreground">
                No subscription data recorded yet.
              </div>
            )}
          </div>

          <div className="mt-6 border-t pt-4">
            <Link
              href="/settings/billing"
              className="text-xs font-semibold text-violet-600 hover:text-violet-700 flex items-center gap-1"
            >
              Configure Tier Limits & Quotas <ArrowUpRight className="h-3 w-3" />
            </Link>
          </div>
        </div>

        {/* Live Institute Directory */}
        <div className="lg:col-span-2 rounded-2xl border bg-card p-6 shadow-xs">
          <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
            <div>
              <h2 className="text-base font-bold tracking-tight">Active Institute Workspaces</h2>
              <p className="text-xs text-muted-foreground">
                Direct tenant monitoring, status control, and read-only diagnostic impersonation.
              </p>
            </div>
            <div className="relative w-48 sm:w-64">
              <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search institutes..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="h-8 w-full rounded-lg border bg-background pl-8 pr-3 text-xs focus:outline-none focus:ring-1 focus:ring-violet-500"
              />
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b bg-muted/40 text-muted-foreground font-medium">
                <tr>
                  <th className="py-2.5 px-3">Institute Name</th>
                  <th className="py-2.5 px-3">Subdomain</th>
                  <th className="py-2.5 px-3">Plan</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {filteredTenants.length > 0 ? (
                  filteredTenants.map((t) => (
                    <tr key={t.id} className="hover:bg-muted/20 transition-colors">
                      <td className="py-3 px-3 font-semibold text-foreground">{t.name}</td>
                      <td className="py-3 px-3">
                        <span className="font-mono text-[11px] rounded bg-muted px-1.5 py-0.5">
                          {t.subdomain}
                        </span>
                      </td>
                      <td className="py-3 px-3">
                        <span className="inline-flex items-center rounded-full bg-violet-500/10 px-2 py-0.5 text-[11px] font-semibold text-violet-600 uppercase">
                          {t.plan}
                        </span>
                      </td>
                      <td className="py-3 px-3">
                        {t.is_active ? (
                          <span className="inline-flex items-center gap-1 text-emerald-600 font-medium">
                            <CheckCircle2 className="h-3 w-3" /> Active
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-rose-600 font-medium">
                            <AlertCircle className="h-3 w-3" /> Suspended
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-3 text-right">
                        <button
                          onClick={() => handleGenerateDiagnosticToken(t.id, t.subdomain)}
                          disabled={generatingTokenFor === t.id}
                          className="inline-flex items-center gap-1 rounded-md border bg-background px-2.5 py-1 text-[11px] font-medium hover:bg-accent transition-colors"
                        >
                          <Eye className="h-3 w-3 text-muted-foreground" />
                          {generatingTokenFor === t.id ? "Generating..." : "Diagnostic Mode"}
                        </button>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-muted-foreground">
                      {loading ? "Loading institute workspaces..." : "No institutes found matching query."}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
