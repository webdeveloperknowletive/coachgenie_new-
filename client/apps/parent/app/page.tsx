"use client";

import { useState, useEffect, useCallback } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

const tabs = ["Overview", "Attendance", "Academics", "Fees", "Notifications"] as const;
type Tab = typeof tabs[number];

interface ChildItem {
  id: string;
  first_name: string;
  last_name: string;
  enrollment_no: string;
  current_class?: string;
  photo_url?: string;
  school_name?: string;
  target_exam?: string;
}

interface AttendanceSummary {
  total_classes: number;
  present: number;
  absent: number;
  late: number;
  percentage: number;
}

interface ExamResultItem {
  id: string;
  exam_id: string;
  marks_obtained: number;
  grade?: string;
  rank_in_batch?: number;
  remarks?: string;
}

interface InvoiceItem {
  id: string;
  invoice_no: string;
  amount_due: number;
  amount_paid: number;
  due_date: string;
  status: string;
}

interface FeeSummary {
  total_due: number;
  total_paid: number;
  balance: number;
  invoices: InvoiceItem[];
}

interface NotificationItem {
  id: string;
  subject?: string;
  body: string;
  channel: string;
  read_at?: string | null;
  created_at: string;
}

interface ParentDashboardData {
  children: ChildItem[];
  selected_child: ChildItem | null;
  attendance: AttendanceSummary;
  fees: FeeSummary;
  exams: ExamResultItem[];
  notifications: NotificationItem[];
}

