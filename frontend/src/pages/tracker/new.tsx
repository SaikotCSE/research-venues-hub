import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { KanbanSquare } from "lucide-react";
import * as React from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";

import { PageContainer, PageHeader } from "@/components/common/page";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter } from "@/components/ui/card";
import { Field, FormError } from "@/components/ui/field";
import { Input, NativeSelect, Textarea } from "@/components/ui/input";
import { VenueCombobox, useVenueOptions } from "@/components/venue/venue-combobox";
import { useDocumentTitle } from "@/hooks/use-document-title";
import { ApiError, api } from "@/lib/api";
import { keys } from "@/lib/query";
import type { Paper, SubmissionDetail } from "@/lib/types";

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
  useDocumentTitle("Track a submission");
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [params] = useSearchParams();
  const { data: options } = useVenueOptions();
  const { data: papers } = useQuery({ queryKey: keys.papers, queryFn: () => api.get<{ results: Paper[] }>("/tracker/papers/") });
  const [form, setForm] = React.useState({
    paper: "",
    new_paper_title: "",
    venue: params.get("venue") ?? "",
    cycle: "",
    status: "planning",
    submitted_on: "",
    decision_on: "",
    notes: "",
  });
  const set = (key: keyof typeof form, value: string) => setForm((f) => ({ ...f, [key]: value }));
  const venue = options?.results.find((v) => v.slug === form.venue);

  // Default to the venue's next cycle (the one with the soonest future deadline, else the latest).
  React.useEffect(() => {
    if (!venue) return;
    const now = Date.now();
    const upcoming = venue.cycles
      .filter((c) => new Date(c.submission_deadline).getTime() > now)
      .sort((a, b) => a.submission_deadline.localeCompare(b.submission_deadline));
    setForm((f) => ({ ...f, cycle: String((upcoming[0] ?? venue.cycles[0])?.id ?? "") }));
  }, [venue]);
  React.useEffect(() => {
    if (papers && !papers.results.length) setForm((f) => ({ ...f, paper: "new" }));
  }, [papers]);

  const create = useMutation({
    mutationFn: () =>
      api.post<{ submission: SubmissionDetail; message: string }>("/tracker/submissions/", {
        paper: form.paper && form.paper !== "new" ? Number(form.paper) : null,
        new_paper_title: form.paper === "new" || !form.paper ? form.new_paper_title : "",
        venue: form.venue,
        cycle: form.cycle ? Number(form.cycle) : null,
        status: form.status,
        submitted_on: form.submitted_on || null,
        decision_on: form.decision_on || null,
        notes: form.notes,
      }),
    onSuccess: (r) => {
      toast.success(r.message);
      qc.invalidateQueries({ queryKey: keys.board });
      qc.invalidateQueries({ queryKey: keys.papers });
      qc.invalidateQueries({ queryKey: keys.dashboard });
      navigate(`/tracker/s/${r.submission.id}/`);
    },
  });
  const fields = create.error instanceof ApiError ? create.error.fields : {};
  const newPaper = !!papers && (form.paper === "new" || !papers.results.length);

  return (
    <PageContainer size="narrow">
      <PageHeader
        icon={KanbanSquare}
        title="Track a submission"
        description="We’ll create a checklist from the venue’s template, page limit and review rules."
      />
      <form
        onSubmit={(e) => {
          e.preventDefault();
          create.mutate();
        }}
      >
        <Card>
          <CardContent className="grid gap-5 p-6">
            <FormError message={create.error && !Object.keys(fields).length ? create.error.message : null} />
            {!papers && <div className="h-[58px] animate-pulse rounded-lg bg-muted" aria-hidden="true" />}
            {!!papers?.results.length && (
              <Field label="Paper" htmlFor="ns-paper" error={fields.paper}>
                <NativeSelect value={form.paper} onChange={(e) => set("paper", e.target.value)} required>
                  <option value="" disabled>
                    Choose a paper…
                  </option>
                  {papers.results.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.title}
                    </option>
                  ))}
                  <option value="new">+ New paper…</option>
                </NativeSelect>
              </Field>
            )}
            {newPaper && (
              <Field label="Paper title" htmlFor="ns-title" error={fields.new_paper_title}>
                <Input
                  value={form.new_paper_title}
                  onChange={(e) => set("new_paper_title", e.target.value)}
                  maxLength={250}
                  required
                  placeholder="Working title of your paper"
                  autoFocus
                />
              </Field>
            )}
            <Field label="Venue" htmlFor="ns-venue" error={fields.venue}>
              <VenueCombobox value={form.venue} onChange={(slug) => set("venue", slug)} invalid={!!fields.venue} />
            </Field>
            {venue && venue.cycles.length > 0 && (
              <Field label="Edition" htmlFor="ns-cycle" error={fields.cycle}>
                <NativeSelect value={form.cycle} onChange={(e) => set("cycle", e.target.value)}>
                  <option value="">No specific edition</option>
                  {venue.cycles.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.label}
                    </option>
                  ))}
                </NativeSelect>
              </Field>
            )}
            <div className="grid gap-5 sm:grid-cols-3">
              <Field label="Status" htmlFor="ns-status" error={fields.status}>
                <NativeSelect value={form.status} onChange={(e) => set("status", e.target.value)}>
                  {STATUSES.map(([v, l]) => (
                    <option key={v} value={v}>
                      {l}
                    </option>
                  ))}
                </NativeSelect>
              </Field>
              <Field label="Submitted on" htmlFor="ns-sub" error={fields.submitted_on} optional>
                <Input type="date" value={form.submitted_on} onChange={(e) => set("submitted_on", e.target.value)} />
              </Field>
              <Field label="Decision on" htmlFor="ns-dec" error={fields.decision_on} optional>
                <Input type="date" value={form.decision_on} onChange={(e) => set("decision_on", e.target.value)} />
              </Field>
            </div>
            <Field label="Notes" htmlFor="ns-notes" error={fields.notes} optional>
              <Textarea
                rows={3}
                value={form.notes}
                onChange={(e) => set("notes", e.target.value)}
                placeholder="Co-authors, submission ID, reviewer assignments…"
              />
            </Field>
          </CardContent>
          <CardFooter className="justify-end">
            <Button variant="ghost" asChild>
              <Link to="/tracker/">Cancel</Link>
            </Button>
            <Button type="submit" loading={create.isPending} disabled={!form.venue}>
              Start tracking
            </Button>
          </CardFooter>
        </Card>
      </form>
    </PageContainer>
  );
}
