

"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";

import { AppShell } from "@/components/layout/AppShell";
import { useAuthStore, type UserRole } from "@/lib/stores/auth.store";

const MODULE_ROLES: Record<string, UserRole[]> = {
  "/dashboard": ["super_admin", "owner", "admin", "counselor", "tutor", "coach"],
  "/platform": ["super_admin"],
  "/automation": ["owner", "admin", "counselor"],
  "/leads": ["owner", "admin", "counselor"],
  "/admissions": ["owner", "admin", "counselor"],
  "/students": ["owner", "admin", "counselor", "tutor", "coach"],
  "/batches": ["owner", "admin", "counselor", "tutor", "coach"],
  "/exams": ["owner", "admin", "tutor", "coach"],
  "/sessions": ["owner", "admin", "tutor", "coach"],
  "/attendance": ["owner", "admin", "tutor", "coach"],
  "/billing": ["owner"],
  "/settings": ["owner", "admin"],
  "/fees": ["owner", "admin", "counselor"],
  "/growth-cards": ["owner", "admin", "counselor", "tutor", "coach"],
  "/notifications": ["owner", "admin", "counselor", "tutor", "coach"],
  "/ai": ["super_admin", "owner", "admin", "counselor", "tutor", "coach"],
  "/docs": ["super_admin", "owner", "admin", "counselor", "tutor", "coach"],
};

function getAllowedRoles(pathname: string): UserRole[] {
  const match = Object.keys(MODULE_ROLES)
    .sort((a, b) => b.length - a.length)
    .find(
      (path) => pathname === path || pathname.startsWith(`${path}/`)
    );

  return match ? MODULE_ROLES[match] : ["owner", "admin"];
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, role, hydrated } = useAuthStore();

  const router = useRouter();
  const pathname = usePathname();

  /**
   * Wait until Zustand Persist has restored localStorage.
   * Otherwise user/role are temporarily null during hydration,
   * causing incorrect redirects.
   */
  useEffect(() => {
    if (!hydrated) return;

    if (!user) {
      router.replace("/login");
    }
  }, [hydrated, user, router]);

  /**
   * Role guard.
   */
  useEffect(() => {
    if (!hydrated) return;
    if (!user || !role) return;

    const allowed = getAllowedRoles(pathname);

    if (!allowed.includes(role)) {
      router.replace("/dashboard");
    }
  }, [hydrated, user, role, pathname, router]);

  /**
   * Proactive background token refresh every 10 minutes.
   */
  useEffect(() => {
    if (!hydrated || !user) return;

    const refresh = async () => {
      try {
        await fetch("/api/auth/refresh", { method: "POST" });
      } catch {}
    };

    // Refresh every 10 minutes
    const interval = setInterval(refresh, 10 * 60 * 1000);

    return () => {
      clearInterval(interval);
    };
  }, [hydrated, user]);

  return (
    <AppShell>
      {children}
    </AppShell>
  );
}