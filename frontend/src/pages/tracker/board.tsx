import {
  DndContext,
  DragOverlay,
  KeyboardSensor,
  PointerSensor,
  useDraggable,
  useDroppable,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRightLeft, CheckSquare, FileText, GripVertical, KanbanSquare, MoreHorizontal, Plus } from "lucide-react";
import * as React from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";

import { EmptyState, ErrorState, PageContainer, PageHeader, Stat } from "@/components/common/page";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { VenueMark } from "@/components/venue/venue-mark";
import { useDocumentTitle } from "@/hooks/use-document-title";
import { api, errorMessage } from "@/lib/api";
import { keys } from "@/lib/query";
import type { Submission } from "@/lib/types";
import { cn } from "@/lib/utils";

interface Board {
  columns: { key: string; label: string; items: Submission[] }[];
  statuses: { value: string; label: string }[];
  stats: { total: number; active: number; accepted: number; rate: number | null };
}

const ACCENT: Record<string, string> = {
  planning: "bg-zinc-400",
  writing: "bg-sky-500",
  submitted: "bg-indigo-500",
  review: "bg-amber-500",
  rebuttal: "bg-orange-500",
  accepted: "bg-emerald-500",
  rejected: "bg-rose-500",
};

type CardProps = { sub: Submission; statuses: Board["statuses"]; onMove: (s: Submission, status: string) => void };

function DraggableSubmission(props: CardProps) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({ id: props.sub.id, data: { sub: props.sub } });
  return <SubmissionCard {...props} nodeRef={setNodeRef} handleProps={{ ...listeners, ...attributes }} isDragging={isDragging} />;
}

function SubmissionCard({
  sub,
  statuses,
  onMove,
  overlay = false,
  nodeRef,
  handleProps,
  isDragging = false,
}: CardProps & { overlay?: boolean; nodeRef?: (el: HTMLElement | null) => void; handleProps?: Record<string, unknown>; isDragging?: boolean }) {
  const pct = sub.checklist.total ? (sub.checklist.done / sub.checklist.total) * 100 : 0;
  return (
    <div
      ref={nodeRef}
      className={cn(
        "group rounded-lg border bg-card p-3 shadow-card transition-shadow",
        isDragging && !overlay && "opacity-40",
        overlay && "rotate-1 shadow-lift ring-2 ring-primary/30",
      )}
    >
      <div className="flex items-start gap-2">
        <button
          type="button"
          className="-ml-1 mt-0.5 cursor-grab touch-none rounded p-0.5 text-muted-foreground/60 hover:text-foreground active:cursor-grabbing"
          aria-label={`Drag ${sub.paper.title}`}
          {...handleProps}
        >
          <GripVertical className="size-4" aria-hidden="true" />
        </button>
        <div className="min-w-0 flex-1">
          <Link to={`/tracker/s/${sub.id}/`} className="line-clamp-2 text-sm font-medium leading-5 hover:text-brand-text">
            {sub.paper.title}
          </Link>
          <p className="mt-1 flex items-center gap-1.5 text-xs text-muted-foreground">
            <VenueMark acronym={sub.venue.acronym} size="sm" className="size-4 rounded text-[7px]" />
            {sub.cycle?.label ?? sub.venue.acronym}
          </p>
        </div>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon-sm" className="-mr-1.5 -mt-1 size-7 opacity-60 group-hover:opacity-100" aria-label={`Move ${sub.paper.title}`}>
              <MoreHorizontal aria-hidden="true" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel className="flex items-center gap-1.5">
              <ArrowRightLeft className="size-3.5" aria-hidden="true" /> Move to
            </DropdownMenuLabel>
            {statuses
              .filter((s) => s.value !== sub.status)
              .map((s) => (
                <DropdownMenuItem key={s.value} onSelect={() => onMove(sub, s.value)}>
                  <span className={cn("size-2 rounded-full", ACCENT[s.value] ?? "bg-zinc-400")} aria-hidden="true" />
                  {s.label}
                </DropdownMenuItem>
              ))}
            <DropdownMenuSeparator />
            <DropdownMenuItem asChild>
              <Link to={`/tracker/s/${sub.id}/`}>Open details</Link>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
      <div className="mt-3 flex items-center gap-2 pl-5">
        {sub.checklist.total > 0 && (
          <span className="flex flex-1 items-center gap-1.5 text-[11px] text-muted-foreground">
            <CheckSquare className="size-3" aria-hidden="true" />
            <span className="tnum">
              {sub.checklist.done}/{sub.checklist.total}
            </span>
            <Progress value={pct} className="h-1 flex-1" label="Checklist progress" indicatorClassName={pct === 100 ? "bg-emerald-500" : undefined} />
          </span>
        )}
        {sub.days_left != null && (
          <span
            className={cn(
              "tnum rounded-md px-1.5 py-0.5 text-[11px] font-semibold",
              sub.days_left < 7 ? "bg-rose-50 text-rose-700 dark:bg-rose-500/10 dark:text-rose-300" : "bg-muted text-muted-foreground",
            )}
          >
            {sub.days_left}d left
          </span>
        )}
      </div>
    </div>
  );
}

