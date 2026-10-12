"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Activity,
  Building2,
  Users,
  Zap,
  TrendingUp,
  ShieldCheck,
  RefreshCw,
  Sparkles,
  PieChart,
  IndianRupee,
  Layers,
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

export default function PlatformMetricsPage() {
  const { t } = useLanguage();
  const [metrics, setMetrics] = useState<PlatformMetrics | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchMetrics = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/proxy/platform/metrics", {
        headers: authHeaders(),
      });
      if (!res.ok) throw new Error("Failed to load platform telemetry");
      const data = await res.json();
      setMetrics(data);
    } catch (err: any) {
      toast.error(err.message || "Failed to load platform metrics");
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
              <Activity className="h-5 w-5" />
            </span>
            <h1 className="text-2xl font-bold tracking-tight">Platform Telemetry & Metrics</h1>
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-xs font-semibold text-emerald-600">
              Live Database Aggregation
            </span>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Global cross-institute telemetry, operational throughput, and SaaS financial health indicators.
          </p>
        </div>

        <button
          onClick={() => fetchMetrics()}
          disabled={loading}
          className="flex items-center gap-1.5 rounded-xl border bg-background px-3.5 py-2 text-xs font-semibold hover:bg-accent transition-colors shadow-xs"
        >
          <RefreshCw className={cn("h-3.5 w-3.5 text-muted-foreground", loading && "animate-spin")} />
          Refresh Telemetry
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {/* Total Institutes */}
        <div className="rounded-2xl border bg-card p-5 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Total Institutes
            </span>
            <div className="rounded-xl bg-blue-500/10 p-2 text-blue-600">
              <Building2 className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold tracking-tight">{metrics ? metrics.total_tenants : "—"}</span>
            <span className="text-xs font-medium text-emerald-600">
              {metrics ? `${metrics.active_tenants} active` : ""}
            </span>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            {metrics?.suspended_tenants ? `${metrics.suspended_tenants} suspended` : "0 suspended"}
          </p>
        </div>

        {/* Global Students */}
        <div className="rounded-2xl border bg-card p-5 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Platform Students
            </span>
            <div className="rounded-xl bg-violet-500/10 p-2 text-violet-600">
              <Users className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold tracking-tight">{metrics ? metrics.total_students : "—"}</span>
            <span className="text-xs text-muted-foreground">enrolled profiles</span>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">Active database records</p>
        </div>

        {/* Global Staff */}
        <div className="rounded-2xl border bg-card p-5 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Platform Staff
            </span>
            <div className="rounded-xl bg-amber-500/10 p-2 text-amber-600">
              <Zap className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold tracking-tight">{metrics ? metrics.total_staff : "—"}</span>
            <span className="text-xs text-muted-foreground">tutors & counselors</span>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">Active operator accounts</p>
        </div>

        {/* Platform Revenue */}
        <div className="rounded-2xl border bg-card p-5 shadow-xs">
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

      {/* Plan Distribution & Telemetry Details */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Tier Breakdown */}
        <div className="rounded-2xl border bg-card p-6 shadow-xs space-y-4">
          <h2 className="text-base font-bold tracking-tight flex items-center gap-2">
            <Layers className="h-4 w-4 text-violet-600" /> Subscription Tier Breakdown
          </h2>
          <p className="text-xs text-muted-foreground">
            Distribution of institutes across Starter, Growth, and Enterprise subscription plans.
          </p>

          <div className="space-y-4 pt-2">
            {metrics && Object.keys(metrics.plan_distribution).length > 0 ? (
              Object.entries(metrics.plan_distribution).map(([plan, count]) => {
                const percent = metrics.total_tenants > 0 ? Math.round((count / metrics.total_tenants) * 100) : 0;
                return (
                  <div key={plan} className="space-y-1.5">
                    <div className="flex justify-between text-xs font-semibold">
                      <span className="capitalize">{plan} Plan</span>
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
              <div className="py-8 text-center text-xs text-muted-foreground">No tier distribution recorded yet.</div>
            )}
          </div>
        </div>

        {/* Financial Collection Efficiency */}
        <div className="rounded-2xl border bg-card p-6 shadow-xs space-y-4">
          <h2 className="text-base font-bold tracking-tight flex items-center gap-2">
            <IndianRupee className="h-4 w-4 text-emerald-600" /> Financial Collection Realization
          </h2>
          <p className="text-xs text-muted-foreground">
            Platform-wide student fee collection efficiency computed across all active tenant invoices.
          </p>

          {metrics && (
            <div className="space-y-4 pt-2">
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="rounded-xl bg-muted/40 p-4 border">
                  <span className="text-muted-foreground block text-[11px]">Total Invoiced</span>
                  <span className="text-lg font-bold text-foreground">
                    ₹{metrics.total_invoiced_amount.toLocaleString("en-IN")}
                  </span>
                </div>
                <div className="rounded-xl bg-emerald-500/10 p-4 border border-emerald-500/20">
                  <span className="text-emerald-700 dark:text-emerald-400 block text-[11px]">Total Collected</span>
                  <span className="text-lg font-bold text-emerald-600">
                    ₹{metrics.total_collected_revenue.toLocaleString("en-IN")}
                  </span>
                </div>
              </div>

              <div className="space-y-1.5">
                <div className="flex justify-between text-xs font-semibold">
                  <span>Collection Realization Rate</span>
                  <span>
                    {metrics.total_invoiced_amount > 0
                      ? Math.round((metrics.total_collected_revenue / metrics.total_invoiced_amount) * 100)
                      : 100}
                    %
                  </span>
                </div>
                <div className="h-2.5 w-full rounded-full bg-muted overflow-hidden">
                  <div
                    className="h-full rounded-full bg-emerald-500 transition-all duration-500"
                    style={{
                      width: `${
                        metrics.total_invoiced_amount > 0
                          ? Math.min(
                              100,
                              Math.round((metrics.total_collected_revenue / metrics.total_invoiced_amount) * 100)
                            )
                          : 100
                      }%`,
                    }}
                  />
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
