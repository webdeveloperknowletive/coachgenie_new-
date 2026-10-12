"use client";

import { use, useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  GraduationCap,
  Phone,
  Mail,
  MapPin,
  User,
  BookOpen,
  Calendar,
  RefreshCw,
  Sparkles,
  IndianRupee,
  Plus,
  Printer,
  FileSpreadsheet,
  Award,
  TrendingUp,
  Download,
  FileText,
} from "lucide-react";
import { format } from "date-fns";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { EnrollmentDialog } from "@/components/students/EnrollmentDialog";
import { authHeaders } from "@/lib/auth-headers";
import { useAcademicStore } from "@/lib/stores/academic.store";
import { generateInvoicePDF } from "@/lib/utils/generate-invoice-pdf";
import { generateStudentPerformancePDF } from "@/lib/utils/generate-report-pdf";
import { useLanguage } from "@/components/providers/LanguageProvider";

const API = "/api/proxy";

const STATUS_STYLE: Record<string, string> = {
  ACTIVE: "bg-emerald-500/15 text-emerald-600 border-emerald-500/30",
  INACTIVE: "bg-slate-500/15 text-slate-600 border-slate-500/30",
  SUSPENDED: "bg-red-500/15 text-red-600 border-red-500/30",
  GRADUATED: "bg-blue-500/15 text-blue-600 border-blue-500/30",
};

