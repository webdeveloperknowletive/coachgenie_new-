"use client";
import { useMemo } from "react";
import { format, eachDayOfInterval, subDays, getDay } from "date-fns";
import { cn } from "@/lib/utils";

function generateMockAttendance() {
  const record: Record<string, number> = {};
  const days = eachDayOfInterval({ start: subDays(new Date(), 180), end: new Date() });
  days.forEach((d) => {
    record[format(d, "yyyy-MM-dd")] = Math.random() > 0.25
      ? Math.floor(Math.random() * 4) + 1
      : 0;
  });
  return record;
}

const LEVELS = [
  "bg-muted",
  "bg-blue-200 dark:bg-blue-900",
  "bg-blue-400 dark:bg-blue-700",
  "bg-blue-500 dark:bg-blue-600",
  "bg-blue-600 dark:bg-blue-500",
];

export function AttendanceHeatmap({ data }: { data?: Record<string, number> } = {}) {
  const attendance = useMemo(() => data ?? generateMockAttendance(), [data]);

  const days   = eachDayOfInterval({ start: subDays(new Date(), 180), end: new Date() });
  const padStart = getDay(days[0]!);
  const weeks: (Date | null)[][] = [];
  let week: (Date | null)[] = Array(padStart).fill(null);
  days.forEach((d) => {
    week.push(d);
    if (week.length === 7) { weeks.push(week); week = []; }
  });
  if (week.length > 0) weeks.push([...week, ...Array(7 - week.length).fill(null)]);

  const months = useMemo(() => {
    const seen = new Set<string>();
    return days.filter((d) => { const m = format(d, "MMM"); return seen.has(m) ? false : (seen.add(m), true); });
  }, [days]);

  return (
    <div className="rounded-xl border bg-card p-5 shadow-sm fade-in col-span-full" style={{ animationDelay: "240ms" }}>
      <div className="mb-4">
        <h3 className="font-semibold">Attendance Heatmap</h3>
        <p className="text-xs text-muted-foreground">Last 6 months · darker = more sessions attended</p>
      </div>
      <div className="overflow-x-auto">
        <div className="inline-flex flex-col gap-1 min-w-max">
          {/* Month labels */}
          <div className="flex gap-1 mb-1 ml-8">
            {weeks.map((_, wi) => {
              const first = weeks[wi]?.find(Boolean);
              const label = first ? format(first, "MMM") : "";
              const prevLabel = wi > 0 ? (weeks[wi - 1]?.find(Boolean) ? format(weeks[wi - 1]!.find(Boolean)!, "MMM") : "") : "";
              return (
                <div key={wi} className="w-3 text-[9px] text-muted-foreground">
                  {label !== prevLabel ? label : ""}
                </div>
              );
            })}
          </div>
          {/* Day rows */}
          {["Su","Mo","Tu","We","Th","Fr","Sa"].map((day, di) => (
            <div key={day} className="flex items-center gap-1">
              <span className="w-7 text-right text-[9px] text-muted-foreground shrink-0">
                {di % 2 === 1 ? day : ""}
              </span>
              {weeks.map((week, wi) => {
                const date = week[di];
                if (!date) return <div key={wi} className="h-3 w-3 rounded-sm bg-transparent" />;
                const key   = format(date, "yyyy-MM-dd");
                const level = attendance[key] ?? 0;
                return (
                  <div
                    key={wi}
                    title={`${key}: ${level === 0 ? "No sessions" : `${level} sessions`}`}
                    className={cn("h-3 w-3 rounded-sm transition-opacity hover:opacity-75 cursor-default", LEVELS[level])}
                  />
                );
              })}
            </div>
          ))}
        </div>
      </div>
      <div className="mt-3 flex items-center gap-1.5 text-[10px] text-muted-foreground">
        <span>Less</span>
        {LEVELS.map((l, i) => (
          <div key={i} className={cn("h-3 w-3 rounded-sm", l)} />
        ))}
        <span>More</span>
      </div>
    </div>
  );
}
