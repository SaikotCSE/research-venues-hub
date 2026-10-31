import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, CheckSquare, Plus, Trash2, X } from "lucide-react";
import * as React from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";

import { ErrorState, PageContainer } from "@/components/common/page";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Field, FormError } from "@/components/ui/field";
import { Input, NativeSelect, Textarea } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { CountdownBlocks, DeadlineTime } from "@/components/venue/countdown";
import { VenueMark } from "@/components/venue/venue-mark";
import { useDocumentTitle } from "@/hooks/use-document-title";
import { ApiError, api, errorMessage } from "@/lib/api";
import { keys } from "@/lib/query";
import { formatAoE } from "@/lib/time";
import type { SubmissionDetail } from "@/lib/types";
import { cn } from "@/lib/utils";
import { NotFoundPage } from "@/pages/not-found";

const STATUSES = [
  ["planning", "Planning"],
  ["writing", "Writing"],
  ["submitted", "Submitted"],
  ["review", "Under review"],
  ["rebuttal", "Rebuttal"],
  ["accepted", "Accepted"],
  ["rejected", "Rejected"],
  ["withdrawn", "Withdrawn"],
];

export function Component() {
  const { id = "" } = useParams();
  const sid = Number(id);
  const navigate = useNavigate();
  const qc = useQueryClient();
  const {
    data: sub,
    error,
    isLoading,
    refetch,
  } = useQuery({ queryKey: keys.submission(sid), queryFn: () => api.get<SubmissionDetail>(`/tracker/submissions/${sid}/`) });
  useDocumentTitle(sub ? `${sub.paper.title} → ${sub.venue.acronym}` : "Submission");
  const [form, setForm] = React.useState({ cycle: "", status: "", submitted_on: "", decision_on: "", notes: "" });
  const [item, setItem] = React.useState("");
  React.useEffect(() => {
    if (sub)
      setForm({
        cycle: sub.cycle ? String(sub.cycle.id) : "",
        status: sub.status,
        submitted_on: sub.submitted_on ?? "",
        decision_on: sub.decision_on ?? "",
        notes: sub.notes,
      });
  }, [sub]);

  const refresh = (d?: SubmissionDetail) => {
    if (d) qc.setQueryData(keys.submission(sid), d);
    qc.invalidateQueries({ queryKey: keys.board });
    qc.invalidateQueries({ queryKey: keys.dashboard });
  };
  const save = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.patch<SubmissionDetail>(`/tracker/submissions/${sid}/`, body),
    onSuccess: (d) => {
      refresh(d);
      toast.success("Saved");
    },
  });
  const toggle = useMutation({
    mutationFn: ({ itemId, done }: { itemId: number; done: boolean }) => api.patch(`/tracker/submissions/${sid}/checklist/${itemId}/`, { done }),
    onMutate: ({ itemId, done }) =>
      qc.setQueryData<SubmissionDetail>(keys.submission(sid), (old) =>
        old
          ? {
              ...old,
              checklist_items: old.checklist_items.map((i) => (i.id === itemId ? { ...i, done } : i)),
              checklist: { total: old.checklist.total, done: old.checklist.done + (done ? 1 : -1) },
            }
          : old,
      ),
    onError: (e) => {
      toast.error(errorMessage(e));
      refetch();
    },
    onSettled: () => qc.invalidateQueries({ queryKey: keys.board }),
  });
  const addItem = useMutation({
    mutationFn: () => api.post(`/tracker/submissions/${sid}/checklist/`, { text: item }),
    onSuccess: () => {
      setItem("");
      refetch();
      qc.invalidateQueries({ queryKey: keys.board });
    },
    onError: (e) => toast.error(errorMessage(e)),
  });
  const removeItem = useMutation({
    mutationFn: (itemId: number) => api.delete(`/tracker/submissions/${sid}/checklist/${itemId}/`),
    onSuccess: () => {
      refetch();
      qc.invalidateQueries({ queryKey: keys.board });
    },
  });
  const remove = useMutation({
    mutationFn: () => api.delete(`/tracker/submissions/${sid}/`),
    onSuccess: () => {
      toast.success("Submission deleted");
      refresh();
      navigate("/tracker/");
    },
  });

  if (error instanceof ApiError && error.status === 404) return <NotFoundPage what="submission" />;
  if (error)
    return (
      <PageContainer>
        <ErrorState error={error} onRetry={() => refetch()} />
      </PageContainer>
    );
  if (isLoading || !sub)
    return (
      <PageContainer size="default">
        <Skeleton className="h-10 w-96 max-w-full" />
        <Skeleton className="mt-8 h-80 rounded-xl" />
      </PageContainer>
    );

  const fields = save.error instanceof ApiError ? save.error.fields : {};
  const pct = sub.checklist.total ? (sub.checklist.done / sub.checklist.total) * 100 : 0;

  return (
    <PageContainer size="default">
      <Button variant="ghost" size="sm" className="-ml-2 mb-4" asChild>
        <Link to="/tracker/">
          <ArrowLeft aria-hidden="true" /> Board
        </Link>
      </Button>
      <header className="mb-8 flex flex-wrap items-start gap-4">
        <VenueMark acronym={sub.venue.acronym} size="lg" />
        <div className="min-w-0 flex-1">
          <h1 className="text-2xl font-semibold tracking-tight">{sub.paper.title}</h1>
          <p className="mt-1 text-muted-foreground">
            →{" "}
            <Link to={`/venue/${sub.venue.slug}/`} className="link">
              {sub.cycle?.label ?? sub.venue.acronym}
            </Link>{" "}
            · {sub.venue_rank_label}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Label htmlFor="sd-status-quick" className="sr-only">
            Status
          </Label>
          <NativeSelect id="sd-status-quick" value={sub.status} onChange={(e) => save.mutate({ status: e.target.value })} className="w-44">
            {STATUSES.map(([v, l]) => (
              <option key={v} value={v}>
                {l}
              </option>
            ))}
          </NativeSelect>
        </div>
      </header>

      <div className="grid gap-6 lg:grid-cols-[1.3fr_1fr]">
        <div className="space-y-6">
          {sub.deadline && (
            <Card className="bg-gradient-to-br from-brand-soft to-card">
              <CardContent className="flex flex-wrap items-end justify-between gap-4 p-5">
                <div>
                  <p className="eyebrow">Paper deadline</p>
                  <CountdownBlocks at={sub.deadline} className="mt-3" />
                </div>
                <div className="text-sm sm:text-right">
                  <DeadlineTime at={sub.deadline} className="font-medium" />
                  <p className="text-muted-foreground">{formatAoE(sub.deadline)}</p>
                </div>
              </CardContent>
            </Card>
          )}
          <Card>
            <CardHeader>
              <CardTitle>
                <CheckSquare className="size-4 text-muted-foreground" aria-hidden="true" /> Checklist
                <Badge tone={pct === 100 ? "green" : "neutral"} className="ml-1">
                  {sub.checklist.done}/{sub.checklist.total}
                </Badge>
              </CardTitle>
              <Progress value={pct} label="Checklist progress" className="mt-2" indicatorClassName={pct === 100 ? "bg-emerald-500" : undefined} />
            </CardHeader>
            <CardContent>
              <ul className="space-y-1">
                {sub.checklist_items.map((i) => (
                  <li key={i.id} className="group flex items-center gap-3 rounded-lg px-2 py-2 hover:bg-accent/50">
                    <Checkbox id={`ci-${i.id}`} checked={i.done} onCheckedChange={(c) => toggle.mutate({ itemId: i.id, done: c === true })} />
                    <Label
                      htmlFor={`ci-${i.id}`}
                      className={cn("flex-1 cursor-pointer text-sm font-normal leading-5", i.done && "text-muted-foreground line-through")}
                    >
                      {i.text}
                    </Label>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      className="size-7 opacity-0 focus-visible:opacity-100 group-hover:opacity-100"
                      onClick={() => removeItem.mutate(i.id)}
                      aria-label={`Remove “${i.text}”`}
                    >
                      <X aria-hidden="true" />
                    </Button>
                  </li>
                ))}
              </ul>
              <form
                className="mt-3 flex gap-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (item.trim()) addItem.mutate();
                }}
              >
                <Input
                  value={item}
                  onChange={(e) => setItem(e.target.value)}
                  placeholder="Add a checklist item"
                  aria-label="New checklist item"
                  maxLength={200}
                />
                <Button type="submit" variant="secondary" loading={addItem.isPending} disabled={!item.trim()}>
                  <Plus aria-hidden="true" /> Add
                </Button>
              </form>
            </CardContent>
          </Card>
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            save.mutate({
              cycle: form.cycle ? Number(form.cycle) : null,
              status: form.status,
              submitted_on: form.submitted_on || null,
              decision_on: form.decision_on || null,
              notes: form.notes,
            });
          }}
        >
          <Card>
            <CardHeader>
              <CardTitle>Details</CardTitle>
              <CardDescription>Submission and decision dates fill in automatically when the status changes.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4">
              <FormError message={save.error && !Object.keys(fields).length ? save.error.message : null} />
              <Field label="Edition" htmlFor="sd-cycle" error={fields.cycle}>
                <NativeSelect value={form.cycle} onChange={(e) => setForm((f) => ({ ...f, cycle: e.target.value }))}>
                  <option value="">No specific edition</option>
                  {sub.venue_cycles.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.label}
                    </option>
                  ))}
                </NativeSelect>
              </Field>
              <Field label="Status" htmlFor="sd-status" error={fields.status}>
                <NativeSelect value={form.status} onChange={(e) => setForm((f) => ({ ...f, status: e.target.value }))}>
                  {STATUSES.map(([v, l]) => (
                    <option key={v} value={v}>
                      {l}
                    </option>
                  ))}
                </NativeSelect>
              </Field>
              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="Submitted on" htmlFor="sd-sub" error={fields.submitted_on}>
                  <Input type="date" value={form.submitted_on} onChange={(e) => setForm((f) => ({ ...f, submitted_on: e.target.value }))} />
                </Field>
                <Field label="Decision on" htmlFor="sd-dec" error={fields.decision_on}>
                  <Input type="date" value={form.decision_on} onChange={(e) => setForm((f) => ({ ...f, decision_on: e.target.value }))} />
                </Field>
              </div>
              <Field label="Notes" htmlFor="sd-notes" error={fields.notes}>
                <Textarea rows={5} value={form.notes} onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))} />
              </Field>
            </CardContent>
            <CardFooter className="justify-between">
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button type="button" variant="ghost" className="text-destructive hover:bg-destructive/10 hover:text-destructive">
                    <Trash2 aria-hidden="true" /> Delete
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogTitle>Delete this submission?</AlertDialogTitle>
                  <AlertDialogDescription>The checklist and notes are removed. The paper itself stays in your papers list.</AlertDialogDescription>
                  <AlertDialogFooter>
                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                    <AlertDialogAction destructive onClick={() => remove.mutate()}>
                      Delete submission
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
              <Button type="submit" loading={save.isPending}>
                Save changes
              </Button>
            </CardFooter>
          </Card>
        </form>
      </div>
    </PageContainer>
  );
}
