"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Eye,
  ShieldAlert,
  ShieldCheck,
  Building2,
  RefreshCw,
  Clock,
  Copy,
  Check,
  Lock,
  Sparkles,
  ArrowRight,
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
}

interface DiagnosticResult {
  token: string;
  token_type: string;
  expires_in_seconds: number;
  tenant_id: string;
  impersonated_email: string;
  issued_for_super_admin: string;
}

export default function PlatformDiagnosticsPage() {
  const { t } = useLanguage();
  const [tenants, setTenants] = useState<PlatformTenant[]>([]);
  const [selectedTenantId, setSelectedTenantId] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [diagResult, setDiagResult] = useState<DiagnosticResult | null>(null);
  const [copied, setCopied] = useState(false);

  const fetchTenants = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/proxy/platform/tenants?limit=100", {
        headers: authHeaders(),
      });
      if (!res.ok) throw new Error("Failed to load tenants");
      const data = await res.json();
      setTenants(data.items ?? []);
      if (data.items && data.items.length > 0 && !selectedTenantId) {
        setSelectedTenantId(data.items[0].id);
      }
    } catch (err: any) {
      toast.error(err.message || "Failed to load tenants");
    } finally {
      setLoading(false);
    }
  }, [selectedTenantId]);

  useEffect(() => {
    fetchTenants();
  }, [fetchTenants]);

  const handleGenerateToken = async () => {
    if (!selectedTenantId) return;
    setGenerating(true);
    try {
      const res = await fetch(`/api/proxy/platform/impersonate/${selectedTenantId}`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ reason: "Super Admin diagnostic system troubleshooting" }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.message || data.detail || "Failed to generate diagnostic token");
      setDiagResult(data);
      toast.success("Diagnostic session token generated. Active for 15 minutes.");
    } catch (err: any) {
      toast.error(err.message || "Failed to generate diagnostic token");
    } finally {
      setGenerating(false);
    }
  };

  const handleCopyToken = () => {
    if (!diagResult?.token) return;
    navigator.clipboard.writeText(diagResult.token);
    setCopied(true);
    toast.success("Diagnostic JWT copied to clipboard");
    setTimeout(() => setCopied(false), 2500);
  };

  const selectedTenant = tenants.find((t) => t.id === selectedTenantId);

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="rounded-md bg-amber-600/10 p-1.5 text-amber-600 dark:text-amber-400">
              <Eye className="h-5 w-5" />
            </span>
            <h1 className="text-2xl font-bold tracking-tight">Diagnostic Impersonation Console</h1>
            <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/10 px-2.5 py-0.5 text-xs font-semibold text-amber-600">
              <Clock className="h-3 w-3" /> 15-Min Time-Limited
            </span>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Generate secure, time-limited diagnostic credentials to investigate tenant issues in read-only mode.
          </p>
        </div>

        <button
          onClick={() => fetchTenants()}
          disabled={loading}
          className="flex items-center gap-1.5 rounded-xl border bg-background px-3.5 py-2 text-xs font-semibold hover:bg-accent transition-colors shadow-xs"
        >
          <RefreshCw className={cn("h-3.5 w-3.5 text-muted-foreground", loading && "animate-spin")} />
          Refresh
        </button>
      </div>

      {/* Security Caution Alert */}
      <div className="rounded-2xl border border-amber-500/30 bg-amber-500/5 p-4 space-y-2">
        <div className="flex items-center gap-2 text-amber-700 dark:text-amber-300 font-bold text-xs">
          <ShieldAlert className="h-4 w-4" /> Strict Security & Auditing Policies
        </div>
        <p className="text-xs text-amber-700/90 dark:text-amber-400/90">
          • Diagnostic tokens strictly expire after <strong>15 minutes</strong> (900 seconds).
          <br />
          • Every diagnostic token generation and subsequent API action is logged with the Super Admin's identity in the immutable platform audit trail.
          <br />
          • Password changes or destructive tenant mutations are strictly prohibited under diagnostic sessions.
        </p>
      </div>

      {/* Generator Form */}
      <div className="rounded-2xl border bg-card p-6 shadow-xs space-y-5">
        <h2 className="text-base font-bold tracking-tight">Generate Tenant Diagnostic Token</h2>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="sm:col-span-2">
            <label className="text-xs font-semibold text-foreground block mb-1.5">Select Target Institute</label>
            <select
              value={selectedTenantId}
              onChange={(e) => setSelectedTenantId(e.target.value)}
              className="h-10 w-full rounded-xl border bg-background px-3 text-xs focus:outline-none focus:ring-1 focus:ring-amber-500 font-medium"
            >
              {tenants.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name} ({t.subdomain}) — {t.is_active ? "Active" : "Suspended"}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-end">
            <button
              onClick={handleGenerateToken}
              disabled={generating || !selectedTenantId}
              className="h-10 w-full rounded-xl bg-amber-600 text-xs font-semibold text-white hover:bg-amber-700 transition-colors shadow-xs flex items-center justify-center gap-2"
            >
              <Eye className="h-4 w-4" />
              {generating ? "Generating..." : "Generate Diagnostic Session"}
            </button>
          </div>
        </div>

        {diagResult && (
          <div className="rounded-xl border bg-muted/40 p-4 space-y-3 mt-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-emerald-700 dark:text-emerald-300 flex items-center gap-1.5">
                <ShieldCheck className="h-4 w-4 text-emerald-600" /> Active Diagnostic Session Issued
              </span>
              <span className="text-[11px] text-muted-foreground font-mono">
                Expires in {diagResult.expires_in_seconds / 60} minutes
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
              <div>
                <span className="text-muted-foreground block text-[11px]">Impersonated Account</span>
                <span className="font-semibold text-foreground">{diagResult.impersonated_email}</span>
              </div>
              <div>
                <span className="text-muted-foreground block text-[11px]">Issued For</span>
                <span className="font-semibold text-foreground">{diagResult.issued_for_super_admin}</span>
              </div>
            </div>

            <div>
              <span className="text-muted-foreground block text-[11px] mb-1">Diagnostic Bearer JWT</span>
              <div className="relative">
                <textarea
                  readOnly
                  rows={3}
                  value={diagResult.token}
                  className="w-full rounded-lg border bg-background p-2 font-mono text-[10px] text-muted-foreground focus:outline-none"
                />
                <button
                  onClick={handleCopyToken}
                  className="absolute right-2 bottom-3 flex items-center gap-1 rounded-md border bg-card px-2 py-1 text-[10px] font-semibold hover:bg-accent transition-colors"
                >
                  {copied ? <Check className="h-3 w-3 text-emerald-600" /> : <Copy className="h-3 w-3" />}
                  {copied ? "Copied" : "Copy Token"}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
