"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  Building2,
  Search,
  Filter,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Eye,
  ShieldCheck,
  Plus,
  Users,
  BookOpen,
  Calendar,
  Sliders,
  Layers,
  ArrowUpRight,
  UserCheck,
  Lock,
  Mail,
  Key,
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
  created_at: string;
  student_count: number;
  staff_count: number;
  batch_count: number;
  settings?: Record<string, any>;
}

export default function PlatformTenantsPage() {
  const { t } = useLanguage();
  const [tenants, setTenants] = useState<PlatformTenant[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [planFilter, setPlanFilter] = useState("all");
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  // Provisioning Modal State
  const [showProvisionModal, setShowProvisionModal] = useState(false);
  const [provisioning, setProvisioning] = useState(false);
  const [newName, setNewName] = useState("");
  const [newSubdomain, setNewSubdomain] = useState("");
  const [newPlan, setNewPlan] = useState("growth");
  const [newOwnerEmail, setNewOwnerEmail] = useState("");
  const [newOwnerPassword, setNewOwnerPassword] = useState("");
  const [newOwnerFirstName, setNewOwnerFirstName] = useState("Institute");
  const [newOwnerLastName, setNewOwnerLastName] = useState("Director");

  // Detail Modal State
  const [inspectingTenant, setInspectingTenant] = useState<PlatformTenant | null>(null);

  const fetchTenants = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set("page", String(page));
      params.set("limit", "20");
      if (search.trim()) params.set("search", search.trim());
      if (statusFilter !== "all") params.set("status", statusFilter);
      if (planFilter !== "all") params.set("plan", planFilter);

      const res = await fetch(`/api/proxy/platform/tenants?${params.toString()}`, {
        headers: authHeaders(),
      });
      if (!res.ok) throw new Error("Failed to load institutes");
      const data = await res.json();
      setTenants(data.items ?? []);
      setTotal(data.total ?? 0);
    } catch (err: any) {
      toast.error(err.message || "Failed to load institutes");
    } finally {
      setLoading(false);
    }
  }, [page, search, statusFilter, planFilter]);

  useEffect(() => {
    fetchTenants();
  }, [fetchTenants]);

  const handleToggleStatus = async (tenant: PlatformTenant) => {
    setActionLoading(tenant.id);
    const action = tenant.is_active ? "suspend" : "activate";
    try {
      const res = await fetch(`/api/proxy/platform/tenants/${tenant.id}/${action}`, {
        method: "POST",
        headers: authHeaders(),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.message || data.detail || `Failed to ${action} tenant`);
      toast.success(data.message || `Tenant ${action}d successfully`);
      fetchTenants();
    } catch (err: any) {
      toast.error(err.message || `Failed to ${action} tenant`);
    } finally {
      setActionLoading(null);
    }
  };

  const handleDiagnosticToken = async (tenant: PlatformTenant) => {
    setActionLoading(`diag-${tenant.id}`);
    try {
      const res = await fetch(`/api/proxy/platform/impersonate/${tenant.id}`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ reason: "Super Admin system verification" }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.message || data.detail || "Failed to initiate diagnostic mode");
      toast.success(`Diagnostic Session generated for ${tenant.name} (${tenant.subdomain}). Active for 15 minutes.`);
    } catch (err: any) {
      toast.error(err.message || "Failed to initiate diagnostic mode");
    } finally {
      setActionLoading(null);
    }
  };

  const handleProvisionTenant = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName || !newSubdomain || !newOwnerEmail || !newOwnerPassword) {
      toast.error("Please fill in all required fields.");
      return;
    }
    setProvisioning(true);
    try {
      const payload = {
        name: newName.trim(),
        subdomain: newSubdomain.trim().toLowerCase(),
        plan: newPlan,
        owner_email: newOwnerEmail.trim().toLowerCase(),
        owner_password: newOwnerPassword,
        owner_first_name: newOwnerFirstName.trim(),
        owner_last_name: newOwnerLastName.trim(),
      };

      const res = await fetch("/api/proxy/platform/tenants", {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.message || data.detail || "Failed to provision workspace");

      toast.success(data.message || "Institute provisioned successfully!");
      setShowProvisionModal(false);
      setNewName("");
      setNewSubdomain("");
      setNewOwnerEmail("");
      setNewOwnerPassword("");
      fetchTenants();
    } catch (err: any) {
      toast.error(err.message || "Failed to provision workspace");
    } finally {
      setProvisioning(false);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="rounded-md bg-violet-600/10 p-1.5 text-violet-600 dark:text-violet-400">
              <Building2 className="h-5 w-5" />
            </span>
            <h1 className="text-2xl font-bold tracking-tight">Institutes & Workspaces</h1>
            <span className="rounded-full bg-violet-500/10 px-2.5 py-0.5 text-xs font-semibold text-violet-600">
              {total} Total Workspaces
            </span>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Manage coaching institute tenant workspaces, direct provisioning, quota controls, and diagnostic access.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowProvisionModal(true)}
            className="flex items-center gap-1.5 rounded-xl bg-violet-600 px-3.5 py-2 text-xs font-semibold text-white hover:bg-violet-700 transition-colors shadow-xs"
          >
            <Plus className="h-3.5 w-3.5" />
            Provision New Institute
          </button>

          <button
            onClick={() => fetchTenants()}
            disabled={loading}
            className="flex items-center gap-1.5 rounded-xl border bg-background px-3.5 py-2 text-xs font-semibold hover:bg-accent transition-colors shadow-xs"
          >
            <RefreshCw className={cn("h-3.5 w-3.5 text-muted-foreground", loading && "animate-spin")} />
            Refresh
          </button>
        </div>
      </div>

      {/* Filter Controls */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border bg-card p-4 shadow-xs">
        <div className="relative flex-1 min-w-[240px] max-w-md">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search by institute name or subdomain..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="h-9 w-full rounded-xl border bg-background pl-9 pr-3 text-xs focus:outline-none focus:ring-1 focus:ring-violet-500"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            className="h-9 rounded-xl border bg-background px-3 text-xs focus:outline-none focus:ring-1 focus:ring-violet-500"
          >
            <option value="all">All Statuses</option>
            <option value="active">Active</option>
            <option value="suspended">Suspended</option>
          </select>

          <select
            value={planFilter}
            onChange={(e) => {
              setPlanFilter(e.target.value);
              setPage(1);
            }}
            className="h-9 rounded-xl border bg-background px-3 text-xs focus:outline-none focus:ring-1 focus:ring-violet-500"
          >
            <option value="all">All Plans</option>
            <option value="starter">Starter</option>
            <option value="growth">Growth</option>
            <option value="enterprise">Enterprise</option>
          </select>
        </div>
      </div>

      {/* Institutes Table */}
      <div className="rounded-2xl border bg-card shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="border-b bg-muted/40 text-muted-foreground font-medium">
              <tr>
                <th className="py-3 px-4">Institute</th>
                <th className="py-3 px-4">Subdomain</th>
                <th className="py-3 px-4">Plan</th>
                <th className="py-3 px-4 text-center">Students</th>
                <th className="py-3 px-4 text-center">Staff</th>
                <th className="py-3 px-4 text-center">Batches</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {tenants.length > 0 ? (
                tenants.map((t) => (
                  <tr key={t.id} className="hover:bg-muted/20 transition-colors">
                    <td className="py-3.5 px-4">
                      <div>
                        <span className="font-bold text-foreground text-sm block">{t.name}</span>
                        <span className="text-[11px] text-muted-foreground">
                          ID: <span className="font-mono">{t.id.slice(0, 8)}...</span>
                        </span>
                      </div>
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="font-mono text-[11px] rounded bg-muted px-2 py-0.5 font-semibold text-foreground">
                        {t.subdomain}
                      </span>
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="inline-flex items-center rounded-full bg-violet-500/10 px-2.5 py-0.5 text-[11px] font-semibold text-violet-600 uppercase">
                        {t.plan}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-center font-medium">{t.student_count}</td>
                    <td className="py-3.5 px-4 text-center font-medium">{t.staff_count}</td>
                    <td className="py-3.5 px-4 text-center font-medium">{t.batch_count}</td>
                    <td className="py-3.5 px-4">
                      {t.is_active ? (
                        <span className="inline-flex items-center gap-1 text-emerald-600 font-semibold text-[11px]">
                          <CheckCircle2 className="h-3.5 w-3.5" /> Active
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-rose-600 font-semibold text-[11px]">
                          <AlertCircle className="h-3.5 w-3.5" /> Suspended
                        </span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => setInspectingTenant(t)}
                          className="rounded-lg border bg-background px-2.5 py-1 text-[11px] font-semibold hover:bg-accent transition-colors shadow-xs"
                          title="Inspect Details"
                        >
                          Details
                        </button>
                        <button
                          onClick={() => handleToggleStatus(t)}
                          disabled={actionLoading === t.id}
                          className={cn(
                            "rounded-lg px-2.5 py-1 text-[11px] font-semibold transition-colors border",
                            t.is_active
                              ? "border-rose-200 text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/20"
                              : "border-emerald-200 text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-950/20"
                          )}
                        >
                          {actionLoading === t.id ? "Updating..." : t.is_active ? "Suspend" : "Activate"}
                        </button>
                        <button
                          onClick={() => handleDiagnosticToken(t)}
                          disabled={actionLoading === `diag-${t.id}`}
                          className="flex items-center gap-1 rounded-lg border bg-background px-2.5 py-1 text-[11px] font-semibold hover:bg-accent transition-colors shadow-xs"
                          title="Generate 15-minute diagnostic session"
                        >
                          <Eye className="h-3 w-3 text-muted-foreground" />
                          {actionLoading === `diag-${t.id}` ? "..." : "Diagnostic"}
                        </button>
                        <Link
                          href={`/platform/quotas?tenantId=${t.id}`}
                          className="flex items-center gap-1 rounded-lg border bg-background px-2 py-1 text-[11px] font-semibold hover:bg-accent transition-colors shadow-xs"
                          title="Configure Quotas"
                        >
                          <Sliders className="h-3 w-3 text-muted-foreground" />
                        </Link>
                      </div>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-muted-foreground">
                    {loading ? "Loading institute workspaces..." : "No institutes found matching the selected criteria."}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Provision Tenant Modal */}
      {showProvisionModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="w-full max-w-lg rounded-2xl border bg-card p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b pb-3">
              <h3 className="font-bold text-base flex items-center gap-2">
                <Building2 className="h-5 w-5 text-violet-600" /> Provision New Coaching Workspace
              </h3>
              <button
                onClick={() => setShowProvisionModal(false)}
                className="rounded-lg p-1 text-muted-foreground hover:bg-accent"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleProvisionTenant} className="space-y-3.5 text-xs">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="font-semibold block mb-1">Institute Name *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Apex IIT Academy"
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    className="h-9 w-full rounded-xl border bg-background px-3 text-xs focus:outline-none focus:ring-1 focus:ring-violet-500"
                  />
                </div>
                <div>
                  <label className="font-semibold block mb-1">Subdomain Slug *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. apex"
                    value={newSubdomain}
                    onChange={(e) => setNewSubdomain(e.target.value.toLowerCase())}
                    className="h-9 w-full rounded-xl border bg-background px-3 text-xs font-mono focus:outline-none focus:ring-1 focus:ring-violet-500"
                  />
                </div>
              </div>

              <div>
                <label className="font-semibold block mb-1">Initial Subscription Tier</label>
                <select
                  value={newPlan}
                  onChange={(e) => setNewPlan(e.target.value)}
                  className="h-9 w-full rounded-xl border bg-background px-3 text-xs focus:outline-none focus:ring-1 focus:ring-violet-500"
                >
                  <option value="starter">Starter Plan (Up to 100 students)</option>
                  <option value="growth">Growth Plan (Up to 500 students, AI Copilot)</option>
                  <option value="enterprise">Enterprise Plan (Up to 5,000 students, Multi-branch)</option>
                </select>
              </div>

              <div className="border-t pt-3 space-y-3">
                <span className="font-bold block text-foreground">Root Owner Account Setup</span>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="font-semibold block mb-1">Owner Email *</label>
                    <input
                      type="email"
                      required
                      placeholder="owner@institute.com"
                      value={newOwnerEmail}
                      onChange={(e) => setNewOwnerEmail(e.target.value)}
                      className="h-9 w-full rounded-xl border bg-background px-3 text-xs focus:outline-none focus:ring-1 focus:ring-violet-500"
                    />
                  </div>
                  <div>
                    <label className="font-semibold block mb-1">Owner Initial Password *</label>
                    <input
                      type="password"
                      required
                      minLength={8}
                      placeholder="Min 8 characters"
                      value={newOwnerPassword}
                      onChange={(e) => setNewOwnerPassword(e.target.value)}
                      className="h-9 w-full rounded-xl border bg-background px-3 text-xs focus:outline-none focus:ring-1 focus:ring-violet-500"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="font-semibold block mb-1">First Name</label>
                    <input
                      type="text"
                      value={newOwnerFirstName}
                      onChange={(e) => setNewOwnerFirstName(e.target.value)}
                      className="h-9 w-full rounded-xl border bg-background px-3 text-xs focus:outline-none focus:ring-1 focus:ring-violet-500"
                    />
                  </div>
                  <div>
                    <label className="font-semibold block mb-1">Last Name</label>
                    <input
                      type="text"
                      value={newOwnerLastName}
                      onChange={(e) => setNewOwnerLastName(e.target.value)}
                      className="h-9 w-full rounded-xl border bg-background px-3 text-xs focus:outline-none focus:ring-1 focus:ring-violet-500"
                    />
                  </div>
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t">
                <button
                  type="button"
                  onClick={() => setShowProvisionModal(false)}
                  className="rounded-xl border px-4 py-2 text-xs font-semibold hover:bg-accent"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={provisioning}
                  className="rounded-xl bg-violet-600 px-5 py-2 text-xs font-semibold text-white hover:bg-violet-700 transition-colors shadow-xs"
                >
                  {provisioning ? "Provisioning..." : "Provision Workspace"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Tenant Detail Modal */}
      {inspectingTenant && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="w-full max-w-xl rounded-2xl border bg-card p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b pb-3">
              <div>
                <h3 className="font-bold text-base">{inspectingTenant.name}</h3>
                <span className="font-mono text-xs text-muted-foreground">{inspectingTenant.subdomain}.thecoachgenie.in</span>
              </div>
              <button
                onClick={() => setInspectingTenant(null)}
                className="rounded-lg p-1 text-muted-foreground hover:bg-accent"
              >
                ✕
              </button>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="rounded-xl bg-muted/40 p-3 border space-y-1">
                <span className="text-muted-foreground block text-[11px]">Workspace Status</span>
                <span className="font-bold text-foreground">
                  {inspectingTenant.is_active ? "Active" : "Suspended"}
                </span>
              </div>
              <div className="rounded-xl bg-violet-500/10 p-3 border border-violet-500/20 space-y-1">
                <span className="text-violet-700 dark:text-violet-300 block text-[11px]">Subscription Plan</span>
                <span className="font-bold text-violet-600 uppercase">{inspectingTenant.plan}</span>
              </div>
              <div className="rounded-xl bg-muted/40 p-3 border space-y-1">
                <span className="text-muted-foreground block text-[11px]">Enrolled Students</span>
                <span className="font-bold text-foreground">{inspectingTenant.student_count}</span>
              </div>
              <div className="rounded-xl bg-muted/40 p-3 border space-y-1">
                <span className="text-muted-foreground block text-[11px]">Staff / Faculty</span>
                <span className="font-bold text-foreground">{inspectingTenant.staff_count}</span>
              </div>
            </div>

            <div>
              <span className="font-semibold text-xs block mb-1">Configuration Settings JSON:</span>
              <pre className="rounded-xl border bg-muted/60 p-3 text-[11px] font-mono overflow-auto max-h-40">
                {JSON.stringify(inspectingTenant.settings || {}, null, 2)}
              </pre>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t">
              <Link
                href={`/platform/quotas?tenantId=${inspectingTenant.id}`}
                className="rounded-xl bg-violet-600 px-4 py-2 text-xs font-semibold text-white hover:bg-violet-700"
              >
                Configure Quotas
              </Link>
              <button
                onClick={() => setInspectingTenant(null)}
                className="rounded-xl border px-4 py-2 text-xs font-semibold hover:bg-accent"
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
