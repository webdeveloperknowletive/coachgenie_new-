"use client";

import { useState, useEffect, useCallback } from "react";
import {
  IndianRupee,
  TrendingUp,
  CreditCard,
  Building2,
  RefreshCw,
  Sparkles,
  PieChart,
  Layers,
  Receipt,
  ShieldCheck,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { authHeaders } from "@/lib/auth-headers";
import { useLanguage } from "@/components/providers/LanguageProvider";

interface PlatformFinance {
  currency: string;
  mrr: number;
  arr: number;
  active_subscriptions: Record<string, number>;
  tier_pricing_monthly: Record<string, number>;
  total_lifetime_subscription_revenue: number;
  total_student_invoiced_across_tenants: number;
  total_student_collected_across_tenants: number;
}

export default function PlatformFinancePage() {
  const { t } = useLanguage();
  const [finance, setFinance] = useState<PlatformFinance | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchFinance = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/proxy/platform/finance", {
        headers: authHeaders(),
      });
      if (!res.ok) throw new Error("Failed to load platform financial metrics");
      const data = await res.json();
      setFinance(data);
    } catch (err: any) {
      toast.error(err.message || "Failed to load finance data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchFinance();
  }, [fetchFinance]);

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="rounded-md bg-emerald-600/10 p-1.5 text-emerald-600 dark:text-emerald-400">
              <IndianRupee className="h-5 w-5" />
            </span>
            <h1 className="text-2xl font-bold tracking-tight">Platform Financial Control Plane</h1>
            <span className="rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-xs font-semibold text-emerald-600">
              SaaS Subscription Metrics
            </span>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Separation of CoachGenie SaaS subscription software license revenue from institute-level student fee collections.
          </p>
        </div>

        <button
          onClick={() => fetchFinance()}
          disabled={loading}
          className="flex items-center gap-1.5 rounded-xl border bg-background px-3.5 py-2 text-xs font-semibold hover:bg-accent transition-colors shadow-xs"
        >
          <RefreshCw className={cn("h-3.5 w-3.5 text-muted-foreground", loading && "animate-spin")} />
          Refresh Finance
        </button>
      </div>

      {/* SaaS Revenue KPI Row */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-2xl border bg-card p-5 shadow-xs">
          <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Monthly Recurring Revenue (MRR)
          </span>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold tracking-tight">
              {finance ? `₹${finance.mrr.toLocaleString("en-IN")}` : "—"}
            </span>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">Active software subscriptions</p>
        </div>

        <div className="rounded-2xl border bg-card p-5 shadow-xs">
          <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Annual Recurring Revenue (ARR)
          </span>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold tracking-tight text-emerald-600">
              {finance ? `₹${finance.arr.toLocaleString("en-IN")}` : "—"}
            </span>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">Annualized contracted run-rate</p>
        </div>

        <div className="rounded-2xl border bg-card p-5 shadow-xs">
          <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Platform Lifetime Value (Est.)
          </span>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold tracking-tight">
              {finance ? `₹${finance.total_lifetime_subscription_revenue.toLocaleString("en-IN")}` : "—"}
            </span>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">Cumulative platform SaaS revenue</p>
        </div>

        <div className="rounded-2xl border bg-card p-5 shadow-xs">
          <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Active Paid Tiers
          </span>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-bold tracking-tight">
              {finance
                ? Object.values(finance.active_subscriptions).reduce((a, b) => a + b, 0)
                : "—"}
            </span>
            <span className="text-xs text-muted-foreground">institutes</span>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">Paying SaaS customer base</p>
        </div>
      </div>

      {/* Subscription Breakdown vs Student Fee Aggregates */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Tier MRR Contribution */}
        <div className="rounded-2xl border bg-card p-6 shadow-xs space-y-4">
          <h2 className="text-base font-bold tracking-tight flex items-center gap-2">
            <Layers className="h-4 w-4 text-violet-600" /> SaaS Subscription Pricing & MRR Contribution
          </h2>
          <p className="text-xs text-muted-foreground">
            Revenue breakdown generated strictly from CoachGenie platform license subscriptions.
          </p>

          <div className="space-y-3 pt-2 text-xs">
            {finance &&
              Object.entries(finance.active_subscriptions).map(([plan, count]) => {
                const price = finance.tier_pricing_monthly[plan] || 0;
                const tierMrr = price * count;

                return (
                  <div key={plan} className="flex items-center justify-between p-3 rounded-xl border bg-muted/20">
                    <div>
                      <span className="font-bold text-foreground capitalize block">{plan} Tier</span>
                      <span className="text-[11px] text-muted-foreground">
                        {count} institutes @ ₹{price.toLocaleString("en-IN")}/mo
                      </span>
                    </div>
                    <span className="font-bold text-foreground text-sm">
                      ₹{tierMrr.toLocaleString("en-IN")}/mo
                    </span>
                  </div>
                );
              })}
          </div>
        </div>

        {/* Aggregate Tenant Student Collections */}
        <div className="rounded-2xl border bg-card p-6 shadow-xs space-y-4">
          <h2 className="text-base font-bold tracking-tight flex items-center gap-2">
            <Receipt className="h-4 w-4 text-blue-600" /> Institute-Level Student Tuition Invoicing
          </h2>
          <p className="text-xs text-muted-foreground">
            Total tuition fee volume invoiced and collected by institutes from their enrolled students.
          </p>

          {finance && (
            <div className="space-y-3 pt-2 text-xs">
              <div className="flex items-center justify-between p-3 rounded-xl border bg-muted/20">
                <span className="text-muted-foreground">Total Invoiced by Institutes</span>
                <span className="font-bold text-foreground text-sm">
                  ₹{finance.total_student_invoiced_across_tenants.toLocaleString("en-IN")}
                </span>
              </div>
              <div className="flex items-center justify-between p-3 rounded-xl border bg-emerald-500/10 border-emerald-500/20">
                <span className="text-emerald-700 dark:text-emerald-400">Total Collected by Institutes</span>
                <span className="font-bold text-emerald-600 text-sm">
                  ₹{finance.total_student_collected_across_tenants.toLocaleString("en-IN")}
                </span>
              </div>
              <div className="flex items-center justify-between p-3 rounded-xl border bg-muted/20">
                <span className="text-muted-foreground">Cross-Institute Collection Rate</span>
                <span className="font-bold text-foreground text-sm">
                  {finance.total_student_invoiced_across_tenants > 0
                    ? Math.round(
                        (finance.total_student_collected_across_tenants /
                          finance.total_student_invoiced_across_tenants) *
                          100
                      )
                    : 100}
                  %
                </span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
