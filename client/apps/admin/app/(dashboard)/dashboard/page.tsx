"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import dynamic from "next/dynamic";
import {
  Sparkles,
  UserPlus,
  Receipt,
  CalendarCheck,
  FileSpreadsheet,
  ArrowUpRight,
  ShieldCheck,
  BookOpen,
  Users,
  Award,
  Bell,
  CreditCard,
  Settings,
  GraduationCap,
  ClipboardList,
  CalendarDays,
} from "lucide-react";
import { KpiCards } from "@/components/dashboard/KpiCards";
import { useAuthStore } from "@/lib/stores/auth.store";
import { useLanguage } from "@/components/providers/LanguageProvider";

// Dynamically import heavy chart components to reduce initial main-thread JavaScript execution time & TBT
const FeeCollectionChart = dynamic(
  () => import("@/components/dashboard/FeeCollectionChart").then((mod) => mod.FeeCollectionChart),
  { ssr: false, loading: () => <div className="h-[300px] rounded-2xl border bg-card/50 p-6 animate-pulse" /> }
);
const LeadFunnelChart = dynamic(
  () => import("@/components/dashboard/LeadFunnelChart").then((mod) => mod.LeadFunnelChart),
  { ssr: false, loading: () => <div className="h-[300px] rounded-2xl border bg-card/50 p-6 animate-pulse" /> }
);
const AttendanceHeatmap = dynamic(
  () => import("@/components/dashboard/AttendanceHeatmap").then((mod) => mod.AttendanceHeatmap),
  { ssr: false, loading: () => <div className="h-[200px] rounded-2xl border bg-card/50 p-6 animate-pulse" /> }
);
const AnalyticsChatBubble = dynamic(
  () => import("@/components/ai/AnalyticsChatBubble").then((mod) => mod.AnalyticsChatBubble),
  { ssr: false }
);

const ALL_MODULES = [
  { name: "Admissions", href: "/admissions", icon: UserPlus, color: "text-blue-600 dark:text-blue-400", bg: "bg-blue-500/10", roles: ["owner", "admin", "counselor"] },
  { name: "Batches & Timetable", href: "/batches", icon: BookOpen, color: "text-violet-600 dark:text-violet-400", bg: "bg-violet-500/10", roles: ["owner", "admin", "tutor", "coach", "counselor"] },
  { name: "Attendance Marker", href: "/attendance", icon: CalendarCheck, color: "text-emerald-600 dark:text-emerald-400", bg: "bg-emerald-500/10", roles: ["owner", "admin", "tutor", "coach"] },
  { name: "Exams & Results", href: "/exams", icon: FileSpreadsheet, color: "text-amber-600 dark:text-amber-400", bg: "bg-amber-500/10", roles: ["owner", "admin", "tutor", "coach"] },
  { name: "Class Sessions", href: "/sessions", icon: CalendarDays, color: "text-indigo-600 dark:text-indigo-400", bg: "bg-indigo-500/10", roles: ["owner", "admin", "tutor", "coach"] },
  { name: "Student Growth Cards", href: "/growth-cards", icon: Award, color: "text-purple-600 dark:text-purple-400", bg: "bg-purple-500/10", roles: ["owner", "admin", "tutor", "coach", "counselor"] },
  { name: "Fee Invoicing", href: "/fees", icon: Receipt, color: "text-green-600 dark:text-green-400", bg: "bg-green-500/10", roles: ["owner", "admin", "counselor"] },
  { name: "Notifications", href: "/notifications", icon: Bell, color: "text-sky-600 dark:text-sky-400", bg: "bg-sky-500/10", roles: ["owner", "admin", "counselor"] },
  { name: "SaaS Billing", href: "/settings/billing", icon: CreditCard, color: "text-rose-600 dark:text-rose-400", bg: "bg-rose-500/10", roles: ["owner"] },
  { name: "Institute Settings", href: "/settings", icon: Settings, color: "text-violet-600 dark:text-violet-400", bg: "bg-violet-500/10", roles: ["owner", "admin"] },
];

import { SuperAdminDashboard } from "@/components/dashboard/SuperAdminDashboard";

