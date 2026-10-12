"use client";
import { useState } from "react";
import { Plus, X, Pencil, Trash2, ChevronDown, ChevronUp } from "lucide-react";
import { format } from "date-fns";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { useFinanceStore } from "@/lib/stores/finance.store";
import { FeeStructureForm, type FeeStructureFormValues } from "@/components/fees/FeeStructureForm";
import type { FeeStructure } from "@/lib/types/finance";

export default function FeeStructuresPage() {
  const { feeStructures, addFeeStructure, updateFeeStructure, deleteFeeStructure } = useFinanceStore();
  const [showForm, setShowForm]         = useState(false);
  const [editTarget, setEditTarget]     = useState<FeeStructure | null>(null);
  const [expanded, setExpanded]         = useState<string | null>(null);

  async function handleCreate(data: FeeStructureFormValues) {
    const isDuplicate = feeStructures.some(
      (fs) => fs.name.trim().toLowerCase() === data.name.trim().toLowerCase()
    );
    if (isDuplicate) {
      toast.error("A fee structure with this name already exists.");
      return;
    }

    await new Promise(r => setTimeout(r, 500));
    addFeeStructure({
      ...data,
      installments: data.installments.map((inst, i) => ({ ...inst, id: `i-new-${i}-${Date.now()}` })),
    });
    toast.success("Fee structure created!");
    setShowForm(false);
  }

  async function handleEdit(data: FeeStructureFormValues) {
    if (!editTarget) return;
    const isDuplicate = feeStructures.some(
      (fs) => fs.id !== editTarget.id && fs.name.trim().toLowerCase() === data.name.trim().toLowerCase()
    );
    if (isDuplicate) {
      toast.error("Another fee structure with this name already exists.");
      return;
    }

    await new Promise(r => setTimeout(r, 500));
    updateFeeStructure(editTarget.id, {
      ...data,
      installments: data.installments.map((inst, i) => ({
        ...inst, id: editTarget.installments[i]?.id ?? `i-${Date.now()}-${i}`,
      })),
    });
    toast.success("Fee structure updated!");
    setEditTarget(null);
  }

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Fee Structures</h1>
          <p className="text-sm text-muted-foreground mt-0.5">{feeStructures.length} structures</p>
        </div>
        <button onClick={() => setShowForm(true)}
          className="flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors shadow-sm">
          <Plus className="h-4 w-4" /> New Structure
        </button>
      </div>

      <div className="space-y-3">
        {feeStructures.map(fs => (
          <div key={fs.id} className="rounded-xl border bg-card overflow-hidden shadow-sm">
            <div className="flex items-center gap-4 p-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <p className="font-semibold">{fs.name}</p>
                  <span className={cn("rounded-full border px-2 py-0.5 text-[10px] font-medium",
                    fs.isActive ? "bg-emerald-50 text-emerald-700 border-emerald-200" : "bg-slate-100 text-slate-600"
                  )}>{fs.isActive ? "Active" : "Inactive"}</span>
                </div>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {fs.course} · {fs.grade} · ₹{fs.totalAmount.toLocaleString("en-IN")} · {fs.installments.length} installments
                </p>
              </div>
              <div className="flex items-center gap-1 shrink-0">
                <button onClick={() => setEditTarget(fs)}
                  className="rounded-md p-1.5 text-muted-foreground hover:bg-accent hover:text-foreground transition-colors">
                  <Pencil className="h-3.5 w-3.5" />
                </button>
                <button onClick={() => { deleteFeeStructure(fs.id); toast.success("Deleted"); }}
                  className="rounded-md p-1.5 text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-colors">
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
                <button onClick={() => setExpanded(expanded === fs.id ? null : fs.id)}
                  className="rounded-md p-1.5 text-muted-foreground hover:bg-accent transition-colors">
                  {expanded === fs.id ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                </button>
              </div>
            </div>

            {expanded === fs.id && (
              <div className="border-t px-4 pb-4 pt-3">
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">Installments</p>
                <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                  {fs.installments.map(inst => (
                    <div key={inst.id} className="rounded-lg border bg-muted/30 px-3 py-2">
                      <p className="text-sm font-medium">{inst.label}</p>
                      <p className="text-lg font-bold text-primary mt-0.5">₹{inst.amount.toLocaleString("en-IN")}</p>
                      <p className="text-xs text-muted-foreground">{format(new Date(inst.dueDate), "dd MMM yyyy")}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {(showForm || editTarget) && (
        <>
          <div className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm"
            onClick={() => { setShowForm(false); setEditTarget(null); }} />
          <div className="fixed left-1/2 top-1/2 z-50 -translate-x-1/2 -translate-y-1/2 w-full max-w-2xl rounded-2xl border bg-background shadow-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b px-6 py-4">
              <h2 className="text-lg font-semibold">{editTarget ? "Edit Fee Structure" : "New Fee Structure"}</h2>
              <button onClick={() => { setShowForm(false); setEditTarget(null); }}
                className="rounded-lg p-1.5 hover:bg-accent"><X className="h-4 w-4" /></button>
            </div>
            <div className="px-6 py-5">
              <FeeStructureForm
                defaultValues={editTarget ? {
                  name: editTarget.name, course: editTarget.course, grade: editTarget.grade,
                  totalAmount: editTarget.totalAmount, isActive: editTarget.isActive,
                  installments: editTarget.installments.map(i => ({ label:i.label, amount:i.amount, dueDate:i.dueDate })),
                } : undefined}
                onSubmit={editTarget ? handleEdit : handleCreate}
                onCancel={() => { setShowForm(false); setEditTarget(null); }}
                submitLabel={editTarget ? "Save Changes" : "Create Structure"}
              />
            </div>
          </div>
        </>
      )}
    </div>
  );
}
