"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard, Users, CalendarDays, CheckSquare,
  CreditCard, Settings, GraduationCap, ChevronLeft,
  UserPlus, FileCheck, BookOpen, ClipboardList, IndianRupee, Bell, Sparkles, ExternalLink,
  Building2, Layers, Sliders, Activity, Eye, ShieldCheck, Zap, Bot, Brain, HeartPulse, Flag, TrendingUp
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuthStore, type UserRole } from "@/lib/stores/auth.store";
import { CoachGenieLogo } from "@/components/common/CoachGenieLogo";
import { useLanguage } from "@/components/providers/LanguageProvider";

const ICON_MAP: Record<string, React.ElementType> = {
  LayoutDashboard, Users, CalendarDays, CheckSquare,
  CreditCard, Settings, GraduationCap, Brain,
  UserPlus, FileCheck, BookOpen, ClipboardList, IndianRupee, Bell, Sparkles, ExternalLink,
  Building2, Layers, Sliders, Activity, Eye, ShieldCheck, Zap, Bot, HeartPulse, Flag, TrendingUp
};

const NAV_ITEMS = [
  { label: "Dashboard", href: "/dashboard", icon: "LayoutDashboard", external: false },
  { label: "Leads", href: "/leads", icon: "UserPlus", external: false },
  { label: "Admissions", href: "/admissions", icon: "FileCheck", external: false },
  { label: "Students", href: "/students", icon: "Users", external: false },
  { label: "Batches", href: "/batches", icon: "BookOpen", external: false },
  { label: "Exams", href: "/exams", icon: "ClipboardList", external: false },
  { label: "Sessions", href: "/sessions", icon: "CalendarDays", external: false },
  { label: "Attendance", href: "/attendance", icon: "CheckSquare", external: false },
  { label: "Attendance Reports", href: "/attendance/reports", icon: "ClipboardList", external: false },
  { label: "Fees", href: "/fees", icon: "IndianRupee", external: false },
  { label: "Automation", href: "/automation", icon: "Zap", external: false },
  { label: "Growth Cards", href: "/growth-cards", icon: "Sparkles", external: false },
  { label: "Notifications", href: "/notifications", icon: "Bell", external: false },
  { label: "Billing", href: "/settings/billing", icon: "CreditCard", external: false },
  { label: "Settings", href: "/settings", icon: "Settings", external: false },
  { label: "AI Analytics", href: "/ai/analytics", icon: "Brain", external: false },
  { label: "Documentation", href: "/docs", icon: "BookOpen", external: false },
  { label: "Career Guidance", href: "https://career-guidence-topaz.vercel.app/", icon: "GraduationCap", external: true },
];

const SUPER_ADMIN_NAV_ITEMS = [
  { label: "Platform Overview", href: "/dashboard", icon: "LayoutDashboard", external: false },
  { label: "Institutes / Tenants", href: "/platform/tenants", icon: "Building2", external: false },
  { label: "Subscriptions & Plans", href: "/platform/plans", icon: "Layers", external: false },
  { label: "Entitlements", href: "/platform/entitlements", icon: "CheckSquare", external: false },
  { label: "Usage & Quotas", href: "/platform/quotas", icon: "Sliders", external: false },
  { label: "AI / LLM Control", href: "/platform/ai", icon: "Brain", external: false },
  { label: "Platform Analytics", href: "/platform/analytics", icon: "TrendingUp", external: false },
  { label: "Platform Finance", href: "/platform/finance", icon: "IndianRupee", external: false },
  { label: "Feature Flags", href: "/platform/feature-flags", icon: "Flag", external: false },
  { label: "Diagnostics", href: "/platform/diagnostics", icon: "Eye", external: false },
  { label: "System Health", href: "/platform/health", icon: "HeartPulse", external: false },
  { label: "Platform Audit Logs", href: "/platform/audit-logs", icon: "ShieldCheck", external: false },
  { label: "Documentation", href: "/docs", icon: "BookOpen", external: false },
  { label: "Career Guidance", href: "https://career-guidence-topaz.vercel.app/", icon: "GraduationCap", external: true },
];