function Column({ col, statuses, onMove }: { col: Board["columns"][number]; statuses: Board["statuses"]; onMove: (s: Submission, status: string) => void }) {
  const { setNodeRef, isOver } = useDroppable({ id: col.key });
  return (
    <section
      ref={setNodeRef}
      aria-labelledby={`col-${col.key}`}
      className={cn("flex w-72 shrink-0 flex-col rounded-xl border bg-surface transition-colors", isOver && "border-primary/50 bg-brand-soft/50")}
    >
      <header className="flex items-center gap-2 px-3 py-2.5">
        <span className={cn("size-2 rounded-full", ACCENT[col.key])} aria-hidden="true" />
        <h2 id={`col-${col.key}`} className="text-sm font-semibold">
          {col.label}
        </h2>
        <span className="tnum ml-auto rounded-full bg-background px-2 text-[11px] font-semibold text-muted-foreground">{col.items.length}</span>
      </header>
      <div className="flex min-h-24 flex-1 flex-col gap-2 px-2 pb-2">
        {col.items.map((s) => (
          <DraggableSubmission key={s.id} sub={s} statuses={statuses} onMove={onMove} />
        ))}
        {col.items.length === 0 && <p className="rounded-lg border border-dashed px-3 py-6 text-center text-xs text-muted-foreground">Drop here</p>}
      </div>
    </section>
  );
}

