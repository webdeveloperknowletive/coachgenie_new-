"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import {
  Plus,
  LayoutGrid,
  List,
  X,
  RefreshCw,
  Search,
  Sparkles,
  Users,
  CheckCircle2,
  TrendingUp,
  UserCheck,
  Filter,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { useLeadStore } from "@/lib/stores/leads.store";
import { LeadTable } from "@/components/leads/LeadTable";
import { LeadKanban } from "@/components/leads/LeadKanban";
import { LeadDrawer } from "@/components/leads/LeadDrawer";
import { LeadForm, type LeadFormValues } from "@/components/leads/LeadForm";
import type { Lead, LeadStage, LeadSource } from "@/lib/types/lead";
import { STAGE_CONFIG, STAGES, SOURCE_LABELS } from "@/lib/constants/leads";
import { authHeaders } from "@/lib/auth-headers";
import { useLanguage } from "@/components/providers/LanguageProvider";

const API = "/api/proxy";
type View = "table" | "kanban";

/** Map raw API lead object → frontend Lead shape */
function mapLead(raw: any): Lead {
  const activities = (raw.activities ?? []).map((a: any) => ({
    id: String(a.id || `a-${Date.now()}`),
    type: String(a.type || "NOTE").toUpperCase(),
    content: a.content || a.description || "",
    createdAt: a.created_at || a.createdAt || new Date().toISOString(),
    createdBy: a.created_by || a.createdBy || "Staff Counselor",
  }));

  return {
    id: String(raw.id),
    name: raw.full_name ?? raw.name ?? "",
    email: raw.email ?? "",
    phone: raw.phone ?? "",
    parentContactNumber: raw.parent_contact_number ?? "",
    schoolName: raw.school_name ?? "",
    source: (raw.source?.toUpperCase() as LeadSource) ?? "WEBSITE",
    stage: (raw.status?.toUpperCase() as LeadStage) ?? "NEW",
    subject: raw.interested_course ?? raw.subject ?? "",
    grade: raw.grade ?? "",
    parentName: raw.parent_name ?? "",
    notes: raw.notes ?? "",
    createdAt: raw.created_at ?? new Date().toISOString(),
    updatedAt: raw.updated_at ?? new Date().toISOString(),
    activities,
    tags: raw.tags ?? [],
    boardName: raw.board_name ?? "",
    batchId: raw.batch_id ?? "",
    batchName: raw.batch_name ?? raw.batch?.name ?? "",
    assignedTo: raw.assigned_to ?? "",
  };
}

export interface Batch {
  id: string;
  name: string;
  subjects: string[];
}

const DEFAULT_SEED_LEADS: Lead[] = [];

