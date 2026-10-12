"use client";

import { useState, useEffect, useCallback } from "react";
import { format } from "date-fns";
import {
  ShieldCheck,
  Search,
  Filter,
  RefreshCw,
  Clock,
  User,
  Activity,
  FileText,
  Building2,
  Terminal,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { authHeaders } from "@/lib/auth-headers";
import { useLanguage } from "@/components/providers/LanguageProvider";

interface AuditLogEntry {
  id: string;
  tenant_id: string;
  actor_id: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  ip_address: string | null;
  metadata_: Record<string, any> | null;
  created_at: string;
}

export default function PlatformAuditLogsPage() {
  const { t } = useLanguage();
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [actionFilter, setActionFilter] = useState("all");
  const [selectedLog, setSelectedLog] = useState<AuditLogEntry | null>(null);

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set("page", String(page));
      params.set("limit", "25");
      if (actionFilter !== "all") params.set("action", actionFilter);

      const res = await fetch(`/api/proxy/platform/audit-logs?${params.toString()}`, {
        headers: authHeaders(),
      });
      if (!res.ok) throw new Error("Failed to load platform audit logs");
      const data = await res.json();
      setLogs(data.items ?? []);
      setTotal(data.total ?? 0);
    } catch (err: any) {
      toast.error(err.message || "Failed to load audit logs");
    } finally {
      setLoading(false);
    }
  }, [page, actionFilter]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="rounded-md bg-violet-600/10 p-1.5 text-violet-600 dark:text-violet-400">
              <ShieldCheck className="h-5 w-5" />
            </span>
            <h1 className="text-2xl font-bold tracking-tight">Platform Audit Logs</h1>
            <span className="rounded-full bg-violet-500/10 px-2.5 py-0.5 text-xs font-semibold text-violet-600">
              {total} Total Audit Records
            </span>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Immutable platform governance log recording all Super Admin modifications, tier changes, and diagnostic access.
          </p>
        </div>

        <button
          onClick={() => fetchLogs()}
          disabled={loading}
          className="flex items-center gap-1.5 rounded-xl border bg-background px-3.5 py-2 text-xs font-semibold hover:bg-accent transition-colors shadow-xs"
        >
          <RefreshCw className={cn("h-3.5 w-3.5 text-muted-foreground", loading && "animate-spin")} />
          Refresh
        </button>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border bg-card p-4 shadow-xs">
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <span className="text-xs font-semibold text-foreground">Action Filter:</span>
          <select
            value={actionFilter}
            onChange={(e) => {
              setActionFilter(e.target.value);
              setPage(1);
            }}
            className="h-8 rounded-lg border bg-background px-3 text-xs focus:outline-none focus:ring-1 focus:ring-violet-500"
          >
            <option value="all">All Platform Actions</option>
            <option value="UPDATE_TENANT_PLAN">UPDATE_TENANT_PLAN</option>
            <option value="SUSPEND_TENANT">SUSPEND_TENANT</option>
            <option value="ACTIVATE_TENANT">ACTIVATE_TENANT</option>
            <option value="UPDATE_TENANT_QUOTAS">UPDATE_TENANT_QUOTAS</option>
            <option value="DIAGNOSTIC_IMPERSONATION">DIAGNOSTIC_IMPERSONATION</option>
          </select>
        </div>

        <span className="text-xs text-muted-foreground">Showing Page {page}</span>
      </div>

      {/* Logs Table */}
      <div className="rounded-2xl border bg-card shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="border-b bg-muted/40 text-muted-foreground font-medium">
              <tr>
                <th className="py-3 px-4">Timestamp</th>
                <th className="py-3 px-4">Action</th>
                <th className="py-3 px-4">Entity Type</th>
                <th className="py-3 px-4">Tenant ID</th>
                <th className="py-3 px-4">IP Address</th>
                <th className="py-3 px-4 text-right">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {logs.length > 0 ? (
                logs.map((log) => (
                  <tr key={log.id} className="hover:bg-muted/20 transition-colors">
                    <td className="py-3 px-4 font-mono text-[11px] text-muted-foreground whitespace-nowrap">
                      {log.created_at ? format(new Date(log.created_at), "yyyy-MM-dd HH:mm:ss") : "—"}
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={cn(
                          "font-mono font-semibold px-2 py-0.5 rounded text-[11px] inline-block",
                          log.action.includes("SUSPEND")
                            ? "bg-rose-500/10 text-rose-600"
                            : log.action.includes("ACTIVATE")
                            ? "bg-emerald-500/10 text-emerald-600"
                            : log.action.includes("DIAGNOSTIC")
                            ? "bg-amber-500/10 text-amber-600"
                            : "bg-violet-500/10 text-violet-600"
                        )}
                      >
                        {log.action}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-medium capitalize">{log.entity_type}</td>
                    <td className="py-3 px-4 font-mono text-[11px] text-muted-foreground">
                      {log.tenant_id.slice(0, 8)}...
                    </td>
                    <td className="py-3 px-4 font-mono text-[11px] text-muted-foreground">{log.ip_address || "—"}</td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => setSelectedLog(log)}
                        className="rounded-md border bg-background px-2.5 py-1 text-[11px] font-medium hover:bg-accent transition-colors"
                      >
                        View JSON
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-muted-foreground">
                    {loading ? "Loading platform audit records..." : "No platform audit records found."}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* JSON Modal */}
      {selectedLog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="w-full max-w-xl rounded-2xl border bg-card p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b pb-3">
              <h3 className="font-bold text-sm">Audit Event Payload: {selectedLog.action}</h3>
              <button
                onClick={() => setSelectedLog(null)}
                className="rounded-lg p-1 text-muted-foreground hover:bg-accent"
              >
                ✕
              </button>
            </div>

            <div className="space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Log ID:</span>
                <span className="font-mono">{selectedLog.id}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Actor ID:</span>
                <span className="font-mono">{selectedLog.actor_id || "System"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Created At:</span>
                <span className="font-mono">{selectedLog.created_at}</span>
              </div>
            </div>

            <div>
              <span className="text-xs font-semibold block mb-1">Metadata JSON:</span>
              <pre className="rounded-xl border bg-muted/60 p-3 text-[11px] font-mono overflow-auto max-h-48">
                {JSON.stringify(selectedLog.metadata_ || {}, null, 2)}
              </pre>
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setSelectedLog(null)}
                className="rounded-xl bg-violet-600 px-4 py-2 text-xs font-semibold text-white hover:bg-violet-700 transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
