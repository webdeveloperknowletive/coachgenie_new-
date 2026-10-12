"use client";

import { useState, useEffect, useCallback } from "react";
import {
  TrendingUp,
  Building2,
  Users,
  Layers,
  Activity,
  RefreshCw,
  Sparkles,
  PieChart,
  BarChart3,
  Calendar,
  IndianRupee,
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

export default function PlatformAnalyticsPage() {
  const { t } = useLanguage();
  const [metrics, setMetrics] = useState<PlatformMetrics | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchMetrics = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/proxy/platform/metrics", {
        headers: authHeaders(),
      });
      if (!res.ok) throw new Error("Failed to load platform analytics");
      const data = await res.json();
      setMetrics(data);
    } catch (err: any) {
      toast.error(err.message || "Failed to load platform analytics");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMetrics();
  }, [fetchMetrics]);

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="rounded-md bg-violet-600/10 p-1.5 text-violet-600 dark:text-violet-400">
              <TrendingUp className="h-5 w-5" />
            </span>
            <h1 className="text-2xl font-bold tracking-tight">Platform Analytics & Growth Telemetry</h1>
            <span className="rounded-full bg-violet-500/10 px-2.5 py-0.5 text-xs font-semibold text-violet-600">
              Cross-Tenant Analytics
            </span>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Aggregated cross-institute student population growth, subscription tier adoption, retention health, and operational volume.
          </p>
        </div>

        <button
          onClick={() => fetchMetrics()}
          disabled={loading}
          className="flex items-center gap-1.5 rounded-xl border bg-background px-3.5 py-2 text-xs font-semibold hover:bg-accent transition-colors shadow-xs"
        >
          <RefreshCw className={cn("h-3.5 w-3.5 text-muted-foreground", loading && "animate-spin")} />
          Refresh Analytics
        </button>
      </div>

      {/* Analytics KPI Row */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-2xl border bg-card p-5 shadow-xs">
          <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Platform Active Ratio
          </span>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold tracking-tight">
              {metrics && metrics.total_tenants > 0
                ? `${Math.round((metrics.active_tenants / metrics.total_tenants) * 100)}%`
                : "100%"}
            </span>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            {metrics ? `${metrics.active_tenants} active of ${metrics.total_tenants} total` : "—"}
          </p>
        </div>

        <div className="rounded-2xl border bg-card p-5 shadow-xs">
          <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Average Students / Institute
          </span>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold tracking-tight">
              {metrics && metrics.active_tenants > 0
                ? Math.round(metrics.total_students / metrics.active_tenants)
                : 0}
            </span>
            <span className="text-xs text-muted-foreground">students</span>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">Mean active enrolled profiles</p>
        </div>

        <div className="rounded-2xl border bg-card p-5 shadow-xs">
          <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Staff-to-Student Ratio
          </span>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold tracking-tight">
              {metrics && metrics.total_staff > 0
                ? `1 : ${Math.round(metrics.total_students / metrics.total_staff)}`
                : "1 : 0"}
            </span>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">Operator leverage ratio</p>
        </div>

        <div className="rounded-2xl border bg-card p-5 shadow-xs">
          <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Suspension Rate
          </span>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold tracking-tight text-rose-600">
              {metrics && metrics.total_tenants > 0
                ? `${Math.round((metrics.suspended_tenants / metrics.total_tenants) * 100)}%`
                : "0%"}
            </span>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            {metrics?.suspended_tenants || 0} suspended workspaces
          </p>
        </div>
      </div>

      {/* Deep Dive Breakdown */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Tier Distribution */}
        <div className="rounded-2xl border bg-card p-6 shadow-xs space-y-4">
          <h2 className="text-base font-bold tracking-tight flex items-center gap-2">
            <Layers className="h-4 w-4 text-violet-600" /> Subscription Tier Adoption
          </h2>
          <p className="text-xs text-muted-foreground">
            Distribution of institute workspaces by commercial plan tier.
          </p>

          <div className="space-y-4 pt-2">
            {metrics && Object.keys(metrics.plan_distribution).length > 0 ? (
              Object.entries(metrics.plan_distribution).map(([plan, count]) => {
                const percent = metrics.total_tenants > 0 ? Math.round((count / metrics.total_tenants) * 100) : 0;
                return (
                  <div key={plan} className="space-y-1.5">
                    <div className="flex justify-between text-xs font-semibold">
                      <span className="capitalize">{plan} Tier</span>
                      <span>
                        {count} institutes ({percent}%)
                      </span>
                    </div>
                    <div className="h-2.5 w-full rounded-full bg-muted overflow-hidden">
                      <div
                        className="h-full rounded-full bg-violet-600 transition-all duration-500"
                        style={{ width: `${percent}%` }}
                      />
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="py-8 text-center text-xs text-muted-foreground">No tier distribution recorded.</div>
            )}
          </div>
        </div>

        {/* Global Operational Scale */}
        <div className="rounded-2xl border bg-card p-6 shadow-xs space-y-4">
          <h2 className="text-base font-bold tracking-tight flex items-center gap-2">
            <Activity className="h-4 w-4 text-emerald-600" /> Operational Scale Distribution
          </h2>
          <p className="text-xs text-muted-foreground">
            Total active entities indexed and managed across the entire multi-tenant database.
          </p>

          <div className="space-y-3 pt-2 text-xs">
            <div className="flex items-center justify-between p-3 rounded-xl border bg-muted/20">
              <span className="text-muted-foreground">Total Active Students</span>
              <span className="font-bold text-foreground text-sm">
                {metrics ? metrics.total_students.toLocaleString() : "—"}
              </span>
            </div>
            <div className="flex items-center justify-between p-3 rounded-xl border bg-muted/20">
              <span className="text-muted-foreground">Total Staff & Faculty Accounts</span>
              <span className="font-bold text-foreground text-sm">
                {metrics ? metrics.total_staff.toLocaleString() : "—"}
              </span>
            </div>
            <div className="flex items-center justify-between p-3 rounded-xl border bg-muted/20">
              <span className="text-muted-foreground">Total Active Institute Workspaces</span>
              <span className="font-bold text-foreground text-sm">
                {metrics ? metrics.active_tenants.toLocaleString() : "—"}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
