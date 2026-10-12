"use client";

import { useState, useEffect, useCallback } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

const tabs = ["Overview", "Timetable", "Attendance", "Exams", "Fees", "Notifications"] as const;
type Tab = typeof tabs[number];

interface StudentProfile {
  id: string;
  first_name: string;
  last_name: string;
  enrollment_no: string;
  email?: string;
  phone?: string;
  current_class?: string;
  target_exam?: string;
  photo_url?: string;
  school_name?: string;
  parent_name?: string;
}

interface BatchItem {
  id: string;
  name: string;
  academic_year?: string;
}

interface ClassSession {
  id: string;
  batch_id: string;
  title: string;
  scheduled_at: string;
  duration_min: number;
  room_or_link?: string;
  status: string;
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

interface DashboardData {
  student: StudentProfile;
  batches: BatchItem[];
  today_classes: ClassSession[];
  attendance: AttendanceSummary;
  fees: FeeSummary;
  exams: ExamResultItem[];
  notifications: NotificationItem[];
}

export default function StudentPortalHome() {
  const [token, setToken] = useState<string | null>(null);
  const [subdomain, setSubdomain] = useState<string>("demo");
  const [activeTab, setActiveTab] = useState<Tab>("Overview");

  // Login form state
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loginLoading, setLoginLoading] = useState(false);
  const [loginError, setLoginError] = useState<string | null>(null);