export default function DashboardPage() {
  const { t } = useLanguage();
  const user = useAuthStore((s) => s.user);
  const storeRole = useAuthStore((s) => s.role);

  const rawRole = (user?.role || storeRole || "owner").toLowerCase();

  // If Super Admin, render the dedicated Platform Management Dashboard
  if (rawRole === "super_admin") {
    return <SuperAdminDashboard />;
  }

  const role = rawRole;
  const userName = `${user?.first_name ?? ""} ${user?.last_name ?? ""}`.trim() || user?.email || "User";

  // Filter modules visible to this role
  const visibleModules = ALL_MODULES.filter((m) => m.roles.includes(role));

  return (
    <div className="space-y-6 max-w-7xl">
      {/* 🚀 Header Banner (Role-Adaptive) */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            {role === "owner" && t("Executive Command Center")}
            {role === "admin" && t("Operations Command Center")}
            {(role === "tutor" || role === "coach") && t("Faculty Teaching Portal")}
            {role === "counselor" && t("Admissions & Counseling Center")}
            {role !== "owner" && role !== "admin" && role !== "tutor" && role !== "coach" && role !== "counselor" && t("CoachGenie Dashboard")}

            <span className="inline-flex items-center gap-1 rounded-full bg-violet-500/10 px-2.5 py-0.5 text-xs font-semibold text-violet-600">
              <Sparkles className="h-3 w-3" /> {t("Live Feed")}
            </span>
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            {t("Welcome back,")} <span className="font-semibold text-foreground">{userName}</span>. {t("Here is today's real-time summary.")}
          </p>
        </div>

        {/* Quick Action Buttons (Role-Adaptive) */}
        <div className="flex flex-wrap items-center gap-2">
          {(role === "owner" || role === "admin" || role === "counselor") && (
            <Link
              href="/leads"
              className="flex items-center gap-1.5 rounded-xl border bg-background px-3.5 py-2 text-xs font-semibold hover:bg-accent transition-colors shadow-xs"
            >
              <UserPlus className="h-3.5 w-3.5 text-blue-600" /> {t("New Lead")}
            </Link>
          )}

          {(role === "owner" || role === "admin" || role === "tutor" || role === "coach") && (
            <Link
              href="/attendance"
              className="flex items-center gap-1.5 rounded-xl border bg-background px-3.5 py-2 text-xs font-semibold hover:bg-accent transition-colors shadow-xs"
            >
              <CalendarCheck className="h-3.5 w-3.5 text-emerald-600" /> {t("Mark Attendance")}
            </Link>
          )}

          {(role === "tutor" || role === "coach") && (
            <Link
              href="/exams"
              className="flex items-center gap-1.5 rounded-xl bg-violet-600 px-4 py-2 text-xs font-semibold text-white hover:bg-violet-700 transition-all shadow-sm"
            >
              <ClipboardList className="h-3.5 w-3.5" /> {t("Enter Exam Scores")}
            </Link>
          )}

          {(role === "owner" || role === "admin") && (
            <Link
              href="/fees"
              className="flex items-center gap-1.5 rounded-xl bg-violet-600 px-4 py-2 text-xs font-semibold text-white hover:bg-violet-700 transition-all shadow-sm"
            >
              <Receipt className="h-3.5 w-3.5" /> {t("Record Fee")}
            </Link>
          )}

          {role === "counselor" && (
            <Link
              href="/admissions"
              className="flex items-center gap-1.5 rounded-xl bg-violet-600 px-4 py-2 text-xs font-semibold text-white hover:bg-violet-700 transition-all shadow-sm"
            >
              <UserPlus className="h-3.5 w-3.5" /> {t("Enroll Student")}
            </Link>
          )}
        </div>
      </div>

      {/* 🟢 System Status Banner (Owner/Admin only) */}
      {(role === "owner" || role === "admin") && (
        <div className="rounded-2xl border-2 border-emerald-500/20 bg-emerald-500/5 p-4 flex flex-wrap items-center justify-between gap-3 shadow-xs">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-xl bg-emerald-500 text-white flex items-center justify-center font-bold">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <div>
              <p className="text-xs font-extrabold text-emerald-800 dark:text-emerald-300 uppercase tracking-wider">
                {t("Institute Health Score: 98% • All Core Modules Active")}
              </p>
              <p className="text-xs text-emerald-700 dark:text-emerald-400 font-semibold">
                {t("Multi-Tenant Security, Real-Time Database Sync & AI Copilot Online")}
              </p>
            </div>
          </div>

          <Link href="/settings" className="text-xs font-bold text-emerald-800 dark:text-emerald-300 hover:underline flex items-center gap-1">
            {t("Institute Settings →")}
          </Link>
        </div>
      )}

      {/* 📊 Key Performance Indicators (Role-Adaptive) */}
      <KpiCards />

      {/* 📈 Charts Row: Filtered as per Role */}
      {(role === "owner" || role === "admin") && (
        <div className="grid gap-6 lg:grid-cols-2">
          <FeeCollectionChart />
          <LeadFunnelChart />
        </div>
      )}

      {role === "counselor" && (
        <div className="grid gap-6 lg:grid-cols-2">
          <LeadFunnelChart />
          <AttendanceHeatmap />
        </div>
      )}

      {/* 📅 Attendance Activity Heatmap (For Faculty, Owners & Admins) */}
      {(role === "owner" || role === "admin" || role === "tutor" || role === "coach") && (
        <AttendanceHeatmap />
      )}

      {/* 🧭 Role-Filtered Quick Module Directory Grid (Authorized Section) */}
      <div className="rounded-2xl border bg-card p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between border-b pb-3">
          <div>
            <h2 className="font-bold text-base tracking-tight">{t("Your Authorized Modules")}</h2>
            <p className="text-xs text-muted-foreground mt-0.5">{t("Quick access to modules enabled for your role")}</p>
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {visibleModules.map((mod) => (
            <Link
              key={mod.name}
              href={mod.href}
              className="rounded-xl border bg-background p-3.5 hover:bg-accent/50 hover:border-primary/40 transition-all flex items-center justify-between group shadow-xs"
            >
              <div className="flex items-center gap-3">
                <div className={`h-9 w-9 rounded-lg flex items-center justify-center ${mod.bg}`}>
                  <mod.icon className={`h-4 w-4 ${mod.color}`} />
                </div>
                <span className="text-xs font-bold text-foreground group-hover:text-primary transition-colors">
                  {t(mod.name)}
                </span>
              </div>
              <ArrowUpRight className="h-4 w-4 text-muted-foreground group-hover:text-primary transition-colors" />
            </Link>
          ))}
        </div>
      </div>

      {/* 🤖 Floating AI Analytics Assistant */}
      <AnalyticsChatBubble />
    </div>
  );
}