const MODULE_ROLES: Record<string, string[]> = {
  "/dashboard": ["super_admin", "owner", "admin", "counselor", "tutor", "coach"],
  "/leads": ["owner", "admin", "counselor"],
  "/admissions": ["owner", "admin", "counselor"],
  "/students": ["owner", "admin", "counselor", "tutor", "coach"],
  "/batches": ["owner", "admin", "counselor", "tutor", "coach"],
  "/exams": ["owner", "admin", "tutor", "coach"],
  "/sessions": ["owner", "admin", "tutor", "coach"],
  "/attendance": ["owner", "admin", "tutor", "coach"],
  "/attendance/reports": ["owner", "admin", "tutor", "coach"],
  "/fees": ["owner", "admin", "counselor"],
  "/automation": ["owner", "admin", "counselor"],
  "/growth-cards": ["owner", "admin", "counselor", "tutor", "coach"],
  "/notifications": ["owner", "admin", "counselor", "tutor", "coach"],
  "/settings/billing": ["owner"],
  "/settings": ["owner", "admin"],
  "/ai/analytics": ["super_admin", "owner", "admin", "counselor", "tutor", "coach"],
  "/docs": ["super_admin", "owner", "admin", "counselor", "tutor", "coach"],
  "/platform/tenants": ["super_admin"],
  "/platform/plans": ["super_admin"],
  "/platform/entitlements": ["super_admin"],
  "/platform/quotas": ["super_admin"],
  "/platform/ai": ["super_admin"],
  "/platform/analytics": ["super_admin"],
  "/platform/finance": ["super_admin"],
  "/platform/feature-flags": ["super_admin"],
  "/platform/diagnostics": ["super_admin"],
  "/platform/health": ["super_admin"],
  "/platform/audit-logs": ["super_admin"],
};

interface SidebarProps {
  collapsed: boolean;
  onCollapse: () => void;
}

export function Sidebar({ collapsed, onCollapse }: SidebarProps) {
  const pathname = usePathname();
  const { t } = useLanguage();
  const user = useAuthStore((state) => state.user);
  const storeRole = useAuthStore((state) => state.role);

  // Normalize role (handle uppercase or lowercase)
  const rawRole = (user?.role || storeRole || "owner").toLowerCase();

  const visibleItems =
    rawRole === "super_admin"
      ? SUPER_ADMIN_NAV_ITEMS
      : NAV_ITEMS.filter((item) => {
          if (item.external) return true;
          const allowed = MODULE_ROLES[item.href];
          if (!allowed) return true;
          return allowed.includes(rawRole);
        });

  // Find the single active item that has the longest matching href prefix
  const activeItemHref = visibleItems
    .filter((item) => !item.external && (pathname === item.href || pathname.startsWith(item.href + "/")))
    .sort((a, b) => b.href.length - a.href.length)[0]?.href;

  return (
    <aside
      data-testid="sidebar"
      className={cn(
        "flex h-screen flex-col border-r bg-card transition-all duration-200 ease-in-out",
        collapsed ? "w-16" : "w-60"
      )}
    >
      <div className="flex h-[3.75rem] items-center gap-2.5 border-b px-4" data-no-translate="true">
        <CoachGenieLogo size="md" plain />
        {!collapsed && (
          <span className="font-bold tracking-tight text-sm truncate bg-gradient-to-r from-violet-600 to-indigo-600 bg-clip-text text-transparent">CoachGenie</span>
        )}
      </div>

      <nav className="flex-1 overflow-y-auto py-4 px-2 space-y-0.5">
        {visibleItems.map((item) => {
          const Icon = ICON_MAP[item.icon] ?? LayoutDashboard;
          const active = !item.external && item.href === activeItemHref;
          const labelTranslated = t(item.label);

          const commonClass = cn(
            "group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
            active
              ? "bg-primary/10 text-primary"
              : "text-muted-foreground hover:bg-accent hover:text-foreground"
          );

          if (item.external) {
            return (
              <a
                key={item.href}
                href={item.href}
                target="_blank"
                rel="noopener noreferrer"
                title={collapsed ? labelTranslated : undefined}
                className={commonClass}
              >
                <Icon className="h-4 w-4 shrink-0" />
                {!collapsed && (
                  <span className="truncate flex items-center gap-1">
                    {labelTranslated}
                    <ExternalLink className="h-3 w-3 opacity-50" />
                  </span>
                )}
              </a>
            );
          }

          return (
            <Link
              key={item.href}
              href={item.href}
              title={collapsed ? labelTranslated : undefined}
              className={commonClass}
            >
              <Icon className={cn("h-4 w-4 shrink-0", active && "text-primary")} />
              {!collapsed && <span className="truncate">{labelTranslated}</span>}
            </Link>
          );
        })}
      </nav>

      <div className="border-t p-2">
        <button data-testid="sidebar-collapse"
          onClick={onCollapse}
          className="flex w-full items-center justify-center rounded-lg p-2 text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
        >
          <ChevronLeft className={cn("h-4 w-4 transition-transform duration-200", collapsed && "rotate-180")} />
        </button>
      </div>
    </aside>
  );
}
