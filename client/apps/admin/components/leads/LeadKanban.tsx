"use client";
import { useState } from "react";
import {
  DndContext, DragOverlay, PointerSensor, useSensor, useSensors,
  useDroppable,
  type DragStartEvent, type DragEndEvent,
} from "@dnd-kit/core";
import { SortableContext, useSortable, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { GripVertical, Phone, Clock } from "lucide-react";
import { format } from "date-fns";
import { cn } from "@/lib/utils";
import type { Lead, LeadStage } from "@/lib/types/lead";
import { STAGE_CONFIG, STAGES } from "@/lib/constants/leads";
import { useLanguage } from "@/components/providers/LanguageProvider";

function formatKanbanDate(dateStr: string, lang: string): string {
  try {
    const d = new Date(dateStr);
    const day = d.getDate();
    const monthIdx = d.getMonth();
    const mrMonths = ["जाने", "फेब्रु", "मार्च", "एप्रिल", "मे", "जून", "जुलै", "ऑगस्ट", "सप्टें", "ऑक्टो", "नोव्हें", "डिसें"];
    const hiMonths = ["जन", "फ़र", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितं", "अक्तू", "नवं", "दिसं"];
    if (lang === "mr") return `${day} ${mrMonths[monthIdx]}`;
    if (lang === "hi") return `${day} ${hiMonths[monthIdx]}`;
    return format(d, "dd MMM");
  } catch {
    return dateStr;
  }
}

// ── Kanban Card ────────────────────────────────────────────────
function KanbanCard({
  lead, onClick, overlay = false,
}: { lead: Lead; onClick: () => void; overlay?: boolean }) {
  const { language, t } = useLanguage();
  const {
    attributes, listeners, setNodeRef,
    transform, transition, isDragging,
  } = useSortable({ id: lead.id });

  return (
    <div
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      className={cn(
        "rounded-xl border bg-card p-3 shadow-sm cursor-pointer select-none",
        "hover:shadow-md hover:border-primary/30 transition-all",
        isDragging && "opacity-40 shadow-lg ring-2 ring-primary/30",
        overlay && "shadow-2xl rotate-1 scale-105 opacity-95"
      )}
      onClick={onClick}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold truncate">{t(lead.name)}</p>
          <p className="text-xs text-muted-foreground truncate">{lead.grade ? t(lead.grade) : ""} · {lead.subject ? t(lead.subject) : ""}</p>
        </div>
        <div
          {...attributes}
          {...listeners}
          onClick={(e) => e.stopPropagation()}
          className="shrink-0 cursor-grab active:cursor-grabbing text-muted-foreground hover:text-foreground p-0.5 mt-0.5"
        >
          <GripVertical className="h-3.5 w-3.5" />
        </div>
      </div>
      <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <Phone className="h-3 w-3 shrink-0" />
        <span className="font-mono">{lead.phone}</span>
      </div>
      {lead.tags?.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {lead.tags.slice(0, 2).map((t) => (
            <span key={t} className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium">{t}</span>
          ))}
        </div>
      )}
      <div className="flex items-center gap-1 mt-2 text-[10px] text-muted-foreground">
        <Clock className="h-2.5 w-2.5" />
        {formatKanbanDate(lead.updatedAt, language)}
      </div>
    </div>
  );
}

// ── Kanban Column (now a proper droppable) ─────────────────────
function KanbanColumn({
  stage, leads, onCardClick,
}: { stage: LeadStage; leads: Lead[]; onCardClick: (lead: Lead) => void }) {
  const { t } = useLanguage();
  const cfg = STAGE_CONFIG[stage];

  // ← KEY FIX: the column itself is a droppable with id = stage string
  const { setNodeRef, isOver } = useDroppable({ id: stage });

  return (
    <div className="flex flex-col rounded-xl border bg-muted/30 min-h-[600px] w-64 shrink-0">
      <div className={cn("flex items-center justify-between rounded-t-xl px-4 py-3 border-b", cfg.bg)}>
        <div className="flex items-center gap-2">
          <span className={cn("h-2 w-2 rounded-full", cfg.color.replace("text-", "bg-"))} />
          <span className={cn("text-xs font-semibold", cfg.color)}>{t(cfg.label)}</span>
        </div>
        <span className={cn(
          "flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold",
          cfg.bg, cfg.color, "ring-1", cfg.border
        )}>
          {leads.length}
        </span>
      </div>

      {/* SortableContext uses lead IDs for intra-column sorting */}
      <SortableContext items={leads.map((l) => l.id)} strategy={verticalListSortingStrategy}>
        {/* droppable ref goes on the inner scrollable div */}
        <div
          ref={setNodeRef}
          className={cn(
            "flex-1 p-3 space-y-3 overflow-y-auto rounded-b-xl transition-colors",
            isOver && "bg-primary/5 ring-2 ring-inset ring-primary/20"
          )}
        >
          {leads.map((lead) => (
            <KanbanCard key={lead.id} lead={lead} onClick={() => onCardClick(lead)} />
          ))}
          {leads.length === 0 && (
            <div className={cn(
              "flex items-center justify-center h-24 rounded-lg border-2 border-dashed text-xs text-muted-foreground transition-colors",
              isOver && "border-primary/40 text-primary bg-primary/5"
            )}>
              {t("Drop here")}
            </div>
          )}
        </div>
      </SortableContext>
    </div>
  );
}

// ── Main Board ─────────────────────────────────────────────────
interface LeadKanbanProps {
  leads:         Lead[];
  onCardClick:   (lead: Lead) => void;
  onStageChange: (leadId: string, newStage: LeadStage) => void;
}

export function LeadKanban({ leads, onCardClick, onStageChange }: LeadKanbanProps) {
  const [activeId, setActiveId] = useState<string | null>(null);
  const activeLead = leads.find((l) => l.id === activeId);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } })
  );

  function onDragStart({ active }: DragStartEvent) {
    setActiveId(active.id as string);
  }

  function onDragEnd({ active, over }: DragEndEvent) {
    setActiveId(null);
    if (!over) return;

    const sourceLead = leads.find((l) => l.id === active.id);
    if (!sourceLead) return;

    // over.id is either a stage string (dropped on column droppable)
    // or a lead id (dropped on a card inside a column)
    const overId = over.id as string;
    const isStage = STAGES.includes(overId as LeadStage);
    const targetStage: LeadStage = isStage
      ? (overId as LeadStage)
      : (leads.find((l) => l.id === overId)?.stage ?? sourceLead.stage);

    if (targetStage && sourceLead.stage !== targetStage) {
      onStageChange(active.id as string, targetStage);
    }
  }

  return (
    <DndContext sensors={sensors} onDragStart={onDragStart} onDragEnd={onDragEnd}>
      <div className="flex gap-4 overflow-x-auto pb-4">
        {STAGES.map((stage) => (
          <KanbanColumn
            key={stage}
            stage={stage}
            leads={leads.filter((l) => l.stage === stage)}
            onCardClick={onCardClick}
          />
        ))}
      </div>
      <DragOverlay>
        {activeLead && (
          <KanbanCard lead={activeLead} onClick={() => {}} overlay />
        )}
      </DragOverlay>
    </DndContext>
  );
}