export default function ParentPortalHome() {
  const [token, setToken] = useState<string | null>(null);
  const [subdomain, setSubdomain] = useState<string>("demo");
  const [activeTab, setActiveTab] = useState<Tab>("Overview");

  // Login form state
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loginLoading, setLoginLoading] = useState(false);
  const [loginError, setLoginError] = useState<string | null>(null);

  // Multi-child switcher state
  const [children, setChildren] = useState<ChildItem[]>([]);
  const [selectedChildId, setSelectedChildId] = useState<string | null>(null);

  // Data fetching state
  const [dashboard, setDashboard] = useState<ParentDashboardData | null>(null);
  const [loading, setLoading] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);

  // Initialize from localStorage
  useEffect(() => {
    const savedToken = localStorage.getItem("cg_parent_token");
    const savedSubdomain = localStorage.getItem("cg_parent_subdomain") || "demo";
    if (savedToken) {
      setToken(savedToken);
      setSubdomain(savedSubdomain);
    }
  }, []);

  const fetchChildrenList = useCallback(async (authToken: string, tenantSub: string) => {
    try {
      const res = await fetch(`${API_BASE}/parents/children`, {
        headers: {
          Authorization: `Bearer ${authToken}`,
          "X-Tenant-Subdomain": tenantSub,
        },
      });

      if (res.status === 401 || res.status === 403) {
        localStorage.removeItem("cg_parent_token");
        setToken(null);
        setFetchError("Session expired. Please sign in again.");
        return;
      }

      const json = await res.json();
      if (res.ok && json.success) {
        const list: ChildItem[] = json.data || [];
        setChildren(list);
        if (list.length > 0 && !selectedChildId) {
          setSelectedChildId(list[0].id);
        }
      }
    } catch (err) {
      console.error("Failed to load children list:", err);
    }
  }, [selectedChildId]);

  const fetchDashboardData = useCallback(
    async (authToken: string, tenantSub: string, childId: string | null) => {
      setLoading(true);
      setFetchError(null);
      try {
        const url = childId
          ? `${API_BASE}/parents/portal/dashboard?student_id=${childId}`
          : `${API_BASE}/parents/portal/dashboard`;

        const res = await fetch(url, {
          headers: {
            Authorization: `Bearer ${authToken}`,
            "X-Tenant-Subdomain": tenantSub,
          },
        });

        if (res.status === 401 || res.status === 403) {
          localStorage.removeItem("cg_parent_token");
          setToken(null);
          setFetchError("Access denied or session expired. Please sign in.");
          return;
        }

        const json = await res.json();
        if (!res.ok || !json.success) {
          throw new Error(json.message || "Failed to load parent dashboard");
        }
        setDashboard(json.data);
        if (json.data.children && json.data.children.length > 0) {
          setChildren(json.data.children);
        }
      } catch (err: any) {
        setFetchError(err.message || "Network error fetching child data");
      } finally {
        setLoading(false);
      }
    },
    []
  );

  useEffect(() => {
    if (token) {
      fetchChildrenList(token, subdomain);
      fetchDashboardData(token, subdomain, selectedChildId);
    }
  }, [token, subdomain, selectedChildId, fetchChildrenList, fetchDashboardData]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginLoading(true);
    setLoginError(null);

    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Tenant-Subdomain": subdomain,
        },
        body: JSON.stringify({ email, password }),
      });

      const json = await res.json();
      if (!res.ok || !json.access_token) {
        throw new Error(json.detail || json.message || "Invalid credentials");
      }

      const userRole = json.user?.role || json.role;
      if (userRole !== "parent") {
        throw new Error("This portal is restricted to Parents. Please use the appropriate portal.");
      }

      const accessToken = json.access_token;
      localStorage.setItem("cg_parent_token", accessToken);
      localStorage.setItem("cg_parent_subdomain", subdomain);
      setToken(accessToken);
    } catch (err: any) {
      setLoginError(err.message || "Login failed");
    } finally {
      setLoginLoading(false);
    }
  };

  const handleSignOut = () => {
    localStorage.removeItem("cg_parent_token");
    setToken(null);
    setDashboard(null);
    setChildren([]);
    setSelectedChildId(null);
    setEmail("");
    setPassword("");
  };

  const markNotificationAsRead = async (notifId: string) => {
    if (!token) return;
    try {
      const res = await fetch(`${API_BASE}/notifications/inbox/${notifId}/read`, {
        method: "PATCH",
        headers: {
          Authorization: `Bearer ${token}`,
          "X-Tenant-Subdomain": subdomain,
        },
      });
      if (res.ok) {
        setDashboard((prev) => {
          if (!prev) return prev;
          return {
            ...prev,
            notifications: prev.notifications.map((n) =>
              n.id === notifId ? { ...n, read_at: new Date().toISOString() } : n
            ),
          };
        });
      }
    } catch (err) {
      console.error("Mark read error:", err);
    }
  };

  if (!token) {
    return (
      <main className="min-h-screen bg-slate-900 px-6 py-8 text-slate-100">
        <section className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-md flex-col justify-center">
          <div className="rounded-2xl border border-slate-800 bg-slate-950/80 p-8 shadow-xl backdrop-blur-sm">
            <p className="text-sm font-semibold tracking-wide text-blue-400 uppercase">CoachGenie Parent Portal</p>
            <h1 className="mt-2 text-3xl font-bold tracking-tight text-white">Parent Sign In</h1>
            <p className="mt-2 text-sm leading-6 text-slate-400">
              Monitor your children's attendance, academic performance, and fee invoices.
            </p>

            {loginError && (
              <div className="mt-4 rounded-lg bg-red-500/10 border border-red-500/30 p-3 text-sm text-red-400">
                {loginError}
              </div>
            )}

            <form onSubmit={handleLogin} className="mt-6 space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Institute Subdomain</label>
                <input
                  value={subdomain}
                  onChange={(e) => setSubdomain(e.target.value)}
                  className="h-11 w-full rounded-lg border border-slate-800 bg-slate-900 px-3 text-sm text-white outline-none focus:border-blue-500"
                  placeholder="demo"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Parent Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="h-11 w-full rounded-lg border border-slate-800 bg-slate-900 px-3 text-sm text-white outline-none focus:border-blue-500"
                  placeholder="parent@example.com"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Password</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="h-11 w-full rounded-lg border border-slate-800 bg-slate-900 px-3 text-sm text-white outline-none focus:border-blue-500"
                  placeholder="••••••••"
                  required
                />
              </div>
              <button
                type="submit"
                disabled={loginLoading}
                className="h-11 w-full rounded-lg bg-blue-600 text-sm font-semibold text-white transition-colors hover:bg-blue-500 disabled:opacity-50"
              >
                {loginLoading ? "Signing in..." : "Sign In"}
              </button>
            </form>
          </div>
        </section>
      </main>
    );
  }

  if (loading && !dashboard) {
    return (
      <main className="min-h-screen bg-slate-900 px-6 py-8 text-slate-100">
        <div className="mx-auto max-w-6xl space-y-6">
          <div className="h-16 w-full animate-pulse rounded-xl bg-slate-800" />
          <div className="grid gap-4 md:grid-cols-3">
            <div className="h-32 animate-pulse rounded-xl bg-slate-800" />
            <div className="h-32 animate-pulse rounded-xl bg-slate-800" />
            <div className="h-32 animate-pulse rounded-xl bg-slate-800" />
          </div>
        </div>
      </main>
    );
  }

  const selectedChild = dashboard?.selected_child;
  const attendance = dashboard?.attendance;
  const fees = dashboard?.fees;
  const exams = dashboard?.exams || [];
  const notifications = dashboard?.notifications || [];

  return (
    <main className="min-h-screen bg-slate-900 px-4 py-6 sm:px-6 sm:py-8 text-slate-100">
      <div className="mx-auto flex max-w-6xl flex-col gap-6">
        {/* Header & Multi-Child Switcher */}
        <header className="flex flex-col gap-4 border-b border-slate-800 pb-6 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-xs font-semibold tracking-wider text-blue-400 uppercase">CoachGenie Parent Portal</p>
            {selectedChild ? (
              <>
                <h1 className="mt-1 text-2xl sm:text-3xl font-bold tracking-tight text-white">
                  {selectedChild.first_name} {selectedChild.last_name}
                </h1>
                <p className="mt-1 text-sm text-slate-400">
                  Enrollment: {selectedChild.enrollment_no} · Class: {selectedChild.current_class || "N/A"} · School: {selectedChild.school_name || "N/A"}
                </p>
              </>
            ) : (
              <h1 className="mt-1 text-2xl sm:text-3xl font-bold tracking-tight text-white">
                No Children Linked
              </h1>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* Child Selector Dropdown / Pills */}
            {children.length > 1 && (
              <div className="flex items-center gap-1.5 bg-slate-800/80 p-1.5 rounded-lg border border-slate-700">
                <span className="text-xs font-medium text-slate-400 px-2">Child:</span>
                {children.map((c) => (
                  <button
                    key={c.id}
                    onClick={() => setSelectedChildId(c.id)}
                    className={`rounded px-3 py-1 text-xs font-semibold transition-colors ${
                      selectedChild?.id === c.id
                        ? "bg-blue-600 text-white"
                        : "text-slate-300 hover:bg-slate-700"
                    }`}
                  >
                    {c.first_name}
                  </button>
                ))}
              </div>
            )}

            <button
              onClick={handleSignOut}
              className="rounded-lg border border-slate-700 px-4 py-2 text-sm font-medium transition-colors hover:bg-slate-800"
            >
              Sign Out
            </button>
          </div>
        </header>

        {/* Navigation Tabs */}
        <nav className="flex flex-wrap gap-2 overflow-x-auto pb-1">
          {tabs.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
                activeTab === tab
                  ? "bg-blue-600 text-white font-semibold"
                  : "border border-slate-800 bg-slate-800/50 text-slate-300 hover:bg-slate-800"
              }`}
            >
              {tab}
              {tab === "Notifications" && notifications.filter((n) => !n.read_at).length > 0 && (
                <span className="ml-2 rounded-full bg-blue-400 text-slate-950 px-1.5 py-0.5 text-xs font-bold">
                  {notifications.filter((n) => !n.read_at).length}
                </span>
              )}
            </button>
          ))}
        </nav>

        {/* Empty State when no children linked */}
        {!selectedChild && (
          <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-12 text-center">
            <p className="text-lg font-semibold text-white">No students linked to this parent account</p>
            <p className="text-sm text-slate-400 mt-2">
              Please contact the institute administrator to verify your parent registration details.
            </p>
          </div>
        )}

        {selectedChild && (
          <>
            {/* TAB 1: OVERVIEW */}
            {activeTab === "Overview" && (
              <div className="space-y-6">
                <section className="grid gap-4 md:grid-cols-3">
                  <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-5 shadow-sm">
                    <p className="text-xs font-medium text-slate-400 uppercase">Attendance Presence</p>
                    <p className="mt-2 text-3xl font-bold text-blue-400">
                      {attendance ? `${attendance.percentage}%` : "0%"}
                    </p>
                    <p className="mt-1 text-xs text-slate-400">
                      {attendance?.present || 0} Attended / {attendance?.total_classes || 0} Total Sessions
                    </p>
                  </div>

                  <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-5 shadow-sm">
                    <p className="text-xs font-medium text-slate-400 uppercase">Fee Balance</p>
                    <p className="mt-2 text-3xl font-bold text-white">
                      ₹{(fees?.balance || 0).toLocaleString("en-IN")}
                    </p>
                    <p className="mt-1 text-xs text-slate-400">
                      Paid: ₹{(fees?.total_paid || 0).toLocaleString("en-IN")} · Due: ₹{(fees?.total_due || 0).toLocaleString("en-IN")}
                    </p>
                  </div>

                  <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-5 shadow-sm">
                    <p className="text-xs font-medium text-slate-400 uppercase">Published Reports</p>
                    <p className="mt-2 text-3xl font-bold text-emerald-400">
                      {exams.length} {exams.length === 1 ? "Exam" : "Exams"}
                    </p>
                    <p className="mt-1 text-xs text-slate-400">Published Academic Evaluations</p>
                  </div>
                </section>

                {/* Child Snapshot */}
                <section className="rounded-xl border border-slate-800 bg-slate-950/50 p-5 shadow-sm">
                  <h2 className="text-lg font-semibold text-white mb-3">Academic Snapshot</h2>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="rounded-lg bg-slate-900 p-4 border border-slate-800">
                      <p className="text-xs text-slate-400">Target Examination</p>
                      <p className="text-base font-semibold text-white mt-1">{selectedChild.target_exam || "Not specified"}</p>
                    </div>
                    <div className="rounded-lg bg-slate-900 p-4 border border-slate-800">
                      <p className="text-xs text-slate-400">Registered School</p>
                      <p className="text-base font-semibold text-white mt-1">{selectedChild.school_name || "Not specified"}</p>
                    </div>
                  </div>
                </section>
              </div>
            )}

            {/* TAB 2: ATTENDANCE */}
            {activeTab === "Attendance" && (
              <section className="rounded-xl border border-slate-800 bg-slate-950/50 p-5 shadow-sm space-y-6">
                <div className="grid gap-4 sm:grid-cols-4">
                  <div className="rounded-lg bg-slate-900 p-4 border border-slate-800">
                    <p className="text-xs text-slate-400">Overall Ratio</p>
                    <p className="text-2xl font-bold text-blue-400 mt-1">{attendance?.percentage || 0}%</p>
                  </div>
                  <div className="rounded-lg bg-slate-900 p-4 border border-slate-800">
                    <p className="text-xs text-slate-400">Attended</p>
                    <p className="text-2xl font-bold text-emerald-400 mt-1">{attendance?.present || 0}</p>
                  </div>
                  <div className="rounded-lg bg-slate-900 p-4 border border-slate-800">
                    <p className="text-xs text-slate-400">Missed</p>
                    <p className="text-2xl font-bold text-red-400 mt-1">{attendance?.absent || 0}</p>
                  </div>
                  <div className="rounded-lg bg-slate-900 p-4 border border-slate-800">
                    <p className="text-xs text-slate-400">Late</p>
                    <p className="text-2xl font-bold text-amber-400 mt-1">{attendance?.late || 0}</p>
                  </div>
                </div>
              </section>
            )}

            {/* TAB 3: ACADEMICS */}
            {activeTab === "Academics" && (
              <section className="rounded-xl border border-slate-800 bg-slate-950/50 shadow-sm overflow-hidden">
                <div className="p-5 border-b border-slate-800">
                  <h2 className="text-lg font-semibold text-white">Published Academic Results</h2>
                </div>
                {exams.length === 0 ? (
                  <p className="text-sm text-slate-400 p-6 text-center">No published exam results available for this child.</p>
                ) : (
                  <div className="divide-y divide-slate-800">
                    {exams.map((ex) => (
                      <div key={ex.id} className="p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                        <div>
                          <p className="font-semibold text-white">Exam Report</p>
                          <p className="text-xs text-slate-400 mt-0.5">
                            Grade: <span className="text-blue-400 font-bold">{ex.grade || "N/A"}</span> · Rank in Batch: #{ex.rank_in_batch || "-"}
                          </p>
                          {ex.remarks && <p className="text-xs text-slate-300 mt-1 italic">Faculty Remark: "{ex.remarks}"</p>}
                        </div>
                        <div className="text-right">
                          <p className="text-xl font-bold text-white">{ex.marks_obtained} Marks</p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </section>
            )}

            {/* TAB 4: FEES */}
            {activeTab === "Fees" && (
              <section className="space-y-6">
                <div className="grid gap-4 sm:grid-cols-3">
                  <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-5">
                    <p className="text-xs text-slate-400">Total Billed</p>
                    <p className="text-2xl font-bold text-white mt-1">₹{(fees?.total_due || 0).toLocaleString("en-IN")}</p>
                  </div>
                  <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-5">
                    <p className="text-xs text-slate-400">Total Paid</p>
                    <p className="text-2xl font-bold text-emerald-400 mt-1">₹{(fees?.total_paid || 0).toLocaleString("en-IN")}</p>
                  </div>
                  <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-5">
                    <p className="text-xs text-slate-400">Outstanding Balance</p>
                    <p className="text-2xl font-bold text-amber-400 mt-1">₹{(fees?.balance || 0).toLocaleString("en-IN")}</p>
                  </div>
                </div>

                <div className="rounded-xl border border-slate-800 bg-slate-950/50 shadow-sm overflow-hidden">
                  <div className="p-5 border-b border-slate-800">
                    <h2 className="text-lg font-semibold text-white">Invoices & Installments</h2>
                  </div>
                  {!fees?.invoices || fees.invoices.length === 0 ? (
                    <p className="text-sm text-slate-400 p-6 text-center">No fee invoices found for this child.</p>
                  ) : (
                    <div className="divide-y divide-slate-800">
                      {fees.invoices.map((inv) => (
                        <div key={inv.id} className="p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                          <div>
                            <p className="font-semibold text-white">{inv.invoice_no}</p>
                            <p className="text-xs text-slate-400">Due: {inv.due_date}</p>
                          </div>
                          <div className="flex items-center gap-4">
                            <div className="text-right">
                              <p className="font-semibold text-white">₹{inv.amount_due.toLocaleString("en-IN")}</p>
                              <p className="text-xs text-slate-400">Paid: ₹{inv.amount_paid.toLocaleString("en-IN")}</p>
                            </div>
                            <span
                              className={`rounded-full px-3 py-1 text-xs font-semibold uppercase ${
                                inv.status === "paid"
                                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                                  : inv.status === "partial"
                                  ? "bg-amber-500/10 text-amber-400 border border-amber-500/30"
                                  : "bg-red-500/10 text-red-400 border border-red-500/30"
                              }`}
                            >
                              {inv.status}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </section>
            )}

            {/* TAB 5: NOTIFICATIONS */}
            {activeTab === "Notifications" && (
              <section className="rounded-xl border border-slate-800 bg-slate-950/50 shadow-sm overflow-hidden">
                <div className="p-5 border-b border-slate-800">
                  <h2 className="text-lg font-semibold text-white">Parent Notices & Alerts</h2>
                </div>
                {notifications.length === 0 ? (
                  <p className="text-sm text-slate-400 p-6 text-center">No notifications found in your inbox.</p>
                ) : (
                  <div className="divide-y divide-slate-800">
                    {notifications.map((notif) => (
                      <div
                        key={notif.id}
                        className={`p-5 flex flex-col sm:flex-row sm:items-start justify-between gap-4 ${
                          !notif.read_at ? "bg-white/[0.03]" : ""
                        }`}
                      >
                        <div>
                          <div className="flex items-center gap-2">
                            <p className="font-semibold text-white">{notif.subject || "Notice"}</p>
                            {!notif.read_at && (
                              <span className="rounded-full bg-blue-500 text-white px-2 py-0.5 text-[10px] font-bold">
                                NEW
                              </span>
                            )}
                          </div>
                          <p className="text-sm text-slate-300 mt-1 leading-relaxed">{notif.body}</p>
                          <p className="text-xs text-slate-500 mt-2">{new Date(notif.created_at).toLocaleString()}</p>
                        </div>
                        {!notif.read_at && (
                          <button
                            onClick={() => markNotificationAsRead(notif.id)}
                            className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs font-medium text-blue-300 hover:bg-slate-700 self-start"
                          >
                            Mark as read
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </section>
            )}
          </>
        )}
      </div>
    </main>
  );
}
