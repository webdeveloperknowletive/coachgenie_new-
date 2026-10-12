"use client";

import { useState, useMemo, useEffect } from "react";
import Link from "next/link";
import { Plus, X, ChevronRight, Clock, CheckCircle, Calendar, Sparkles, BookOpen, Award, TrendingUp, Search } from "lucide-react";
import { format } from "date-fns";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { useAcademicStore } from "@/lib/stores/academic.store";
import { ExamForm, type ExamFormValues } from "@/components/exams/ExamForm";
import type { Exam } from "@/lib/types/academic";
import { authHeaders } from "@/lib/auth-headers";

const STATUS_CONFIG: Record<
  Exam["status"],
  { label: string; color: string; bg: string; border: string; icon: React.ElementType }
> = {
  UPCOMING: { label: "Upcoming", color: "text-blue-600 dark:text-blue-400", bg: "bg-blue-500/10", border: "border-blue-500/30", icon: Calendar },
  ONGOING: { label: "Ongoing", color: "text-amber-600 dark:text-amber-400", bg: "bg-amber-500/10", border: "border-amber-500/30", icon: Clock },
  COMPLETED: { label: "Completed", color: "text-emerald-600 dark:text-emerald-400", bg: "bg-emerald-500/10", border: "border-emerald-500/30", icon: CheckCircle },
};

const DEFAULT_SEED_EXAMS: Exam[] = [];

