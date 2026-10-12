"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import {
  Users,
  CalendarDays,
  IndianRupee,
  TrendingUp,
  ArrowUpRight,
  BookOpen,
  ClipboardList,
  UserPlus,
  FileCheck,
  Award,
  Sparkles,
} from "lucide-react";
import { useAcademicStore } from "@/lib/stores/academic.store";
import { useAuthStore } from "@/lib/stores/auth.store";
import { useLanguage } from "@/components/providers/LanguageProvider";
import { authHeaders } from "@/lib/auth-headers";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";

const API = "/api/proxy";

function formatCurrency(val: number) {
  if (val >= 100000) return `₹${(val / 100000).toFixed(2)}L`;
  if (val >= 1000) return `₹${(val / 1000).toFixed(1)}K`;
  return `₹${val.toLocaleString("en-IN")}`;
}

export function KpiCards() {
  const { language, t } = useLanguage();
  const academicStore = useAcademicStore();
  const user = useAuthStore((s) => s.user);
  const storeRole = useAuthStore((s) => s.role);

  const rawRole = (user?.role || storeRole || "owner").toLowerCase();
  const role = rawRole === "super_admin" ? "owner" : rawRole;

  const [dashboardData, setDashboardData] = useState<any>(null);
  const [feeSummary, setFeeSummary] = useState<any>(null);
  const [invoices, setInvoices] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const loadKpiData = useCallback(async (silent = false) => {
    try {
      if (!silent) setLoading(true);

      // Fetch generalized dashboard data for current role
      const dashRes = (await api.get<any>("/dashboard/").catch(() => null)) as any;

      if (dashRes && dashRes.data) {
        setDashboardData(dashRes.data);
      }

      // If owner or admin, also fetch financial metrics
      if (role === "owner" || role === "admin") {
        const [feeRes, invRes] = await Promise.all([
          api.get<any>("/fees/revenue/summary").catch(() => null) as Promise<any>,
          api.get<any>("/fees/invoices").catch(() => null) as Promise<any>,
        ]);

        if (feeRes) setFeeSummary(feeRes?.data ?? feeRes);
        if (invRes) {
          const invList = Array.isArray(invRes) ? invRes : invRes?.data ?? invRes?.items ?? [];
          setInvoices(invList);
        }
      }
    } catch (err) {
      console.warn("Failed fetching KPI data:", err);
    } finally {
      if (!silent) setLoading(false);
    }
  }, [role]);

  useEffect(() => {
    loadKpiData(false);
  }, [loadKpiData]);

  // Compute exact KPIs according to the active role
  const kpis = useMemo(() => {
    // 1. 👑 Owner / Admin KPI Cards (Executive & Financial View)
    if (role === "owner" || role === "admin") {
      const studentCount = dashboardData?.total_students ?? (academicStore.students.length > 0 ? academicStore.students.length : 0);
      const batchCount = dashboardData?.active_batches ?? (academicStore.batches.length > 0 ? academicStore.batches.length : 0);

      let calculatedCollected = 0;
      let calculatedPending = 0;

      if (dashboardData !== null && typeof dashboardData.total_collected === "number") {
        calculatedCollected = dashboardData.total_collected;
        calculatedPending = dashboardData.pending_revenue ?? 0;
      } else if (feeSummary && typeof feeSummary.total_collected === "number") {
        calculatedCollected = feeSummary.total_collected;
        calculatedPending = feeSummary.total_outstanding ?? 0;
      } else if (invoices.length > 0) {
        invoices.forEach((inv) => {
          const paid = Number(inv.amountPaid ?? inv.paidAmount ?? (inv.status === "PAID" || inv.status === "paid" ? inv.amount ?? inv.totalAmount ?? 0 : 0));
          const total = Number(inv.amountDue ?? inv.amount ?? inv.totalAmount ?? 0);
          calculatedCollected += paid;
          if (inv.status !== "PAID" && inv.status !== "paid") {
            calculatedPending += Math.max(0, total - paid);
          }
        });
      }

      const avgAttendance = dashboardData?.avg_attendance_percent ?? 0;

      return [
        {
          title: "Total Students",
          value: String(studentCount),
          icon: Users,
          color: "text-blue-600 dark:text-blue-400",
          bg: "bg-blue-500/10 border-blue-500/20",
          sub: "Active enrolled students",
          link: "/students",
        },
        {
          title: "Active Batches",
          value: String(batchCount),
          icon: CalendarDays,
          color: "text-violet-600 dark:text-violet-400",
          bg: "bg-violet-500/10 border-violet-500/20",
          sub: "Running class schedules",
          link: "/batches",
        },
        {
          title: "Tuition Fee Collected",
          value: formatCurrency(calculatedCollected),
          icon: IndianRupee,
          color: "text-emerald-600 dark:text-emerald-400",
          bg: "bg-emerald-500/10 border-emerald-500/20",
          sub: calculatedPending > 0 ? `₹${calculatedPending.toLocaleString("en-IN")} ${t("pending dues")}` : t("All student fees settled"),
          link: "/fees",
        },
        {
          title: "Avg Attendance Rate",
          value: `${avgAttendance}%`,
          icon: TrendingUp,
          color: "text-amber-600 dark:text-amber-400",
          bg: "bg-amber-500/10 border-amber-500/20",
          sub: "Batch presence average",
          link: "/attendance",
        },
      ];
    }

    // 2. 👨‍🏫 Tutor / Coach KPI Cards (Faculty & Classroom View)
    if (role === "tutor" || role === "coach") {
      const myClasses = dashboardData?.my_classes_today ?? 0;
      const myBatches = dashboardData?.my_batches ?? (academicStore.batches.length > 0 ? academicStore.batches.length : 0);
      const examsCreated = dashboardData?.exams_created ?? (academicStore.exams.length > 0 ? academicStore.exams.length : 0);
      const avgScore = dashboardData?.avg_student_score ?? 78.5;

      return [
        {
          title: "Classes Today",
          value: String(myClasses),
          icon: CalendarDays,
          color: "text-blue-600 dark:text-blue-400",
          bg: "bg-blue-500/10 border-blue-500/20",
          sub: "Scheduled lectures today",
          link: "/sessions",
        },
        {
          title: "Assigned Batches",
          value: String(myBatches),
          icon: BookOpen,
          color: "text-violet-600 dark:text-violet-400",
          bg: "bg-violet-500/10 border-violet-500/20",
          sub: "Active classes teaching",
          link: "/batches",
        },
        {
          title: "Exams Evaluated",
          value: String(examsCreated),
          icon: ClipboardList,
          color: "text-amber-600 dark:text-amber-400",
          bg: "bg-amber-500/10 border-amber-500/20",
          sub: "Tests & assessments",
          link: "/exams",
        },
        {
          title: "Avg Student Score",
          value: `${avgScore}%`,
          icon: Award,
          color: "text-emerald-600 dark:text-emerald-400",
          bg: "bg-emerald-500/10 border-emerald-500/20",
          sub: "Class evaluation average",
          link: "/exams",
        },
      ];
    }

    // 3. 🧑‍💼 Counselor KPI Cards (Leads & Admissions View)
    if (role === "counselor") {
      const totalLeads = dashboardData?.total_leads ?? 0;
      const converted = dashboardData?.converted_leads ?? 0;
      const conversionRate = totalLeads > 0 ? Math.round((converted / totalLeads) * 100) : 0;
      const studentCount = academicStore.students.length > 0 ? academicStore.students.length : 0;

      return [
        {
          title: "Total Inquiries",
          value: String(totalLeads),
          icon: UserPlus,
          color: "text-blue-600 dark:text-blue-400",
          bg: "bg-blue-500/10 border-blue-500/20",
          sub: "Prospective student leads",
          link: "/leads",
        },
        {
          title: "Admissions Converted",
          value: String(converted),
          icon: FileCheck,
          color: "text-emerald-600 dark:text-emerald-400",
          bg: "bg-emerald-500/10 border-emerald-500/20",
          sub: "Successful enrollments",
          link: "/admissions",
        },
        {
          title: "Conversion Rate",
          value: `${conversionRate}%`,
          icon: TrendingUp,
          color: "text-violet-600 dark:text-violet-400",
          bg: "bg-violet-500/10 border-violet-500/20",
          sub: "Lead conversion efficacy",
          link: "/leads",
        },
        {
          title: "Enrolled Students",
          value: String(studentCount),
          icon: Users,
          color: "text-amber-600 dark:text-amber-400",
          bg: "bg-amber-500/10 border-amber-500/20",
          sub: "Active student directory",
          link: "/students",
        },
      ];
    }

    return [];
  }, [role, dashboardData, feeSummary, invoices, academicStore, language, t]);

  if (loading && !dashboardData && invoices.length === 0) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="rounded-2xl border bg-card p-5 shadow-sm animate-pulse space-y-3">
            <div className="h-4 w-28 bg-muted rounded-md" />
            <div className="h-8 w-20 bg-muted rounded-lg" />
            <div className="h-3 w-24 bg-muted rounded-md" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {kpis.map((kpi, i) => (
        <Link
          key={kpi.title}
          href={kpi.link}
          className="rounded-2xl border bg-card p-5 shadow-sm hover:shadow-md hover:border-primary/40 transition-all group fade-in flex flex-col justify-between space-y-3"
          style={{ animationDelay: `${i * 50}ms` }}
        >
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{t(kpi.title)}</p>
              <p className="mt-2 text-3xl font-extrabold tracking-tight text-foreground group-hover:text-primary transition-colors">
                {kpi.value}
              </p>
            </div>
            <div className={cn("rounded-xl p-3 border", kpi.bg)}>
              <kpi.icon className={cn("h-5 w-5", kpi.color)} />
            </div>
          </div>

          <div className="flex items-center justify-between text-xs pt-2 border-t text-muted-foreground">
            <span className="font-medium truncate">{t(kpi.sub)}</span>
            <span className="flex items-center gap-0.5 font-bold text-primary group-hover:underline shrink-0">
              {t("View")} <ArrowUpRight className="h-3 w-3" />
            </span>
          </div>
        </Link>
      ))}
    </div>
  );
}