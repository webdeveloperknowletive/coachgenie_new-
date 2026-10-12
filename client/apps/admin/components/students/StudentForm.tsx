"use client";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Loader2 } from "lucide-react";
import type { Student } from "@/lib/types/academic";
import { useLanguage } from "@/components/providers/LanguageProvider";

const schema = z.object({
  name:        z.string().min(2, "Name must be at least 2 characters").regex(/^[a-zA-Z\s.'-]+$/, "Name cannot contain numbers"),
  email:       z.string().email("Invalid email address").optional().or(z.literal("")),
  phone:       z.string().regex(/^\d{10}$/, "Phone must be exactly 10 digits").optional().or(z.literal("")),
  parentName:  z.string().regex(/^[a-zA-Z\s.'-]+$/, "Parent name cannot contain numbers").optional().or(z.literal("")),
  parentPhone: z.string().regex(/^\d{10}$/, "Parent phone must be exactly 10 digits").optional().or(z.literal("")),
  grade:       z.string().optional().or(z.literal("")),
  subjects:    z.string().optional().or(z.literal("")),
  address:     z.string().optional().or(z.literal("")),
  dob:         z.string().optional().or(z.literal("")),
  status:      z.enum(["ACTIVE", "INACTIVE", "SUSPENDED", "GRADUATED"]),
  targetExam:  z.string().optional().or(z.literal("")),
  schoolName:  z.string().optional().or(z.literal("")),
  gender:      z.string().optional().or(z.literal("")),
});
export type StudentFormValues = z.infer<typeof schema>;

const inputCls = "flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring";

function normalizeGrade(grade?: string): string {
  if (!grade) return "";
  const clean = grade.trim();
  if (/^\d+$/.test(clean)) {
    return `${clean}th`;
  }
  return clean;
}

function normalizeDob(dob?: string): string {
  if (!dob) return "";
  return String(dob).split("T")[0];
}

interface StudentFormProps {
  defaultValues?: Partial<Student>;
  onSubmit:  (d: StudentFormValues) => Promise<void>;
  onCancel:  () => void;
  submitLabel?: string;
}

const Field = ({ label, error, className, children }: { label: string; error?: string; className?: string; children: React.ReactNode }) => (
  <div className={`space-y-1.5 ${className ?? ""}`}>
    <label className="text-sm font-medium">{label}</label>
    {children}
    {error && <p className="text-xs text-destructive">{error}</p>}
  </div>
);

export function StudentForm({ defaultValues, onSubmit, onCancel, submitLabel = "Create Student" }: StudentFormProps) {
  const { language, t } = useLanguage();
  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<StudentFormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name:        defaultValues?.name        ?? "",
      email:       defaultValues?.email       ?? "",
      phone:       defaultValues?.phone       ?? "",
      parentName:  defaultValues?.parentName  ?? "",
      parentPhone: defaultValues?.parentPhone ?? "",
      grade:       normalizeGrade(defaultValues?.grade),
      subjects:    Array.isArray(defaultValues?.subjects) ? defaultValues.subjects.join(", ") : (defaultValues?.subjects ?? ""),
      address:     defaultValues?.address     ?? "",
      dob:         normalizeDob(defaultValues?.dob),
      status:      defaultValues?.status      ?? "ACTIVE",
      targetExam:  defaultValues?.targetExam  ?? "",
      schoolName:  defaultValues?.schoolName  ?? "",
      gender:      defaultValues?.gender      ?? "",
    },
  });

  useEffect(() => {
    if (defaultValues) {
      reset({
        name:        defaultValues.name        ?? "",
        email:       defaultValues.email       ?? "",
        phone:       defaultValues.phone       ?? "",
        parentName:  defaultValues.parentName  ?? "",
        parentPhone: defaultValues.parentPhone ?? "",
        grade:       normalizeGrade(defaultValues.grade),
        subjects:    Array.isArray(defaultValues.subjects) ? defaultValues.subjects.join(", ") : (defaultValues.subjects ?? ""),
        address:     defaultValues.address     ?? "",
        dob:         normalizeDob(defaultValues.dob),
        status:      defaultValues.status      ?? "ACTIVE",
        targetExam:  defaultValues.targetExam  ?? "",
        schoolName:  defaultValues.schoolName  ?? "",
        gender:      defaultValues.gender      ?? "",
      });
    }
  }, [defaultValues, reset]);

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Field label={t("Student Name")} error={errors.name?.message}>
          <input
            {...register("name", {
              onChange: (e) => {
                e.target.value = e.target.value.replace(/[^a-zA-Z\s.'-]/g, "");
              },
            })}
            placeholder="Aarav Sharma"
            className={inputCls}
          />
        </Field>
        <Field label={t("Date of Birth")} error={errors.dob?.message}>
          <input {...register("dob")} type="date" className={inputCls} />
        </Field>
        <Field label={t("Email")} error={errors.email?.message}>
          <input {...register("email")} type="email" placeholder="aarav@gmail.com" className={inputCls} />
        </Field>
        <Field label={t("Phone (10 Digits)")} error={errors.phone?.message}>
          <input
            maxLength={10}
            inputMode="numeric"
            {...register("phone", {
              onChange: (e) => {
                e.target.value = e.target.value.replace(/\D/g, "").slice(0, 10);
              },
            })}
            placeholder="9876543210"
            className={inputCls}
          />
        </Field>
        <Field label={t("Parent Name")} error={errors.parentName?.message}>
          <input
            {...register("parentName", {
              onChange: (e) => {
                e.target.value = e.target.value.replace(/[^a-zA-Z\s.'-]/g, "");
              },
            })}
            placeholder="Suresh Sharma"
            className={inputCls}
          />
        </Field>
        <Field label={t("Parent Phone (10 Digits)")} error={errors.parentPhone?.message}>
          <input
            maxLength={10}
            inputMode="numeric"
            {...register("parentPhone", {
              onChange: (e) => {
                e.target.value = e.target.value.replace(/\D/g, "").slice(0, 10);
              },
            })}
            placeholder="9876543200"
            className={inputCls}
          />
        </Field>
        <Field label={t("Grade")} error={errors.grade?.message}>
          <select {...register("grade")} className={inputCls}>
            <option value="">{t("Select Grade")}</option>
            {["8th", "9th", "10th", "11th", "12th", "Dropper"].map((g) => (
              <option key={g} value={g}>{g}</option>
            ))}
          </select>
        </Field>
        <Field label={t("Status")} error={errors.status?.message}>
          <select {...register("status")} className={inputCls}>
            <option value="ACTIVE">{t("Active")}</option>
            <option value="INACTIVE">{t("Inactive")}</option>
            <option value="SUSPENDED">{t("Suspended")}</option>
            <option value="GRADUATED">{t("Graduated")}</option>
          </select>
        </Field>
        <Field label={t("Subjects (comma separated)")} error={errors.subjects?.message}>
          <input {...register("subjects")} placeholder="Mathematics, Physics" className={inputCls} />
        </Field>
        <Field label={t("Target Exam")} error={errors.targetExam?.message}>
          <input {...register("targetExam")} placeholder="JEE, NEET, Boards" className={inputCls} />
        </Field>
        <Field label={t("School Name")} error={errors.schoolName?.message}>
          <input {...register("schoolName")} placeholder="Delhi Public School" className={inputCls} />
        </Field>
        <Field label={t("Gender")} error={errors.gender?.message}>
          <select {...register("gender")} className={inputCls}>
            <option value="">{t("Select")}</option>
            <option value="MALE">{t("Male")}</option>
            <option value="FEMALE">{t("Female")}</option>
            <option value="OTHER">{t("Other")}</option>
          </select>
        </Field>
        <Field label={t("Address")} error={errors.address?.message} className="col-span-1 sm:col-span-2">
          <input {...register("address")} placeholder="Shivajinagar, Pune" className={inputCls} />
        </Field>
      </div>
      <div className="flex justify-end gap-3 pt-2 border-t">
        <button
          type="button"
          onClick={onCancel}
          className="rounded-md border px-4 py-2 text-sm font-medium hover:bg-accent transition-colors"
        >
          {t("Cancel")}
        </button>
        <button
          type="submit"
          disabled={isSubmitting}
          className="flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-60 transition-colors"
        >
          {isSubmitting && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
          {submitLabel}
        </button>
      </div>
    </form>
  );
}
