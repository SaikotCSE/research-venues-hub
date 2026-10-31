import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileText, Plus, Trash2 } from "lucide-react";
import * as React from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";

import { EmptyState, ErrorState, PageContainer, PageHeader } from "@/components/common/page";
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
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, FormError } from "@/components/ui/field";
import { Input, Textarea } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useDocumentTitle } from "@/hooks/use-document-title";
import { ApiError, api, errorMessage } from "@/lib/api";
import { keys } from "@/lib/query";
import { relativeTime } from "@/lib/time";
import type { Paper } from "@/lib/types";

export function Component() {
  useDocumentTitle("My papers");
  const qc = useQueryClient();
  const { data, error, isLoading, refetch } = useQuery({ queryKey: keys.papers, queryFn: () => api.get<{ results: Paper[] }>("/tracker/papers/") });
  const [form, setForm] = React.useState({ title: "", abstract: "", keywords: "" });
  const create = useMutation({
    mutationFn: () => api.post<{ message: string }>("/tracker/papers/", form),
    onSuccess: (r) => {
      toast.success(r.message);
      setForm({ title: "", abstract: "", keywords: "" });
      qc.invalidateQueries({ queryKey: keys.papers });
    },
  });
  const remove = useMutation({
    mutationFn: (id: number) => api.delete(`/tracker/papers/${id}/`),
    onSuccess: () => {
      toast.success("Paper deleted");
      qc.invalidateQueries({ queryKey: keys.papers });
      qc.invalidateQueries({ queryKey: keys.board });
    },
    onError: (e) => toast.error(errorMessage(e)),
  });
  const fields = create.error instanceof ApiError ? create.error.fields : {};
  return (
    <PageContainer size="default">
      <PageHeader
        icon={FileText}
        title="My papers"
        description="Papers you are writing or have submitted. Track each one against as many venues as you like."
        actions={
          <Button variant="secondary" asChild>
            <Link to="/tracker/">Open board</Link>
          </Button>
        }
      />
      <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <div>
          {error ? (
            <ErrorState error={error} onRetry={() => refetch()} />
          ) : isLoading ? (
            <Skeleton className="h-64 rounded-xl" />
          ) : !data?.results.length ? (
            <EmptyState icon={FileText} title="No papers yet" description="Add a paper here, or create one directly when you track a submission." />
          ) : (
            <ul className="space-y-3">
              {data.results.map((p) => (
                <li key={p.id} className="rounded-xl border bg-card p-4 shadow-card">
                  <div className="flex items-start gap-3">
                    <div className="min-w-0 flex-1">
                      <h2 className="font-semibold leading-6">{p.title}</h2>
                      <p className="mt-0.5 text-xs text-muted-foreground">
                        {p.submission_count ?? 0} submission{p.submission_count === 1 ? "" : "s"} · added {relativeTime(p.created_at)}
                      </p>
                      {p.keywords && (
                        <ul className="mt-2 flex flex-wrap gap-1">
                          {p.keywords
                            .split(",")
                            .map((k) => k.trim())
                            .filter(Boolean)
                            .map((k) => (
                              <li key={k} className="rounded-md bg-muted px-1.5 py-0.5 text-[11px] text-muted-foreground">
                                {k}
                              </li>
                            ))}
                        </ul>
                      )}
                      {p.abstract && <p className="mt-2 line-clamp-3 text-sm leading-6 text-muted-foreground">{p.abstract}</p>}
                    </div>
                    <div className="flex shrink-0 gap-1">
                      <Button variant="secondary" size="sm" asChild>
                        <Link to={`/recommend/?text=${encodeURIComponent([p.title, p.keywords, p.abstract].filter(Boolean).join(". ").slice(0, 1800))}`}>
                          Find venues
                        </Link>
                      </Button>
                      <AlertDialog>
                        <AlertDialogTrigger asChild>
                          <Button variant="ghost" size="icon-sm" aria-label={`Delete ${p.title}`}>
                            <Trash2 aria-hidden="true" />
                          </Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogTitle>Delete “{p.title}”?</AlertDialogTitle>
                          <AlertDialogDescription>
                            This also deletes its {p.submission_count ?? 0} tracked submission(s) and their checklists.
                          </AlertDialogDescription>
                          <AlertDialogFooter>
                            <AlertDialogCancel>Cancel</AlertDialogCancel>
                            <AlertDialogAction destructive onClick={() => remove.mutate(p.id)}>
                              Delete paper
                            </AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
        <Card className="h-fit">
          <CardHeader>
            <CardTitle>
              <Plus className="size-4 text-muted-foreground" aria-hidden="true" /> Add a paper
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form
              className="grid gap-4"
              onSubmit={(e) => {
                e.preventDefault();
                create.mutate();
              }}
            >
              <FormError message={create.error && !Object.keys(fields).length ? create.error.message : null} />
              <Field label="Title" htmlFor="pp-title" error={fields.title}>
                <Input value={form.title} onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))} maxLength={250} required />
              </Field>
              <Field label="Keywords" htmlFor="pp-kw" error={fields.keywords} optional description="Comma-separated">
                <Input value={form.keywords} onChange={(e) => setForm((f) => ({ ...f, keywords: e.target.value }))} maxLength={300} />
              </Field>
              <Field label="Abstract" htmlFor="pp-abs" error={fields.abstract} optional>
                <Textarea rows={5} value={form.abstract} onChange={(e) => setForm((f) => ({ ...f, abstract: e.target.value }))} />
              </Field>
              <Button type="submit" loading={create.isPending}>
                Add paper
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </PageContainer>
  );
}
