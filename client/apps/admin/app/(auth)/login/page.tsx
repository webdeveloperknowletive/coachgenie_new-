"use client";

import { useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import {
  Eye,
  EyeOff,
  GraduationCap,
  Loader2,
} from "lucide-react";
import { useAuthStore } from "@/lib/stores/auth.store";
import { CoachGenieLogo } from "@/components/common/CoachGenieLogo";

const schema = z.object({
  institute: z.string().optional(),
  email: z.string().email("Enter a valid email"),
  password: z.string().min(1, "Password required"),
});

type LoginInput = z.infer<typeof schema>;

export default function LoginPage() {
  const setUser = useAuthStore((s) => s.setUser);
  const [showPw, setShowPw] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginInput>({
    resolver: zodResolver(schema),
    defaultValues: {
      institute: "",
      email: "",
    },
  });

  async function onSubmit(data: LoginInput) {
    try {
      const loginUrl = `${process.env.NEXT_PUBLIC_API_URL ??
        "http://localhost:8000/api/v1"
        }/auth/login`;

      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      if (data.institute && data.institute.trim()) {
        headers["X-Tenant-Subdomain"] = data.institute.trim();
      }

      const backendRes = await fetch(loginUrl, {
        method: "POST",
        headers,
        body: JSON.stringify({
          email: data.email,
          password: data.password,
        }),
      });

      const responseText = await backendRes.text();

      if (!backendRes.ok) {
        let errorMsg = "Login failed";
        try {
          const errObj = JSON.parse(responseText);
          errorMsg = errObj.detail || errObj.message || "Invalid credentials";
        } catch {
          errorMsg = responseText || "Login failed";
        }
        toast.error(errorMsg);
        return;
      }

      const parsed = JSON.parse(responseText);

      const {
        access_token,
        refresh_token = null,
        user = null,
      } = parsed;

      const sessionRes = await fetch("/api/auth/session", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          access_token,
          refresh_token,
          user,
        }),
      });

      const sessionText = await sessionRes.text();

      if (!sessionRes.ok) {
        throw new Error(sessionText);
      }

      const session = JSON.parse(sessionText);

      if (session.user) {
        setUser(session.user);
      }

      toast.success("Login successful");

      window.location.href = "/dashboard";
    } catch (err) {
      toast.error(
        err instanceof Error
          ? err.message
          : "Something went wrong"
      );
    }
  }

  return (
    <div
      data-no-translate
      lang="en"
      className="rounded-2xl border bg-card shadow-xl shadow-black/5 p-8 space-y-6 fade-in"
    >
      <div className="flex flex-col items-center gap-2 text-center">
        <CoachGenieLogo size="xl" className="shadow-lg shadow-violet-500/20" />

        <h1 className="text-2xl font-bold tracking-tight bg-gradient-to-r from-violet-600 to-indigo-600 bg-clip-text text-transparent">
          CoachGenie
        </h1>

        <p className="text-sm text-muted-foreground">
          Sign in to your admin portal
        </p>
      </div>

      <form
        onSubmit={handleSubmit(onSubmit)}
        className="space-y-4"
      >
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium">
              Institute Code
            </label>
            <span className="text-[11px] text-muted-foreground">Optional for Super Admin</span>
          </div>

          <input
            {...register("institute")}
            type="text"
            placeholder="demo (or leave blank for Super Admin)"
            autoComplete="off"
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          />

          {errors.institute && (
            <p className="text-xs text-destructive">
              {errors.institute.message}
            </p>
          )}
        </div>

        <div className="space-y-1.5">
          <label className="text-sm font-medium">
            Email
          </label>

          <input
            {...register("email")}
            type="email"
            placeholder="admin@example.com"
            autoComplete="email"
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          />

          {errors.email && (
            <p className="text-xs text-destructive">
              {errors.email.message}
            </p>
          )}
        </div>

        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium">
              Password
            </label>

            <Link
              href="/forgot-password"
              className="text-xs text-primary hover:underline"
            >
              Forgot password?
            </Link>
          </div>

          <div className="relative">
            <input
              {...register("password")}
              type={showPw ? "text" : "password"}
              placeholder="••••••••"
              autoComplete="current-password"
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 pr-10 text-sm"
            />

            <button
              type="button"
              onClick={() => setShowPw((v) => !v)}
              className="absolute right-3 top-1/2 -translate-y-1/2"
            >
              {showPw ? (
                <EyeOff className="h-4 w-4" />
              ) : (
                <Eye className="h-4 w-4" />
              )}
            </button>
          </div>

          {errors.password && (
            <p className="text-xs text-destructive">
              {errors.password.message}
            </p>
          )}
        </div>

        <button
          type="submit"
          disabled={isSubmitting}
          className="flex w-full items-center justify-center gap-2 rounded-md bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground disabled:opacity-50"
        >
          {isSubmitting && (
            <Loader2 className="h-4 w-4 animate-spin" />
          )}

          {isSubmitting
            ? "Signing in..."
            : "Sign in"}
        </button>
      </form>
    </div>
  );
}