  // Data fetching state
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [timetable, setTimetable] = useState<ClassSession[]>([]);
  const [loading, setLoading] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);

  // Receipt modal state
  const [receiptLoading, setReceiptLoading] = useState(false);
  const [selectedReceipt, setSelectedReceipt] = useState<any | null>(null);

  // Initialize from localStorage
  useEffect(() => {
    const savedToken = localStorage.getItem("cg_student_token");
    const savedSubdomain = localStorage.getItem("cg_student_subdomain") || "demo";
    if (savedToken) {
      setToken(savedToken);
      setSubdomain(savedSubdomain);
    }
  }, []);

  const fetchDashboardData = useCallback(async (authToken: string, tenantSub: string) => {
    setLoading(true);
    setFetchError(null);
    try {
      const res = await fetch(`${API_BASE}/students/portal/dashboard`, {
        headers: {
          Authorization: `Bearer ${authToken}`,
          "X-Tenant-Subdomain": tenantSub,
        },
      });

      if (res.status === 401 || res.status === 403) {
        localStorage.removeItem("cg_student_token");
        setToken(null);
        setFetchError("Session expired or unauthorized. Please sign in again.");
        return;
      }

      const json = await res.json();
      if (!res.ok || !json.success) {
        throw new Error(json.message || "Failed to load dashboard");
      }
      setDashboard(json.data);
    } catch (err: any) {
      setFetchError(err.message || "Network error fetching student data");
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchTimetableData = useCallback(async (authToken: string, tenantSub: string) => {
    try {
      const res = await fetch(`${API_BASE}/students/portal/timetable`, {
        headers: {
          Authorization: `Bearer ${authToken}`,
          "X-Tenant-Subdomain": tenantSub,
        },
      });
      const json = await res.json();
      if (res.ok && json.success) {
        setTimetable(json.data || []);
      }
    } catch (err) {
      console.error("Timetable load error:", err);
    }
  }, []);

  useEffect(() => {
    if (token) {
      fetchDashboardData(token, subdomain);
      fetchTimetableData(token, subdomain);
    }
  }, [token, subdomain, fetchDashboardData, fetchTimetableData]);

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
        throw new Error(json.detail || json.message || "Invalid email or password");
      }

      const userRole = json.user?.role || json.role;
      if (userRole !== "student") {
        throw new Error("This portal is for students only. Please use the appropriate portal.");
      }

      const accessToken = json.access_token;
      localStorage.setItem("cg_student_token", accessToken);
      localStorage.setItem("cg_student_subdomain", subdomain);
      setToken(accessToken);
    } catch (err: any) {
      setLoginError(err.message || "Login failed");
    } finally {
      setLoginLoading(false);
    }
  };

  const handleSignOut = () => {
    localStorage.removeItem("cg_student_token");
    setToken(null);
    setDashboard(null);
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
      <main className="min-h-screen bg-zinc-950 px-6 py-8 text-white">
        <section className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-md flex-col justify-center">
          <div className="rounded-2xl border border-white/10 bg-white/5 p-8 shadow-sm">
            <p className="text-sm font-semibold tracking-wide text-cyan-400 uppercase">CoachGenie Student Portal</p>
            <h1 className="mt-2 text-3xl font-bold tracking-tight text-white">Student Sign In</h1>
            <p className="mt-2 text-sm leading-6 text-zinc-400">
              Access your class schedule, attendance records, exam results, and fee receipts.
            </p>

            {loginError && (
              <div className="mt-4 rounded-lg bg-red-500/10 border border-red-500/30 p-3 text-sm text-red-400">
                {loginError}
              </div>
            )}

            <form onSubmit={handleLogin} className="mt-6 space-y-4">
              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1">Institute Subdomain</label>
                <input
                  value={subdomain}
                  onChange={(e) => setSubdomain(e.target.value)}
                  className="h-11 w-full rounded-lg border border-white/10 bg-zinc-900 px-3 text-sm text-white outline-none focus:border-cyan-400"
                  placeholder="demo"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1">Email Address</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="h-11 w-full rounded-lg border border-white/10 bg-zinc-900 px-3 text-sm text-white outline-none focus:border-cyan-400"
                  placeholder="student@institute.com"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1">Password</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="h-11 w-full rounded-lg border border-white/10 bg-zinc-900 px-3 text-sm text-white outline-none focus:border-cyan-400"
                  placeholder="••••••••"
                  required
                />
              </div>
              <button
                type="submit"
                disabled={loginLoading}
                className="h-11 w-full rounded-lg bg-cyan-400 text-sm font-semibold text-zinc-950 transition-colors hover:bg-cyan-300 disabled:opacity-50"
              >
                {loginLoading ? "Signing in..." : "Sign In to Portal"}
              </button>
            </form>
          </div>
        </section>
      </main>
    );
  }

  if (loading && !dashboard) {
    return (
      <main className="min-h-screen bg-zinc-950 px-6 py-8 text-white">
        <div className="mx-auto max-w-6xl space-y-6">
          <div className="h-16 w-full animate-pulse rounded-xl bg-white/5" />
          <div className="grid gap-4 md:grid-cols-3">
            <div className="h-32 animate-pulse rounded-xl bg-white/5" />
            <div className="h-32 animate-pulse rounded-xl bg-white/5" />
            <div className="h-32 animate-pulse rounded-xl bg-white/5" />
          </div>
        </div>
      </main>
    );
  }

  if (fetchError && !dashboard) {
    return (
      <main className="min-h-screen bg-zinc-950 px-6 py-8 text-white">
        <div className="mx-auto max-w-md text-center py-20">
          <p className="text-red-400 mb-4">{fetchError}</p>
          <button
            onClick={() => token && fetchDashboardData(token, subdomain)}
            className="rounded-lg bg-cyan-400 px-4 py-2 text-sm font-semibold text-zinc-950 hover:bg-cyan-300"
          >
            Retry
          </button>
        </div>
      </main>
    );
  }

  const student = dashboard?.student;
  const attendance = dashboard?.attendance;
  const fees = dashboard?.fees;
  const exams = dashboard?.exams || [];
  const notifications = dashboard?.notifications || [];
  const todayClasses = dashboard?.today_classes || [];

  return (
    <main className="min-h-screen bg-zinc-950 px-4 py-6 sm:px-6 sm:py-8 text-white">
      <div className="mx-auto flex max-w-6xl flex-col gap-6">
        {/* Header */}
        <header className="flex flex-col gap-4 border-b border-white/10 pb-6 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-xs font-semibold tracking-wider text-cyan-400 uppercase">CoachGenie Student Portal</p>
            <h1 className="mt-1 text-2xl sm:text-3xl font-bold tracking-tight">
              Welcome, {student?.first_name} {student?.last_name}
            </h1>
            <p className="mt-1 text-sm text-zinc-400">
              Enrollment: {student?.enrollment_no} · Class: {student?.current_class || "N/A"} · Target: {student?.target_exam || "General"}
            </p>
          </div>
          <button
            onClick={handleSignOut}
            className="self-start sm:self-auto rounded-lg border border-white/10 px-4 py-2 text-sm font-medium transition-colors hover:bg-white/10"
          >
            Sign Out
          </button>
        </header>

        {/* Navigation Tabs */}
        <nav className="flex flex-wrap gap-2 overflow-x-auto pb-1">
          {tabs.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
                activeTab === tab
                  ? "bg-cyan-400 text-zinc-950 font-semibold"
                  : "border border-white/10 bg-white/5 text-zinc-300 hover:bg-white/10"
              }`}
            >
              {tab}
              {tab === "Notifications" && notifications.filter((n) => !n.read_at).length > 0 && (
                <span className="ml-2 rounded-full bg-cyan-400 text-zinc-950 px-1.5 py-0.5 text-xs font-bold">
                  {notifications.filter((n) => !n.read_at).length}
                </span>
              )}
            </button>
          ))}
        </nav>

        {/* TAB 1: OVERVIEW */}
        {activeTab === "Overview" && (
          <div className="space-y-6">
            <section className="grid gap-4 md:grid-cols-3">
              <div className="rounded-xl border border-white/10 bg-white/5 p-5 shadow-sm">
                <p className="text-xs font-medium text-zinc-400 uppercase">Attendance Presence</p>
                <p className="mt-2 text-3xl font-bold text-cyan-400">
                  {attendance ? `${attendance.percentage}%` : "0%"}
                </p>
                <p className="mt-1 text-xs text-zinc-400">
                  {attendance?.present || 0} Attended / {attendance?.total_classes || 0} Total Sessions
                </p>
              </div>

              <div className="rounded-xl border border-white/10 bg-white/5 p-5 shadow-sm">
                <p className="text-xs font-medium text-zinc-400 uppercase">Fee Balance</p>
                <p className="mt-2 text-3xl font-bold text-white">
                  ₹{(fees?.balance || 0).toLocaleString("en-IN")}
                </p>
                <p className="mt-1 text-xs text-zinc-400">
                  Paid: ₹{(fees?.total_paid || 0).toLocaleString("en-IN")} · Due: ₹{(fees?.total_due || 0).toLocaleString("en-IN")}
                </p>
              </div>

              <div className="rounded-xl border border-white/10 bg-white/5 p-5 shadow-sm">
                <p className="text-xs font-medium text-zinc-400 uppercase">Published Results</p>
                <p className="mt-2 text-3xl font-bold text-emerald-400">
                  {exams.length} {exams.length === 1 ? "Exam" : "Exams"}
                </p>
                <p className="mt-1 text-xs text-zinc-400">Verified & Published Academic Reports</p>
              </div>
            </section>

            {/* Today's Schedule */}
            <section className="rounded-xl border border-white/10 bg-white/5 p-5 shadow-sm">
              <h2 className="text-lg font-semibold text-white mb-4">Upcoming Schedule</h2>
              {todayClasses.length === 0 ? (
                <p className="text-sm text-zinc-400 py-4">No upcoming classes scheduled for today.</p>
              ) : (
                <div className="space-y-3">
                  {todayClasses.map((cls) => (
                    <div
                      key={cls.id}
                      className="flex flex-col sm:flex-row sm:items-center justify-between rounded-lg border border-white/10 bg-zinc-900/50 p-4 gap-2"
                    >
                      <div>
                        <p className="font-semibold text-white">{cls.title}</p>
                        <p className="text-xs text-zinc-400">
                          {new Date(cls.scheduled_at).toLocaleString()} · {cls.duration_min} mins
                        </p>
                      </div>
                      {cls.room_or_link && (
                        <span className="rounded bg-cyan-400/10 border border-cyan-400/30 px-2.5 py-1 text-xs font-medium text-cyan-300">
                          {cls.room_or_link}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </section>
          </div>
        )}

        {/* TAB 2: TIMETABLE */}
        {activeTab === "Timetable" && (
          <section className="rounded-xl border border-white/10 bg-white/5 p-5 shadow-sm">
            <h2 className="text-lg font-semibold text-white mb-4">Weekly Schedule</h2>
            {timetable.length === 0 ? (
              <p className="text-sm text-zinc-400 py-6 text-center">No batch sessions found in timetable.</p>
            ) : (
              <div className="space-y-3">
                {timetable.map((item) => (
                  <div
                    key={item.id}
                    className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-white/10 pb-3 last:border-b-0 gap-2"
                  >
                    <div>
                      <p className="font-medium text-white">{item.title}</p>
                      <p className="text-xs text-zinc-400">
                        {new Date(item.scheduled_at).toLocaleString()} ({item.duration_min} minutes)
                      </p>
                    </div>
                    <span className="rounded bg-white/10 px-2.5 py-1 text-xs text-zinc-300">
                      {item.room_or_link || "Classroom"}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}

        {/* TAB 3: ATTENDANCE */}
        {activeTab === "Attendance" && (
          <section className="rounded-xl border border-white/10 bg-white/5 p-5 shadow-sm space-y-6">
            <div className="grid gap-4 sm:grid-cols-4">
              <div className="rounded-lg bg-zinc-900/50 p-4 border border-white/10">
                <p className="text-xs text-zinc-400">Overall Ratio</p>
                <p className="text-2xl font-bold text-cyan-400 mt-1">{attendance?.percentage || 0}%</p>
              </div>
              <div className="rounded-lg bg-zinc-900/50 p-4 border border-white/10">
                <p className="text-xs text-zinc-400">Classes Attended</p>
                <p className="text-2xl font-bold text-emerald-400 mt-1">{attendance?.present || 0}</p>
              </div>
              <div className="rounded-lg bg-zinc-900/50 p-4 border border-white/10">
                <p className="text-xs text-zinc-400">Classes Missed</p>
                <p className="text-2xl font-bold text-red-400 mt-1">{attendance?.absent || 0}</p>
              </div>
              <div className="rounded-lg bg-zinc-900/50 p-4 border border-white/10">
                <p className="text-xs text-zinc-400">Late Arrivals</p>
                <p className="text-2xl font-bold text-amber-400 mt-1">{attendance?.late || 0}</p>
              </div>
            </div>
          </section>
        )}

        {/* TAB 4: EXAMS */}
        {activeTab === "Exams" && (
          <section className="rounded-xl border border-white/10 bg-white/5 shadow-sm overflow-hidden">
            <div className="p-5 border-b border-white/10">
              <h2 className="text-lg font-semibold text-white">Published Examination Results</h2>
              <p className="text-xs text-zinc-400 mt-1">Only official published reports are shown.</p>
            </div>
            {exams.length === 0 ? (
              <p className="text-sm text-zinc-400 p-6 text-center">No published exam results found yet.</p>
            ) : (
              <div className="divide-y divide-white/10">
                {exams.map((ex) => (
                  <div key={ex.id} className="p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div>
                      <p className="font-semibold text-white">Exam Report</p>
                      <p className="text-xs text-zinc-400 mt-0.5">
                        Grade: <span className="text-cyan-300 font-bold">{ex.grade || "N/A"}</span> · Rank: #{ex.rank_in_batch || "-"}
                      </p>
                      {ex.remarks && <p className="text-xs text-zinc-300 mt-1 italic">"{ex.remarks}"</p>}
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

        {/* TAB 5: FEES */}
        {activeTab === "Fees" && (
          <section className="space-y-6">
            <div className="grid gap-4 sm:grid-cols-3">
              <div className="rounded-xl border border-white/10 bg-white/5 p-5">
                <p className="text-xs text-zinc-400">Total Billed</p>
                <p className="text-2xl font-bold text-white mt-1">₹{(fees?.total_due || 0).toLocaleString("en-IN")}</p>
              </div>
              <div className="rounded-xl border border-white/10 bg-white/5 p-5">
                <p className="text-xs text-zinc-400">Total Paid</p>
                <p className="text-2xl font-bold text-emerald-400 mt-1">₹{(fees?.total_paid || 0).toLocaleString("en-IN")}</p>
              </div>
              <div className="rounded-xl border border-white/10 bg-white/5 p-5">
                <p className="text-xs text-zinc-400">Outstanding Balance</p>
                <p className="text-2xl font-bold text-amber-400 mt-1">₹{(fees?.balance || 0).toLocaleString("en-IN")}</p>
              </div>
            </div>

            <div className="rounded-xl border border-white/10 bg-white/5 shadow-sm overflow-hidden">
              <div className="p-5 border-b border-white/10">
                <h2 className="text-lg font-semibold text-white">Fee Invoices</h2>
              </div>
              {!fees?.invoices || fees.invoices.length === 0 ? (
                <p className="text-sm text-zinc-400 p-6 text-center">No fee invoices recorded.</p>
              ) : (
                <div className="divide-y divide-white/10">
                  {fees.invoices.map((inv) => (
                    <div key={inv.id} className="p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                      <div>
                        <p className="font-semibold text-white">{inv.invoice_no}</p>
                        <p className="text-xs text-zinc-400">Due Date: {inv.due_date}</p>
                      </div>
                      <div className="flex items-center gap-4">
                        <div className="text-right">
                          <p className="font-semibold text-white">₹{inv.amount_due.toLocaleString("en-IN")}</p>
                          <p className="text-xs text-zinc-400">Paid: ₹{inv.amount_paid.toLocaleString("en-IN")}</p>
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

        {/* TAB 6: NOTIFICATIONS */}
        {activeTab === "Notifications" && (
          <section className="rounded-xl border border-white/10 bg-white/5 shadow-sm overflow-hidden">
            <div className="p-5 border-b border-white/10">
              <h2 className="text-lg font-semibold text-white">Institute Alerts & Notices</h2>
            </div>
            {notifications.length === 0 ? (
              <p className="text-sm text-zinc-400 p-6 text-center">No notifications found in your inbox.</p>
            ) : (
              <div className="divide-y divide-white/10">
                {notifications.map((notif) => (
                  <div
                    key={notif.id}
                    className={`p-5 flex flex-col sm:flex-row sm:items-start justify-between gap-4 ${
                      !notif.read_at ? "bg-white/[0.03]" : ""
                    }`}
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <p className="font-semibold text-white">{notif.subject || "Notification"}</p>
                        {!notif.read_at && (
                          <span className="rounded-full bg-cyan-400 text-zinc-950 px-2 py-0.5 text-[10px] font-bold">
                            NEW
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-zinc-300 mt-1 leading-relaxed">{notif.body}</p>
                      <p className="text-xs text-zinc-500 mt-2">{new Date(notif.created_at).toLocaleString()}</p>
                    </div>
                    {!notif.read_at && (
                      <button
                        onClick={() => markNotificationAsRead(notif.id)}
                        className="rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-xs font-medium text-cyan-300 hover:bg-white/10 self-start"
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
      </div>
    </main>
  );
}