export function Component() {
  useDocumentTitle("Submission tracker");
  const qc = useQueryClient();
  const [active, setActive] = React.useState<Submission | null>(null);
  const { data, error, isLoading, refetch } = useQuery({ queryKey: keys.board, queryFn: () => api.get<Board>("/tracker/board/") });
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 6 } }), useSensor(KeyboardSensor));
  const move = useMutation({
    mutationFn: ({ sub, status }: { sub: Submission; status: string }) => api.patch(`/tracker/submissions/${sub.id}/`, { status }),
    onMutate: async ({ sub, status }) => {
      await qc.cancelQueries({ queryKey: keys.board });
      const prev = qc.getQueryData<Board>(keys.board);
      qc.setQueryData<Board>(keys.board, (old) =>
        old
          ? {
              ...old,
              columns: old.columns.map((c) => ({
                ...c,
                items:
                  c.key === status
                    ? [
                        { ...sub, status, status_label: old.statuses.find((s) => s.value === status)?.label ?? status },
                        ...c.items.filter((i) => i.id !== sub.id),
                      ]
                    : c.items.filter((i) => i.id !== sub.id),
              })),
            }
          : old,
      );
      return { prev };
    },
    onError: (e, _v, ctx) => {
      if (ctx?.prev) qc.setQueryData(keys.board, ctx.prev);
      toast.error(errorMessage(e));
    },
    onSuccess: (_d, { sub, status }) => toast.success(`Moved “${sub.paper.title}” to ${data?.statuses.find((s) => s.value === status)?.label ?? status}`),
    onSettled: () => {
      qc.invalidateQueries({ queryKey: keys.board });
      qc.invalidateQueries({ queryKey: keys.dashboard });
    },
  });
  const onMove = (sub: Submission, status: string) => sub.status !== status && move.mutate({ sub, status });
  const onDragStart = (e: DragStartEvent) => setActive((e.active.data.current as { sub: Submission }).sub);
  const onDragEnd = (e: DragEndEvent) => {
    setActive(null);
    const sub = (e.active.data.current as { sub: Submission } | undefined)?.sub;
    if (sub && e.over) onMove(sub, String(e.over.id));
  };
  const label = (id: string | number) => data?.columns.flatMap((c) => c.items).find((s) => s.id === id)?.paper.title ?? "submission";
  const colLabel = (id: string | number | undefined) => data?.columns.find((c) => c.key === id)?.label ?? "column";

  return (
    <PageContainer>
      <PageHeader
        icon={KanbanSquare}
        title="Submission tracker"
        description="Drag papers between stages — or use a card’s menu. Each submission gets a checklist generated from the venue’s rules."
        actions={
          <>
            <Button variant="secondary" asChild>
              <Link to="/tracker/papers/">
                <FileText aria-hidden="true" /> Papers
              </Link>
            </Button>
            <Button asChild>
              <Link to="/tracker/new/">
                <Plus aria-hidden="true" /> Track submission
              </Link>
            </Button>
          </>
        }
      />
      {error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : isLoading || !data ? (
        <div className="flex gap-4 overflow-hidden">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-96 w-72 shrink-0 rounded-xl" />
          ))}
        </div>
      ) : data.stats.total === 0 ? (
        <EmptyState
          icon={KanbanSquare}
          title="Track your first submission"
          description="Pick a paper and a target venue; we’ll set up a checklist with the venue’s template, page limit and anonymity rules."
        >
          <Button asChild>
            <Link to="/tracker/new/">
              <Plus aria-hidden="true" /> Track submission
            </Link>
          </Button>
        </EmptyState>
      ) : (
        <>
          <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-4">
            <Stat label="Submissions" value={data.stats.total} />
            <Stat label="In progress" value={data.stats.active} />
            <Stat label="Accepted" value={data.stats.accepted} />
            <Stat label="Acceptance rate" value={data.stats.rate != null ? `${data.stats.rate}%` : "—"} hint="Of decided submissions" />
          </div>
          <DndContext
            sensors={sensors}
            onDragStart={onDragStart}
            onDragEnd={onDragEnd}
            onDragCancel={() => setActive(null)}
            accessibility={{
              announcements: {
                onDragStart: ({ active: a }) => `Picked up ${label(a.id)}.`,
                onDragOver: ({ active: a, over }) => (over ? `${label(a.id)} is over ${colLabel(over.id)}.` : `${label(a.id)} is no longer over a column.`),
                onDragEnd: ({ active: a, over }) => (over ? `${label(a.id)} was moved to ${colLabel(over.id)}.` : `${label(a.id)} was dropped.`),
                onDragCancel: ({ active: a }) => `Moving ${label(a.id)} was cancelled.`,
              },
            }}
          >
            <div className="scrollbar-thin -mx-4 flex gap-3 overflow-x-auto px-4 pb-4 sm:-mx-6 sm:px-6 lg:-mx-8 lg:px-8">
              {data.columns.map((col) => (
                <Column key={col.key} col={col} statuses={data.statuses} onMove={onMove} />
              ))}
            </div>
            <DragOverlay>{active ? <SubmissionCard sub={active} statuses={data.statuses} onMove={onMove} overlay /> : null}</DragOverlay>
          </DndContext>
        </>
      )}
    </PageContainer>
  );
}
