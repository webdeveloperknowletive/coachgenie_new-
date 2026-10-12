"use client";
import { useState, useEffect } from "react";
import { X, Loader2, IndianRupee, UserCheck, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { format } from "date-fns";
import { cn } from "@/lib/utils";
import type { Lead } from "@/lib/types/lead";
import { authHeaders } from "@/lib/auth-headers";
import {
  createInitialInstallmentSchedule,
  rebalanceInstallmentSchedule,
  addInstallmentToSchedule,
  removeInstallmentFromSchedule,
  type InstallmentItem,
} from "@/lib/utils/installment-rebalancer";

const API = "/api/proxy";

const REQUIRED_DOCUMENTS = [
  { id: "aadhar",    label: "Aadhar Card",          required: true  },
  { id: "marksheet", label: "Previous Marksheet",   required: true  },
  { id: "photo",     label: "Passport Photo",       required: true  },
  { id: "tc",        label: "Transfer Certificate", required: false },
  { id: "address",   label: "Address Proof",        required: false },
  { id: "birth",     label: "Birth Certificate",    required: false },
];

const PAYMENT_MODES = [
  { value: "CASH",          label: "Cash"          },
  { value: "UPI",           label: "UPI"           },
  { value: "BANK_TRANSFER", label: "Bank Transfer" },
  { value: "CHEQUE",        label: "Cheque"        },
  { value: "CARD",          label: "Card"          },
];

interface ConvertLeadModalProps {
  lead: Lead;
  onClose: () => void;
  onSuccess: (admission: any) => void;
}

export function ConvertLeadModal({ lead, onClose, onSuccess }: ConvertLeadModalProps) {
  const [totalFee, setTotalFee] = useState<string>("50000");
  const [amountPaid, setAmountPaid] = useState<string>("0");
  const [modeOfPayment, setModeOfPayment] = useState<string>("UPI");
  const [dateOfPayment, setDateOfPayment] = useState<string>(format(new Date(), "yyyy-MM-dd"));
  const [hasInstallments, setHasInstallments] = useState<boolean>(false);
  const [numberOfInstallments, setNumberOfInstallments] = useState<number>(3);
  const [customSchedule, setCustomSchedule] = useState<InstallmentItem[]>([]);
  const [selectedDocs, setSelectedDocs] = useState<string[]>(["aadhar", "marksheet", "photo"]);
  const [notes, setNotes] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const numTotalFee = parseFloat(totalFee) || 0;
  const numAmountPaid = parseFloat(amountPaid) || 0;
  const remaining = Math.max(0, numTotalFee - numAmountPaid);

  let payStatus: "UNPAID" | "PARTIAL" | "FULL" = "UNPAID";
  if (numAmountPaid >= numTotalFee && numTotalFee > 0) payStatus = "FULL";
  else if (numAmountPaid > 0) payStatus = "PARTIAL";

  // Re-initialize installment schedule on count or remaining change
  useEffect(() => {
    if (hasInstallments && remaining > 0) {
      setCustomSchedule(createInitialInstallmentSchedule(remaining, numberOfInstallments));
    }
  }, [hasInstallments, numberOfInstallments, remaining]);

  function setNumInstallments(n: number) {
    setNumberOfInstallments(n);
    if (remaining > 0) {
      setCustomSchedule(createInitialInstallmentSchedule(remaining, n));
    }
  }

  function handleAmountChange(idx: number, newVal: number) {
    setCustomSchedule((prev) => rebalanceInstallmentSchedule(prev, remaining, idx, newVal));
  }

  function handleDateChange(idx: number, dateStr: string) {
    setCustomSchedule((prev) =>
      prev.map((item, i) => (i === idx ? { ...item, dueDate: dateStr } : item))
    );
  }

  function handleAddTerm() {
    setCustomSchedule((prev) => {
      const updated = addInstallmentToSchedule(prev, remaining);
      setNumberOfInstallments(updated.length);
      return updated;
    });
  }

  function handleRemoveTerm(idx: number) {
    setCustomSchedule((prev) => {
      const updated = removeInstallmentFromSchedule(prev, idx, remaining);
      setNumberOfInstallments(updated.length);
      return updated;
    });
  }

  function toggleDoc(docId: string) {
    setSelectedDocs(prev =>
      prev.includes(docId) ? prev.filter(id => id !== docId) : [...prev, docId]
    );
  }

  async function handleConfirmConversion() {
    if (numTotalFee < 0 || numAmountPaid < 0) {
      toast.error("Fee amounts cannot be negative");
      return;
    }
    if (numAmountPaid > numTotalFee) {
      toast.error("Amount paid cannot exceed total fee");
      return;
    }

    setIsSubmitting(true);
    try {
      let admStatus: "PENDING_DOCS" | "FEE_PENDING" | "CONFIRMED" = "PENDING_DOCS";
      if (payStatus === "FULL") admStatus = "CONFIRMED";
      else if (payStatus === "PARTIAL") admStatus = "FEE_PENDING";

      const schedule = hasInstallments && remaining > 0 && customSchedule.length > 0
        ? customSchedule.map((inst) => ({
            number: inst.number,
            amount: inst.amount,
            dueDate: inst.dueDate || format(new Date(), "yyyy-MM-dd"),
            paid: inst.paid || false,
          }))
        : [];

      const documents = REQUIRED_DOCUMENTS.map(doc => ({
        name: doc.label,
        required: doc.required,
        submitted: selectedDocs.includes(doc.id),
      }));

      const payload = {
        lead_id: lead.id,
        student_name: lead.name,
        email: lead.email || undefined,
        phone: lead.phone || undefined,
        parent_name: lead.parentName || undefined,
        parent_phone: lead.parentContactNumber || undefined,
        school_name: lead.schoolName || undefined,
        grade: lead.grade || undefined,
        board_name: lead.boardName || undefined,
        batch_id: lead.batchId || undefined,
        batch_name: lead.batchName || undefined,
        subjects: Array.isArray(lead.subject)
          ? lead.subject
          : [lead.subject].filter(Boolean),
        applied_course: Array.isArray(lead.subject)
          ? lead.subject[0]
          : lead.subject || "N/A",
        status: admStatus,
        fee_amount: numTotalFee,
        fee_paid: numAmountPaid,
        documents,
        payment: {
          totalFee: numTotalFee,
          amountPaid: numAmountPaid,
          remaining,
          paymentStatus: payStatus,
          dateOfPayment,
          modeOfPayment,
          hasInstallments,
          numberOfInstallments,
          installmentAmount: customSchedule[0]?.amount ?? (hasInstallments && numberOfInstallments > 0 ? Math.ceil(remaining / numberOfInstallments) : 0),
          installmentSchedule: schedule,
          notes,
        },
      };

      const res = await fetch(`${API}/admissions`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        const detail = Array.isArray(err.detail)
          ? err.detail.map((e: any) => `${e.loc?.slice(-1)[0]}: ${e.msg}`).join(", ")
          : (err.detail ?? "Failed to create admission");
        throw new Error(detail);
      }

      const json = await res.json();
      const admission = json.data ?? json;

      // Also update lead status to enrolled
      await fetch(`${API}/leads/${lead.id}`, {
        method: "PATCH",
        headers: authHeaders(),
        body: JSON.stringify({ status: "enrolled" }),
      }).catch(() => null);

      toast.success(`${lead.name} converted to admission with fee details!`);
      onSuccess(admission);
    } catch (err: any) {
      toast.error(err.message ?? "Conversion failed");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div className="fixed left-1/2 top-1/2 z-50 -translate-x-1/2 -translate-y-1/2 w-full max-w-2xl rounded-2xl border bg-background shadow-2xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between border-b px-6 py-4 shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="h-9 w-9 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center">
              <UserCheck className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold">Convert to Admission</h2>
              <p className="text-xs text-muted-foreground">Setup course fees & admission details for {lead.name}</p>
            </div>
          </div>
          <button onClick={onClose} className="rounded-lg p-1.5 hover:bg-accent text-muted-foreground">
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Form Body */}
        <div className="px-6 py-5 overflow-y-auto space-y-5 flex-1 text-sm">
          {/* Summary Strip */}
          <div className="rounded-xl border bg-muted/40 p-4 grid grid-cols-2 sm:grid-cols-3 gap-3">
            <div>
              <p className="text-xs text-muted-foreground">Student Name</p>
              <p className="font-semibold">{lead.name}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Course / Grade</p>
              <p className="font-semibold">{lead.subject || "N/A"} {lead.grade ? `(${lead.grade})` : ""}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Batch</p>
              <p className="font-semibold">{lead.batchName || "Not assigned"}</p>
            </div>
          </div>

          {/* Fee Section */}
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              <IndianRupee className="h-3.5 w-3.5" /> Fee Setup
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-medium">Total Course Fee (₹) <span className="text-destructive">*</span></label>
                <input
                  type="number"
                  value={totalFee}
                  onChange={e => setTotalFee(e.target.value)}
                  placeholder="e.g. 50000"
                  className="w-full rounded-lg border bg-background px-3 py-2 text-sm font-semibold outline-none focus:ring-2 focus:ring-primary/30"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium">Initial Amount Paid (₹)</label>
                <input
                  type="number"
                  value={amountPaid}
                  onChange={e => setAmountPaid(e.target.value)}
                  placeholder="0"
                  className="w-full rounded-lg border bg-background px-3 py-2 text-sm font-semibold outline-none focus:ring-2 focus:ring-primary/30"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium">Remaining Due (₹)</label>
                <div className="w-full rounded-lg border bg-muted px-3 py-2 text-sm font-bold text-amber-600">
                  ₹{remaining.toLocaleString("en-IN")}
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium">Payment Mode</label>
                <select
                  value={modeOfPayment}
                  disabled={numAmountPaid <= 0}
                  onChange={e => setModeOfPayment(e.target.value)}
                  className="w-full rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary/30 disabled:opacity-50"
                >
                  {PAYMENT_MODES.map(m => (
                    <option key={m.value} value={m.value}>{m.label}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Installments Option */}
            <div className="pt-2 space-y-3">
              <label className="flex items-center gap-2 cursor-pointer text-xs font-semibold">
                <input
                  type="checkbox"
                  checked={hasInstallments}
                  disabled={remaining <= 0}
                  onChange={e => setHasInstallments(e.target.checked)}
                  className="h-4 w-4 rounded accent-primary"
                />
                Enable Installment Schedule for Remaining Balance
              </label>

              {hasInstallments && remaining > 0 && (
                <div className="rounded-xl border bg-card p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="space-y-1">
                      <label className="text-xs text-muted-foreground font-medium">Number of Installments</label>
                      <select
                        value={numberOfInstallments}
                        onChange={e => setNumInstallments(parseInt(e.target.value))}
                        className="rounded-lg border bg-background px-3 py-1 text-xs outline-none font-semibold"
                      >
                        {[1, 2, 3, 4, 5, 6, 9, 12].map(n => (
                          <option key={n} value={n}>{n} Installments</option>
                        ))}
                      </select>
                    </div>

                    <button
                      type="button"
                      onClick={handleAddTerm}
                      className="flex items-center gap-1 text-xs font-bold text-violet-600 bg-violet-50 dark:bg-violet-950/50 hover:bg-violet-100 dark:hover:bg-violet-900/60 px-3 py-1.5 rounded-lg border border-violet-200/60 transition-all"
                    >
                      <Plus className="h-3.5 w-3.5" /> Add Term
                    </button>
                  </div>

                  <div className="space-y-2 pt-1">
                    {customSchedule.map((inst, i) => (
                      <div key={i} className="grid grid-cols-12 gap-2 items-center text-xs border rounded-lg p-2 bg-muted/20">
                        <span className="col-span-3 font-bold text-foreground">Term #{inst.number}</span>
                        <div className="col-span-4">
                          <input
                            type="date"
                            value={inst.dueDate}
                            onChange={e => handleDateChange(i, e.target.value)}
                            className="w-full rounded-md border bg-background px-2 py-1 text-xs outline-none"
                          />
                        </div>
                        <div className="col-span-4 flex items-center gap-1">
                          <span className="text-muted-foreground font-semibold">₹</span>
                          <input
                            type="number"
                            min="0"
                            value={inst.amount}
                            onChange={e => handleAmountChange(i, parseFloat(e.target.value) || 0)}
                            className="w-full rounded-md border bg-background px-2 py-1 text-xs font-bold text-foreground outline-none focus:ring-1 focus:ring-violet-500"
                          />
                        </div>
                        <div className="col-span-1 text-right">
                          {customSchedule.length > 1 && (
                            <button
                              type="button"
                              onClick={() => handleRemoveTerm(i)}
                              className="text-muted-foreground hover:text-destructive p-1 rounded transition-colors"
                              title="Remove installment term"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Required Documents */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Submitted Documents</label>
            <div className="grid grid-cols-2 gap-2">
              {REQUIRED_DOCUMENTS.map(doc => {
                const isSelected = selectedDocs.includes(doc.id);
                return (
                  <label
                    key={doc.id}
                    className={cn(
                      "flex items-center gap-2 rounded-lg border px-3 py-2 text-xs cursor-pointer transition-all",
                      isSelected ? "border-primary/40 bg-primary/5 font-medium" : "hover:bg-accent"
                    )}
                  >
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => toggleDoc(doc.id)}
                      className="h-3.5 w-3.5 rounded accent-primary shrink-0"
                    />
                    <span className="flex-1">{doc.label}</span>
                    {doc.required && <span className="text-[10px] text-destructive font-bold">Req</span>}
                  </label>
                );
              })}
            </div>
          </div>

          {/* Notes */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium">Conversion Notes</label>
            <textarea
              value={notes}
              onChange={e => setNotes(e.target.value)}
              rows={2}
              placeholder="Any admission or payment comments..."
              className="w-full rounded-lg border bg-background px-3 py-2 text-xs outline-none resize-none"
            />
          </div>
        </div>

        {/* Actions Footer */}
        <div className="flex items-center justify-end gap-3 border-t px-6 py-4 shrink-0">
          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            className="rounded-lg border px-4 py-2 text-sm font-medium hover:bg-accent transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleConfirmConversion}
            disabled={isSubmitting || numTotalFee <= 0}
            className="flex items-center gap-2 rounded-lg bg-emerald-600 px-5 py-2 text-sm font-bold text-white hover:bg-emerald-700 transition-colors shadow-sm disabled:opacity-50"
          >
            {isSubmitting ? (
              <><Loader2 className="h-4 w-4 animate-spin" /> Converting…</>
            ) : (
              <><UserCheck className="h-4 w-4" /> Confirm & Convert Admission</>
            )}
          </button>
        </div>
      </div>
    </>
  );
}