export default function LeadsPage() {
  const { t } = useLanguage();
  const { leads, setLeads, addLead, deleteLead, updateStage } = useLeadStore();

  const [view, setView] = useState<View>("table");
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [stageFilter, setStageFilter] = useState<LeadStage | "ALL">("ALL");
  const [sourceFilter, setSourceFilter] = useState<LeadSource | "ALL">("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(true);

  const [batches, setBatches] = useState<Batch[]>([]);
  const [batchesLoading, setBatchesLoading] = useState(false);

  const fetchLeads = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/leads/`, { headers: authHeaders() }).catch(() => null);
      if (res && res.ok) {
        const json = await res.json();
        const raw: any[] = Array.isArray(json) ? json : json.data ?? json.items ?? [];
        if (raw.length > 0) {
          setLeads(raw.map(mapLead));
        } else {
          setLeads([]);
        }
      } else {
        setLeads([]);
      }
    } catch {
      // keep current state
    } finally {
      setLoading(false);
    }
  }, [setLeads, leads.length]);

  const fetchBatches = useCallback(async () => {
    setBatchesLoading(true);
    try {
      const res = await fetch(`${API}/batches/`, { headers: authHeaders() }).catch(() => null);
      if (res && res.ok) {
        const json = await res.json();
        const raw: any[] = Array.isArray(json) ? json : json.data ?? json.items ?? [];
        setBatches(raw.map((b) => ({ id: String(b.id), name: b.name ?? b.batch_name ?? "", subjects: b.subjects ?? [] })));
      }
    } catch {
      // quiet fallback
    } finally {
      setBatchesLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchLeads();
    fetchBatches();
  }, [fetchLeads, fetchBatches]);

  // Filtered Leads
  const filteredLeads = useMemo(() => {
    return leads.filter((l) => {
      const matchStage = stageFilter === "ALL" || l.stage === stageFilter;
      const matchSource = sourceFilter === "ALL" || l.source === sourceFilter;
      const matchSearch =
        !searchQuery ||
        l.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        l.phone.includes(searchQuery) ||
        l.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
        l.schoolName.toLowerCase().includes(searchQuery.toLowerCase());

      return matchStage && matchSource && matchSearch;
    });
  }, [leads, stageFilter, sourceFilter, searchQuery]);

  // Executive KPI Stats
  const kpiStats = useMemo(() => {
    const totalCount = leads.length;
    const enrolledCount = leads.filter((l) => l.stage === "ENROLLED").length;
    const activeCount = leads.filter((l) => l.stage !== "ENROLLED" && l.stage !== "LOST").length;
    const conversionPct = totalCount > 0 ? Math.round((enrolledCount / totalCount) * 100) : 0;

    return {
      totalCount,
      enrolledCount,
      activeCount,
      conversionPct,
    };
  }, [leads]);

  // Create Lead
  async function handleCreate(data: LeadFormValues) {
    try {
      const payload = {
        full_name: data.name,
        parent_name: data.parentName,
        email: data.email,
        phone: data.phone,
        grade: data.grade,
        parent_contact_number: data.parentContactNumber,
        school_name: data.schoolName,
        source: data.source.toLowerCase(),
        interested_course: data.subject,
        notes: data.notes ?? "",
        board_name: data.boardName ?? "",
        batch_id: data.batchId || null,
        subjects: data.subjects ?? [],
      };

      const res = await fetch(`${API}/leads/`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        const errorMsg = Array.isArray(errJson?.detail)
          ? errJson.detail.map((e: any) => e.msg?.replace(/^Value error,\s*/i, "") || e.message || JSON.stringify(e)).join(", ")
          : (errJson?.detail ?? errJson?.message ?? "Failed to create lead");
        toast.error(errorMsg);
        return;
      }

      const json = await res.json();
      const created = json.data ?? json;
      addLead(mapLead(created));

      toast.success("New lead created successfully!");
      setShowForm(false);
    } catch (err: any) {
      toast.error(err.message || "Failed to create lead");
    }
  }

  // Delete Lead
  async function handleDelete(id: string) {
    try {
      await fetch(`${API}/leads/${id}`, { method: "DELETE", headers: authHeaders() }).catch(() => null);
    } catch {
      // quiet fallback
    }
    deleteLead(id);
    toast.success("Lead record removed");
    if (selectedLead?.id === id) setSelectedLead(null);
  }

  // Stage change
  async function handleStageChange(id: string, stage: LeadStage) {
    updateStage(id, stage);
    try {
      await fetch(`${API}/leads/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({ status: stage.toLowerCase() }),
      }).catch(() => null);
    } catch {
      // quiet fallback
    }
  }

  return (
    <div className="space-y-6 max-w-7xl">
      {/* 🚀 Header Toolbar */}
      <div className="flex flex-wrap items-start justify-between gap-4 border-b pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            {t("Leads & Admissions Pipeline")}
            <span className="inline-flex items-center gap-1 rounded-full bg-blue-500/10 px-2.5 py-0.5 text-xs font-semibold text-blue-600">
              <Sparkles className="h-3 w-3" /> {t("CRM Funnel")}
            </span>
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            {t("Manage student enquiries, demo session bookings, parent follow-ups, and admission conversions")}
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={fetchLeads}
            disabled={loading}
            aria-label="Refresh leads list"
            className="rounded-xl border p-2 text-muted-foreground hover:bg-accent hover:text-foreground transition-colors shadow-xs"
            title={t("Refresh list")}
          >
            <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
          </button>

          {/* View Switcher */}
          <div className="flex rounded-xl border bg-card p-1 shadow-xs">
            {(["table", "kanban"] as View[]).map((v) => (
              <button
                key={v}
                onClick={() => setView(v)}
                aria-label={`Switch to ${v} view`}
                className={cn(
                  "flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg transition-all capitalize",
                  view === v ? "bg-primary text-primary-foreground shadow-xs" : "text-muted-foreground hover:text-foreground"
                )}
              >
                {v === "table" ? <List className="h-3.5 w-3.5" /> : <LayoutGrid className="h-3.5 w-3.5" />}
                {v === "table" ? t("Table") : t("Kanban")}
              </button>
            ))}
          </div>

          <button
            data-testid="add-lead-btn"
            onClick={() => setShowForm(true)}
            aria-label="Add new lead"
            className="flex items-center gap-1.5 rounded-xl bg-violet-600 px-4 py-2 text-xs font-semibold text-white hover:bg-violet-700 transition-all shadow-sm"
          >
            <Plus className="h-4 w-4" /> {t("Add New Lead")}
          </button>
        </div>
      </div>

      {/* 📊 KPI Metric Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-2xl border bg-card p-5 shadow-sm space-y-1">
          <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{t("Total Inquiries")}</span>
          <p className="text-3xl font-extrabold text-foreground tracking-tight">{kpiStats.totalCount}</p>
          <p className="text-xs text-muted-foreground">{t("Total logged leads")}</p>
        </div>

        <div className="rounded-2xl border bg-card p-5 shadow-sm space-y-1">
          <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{t("Active Pipeline")}</span>
          <p className="text-3xl font-extrabold text-blue-600 tracking-tight">{kpiStats.activeCount}</p>
          <p className="text-xs text-muted-foreground">{t("Under active follow-up")}</p>
        </div>

        <div className="rounded-2xl border bg-card p-5 shadow-sm space-y-1">
          <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{t("Converted Admissions")}</span>
          <p className="text-3xl font-extrabold text-emerald-600 tracking-tight">{kpiStats.enrolledCount}</p>
          <p className="text-xs text-emerald-700 dark:text-emerald-300 font-semibold">{t("Successfully enrolled")}</p>
        </div>

        <div className="rounded-2xl border bg-card p-5 shadow-sm space-y-1">
          <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{t("Conversion Rate")}</span>
          <p className="text-3xl font-extrabold text-amber-600 tracking-tight">{kpiStats.conversionPct}%</p>
          <p className="text-xs text-muted-foreground">{t("Enquiry to Student ratio")}</p>
        </div>
      </div>

      {/* 🔍 Search & Stage Filters Bar */}
      <div className="rounded-2xl border bg-card p-4 shadow-sm space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          {/* Search Box */}
          <div className="relative min-w-[240px] max-w-xs flex-1">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              placeholder={t("Search lead name, phone, email, or school...")}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              aria-label="Search lead name, phone, email, or school"
              className="h-9 w-full rounded-xl border bg-background pl-9 pr-3 text-xs font-medium focus:ring-2 focus:ring-primary outline-none"
            />
          </div>

          {/* Source Filter */}
          <div className="flex items-center gap-2">
            <label htmlFor="lead-source-select" className="text-xs font-semibold text-muted-foreground">{t("Source:")}</label>
            <select
              id="lead-source-select"
              value={sourceFilter}
              onChange={(e) => setSourceFilter(e.target.value as any)}
              aria-label="Filter leads by source"
              className="h-9 rounded-xl border bg-background px-3 text-xs font-medium focus:ring-2 focus:ring-primary outline-none"
            >
              <option value="ALL">{t("All Sources")}</option>
              <option value="WEBSITE">{t("Website")}</option>
              <option value="REFERRAL">{t("Referral")}</option>
              <option value="SOCIAL_MEDIA">{t("Social Media")}</option>
              <option value="WALK_IN">{t("Walk-in")}</option>
              <option value="PHONE">{t("Phone Call")}</option>
            </select>
          </div>
        </div>

        {/* Stage Pills */}
        <div className="flex flex-wrap gap-2 pt-2 border-t">
          <button
            onClick={() => setStageFilter("ALL")}
            className={cn(
              "rounded-xl border px-3 py-1 text-xs font-semibold transition-all",
              stageFilter === "ALL" ? "bg-foreground text-background shadow-xs" : "hover:bg-accent text-muted-foreground"
            )}
          >
            {t("All")} ({leads.length})
          </button>
          {STAGES.map((s) => {
            const count = leads.filter((l) => l.stage === s).length;
            const cfg = STAGE_CONFIG[s];
            return (
              <button
                key={s}
                onClick={() => setStageFilter(stageFilter === s ? "ALL" : s)}
                className={cn(
                  "rounded-xl border px-3 py-1 text-xs font-semibold transition-all",
                  stageFilter === s ? `${cfg.color} ${cfg.bg} ${cfg.border} shadow-xs` : "hover:bg-accent text-muted-foreground"
                )}
              >
                {t(cfg.label)} ({count})
              </button>
            );
          })}
        </div>
      </div>

      {/* 🚀 Loading Skeleton */}
      {loading ? (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-16 rounded-2xl bg-card border animate-pulse" />
          ))}
        </div>
      ) : (
        /* 📋 Main View: Table vs Kanban */
        filteredLeads.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 gap-2 rounded-2xl border border-dashed bg-card text-center">
            <Users className="h-8 w-8 text-muted-foreground/40" />
            <p className="font-semibold text-sm">{t("No leads match your filter selection.")}</p>
            <p className="text-xs text-muted-foreground">{t("Try adjusting your search term or stage filter.")}</p>
          </div>
        ) : view === "table" ? (
          <LeadTable leads={filteredLeads} onView={setSelectedLead} onDelete={handleDelete} />
        ) : (
          <LeadKanban leads={filteredLeads} onCardClick={setSelectedLead} onStageChange={handleStageChange} />
        )
      )}

      {/* Lead Detail Drawer */}
      {selectedLead && <LeadDrawer lead={selectedLead} onClose={() => setSelectedLead(null)} />}

      {/* Create Lead Modal */}
      {showForm && (
        <>
          <div className="fixed inset-0 z-40 bg-black/40 backdrop-blur-xs" onClick={() => setShowForm(false)} aria-hidden="true" />
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="add-lead-dialog-title"
            data-testid="add-lead-modal"
            className="fixed left-1/2 top-1/2 z-50 -translate-x-1/2 -translate-y-1/2 w-full max-w-2xl rounded-2xl border bg-background shadow-2xl max-h-[90vh] flex flex-col"
          >
            <div className="flex items-center justify-between border-b px-6 py-4 shrink-0">
              <h2 id="add-lead-dialog-title" className="text-base font-bold">
                {t("Add New Student Inquiry / Lead")}
              </h2>
              <button onClick={() => setShowForm(false)} className="rounded-xl p-1.5 hover:bg-accent text-muted-foreground" aria-label="Close">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="px-6 py-5 overflow-y-auto">
              <LeadForm onSubmit={handleCreate} onCancel={() => setShowForm(false)} batches={batches} batchesLoading={batchesLoading} />
            </div>
          </div>
        </>
      )}
    </div>
  );
}