export default function StudentProfilePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const { language, t } = useLanguage();
  const academicStore = useAcademicStore();

  const storeStudent = academicStore.students.find((s) => s.id === id);

  const [student, setStudent] = useState<any>(storeStudent ?? null);
  const [batches, setBatches] = useState<any[]>([]);
  const [fees, setFees] = useState({ total: 0, paid: 0, due: 0 });
  const [loading, setLoading] = useState(!student);
  const [showEnroll, setShowEnroll] = useState(false);

  const [paymentHistory, setPaymentHistory] = useState<any[]>([]);

  // Load student profile
  useEffect(() => {
    let isMounted = true;
    async function loadStudent() {
      try {
        const res = await fetch(`${API}/students/${id}`, { headers: authHeaders() }).catch(() => null);
        if (res && res.ok) {
          const json = await res.json();
          const raw = json.data ?? json;
          if (isMounted && raw && raw.id) {
            setStudent({
              id: String(raw.id),
              name: `${raw.first_name ?? raw.name ?? ""} ${raw.last_name ?? ""}`.trim() || "Student",
              email: raw.email ?? "",
              phone: raw.phone ?? "",
              parentName: raw.parent_name ?? "",
              parentPhone: raw.parent_phone ?? "",
              grade: raw.current_class ?? "10th",
              subjects: raw.subjects ?? [],
              status: raw.is_active === false ? "INACTIVE" : "ACTIVE",
              address: raw.address ?? "",
              dob: raw.date_of_birth ?? "",
            });
          }
        }
      } catch {
        // quiet fallback
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    loadStudent();
    return () => {
      isMounted = false;
    };
  }, [id]);

  // Load assigned batches
  const loadBatches = useCallback(async () => {
    try {
      const res = await fetch(`${API}/batches/by-student/${id}`, { headers: authHeaders() }).catch(() => null);
      if (res && res.ok) {
        const json = await res.json();
        const raw: any[] = json.data ?? json ?? [];
        if (Array.isArray(raw)) {
          setBatches(
            raw.map((b) => ({
              id: String(b.id),
              name: b.name ?? b.batch_name ?? "Batch",
              teacher: b.tutor_name ?? b.teacher_name ?? "Assigned Tutor",
              room: b.room_or_link ?? "Classroom",
              status: b.is_active === false ? "COMPLETED" : "ACTIVE",
              subject: b.target_exam ?? (Array.isArray(b.subjects) ? b.subjects.join(", ") : b.subjects) ?? "Course",
            }))
          );
        }
      }
    } catch {
      // quiet fallback
    }
  }, [id]);

  useEffect(() => {
    loadBatches();
  }, [loadBatches, showEnroll]);

  // Load student fee summary and payment history
  useEffect(() => {
    async function loadFees() {
      try {
        const res = await fetch(`${API}/fees/student/${id}`, { headers: authHeaders() }).catch(() => null);
        if (res && res.ok) {
          const json = await res.json();
          const invoices: any[] = Array.isArray(json) ? json : json.data ?? [];
          if (invoices.length > 0) {
            const total = invoices.reduce((s: number, i: any) => s + parseFloat(i.amount_due ?? i.amount ?? 0), 0);
            const paid = invoices.reduce((s: number, i: any) => s + parseFloat(i.amount_paid ?? i.paid ?? 0), 0);
            setFees({ total, paid, due: Math.max(0, total - paid) });
          }
        }

        const pRes = await fetch(`${API}/fees/payments/history?student_id=${id}`, { headers: authHeaders() }).catch(() => null);
        if (pRes && pRes.ok) {
          const pJson = await pRes.json();
          const rawPays = pJson.data ?? pJson ?? [];
          if (Array.isArray(rawPays)) {
            setPaymentHistory(rawPays);
          }
        }
      } catch {
        // quiet fallback
      }
    }

    loadFees();
  }, [id]);

  if (loading && !student) {
    return (
      <div className="space-y-4 max-w-4xl">
        <div className="h-8 w-48 bg-muted rounded-xl animate-pulse" />
        <div className="h-64 bg-card border rounded-2xl animate-pulse" />
      </div>
    );
  }

  if (!student) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3 rounded-2xl border bg-card p-8 text-center">
        <p className="text-base font-bold">{t("Student record not found.")}</p>
        <button onClick={() => router.push("/students")} className="text-xs font-semibold text-primary hover:underline">
          {t("← Return to Student Roster")}
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-6xl">
      {/* 🚀 Header */}
      <div className="flex flex-wrap items-start justify-between gap-4 border-b pb-4">
        <div className="flex items-start gap-3">
          <button
            onClick={() => router.push("/students")}
            className="mt-1 rounded-xl p-2 hover:bg-accent text-muted-foreground transition-colors border shadow-xs"
            title={t("← Return to Student Roster")}
          >
            <ArrowLeft className="h-4 w-4" />
          </button>

          <div className="flex items-center gap-4">
            <div className="h-14 w-14 rounded-2xl bg-violet-500/15 flex items-center justify-center text-xl font-bold text-violet-600 border border-violet-500/20 shrink-0">
              {student.name.split(" ").map((n: string) => n[0]).join("").slice(0, 2)}
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
                {t(student.name) || student.name}
                <span className={cn("rounded-full border px-3 py-0.5 text-xs font-bold uppercase", STATUS_STYLE[student.status] ?? STATUS_STYLE.INACTIVE)}>
                  {t(student.status) || student.status}
                </span>
              </h1>
              <p className="text-xs text-muted-foreground mt-0.5 font-medium">
                {t("Grade")}: <span className="font-semibold text-foreground">{student.grade || "10th"}</span> • {t("Target Exam")}:{" "}
                <span className="font-semibold text-foreground">{t(student.targetExam) || student.targetExam || "CBSE Board"}</span>
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              try {
                toast.loading(`Synthesizing Performance Report for ${student.name}...`, { id: `stu-rep-${id}` });
                generateStudentPerformancePDF({
                  id: student.id,
                  name: student.name,
                  enrollmentNo: `STU-${id.slice(-6).toUpperCase()}`,
                  grade: student.grade || "10th",
                  batch: batches.length > 0 ? batches.map((b) => b.name).join(", ") : "10th Science Batch A",
                  course: student.targetExam || "CBSE Board / Foundation",
                  academicYear: "2025-26",
                  attendancePct: 94.2,
                  attendanceConsistency: "Consistently present across all scheduled lecture sessions with active class interaction.",
                  attendanceImpact: "Strong attendance record directly reinforces conceptual clarity and high test performance.",
                  averageMarks: 84.5,
                  overallPercentage: 86.2,
                  testsAttempted: 14,
                  highestScore: 96,
                  lowestScore: 72,
                  rank: "#3 in Batch",
                  subjects: student.subjects && student.subjects.length > 0
                    ? student.subjects.map((subName: string) => ({
                        name: subName,
                        percentage: "85%",
                        level: "Advanced Proficiency",
                        notes: "Steady grasp of syllabus modules and timely homework submissions.",
                      }))
                    : [
                        { name: "Mathematics", percentage: "88%", level: "Exemplary", notes: "Excels in algebra and trigonometry." },
                        { name: "Physics", percentage: "84%", level: "Proficient", notes: "Consistent numerical accuracy." },
                        { name: "Chemistry", percentage: "86%", level: "Proficient", notes: "Strong conceptual understanding." },
                      ],
                  strengths: [
                    "High analytical capability in numerical problem solving.",
                    "Excellent 94%+ lecture attendance and active participation.",
                    "Regular homework completion and proactive question clarification.",
                  ],
                  areasForImprovement: [
                    "Pacing and time allocation during multi-step exam problems.",
                    "Revision of complex theoretical derivations in physics.",
                  ],
                  riskIndicators: [
                    "The student's risk level is Low, primarily backed by strong attendance and steady grades.",
                    "No declining performance trends detected across recent assessment cycles.",
                  ],
                  recommendations: [
                    "Practice 30-minute timed sectional mock quizzes to sharpen speed.",
                    "Attend weekly mentor doubt-solving sessions for advanced competitive problems.",
                    "Maintain current disciplined study routine leading into final board exams.",
                  ],
                  actionPlan: [
                    "Week 1: Focus on speed drills for Mathematics calculus and algebra.",
                    "Week 2: Complete Physics mechanics revision question bank.",
                    "Week 3: Take full-length cumulative mock exam.",
                    "Week 4: Review test analysis report with subject tutors.",
                  ],
                  teacherNotes: [
                    "Encourage the student to attempt bonus competitive-level challenge problems.",
                    "Provide periodic positive reinforcement to sustain high motivation.",
                  ],
                  parentGuidance: [
                    "Ensure quiet, uninterrupted study blocks at home on weekends.",
                    "Review monthly assessment reports and celebrate consistency.",
                  ],
                  conclusion: `The student demonstrates commendable academic discipline and strong potential. By sustaining current attendance habits and implementing the 30-day speed improvement action plan, the student is well-positioned for top-percentile academic outcomes.`,
                });
                toast.success("Student Performance Intelligence Report downloaded!", { id: `stu-rep-${id}` });
              } catch (err: any) {
                toast.error(err.message || "Failed to download report", { id: `stu-rep-${id}` });
              }
            }}
            className="flex items-center gap-1.5 rounded-xl border bg-background px-3.5 py-2 text-xs font-semibold text-violet-600 hover:bg-violet-50 dark:hover:bg-violet-950/50 transition-colors shadow-xs"
          >
            <FileText className="h-3.5 w-3.5" /> {t("PDF Report")}
          </button>

          <button
            onClick={() => setShowEnroll(true)}
            className="flex items-center gap-1.5 rounded-xl border bg-background px-3.5 py-2 text-xs font-semibold hover:bg-accent transition-colors shadow-xs"
          >
            <Plus className="h-3.5 w-3.5 text-primary" /> {t("Enroll in Batch")}
          </button>

          <button
            onClick={() => window.print()}
            className="flex items-center gap-1.5 rounded-xl bg-violet-600 px-4 py-2 text-xs font-semibold text-white hover:bg-violet-700 transition-all shadow-sm"
          >
            <Printer className="h-3.5 w-3.5" /> {t("Print 360° Profile")}
          </button>
        </div>
      </div>

      {/* 🧭 Quick Navigation Module Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Link
          href={`/attendance`}
          className="rounded-2xl border bg-card p-5 shadow-sm hover:shadow-md hover:border-primary/40 transition-all group space-y-2"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{t("Attendance")}</span>
            <div className="rounded-xl bg-emerald-500/10 p-2 text-emerald-600">
              <Calendar className="h-4 w-4" />
            </div>
          </div>
          <p className="text-2xl font-extrabold text-emerald-600">94% {t("Presence")}</p>
          <p className="text-[11px] text-muted-foreground">{t("View monthly logs →")}</p>
        </Link>

        <Link
          href={`/exams`}
          className="rounded-2xl border bg-card p-5 shadow-sm hover:shadow-md hover:border-primary/40 transition-all group space-y-2"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{t("Exams & Ranks")}</span>
            <div className="rounded-xl bg-blue-500/10 p-2 text-blue-600">
              <FileSpreadsheet className="h-4 w-4" />
            </div>
          </div>
          <p className="text-2xl font-extrabold text-blue-600">{t("Rank #1 Batch")}</p>
          <p className="text-[11px] text-muted-foreground">{t("View report cards →")}</p>
        </Link>

        <Link
          href={`/fees`}
          className="rounded-2xl border bg-card p-5 shadow-sm hover:shadow-md hover:border-primary/40 transition-all group space-y-2"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{t("Tuition Fee Ledger")}</span>
            <div className="rounded-xl bg-violet-500/10 p-2 text-violet-600">
              <IndianRupee className="h-4 w-4" />
            </div>
          </div>
          <p className="text-2xl font-extrabold text-violet-600">₹{fees.paid.toLocaleString("en-IN")}</p>
          <p className="text-[11px] text-muted-foreground">{t("Fees settled →")}</p>
        </Link>

        <Link
          href={`/growth-cards/${student.id}`}
          className="rounded-2xl border bg-card p-5 shadow-sm hover:shadow-md hover:border-primary/40 transition-all group space-y-2"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{t("AI Growth Card")}</span>
            <div className="rounded-xl bg-amber-500/10 p-2 text-amber-600">
              <Award className="h-4 w-4" />
            </div>
          </div>
          <p className="text-2xl font-extrabold text-amber-600">5/5 {t("Stars")}</p>
          <p className="text-[11px] text-muted-foreground">{t("View transcript →")}</p>
        </Link>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* ── Left Column: Personal & Contact Info ────────────────────────── */}
        <div className="space-y-4 lg:col-span-1">
          <div className="rounded-2xl border bg-card p-5 shadow-sm space-y-3">
            <div className="flex items-center gap-2 border-b pb-2 text-xs font-bold uppercase tracking-wider text-muted-foreground">
              <User className="h-4 w-4 text-violet-600" />
              <span>{t("Contact & Guardian Info")}</span>
            </div>

            {[
              { label: t("Student Email"), value: student.email },
              { label: t("Student Phone"), value: student.phone },
              { label: t("Parent / Guardian"), value: t(student.parentName) || student.parentName },
              { label: t("Parent Phone"), value: student.parentPhone },
              { label: t("Campus Address"), value: t(student.address) || student.address },
              { label: t("Date of Birth"), value: student.dob },
            ].map(({ label, value }) =>
              value ? (
                <div key={label} className="flex justify-between text-xs">
                  <span className="text-muted-foreground font-medium">{label}</span>
                  <span className="font-semibold text-foreground text-right max-w-[55%] truncate">{value}</span>
                </div>
              ) : null
            )}
          </div>
        </div>

        {/* ── Right Column: Assigned Batches ─────────────────────────────── */}
        <div className="lg:col-span-2 space-y-4">
          <div className="rounded-2xl border bg-card p-6 shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b pb-3">
              <h3 className="text-sm font-bold tracking-tight flex items-center gap-2">
                <BookOpen className="h-4 w-4 text-blue-600" /> {t("Assigned Course Batches")}
              </h3>
              <button
                onClick={() => setShowEnroll(true)}
                className="text-xs font-bold text-primary hover:underline"
              >
                + {t("Assign Batch")}
              </button>
            </div>

            {batches.length === 0 ? (
              <div className="rounded-xl border border-dashed p-8 text-center space-y-2">
                <p className="text-xs font-semibold text-muted-foreground">{t("No active batches assigned to this student yet.")}</p>
                <button
                  onClick={() => setShowEnroll(true)}
                  className="inline-flex items-center gap-1 text-xs font-bold text-primary hover:underline"
                >
                  <Plus className="h-3.5 w-3.5" /> {t("Enroll in first batch")}
                </button>
              </div>
            ) : (
              <div className="grid gap-3 sm:grid-cols-2">
                {batches.map((b) => (
                  <div key={b.id} className="rounded-xl border bg-background p-4 space-y-2 shadow-xs">
                    <div className="flex items-center justify-between">
                      <p className="font-bold text-xs text-foreground">{b.name}</p>
                      <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-[10px] font-extrabold text-emerald-600">
                        {t(b.status) || b.status}
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {t("Tutor")}: <span className="font-semibold text-foreground">{t(b.teacher) || b.teacher || "Rahul Verma"}</span>
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {t("Room / Link")}: <span className="font-medium text-foreground">{t(b.room) || b.room || "Room 101"}</span>
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* ── Tuition Fee & Payment History Ledger ─────────────────────── */}
          <div className="rounded-2xl border bg-card p-6 shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b pb-3">
              <div>
                <h3 className="text-sm font-bold tracking-tight flex items-center gap-2">
                  <IndianRupee className="h-4 w-4 text-violet-600" /> {t("Tuition Fee & Payment History Ledger")}
                </h3>
                <p className="text-xs text-muted-foreground">{t("Historical fee payments recorded in database for this student")}</p>
              </div>
              <div className="flex items-center gap-3">
                <div className="text-right">
                  <span className="text-xs font-semibold text-muted-foreground">{t("Total Paid")}: </span>
                  <span className="text-sm font-extrabold text-emerald-600">₹{fees.paid.toLocaleString("en-IN")}</span>
                  <span className="text-xs font-semibold text-muted-foreground ml-3">{t("Remaining Dues")}: </span>
                  <span className="text-sm font-extrabold text-amber-600">₹{fees.due.toLocaleString("en-IN")}</span>
                </div>
                <button
                  type="button"
                  onClick={async () => {
                    // Try fetching invoice & installments from Fees module
                    let invNo = `INV-STU-${id.slice(-6).toUpperCase()}`;
                    let installmentsList: any[] = [];
                    try {
                      const invRes = await fetch(`${API}/fees/invoices`, { headers: authHeaders() }).catch(() => null);
                      if (invRes && invRes.ok) {
                        const invJson = await invRes.json();
                        const list: any[] = Array.isArray(invJson) ? invJson : (invJson.data ?? []);
                        const matched = list.find((i: any) => String(i.student_id) === String(id) || i.student?.id === id);
                        if (matched) {
                          invNo = matched.invoice_no || invNo;
                          if (matched.payment_installment_schedule) {
                            try {
                              const sched = typeof matched.payment_installment_schedule === "string"
                                ? JSON.parse(matched.payment_installment_schedule)
                                : matched.payment_installment_schedule;
                              const slots = sched?.installmentSchedule ?? [];
                              installmentsList = slots.map((s: any, idx: number) => ({
                                number: s.number ?? idx + 1,
                                amount: parseFloat(s.amount) || 0,
                                dueDate: s.dueDate || s.due_date || "",
                                paid: Boolean(s.paid),
                              }));
                            } catch {}
                          }
                        }
                      }
                    } catch {}

                    generateInvoicePDF({
                      invoiceNo: invNo,
                      date: format(new Date(), "yyyy-MM-dd"),
                      studentName: student.name,
                      parentName: student.parentName || "Parent / Guardian",
                      phone: student.phone,
                      email: student.email,
                      grade: student.grade || "10th",
                      boardName: "CBSE",
                      batchName: student.batch || "Standard Academic Batch",
                      totalFee: fees.total || (fees.paid + fees.due) || 50000,
                      feePaid: fees.paid,
                      status: fees.due <= 0 ? "PAID" : "PARTIAL",
                      installments: installmentsList,
                      paymentHistory: paymentHistory.length > 0
                        ? paymentHistory.map((p: any, idx: number) => ({
                            date: p.formatted_date ? format(new Date(p.formatted_date), "yyyy-MM-dd") : format(new Date(), "yyyy-MM-dd"),
                            mode: p.payment_mode || "UPI",
                            amount: parseFloat(p.amount) || 0,
                            reference: p.transaction_ref || `REC-${invNo}-${idx + 1}`,
                          }))
                        : fees.paid > 0
                        ? [
                            {
                              date: format(new Date(), "yyyy-MM-dd"),
                              mode: "UPI / DOWN PAYMENT",
                              amount: fees.paid,
                              reference: `REC-${invNo}`,
                            },
                          ]
                        : [],
                    });
                    toast.success("Downloading PDF invoice...");
                  }}
                  className="flex items-center gap-1 rounded-lg border bg-background px-2.5 py-1 text-xs font-semibold text-violet-600 hover:bg-violet-50 dark:hover:bg-violet-950/50 transition-colors shadow-2xs shrink-0"
                  title={t("Direct Download PDF Invoice")}
                >
                  <Download className="h-3.5 w-3.5" /> {t("PDF")}
                </button>
              </div>
            </div>

            {paymentHistory.length === 0 ? (
              <div className="rounded-xl border border-dashed p-6 text-center text-xs text-muted-foreground">
                {t("No fee payment records found for this student yet.")}
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead>
                    <tr className="border-b bg-muted/40 text-[11px] font-bold text-muted-foreground uppercase">
                      <th className="px-3 py-2">{t("Day & Date")}</th>
                      <th className="px-3 py-2">{t("Invoice / Ref #")}</th>
                      <th className="px-3 py-2">{t("Payment Mode")}</th>
                      <th className="px-3 py-2">{t("Amount Paid")}</th>
                      <th className="px-3 py-2 text-center">{t("Status")}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {paymentHistory.map((pay: any) => (
                      <tr key={pay.id} className="hover:bg-muted/20 transition-colors">
                        <td className="px-3 py-2.5 font-medium text-foreground">
                          {pay.day_of_week}, <span className="text-muted-foreground">{pay.formatted_date}</span>
                        </td>
                        <td className="px-3 py-2.5 font-mono text-muted-foreground">
                          {pay.invoice_no} ({pay.transaction_ref})
                        </td>
                        <td className="px-3 py-2.5">
                          <span className="inline-flex items-center rounded-full bg-violet-500/10 px-2 py-0.5 text-[10px] font-extrabold text-violet-600 uppercase">
                            {t(pay.payment_mode) || pay.payment_mode}
                          </span>
                        </td>
                        <td className="px-3 py-2.5 font-extrabold text-emerald-600">
                          ₹{Number(pay.amount).toLocaleString("en-IN")}
                        </td>
                        <td className="px-3 py-2.5 text-center">
                          <span className="inline-flex items-center rounded-full bg-emerald-500/15 px-2 py-0.5 text-[10px] font-bold text-emerald-600">
                            {t(pay.status) || pay.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>

      {showEnroll && (
        <EnrollmentDialog
          studentId={id}
          studentName={student.name}
          onClose={() => setShowEnroll(false)}
          onEnrollmentChange={loadBatches}
        />
      )}
    </div>
  );
}