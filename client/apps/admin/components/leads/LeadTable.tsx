"use client";
import { useState, useMemo } from "react";
import {
  useReactTable, getCoreRowModel, getSortedRowModel,
  getFilteredRowModel, getPaginationRowModel,
  flexRender, type ColumnDef, type SortingState,
} from "@tanstack/react-table";
import { ArrowUpDown, ChevronLeft, ChevronRight, Search, Eye, Trash2 } from "lucide-react";
import { format } from "date-fns";
import { cn } from "@/lib/utils";
import type { Lead } from "@/lib/types/lead";
import { StageBadge } from "./StageBadge";
import { SOURCE_LABELS, BOARD_LABELS } from "@/lib/constants/leads";
import { useLanguage } from "@/components/providers/LanguageProvider";

function formatLeadDate(dateStr: string, lang: string): string {
  try {
    const d = new Date(dateStr);
    const day = d.getDate();
    const monthIdx = d.getMonth();
    const yr = d.getFullYear().toString().slice(-2);
    const mrMonths = ["जाने", "फेब्रु", "मार्च", "एप्रिल", "मे", "जून", "जुलै", "ऑगस्ट", "सप्टें", "ऑक्टो", "नोव्हें", "डिसें"];
    const hiMonths = ["जन", "फ़र", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितं", "अक्तू", "नवं", "दिसं"];
    if (lang === "mr") return `${day} ${mrMonths[monthIdx]} ${yr}`;
    if (lang === "hi") return `${day} ${hiMonths[monthIdx]} ${yr}`;
    return format(d, "dd MMM yy");
  } catch {
    return dateStr;
  }
}

interface LeadTableProps {
  leads:    Lead[];
  onView:   (lead: Lead) => void;
  onDelete: (id: string) => void;
}

export function LeadTable({ leads, onView, onDelete }: LeadTableProps) {
  const { language, t } = useLanguage();
  const [sorting,      setSorting]      = useState<SortingState>([]);
  const [globalFilter, setGlobalFilter] = useState("");

  const columns = useMemo<ColumnDef<Lead>[]>(() => [
    // ── Student ────────────────────────────────────────────────────────────
    {
      accessorKey: "name",
      header: ({ column }) => (
        <button
          className="flex items-center gap-1 hover:text-foreground transition-colors"
          onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
        >
          {t("Student")} <ArrowUpDown className="h-3.5 w-3.5" />
        </button>
      ),
      cell: ({ row }) => (
        <div>
          <p className="font-medium text-sm">{t(row.original.name)}</p>
          <p className="text-xs text-muted-foreground">{row.original.email || "—"}</p>
        </div>
      ),
    },

    // ── Phone ──────────────────────────────────────────────────────────────
    {
      accessorKey: "phone",
      header: () => <span>{t("Phone")}</span>,
      cell: ({ getValue }) => (
        <span className="text-sm font-mono">{getValue<string>()}</span>
      ),
    },

    // ── Grade ──────────────────────────────────────────────────────────────
    {
      accessorKey: "grade",
      header: () => <span>{t("Grade")}</span>,
      cell: ({ getValue }) => (
        <span className="text-sm">{getValue<string>() || "—"}</span>
      ),
    },

    // ── Board (NEW) ────────────────────────────────────────────────────────
    {
      accessorKey: "boardName",
      header: () => <span>{t("Board")}</span>,
      cell: ({ getValue }) => {
        const val = getValue<string>();
        return val ? (
          <span className="text-xs bg-muted rounded-full px-2.5 py-0.5 font-medium">
            {t(BOARD_LABELS[val] || val)}
          </span>
        ) : (
          <span className="text-sm text-muted-foreground">—</span>
        );
      },
    },

    // ── Batch (NEW) ────────────────────────────────────────────────────────
    {
      accessorKey: "batchName",
      header: () => <span>{t("Batch")}</span>,
      cell: ({ row }) => {
        const name = row.original.batchName;
        return name ? (
          <span className="text-xs bg-primary/10 text-primary rounded-full px-2.5 py-0.5 font-medium">
            {t(name)}
          </span>
        ) : (
          <span className="text-xs text-muted-foreground">—</span>
        );
      },
    },

    // ── Subject ────────────────────────────────────────────────────
    {
      accessorKey: "subject",
      header: () => <span>{t("Course")}</span>,
      cell: ({ getValue }) => (
        <span className="text-sm">{t(getValue<string>() || "—")}</span>
      ),
    },

    // ── Source ─────────────────────────────────────────────────────
    {
      accessorKey: "source",
      header: () => <span>{t("Source")}</span>,
      cell: ({ getValue }) => (
        <span className="text-xs bg-muted rounded-full px-2.5 py-0.5 font-medium">
          {t(SOURCE_LABELS[getValue<Lead["source"]>()] || getValue<string>() || "Other")}
        </span>
      ),
    },

    // ── Stage ──────────────────────────────────────────────────────
    {
      accessorKey: "stage",
      header: () => <span>{t("Stage")}</span>,
      cell: ({ getValue }) => <StageBadge stage={getValue<Lead["stage"]>()} />,
    },

    // ── Date ───────────────────────────────────────────────────────
    {
      accessorKey: "createdAt",
      header: ({ column }) => (
        <button
          className="flex items-center gap-1 hover:text-foreground transition-colors"
          onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
        >
          {t("Date")} <ArrowUpDown className="h-3.5 w-3.5" />
        </button>
      ),
      cell: ({ getValue }) => (
        <span className="text-xs text-muted-foreground">
          {formatLeadDate(getValue<string>(), language)}
        </span>
      ),
    },

    // ── Actions ────────────────────────────────────────────────────
    {
      id: "actions",
      header: () => <span>{t("Actions")}</span>,
      cell: ({ row }) => (
        <div className="flex items-center gap-1">
          <button
            onClick={() => onView(row.original)}
            data-testid={`lead-view-${row.original.id}`}
            aria-label={`${t("View Profile")}: ${row.original.name}`}
            title={t("View Profile")}
            className="rounded-md p-1.5 text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
          >
            <Eye className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={() => onDelete(row.original.id)}
            data-testid={`lead-delete-${row.original.id}`}
            aria-label={`${t("Delete")}: ${row.original.name}`}
            title={t("Delete")}
            className="rounded-md p-1.5 text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-colors"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        </div>
      ),
    },
  ], [onView, onDelete, language, t]);

  const table = useReactTable({
    data:                   leads,
    columns,
    getCoreRowModel:        getCoreRowModel(),
    getSortedRowModel:      getSortedRowModel(),
    getFilteredRowModel:    getFilteredRowModel(),
    getPaginationRowModel:  getPaginationRowModel(),
    onSortingChange:        setSorting,
    globalFilterFn:         "includesString",
    onGlobalFilterChange:   setGlobalFilter,
    initialState:           { pagination: { pageSize: 10 } },
    state:                  { sorting, globalFilter },
  });

  return (
    <div className="space-y-3">
      {/* Search */}
      <div className="flex items-center gap-2 rounded-lg border bg-background px-3 py-2 max-w-xs">
        <Search className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
        <input
          value={globalFilter}
          onChange={(e) => setGlobalFilter(e.target.value)}
          data-testid="lead-search"
          placeholder={t("Search leads…")}
          aria-label="Search leads"
          className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
        />
      </div>

      {/* Table */}
      <div className="rounded-xl border overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id} className="border-b bg-muted/40">
                {hg.headers.map((h) => (
                  <th
                    key={h.id}
                    className="px-4 py-3 text-left text-xs font-medium text-muted-foreground whitespace-nowrap"
                  >
                    {h.isPlaceholder ? null : flexRender(h.column.columnDef.header, h.getContext())}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.length ? (
              table.getRowModel().rows.map((row) => (
                <tr
                  key={row.id}
                  data-testid="lead-row"
                  className="border-b last:border-0 hover:bg-muted/30 transition-colors"
                >
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className="px-4 py-3 align-middle whitespace-nowrap">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))
            ) : (
              <tr>
                <td
                  colSpan={columns.length}
                  className="h-32 text-center text-sm text-muted-foreground"
                >
                  {t("No leads found.")}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between text-sm">
        <p className="text-muted-foreground text-xs">
          {table.getFilteredRowModel().rows.length} {table.getFilteredRowModel().rows.length === 1 ? t("lead") : t("leads")}
        </p>
        <div className="flex items-center gap-2">
          <button
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
            aria-label="Go to previous page"
            className="rounded-md border p-1.5 disabled:opacity-40 hover:bg-accent transition-colors"
          >
            <ChevronLeft className="h-3.5 w-3.5" />
          </button>
          <span className="text-xs text-muted-foreground">
            {table.getState().pagination.pageIndex + 1} / {table.getPageCount() || 1}
          </span>
          <button
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
            aria-label="Go to next page"
            className="rounded-md border p-1.5 disabled:opacity-40 hover:bg-accent transition-colors"
          >
            <ChevronRight className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}