export default function ExamsPage() {
  const { exams, addExam, setExams, batches } = useAcademicStore();
  const [showForm, setShowForm] = useState(false);
  const [filter, setFilter] = useState<Exam["status"] | "ALL">("ALL");
  const [searchQuery, setSearchQuery] = useState("");


  const filtered = useMemo(() => {
    return exams.filter((e) => {
      const matchStatus = filter === "ALL" || e.status === filter;
      const matchSearch =
        !searchQuery ||
        e.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        e.subject.toLowerCase().includes(searchQuery.toLowerCase());
      return matchStatus && matchSearch;
    });
  }, [exams, filter, searchQuery]);

  // Executive KPI Stats
  const kpiStats = useMemo(() => {
    const totalCount = exams.length;
    const completedExams = exams.filter((e) => e.status === "COMPLETED");
    let totalMarks = 0;
    let totalMax = 0;

    completedExams.forEach((e) => {
      e.results?.forEach((r) => {
        if (r.marks !== null && r.marks !== undefined) {
          totalMarks += r.marks;
          totalMax += e.maxMarks;
        }
      });
    });

    const avgScorePct = totalMax > 0 ? Math.round((totalMarks / totalMax) * 100) : 0;
    const upcomingCount = exams.filter((e) => e.status === "UPCOMING").length;

    return {
      totalCount,
      completedCount: completedExams.length,
      upcomingCount,
      avgScorePct,
    };
  }, [exams]);

  async function handleCreate(data: ExamFormValues) {
    const isDuplicate = exams.some(
      (e) =>
        e.name.trim().toLowerCase() === data.name.trim().toLowerCase() &&
        e.batchId === data.batchId &&
        e.date === data.date
    );
    if (isDuplicate) {
      toast.error("An examination with this name and date already exists for this batch.");
      return;
    }

    await new Promise((r) => setTimeout(r, 400));
    addExam(data);
    toast.success("New examination scheduled!");
    setShowForm(false);
  }

  return (
    <div className="space-y-6 max-w-7xl">
      {/* 🚀 Header */}
      <div className="flex flex-wrap items-start justify-between gap-4 border-b pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            Examinations &amp; Gradebooks
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-xs font-semibold text-emerald-600">
              <Sparkles className="h-3 w-3" /> AI Rank Engine
            </span>
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Schedule tests, publish student marksheets, analyze class average scores, and rank top performers
          </p>
        </div>

        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-1.5 rounded-xl bg-violet-600 px-4 py-2 text-xs font-semibold text-white hover:bg-violet-700 transition-all shadow-sm"
        >
          <Plus className="h-4 w-4" /> Schedule New Exam
        </button>
      </div>

      {/* 📊 KPI Summary Metric Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-2xl border bg-card p-5 shadow-sm space-y-1">
          <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Total Exams</span>
          <p className="text-3xl font-extrabold tracking-tight">{kpiStats.totalCount}</p>
          <p className="text-xs text-muted-foreground">Scheduled in portal</p>
        </div>

        <div className="rounded-2xl border bg-card p-5 shadow-sm space-y-1">
          <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Completed Tests</span>
          <p className="text-3xl font-extrabold text-emerald-600 tracking-tight">{kpiStats.completedCount}</p>
          <p className="text-xs text-emerald-600 font-medium">Marks published</p>
        </div>

        <div className="rounded-2xl border bg-card p-5 shadow-sm space-y-1">
          <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Average Batch Score</span>
          <p className="text-3xl font-extrabold text-blue-600 tracking-tight">{kpiStats.avgScorePct}%</p>
          <p className="text-xs text-muted-foreground">Across all subjects</p>
        </div>

        <div className="rounded-2xl border bg-card p-5 shadow-sm space-y-1">
          <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Upcoming Exams</span>
          <p className="text-3xl font-extrabold text-amber-600 tracking-tight">{kpiStats.upcomingCount}</p>
          <p className="text-xs text-muted-foreground">Awaiting date</p>
        </div>
      </div>

      {/* 🔍 Search & Filters Bar */}
      <div className="rounded-2xl border bg-card p-4 shadow-sm space-y-3">
        <div className="relative max-w-xs">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search exam name or subject..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="h-9 w-full rounded-xl border bg-background pl-9 pr-3 text-xs font-medium focus:ring-2 focus:ring-primary outline-none"
          />
        </div>

        <div className="flex flex-wrap gap-2 pt-2 border-t">
          {(["ALL", "UPCOMING", "ONGOING", "COMPLETED"] as const).map((s) => (
            <button
              key={s}
              onClick={() => setFilter(s)}
              className={cn(
                "rounded-xl border px-3.5 py-1.5 text-xs font-semibold transition-all uppercase",
                filter === s ? "bg-foreground text-background shadow-xs" : "hover:bg-accent text-muted-foreground"
              )}
            >
              {s} ({s === "ALL" ? exams.length : exams.filter((e) => e.status === s).length})
            </button>
          ))}
        </div>
      </div>

      {/* 🚀 Exams List */}
      <div className="space-y-3">
        {filtered.length === 0 && (
          <div className="flex flex-col items-center justify-center py-16 gap-2 rounded-2xl border border-dashed bg-card text-center">
            <BookOpen className="h-8 w-8 text-muted-foreground/40" />
            <p className="font-semibold text-sm">No exams match your search.</p>
          </div>
        )}

        {filtered.map((exam) => {
          const cfg =
            STATUS_CONFIG[exam.status] ??
            (exam.status ? STATUS_CONFIG[exam.status.toUpperCase() as Exam["status"]] : null) ??
            STATUS_CONFIG.UPCOMING;
          const batch = batches.find((b) => b.id === exam.batchId);
          const StatusIcon = cfg.icon || Calendar;

          return (
            <Link
              key={exam.id}
              href={`/exams/${exam.id}`}
              className="flex items-center justify-between gap-4 rounded-2xl border bg-card p-4 shadow-sm hover:shadow-md hover:border-violet-500/40 transition-all group"
            >
              <div className="flex items-center gap-3.5 min-w-0">
                <div className={cn("flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border", cfg.bg, cfg.border)}>
                  <StatusIcon className={cn("h-5 w-5", cfg.color)} />
                </div>

                <div className="min-w-0">
                  <p className="font-bold text-sm text-foreground truncate">{exam.name}</p>
                  <p className="text-xs text-muted-foreground font-medium truncate">
                    {exam.subject} • {batch?.name || "10th Science Batch A"} •{" "}
                    {exam.date ? format(new Date(exam.date), "dd MMM yyyy") : "—"}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-6">
                <div className="hidden sm:flex flex-col items-end gap-0.5 text-xs">
                  <span className={cn("font-extrabold text-xs", cfg.color)}>{cfg.label}</span>
                  <span className="text-muted-foreground font-medium">
                    Max: <span className="font-bold text-foreground">{exam.maxMarks}</span> marks • {exam.duration} mins
                  </span>
                </div>

                {exam.status === "COMPLETED" && (
                  <div className="hidden md:block text-xs font-bold text-emerald-600 bg-emerald-500/10 px-3 py-1 rounded-full border border-emerald-500/20">
                    {exam.results?.length ?? 0} Marks Published
                  </div>
                )}

                <ChevronRight className="h-4 w-4 text-muted-foreground group-hover:text-foreground transition-colors shrink-0" />
              </div>
            </Link>
          );
        })}
      </div>

      {/* Create Exam Modal */}
      {showForm && (
        <>
          <div className="fixed inset-0 z-40 bg-black/40 backdrop-blur-xs" onClick={() => setShowForm(false)} />
          <div className="fixed left-1/2 top-1/2 z-50 -translate-x-1/2 -translate-y-1/2 w-full max-w-xl rounded-2xl border bg-background shadow-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b px-6 py-4">
              <h2 className="text-base font-bold">Schedule New Examination</h2>
              <button onClick={() => setShowForm(false)} className="rounded-xl p-1.5 hover:bg-accent text-muted-foreground">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="px-6 py-5">
              <ExamForm onSubmit={handleCreate} onCancel={() => setShowForm(false)} />
            </div>
          </div>
        </>
      )}
    </div>
  );
}
