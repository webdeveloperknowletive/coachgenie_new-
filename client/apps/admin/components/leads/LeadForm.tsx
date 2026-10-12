"use client";
import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { cn } from "@/lib/utils";
import { Loader2, X } from "lucide-react";
import type { Batch } from "@/app/(dashboard)/leads/page";
import { useLanguage } from "@/components/providers/LanguageProvider";

// ─── Validation schema ────────────────────────────────────────────────────────
const schema = z.object({
  name:                 z.string().min(1, "Name is required").regex(/^[a-zA-Z\s.'-]+$/, "Name cannot contain numbers"),
  email:                z.string().email("Invalid email").or(z.literal("")),
  phone:                z.string().min(1, "Phone is required").regex(/^\d{10}$/, "Phone number must be exactly 10 digits"),
  source:               z.string().min(1, "Source is required"),
  subject:              z.string().min(1, "Interested course is required"),
  parentName:           z.string().regex(/^[a-zA-Z\s.'-]+$/, "Parent name cannot contain numbers").optional().or(z.literal("")),
  parentContactNumber:  z.string().regex(/^\d{10}$/, "Parent contact must be exactly 10 digits").optional().or(z.literal("")),
  schoolName:           z.string().optional(),
  grade:                z.string().optional(),
  notes:                z.string().optional(),
  boardName:            z.string().optional(),
  batchId:              z.string().optional(),
  subjects:             z.array(z.string()).optional(),
});

export type LeadFormValues = z.infer<typeof schema>;

// ─── Subject options ──────────────────────────────────────────────────────────
// const SUBJECT_OPTIONS = [
//   "Maths", "Physics", "Chemistry", "Biology",
//   "Science", "English", "History", "Geography",
//   "Computer Science", "Economics", "Accountancy",
// ];

// ─── Source options ───────────────────────────────────────────────────────────
const SOURCES = [
  { value: "WEBSITE",  label: "Website"     },
  { value: "REFERRAL", label: "Referral"    },
  { value: "SOCIAL",   label: "Social Media"},
  { value: "WALK_IN",  label: "Walk-in"     },
  { value: "PHONE",    label: "Phone"       },
  { value: "EMAIL",    label: "Email"       },
  { value: "WHATSAPP", label: "WhatsApp"    },
  { value: "OTHER",    label: "Other"       },
];

// ─── Board options ────────────────────────────────────────────────────────────
const BOARDS = [
  { value: "CBSE",  label: "CBSE"             },
  { value: "ICSE",  label: "ICSE / ISC"       },
  { value: "STATE", label: "State Board"      },
  { value: "IB",    label: "IB"               },
  { value: "IGCSE", label: "IGCSE / Cambridge" },
  { value: "NIOS",  label: "NIOS"             },
  { value: "OTHER", label: "Other"            },
];

// ─── Reusable field wrapper ───────────────────────────────────────────────────
function Field({
  label, required, error, children,
}: {
  label: string; required?: boolean; error?: string; children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <label className="text-sm font-medium leading-none">
        {label}
        {required && <span className="text-destructive ml-0.5">*</span>}
      </label>
      {children}
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  );
}

const inputCls = (hasError?: boolean) =>
  cn(
    "w-full rounded-lg border bg-background px-3 py-2 text-sm",
    "placeholder:text-muted-foreground",
    "focus:outline-none focus:ring-2 focus:ring-ring",
    "disabled:opacity-50 disabled:cursor-not-allowed",
    hasError && "border-destructive focus:ring-destructive"
  );

// ─── Props ────────────────────────────────────────────────────────────────────
interface LeadFormProps {
  onSubmit:        (data: LeadFormValues) => Promise<void>;
  onCancel:        () => void;
  batches?:        Batch[];
  batchesLoading?: boolean;
  defaultValues?:  Partial<LeadFormValues>;
}

// ─── Component ────────────────────────────────────────────────────────────────
export function LeadForm({
  onSubmit, onCancel, batches = [], batchesLoading = false, defaultValues,
}: LeadFormProps) {
  const { t } = useLanguage();
  const [selectedSubjects, setSelectedSubjects] = useState<string[]>(
    defaultValues?.subjects ?? []
  );

  // const {
  //   register,
  //   handleSubmit,
  //    watch,
  //   formState: { errors, isSubmitting },
  // } = useForm<LeadFormValues>({
  //   resolver: zodResolver(schema),
  //   defaultValues: {
  //     source:    "WEBSITE",
  //     email:     "",
  //     notes:     "",
  //     boardName: "",
  //     batchId:   "",
  //     subjects:  [],
  //     ...defaultValues,
  //   },
  // });

  // function toggleSubject(subject: string) {
  //   setSelectedSubjects(prev =>
  //     prev.includes(subject)
  //       ? prev.filter(s => s !== subject)
  //       : [...prev, subject]
  //   );
  // }

  const [subjectInput, setSubjectInput] = useState("");

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<LeadFormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      source:    "WEBSITE",
      email:     "",
      notes:     "",
      boardName: "",
      batchId:   "",
      subjects:  [],
      ...defaultValues,
    },
  });

  

  // function addSubject() {
  //   const s = subjectInput.trim();
  //   if (!s || selectedSubjects.includes(s)) return;
  //   setSelectedSubjects(prev => [...prev, s]);
  //   setSubjectInput("");
  // }
  function addSubject() {
    const parts = subjectInput.split(",").map(s => s.trim()).filter(Boolean);
    if (!parts.length) return;
    setSelectedSubjects(prev => [
      ...prev,
      ...parts.filter(p => !prev.includes(p)),
    ]);
    setSubjectInput("");
  }

  function removeSubject(s: string) {
    setSelectedSubjects(prev => prev.filter(x => x !== s));
  }
  const selectedBatchId = watch("batchId");

 useEffect(() => {
    if (!selectedBatchId) {
      setSelectedSubjects([]);
      return;
    }
    const batch = batches.find(b => b.id === selectedBatchId);
    // Always reset — even if new batch has no subjects
    setSelectedSubjects(
      batch?.subjects?.filter((s: string) => s && s !== "N/A") ?? []
    );
  }, [selectedBatchId, batches]);

  

  async function handleFormSubmit(data: LeadFormValues) {
    await onSubmit({ ...data, subjects: selectedSubjects });
  }

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-5" noValidate>

      {/* ── Student Info ─────────────────────────────────────────────────── */}
      <SectionTitle>{t("Student Information")}</SectionTitle>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Field label={t("Full Name")} required error={errors.name?.message}>
          <input
            data-testid="lead-name"
            {...register("name", {
              onChange: (e) => {
                e.target.value = e.target.value.replace(/[^a-zA-Z\s.'-]/g, "");
              },
            })}
            placeholder={t("Student's full name")}
            className={inputCls(!!errors.name)}
          />
        </Field>

        <Field label={t("Email")} error={errors.email?.message}>
          <input data-testid="lead-email" {...register("email")} type="email" placeholder="student@example.com" className={inputCls(!!errors.email)} />
        </Field>

        <Field label={t("Phone (10 Digits)")} required error={errors.phone?.message}>
          <input
            data-testid="lead-phone"
            maxLength={10}
            inputMode="numeric"
            {...register("phone", {
              onChange: (e) => {
                e.target.value = e.target.value.replace(/\D/g, "").slice(0, 10);
              },
            })}
            placeholder="9876543210"
            className={inputCls(!!errors.phone)}
          />
        </Field>

        <Field label={t("Grade")} error={errors.grade?.message}>
          <input data-testid="lead-grade" {...register("grade")} placeholder="e.g. 10, 11, 12" className={inputCls(!!errors.grade)} />
        </Field>

        <Field label={t("Board Name")} error={errors.boardName?.message}>
          <select {...register("boardName")} className={inputCls(!!errors.boardName)}>
            <option value="">{t("— Select Board —")}</option>
            {BOARDS.map((b) => (
              <option key={b.value} value={b.value}>{t(b.label)}</option>
            ))}
          </select>
        </Field>
      </div>

      {/* ── Academic & Batch ─────────────────────────────────────────────── */}
      <SectionTitle>{t("Academic & Batch")}</SectionTitle>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Field label={t("Interested Course")} required error={errors.subject?.message}>
          <input {...register("subject")} placeholder="e.g. JEE Mains, NEET, Foundation" className={inputCls(!!errors.subject)} />
        </Field>

        <Field label={t("Batch Name")} error={errors.batchId?.message}>
          <div className="relative">
            <select {...register("batchId")} disabled={batchesLoading} className={inputCls(!!errors.batchId)}>
              <option value="">{batchesLoading ? t("Loading batches…") : t("— Select Batch —")}</option>
              {batches.map((b) => (
                <option key={b.id} value={b.id}>{b.name}</option>
              ))}
            </select>
            {batchesLoading && (
              <Loader2 className="absolute right-3 top-2.5 h-4 w-4 animate-spin text-muted-foreground pointer-events-none" />
            )}
          </div>
        </Field>

        <Field label={t("Source")} required error={errors.source?.message}>
          <select {...register("source")} className={inputCls(!!errors.source)}>
            {SOURCES.map((s) => (
              <option key={s.value} value={s.value}>{t(s.label)}</option>
            ))}
          </select>
        </Field>

        <Field label={t("School Name")} error={errors.schoolName?.message}>
          <input {...register("schoolName")} placeholder={t("School / college name")} className={inputCls(!!errors.schoolName)} />
        </Field>
      </div>

      {/* ── Subjects ────────────────────────────────────────────────────── */}
      <Field label={t("Subjects")}>
        <div className="flex gap-2">
          <input
            value={subjectInput}
            onChange={e => setSubjectInput(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); addSubject(); } }}
            placeholder={selectedBatchId ? t("Add more subjects…") : t("e.g. Physics, Maths…")}
            className={inputCls()}
          />
          <button
            type="button"
            onClick={addSubject}
            className="rounded-lg border px-3 py-2 text-sm font-medium hover:bg-accent transition-colors shrink-0"
          >
            {t("Add")}
          </button>
        </div>
        {selectedSubjects.length > 0 ? (
          <div className="flex flex-wrap gap-1.5 pt-2">
            {selectedSubjects.map(s => (
              <span key={s}
                className="flex items-center gap-1 rounded-full bg-primary/10 text-primary text-xs px-2.5 py-0.5 font-medium border border-primary/20">
                {s}
                <button type="button" onClick={() => removeSubject(s)}
                  className="hover:text-destructive transition-colors">
                  <X className="h-3 w-3" />
                </button>
              </span>
            ))}
          </div>
        ) : (
          <p className="text-xs text-muted-foreground pt-1">
            {selectedBatchId
              ? t("No subjects in this batch — add them above")
              : t("Select a batch to auto-fill subjects, or add manually")}
          </p>
        )}
      </Field>

      {/* ── Parent Info ───────────────────────────────────────────────────── */}
      <SectionTitle>{t("Parent / Guardian")}</SectionTitle>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Field label={t("Parent Name")} error={errors.parentName?.message}>
          <input
            {...register("parentName", {
              onChange: (e) => {
                e.target.value = e.target.value.replace(/[^a-zA-Z\s.'-]/g, "");
              },
            })}
            placeholder={t("Parent / guardian name")}
            className={inputCls(!!errors.parentName)}
          />
        </Field>

        <Field label={t("Parent Contact (10 Digits)")} error={errors.parentContactNumber?.message}>
          <input
            maxLength={10}
            inputMode="numeric"
            {...register("parentContactNumber", {
              onChange: (e) => {
                e.target.value = e.target.value.replace(/\D/g, "").slice(0, 10);
              },
            })}
            placeholder="9876543210"
            className={inputCls(!!errors.parentContactNumber)}
          />
        </Field>
      </div>

      {/* ── Notes ────────────────────────────────────────────────────────── */}
      <Field label={t("Notes")} error={errors.notes?.message}>
        <textarea
          {...register("notes")}
          rows={3}
          placeholder={t("Any additional notes…")}
          className={cn(inputCls(!!errors.notes), "resize-none")}
        />
      </Field>

      {/* ── Actions ──────────────────────────────────────────────────────── */}
      <div className="flex justify-end gap-3 pt-1">
        <button
          type="button"
          onClick={onCancel}
          disabled={isSubmitting}
          data-testid="lead-form-cancel"
          className="rounded-lg border px-4 py-2 text-sm font-medium hover:bg-accent transition-colors disabled:opacity-50"
        >
          {t("Cancel")}
        </button>
        <button
          type="submit"
          disabled={isSubmitting}
          data-testid="lead-form-submit"
          className="flex items-center gap-2 rounded-lg bg-primary px-5 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50 shadow-sm"
        >
          {isSubmitting && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
          {isSubmitting ? t("Saving…") : t("Create Lead")}
        </button>
      </div>
    </form>
  );
}

// ── tiny helper ───────────────────────────────────────────────────────────────
function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-3">
      <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground whitespace-nowrap">
        {children}
      </p>
      <div className="h-px flex-1 bg-border" />
    </div>
  );
}

