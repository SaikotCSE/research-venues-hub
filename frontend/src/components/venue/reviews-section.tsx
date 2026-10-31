import { useMutation, useQueryClient } from "@tanstack/react-query";
import { MessageSquareText, PenLine, Trash2 } from "lucide-react";
import * as React from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Field, FormError } from "@/components/ui/field";
import { Input, Textarea } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ApiError, api, errorMessage } from "@/lib/api";
import { keys } from "@/lib/query";
import { relativeTime } from "@/lib/time";
import type { Review, ReviewStats, VenueDetail } from "@/lib/types";
import { useSession } from "@/providers/session";

import { StarInput, Stars } from "./rating";

function ReviewDialog({ venue, open, onOpenChange }: { venue: VenueDetail; open: boolean; onOpenChange: (o: boolean) => void }) {
  const qc = useQueryClient();
  const mine = venue.me.review;
  const [form, setForm] = React.useState({ rating: 4, review_quality: 3, turnaround_days: "", outcome: "pending", comment: "" });
  React.useEffect(() => {
    if (open)
      setForm({
        rating: mine?.rating ?? 4,
        review_quality: mine?.review_quality ?? 3,
        turnaround_days: mine?.turnaround_days != null ? String(mine.turnaround_days) : "",
        outcome: mine?.outcome ?? "pending",
        comment: mine?.comment ?? "",
      });
  }, [open, mine]);
  const save = useMutation({
    mutationFn: () =>
      api.put<{ message: string; review: Review; stats: ReviewStats }>(`/venues/${venue.slug}/review/`, {
        ...form,
        turnaround_days: form.turnaround_days ? Number(form.turnaround_days) : null,
      }),
    onSuccess: (r) => {
      toast.success(r.message);
      qc.invalidateQueries({ queryKey: keys.venue(venue.slug) });
      onOpenChange(false);
    },
  });
  const remove = useMutation({
    mutationFn: () => api.delete(`/venues/${venue.slug}/review/`),
    onSuccess: () => {
      toast.success("Your review was removed");
      qc.invalidateQueries({ queryKey: keys.venue(venue.slug) });
      onOpenChange(false);
    },
    onError: (e) => toast.error(errorMessage(e)),
  });
  const fields = save.error instanceof ApiError ? save.error.fields : {};
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{mine ? "Update your experience" : `Share your ${venue.acronym} experience`}</DialogTitle>
          <DialogDescription>Help others decide where to submit. Your display name is shown with the review.</DialogDescription>
        </DialogHeader>
        <form
          className="grid gap-4"
          onSubmit={(e) => {
            e.preventDefault();
            save.mutate();
          }}
        >
          <FormError message={save.error && !Object.keys(fields).length ? errorMessage(save.error) : null} />
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="grid gap-1.5">
              <Label id="rv-rating">Overall experience</Label>
              <StarInput id="rv-rating" value={form.rating} onChange={(rating) => setForm((f) => ({ ...f, rating }))} label="Overall experience rating" />
            </div>
            <div className="grid gap-1.5">
              <Label id="rv-quality">Review quality</Label>
              <StarInput
                id="rv-quality"
                value={form.review_quality}
                onChange={(review_quality) => setForm((f) => ({ ...f, review_quality }))}
                label="Quality of the reviews"
              />
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Outcome" htmlFor="rv-outcome" error={fields.outcome}>
              <Select value={form.outcome} onValueChange={(outcome) => setForm((f) => ({ ...f, outcome }))}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="accepted">Accepted</SelectItem>
                  <SelectItem value="rejected">Rejected</SelectItem>
                  <SelectItem value="pending">Still pending</SelectItem>
                </SelectContent>
              </Select>
            </Field>
            <Field label="Days to decision" htmlFor="rv-days" error={fields.turnaround_days} optional>
              <Input
                type="number"
                min={0}
                max={1000}
                inputMode="numeric"
                value={form.turnaround_days}
                onChange={(e) => setForm((f) => ({ ...f, turnaround_days: e.target.value }))}
              />
            </Field>
          </div>
          <Field label="Comment" htmlFor="rv-comment" error={fields.comment} optional>
            <Textarea
              rows={4}
              maxLength={2000}
              value={form.comment}
              onChange={(e) => setForm((f) => ({ ...f, comment: e.target.value }))}
              placeholder="Reviewer engagement, rebuttal process, anything others should know…"
            />
          </Field>
          <DialogFooter className="sm:justify-between">
            {mine ? (
              <Button
                type="button"
                variant="ghost"
                className="text-destructive hover:bg-destructive/10 hover:text-destructive"
                onClick={() => remove.mutate()}
                loading={remove.isPending}
              >
                <Trash2 aria-hidden="true" /> Delete review
              </Button>
            ) : (
              <span />
            )}
            <div className="flex flex-col-reverse gap-2 sm:flex-row">
              <Button type="button" variant="secondary" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button type="submit" loading={save.isPending}>
                {mine ? "Update review" : "Publish review"}
              </Button>
            </div>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export function ReviewsSection({ venue }: { venue: VenueDetail }) {
  const session = useSession();
  const [open, setOpen] = React.useState(false);
  const s = venue.review_stats;
  return (
    <section aria-labelledby="reviews-h" id="reviews" className="scroll-mt-20">
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <h2 id="reviews-h" className="flex items-center gap-2 text-lg font-semibold tracking-tight">
          <MessageSquareText className="size-5 text-muted-foreground" aria-hidden="true" /> Community experience
        </h2>
        <div className="ml-auto">
          {session.authenticated ? (
            <Button variant="secondary" size="sm" onClick={() => setOpen(true)}>
              <PenLine aria-hidden="true" /> {venue.me.review ? "Edit your review" : "Share your experience"}
            </Button>
          ) : (
            <Button variant="secondary" size="sm" asChild>
              <Link to={`/accounts/login/?next=${encodeURIComponent(`/venue/${venue.slug}/#reviews`)}`}>Log in to review</Link>
            </Button>
          )}
        </div>
      </div>
      {s.n === 0 ? (
        <p className="rounded-xl border border-dashed px-4 py-8 text-center text-sm text-muted-foreground">
          No reviews yet. Submitted here before? Your experience helps others decide.
        </p>
      ) : (
        <div className="grid gap-4 lg:grid-cols-[15rem_1fr]">
          <div className="rounded-xl border bg-surface p-4">
            <p className="tnum text-4xl font-semibold tracking-tight">{s.rating?.toFixed(1)}</p>
            <Stars value={s.rating ?? 0} className="mt-1" />
            <p className="mt-1 text-xs text-muted-foreground">
              from {s.n} review{s.n === 1 ? "" : "s"}
            </p>
            <dl className="mt-4 space-y-2 text-sm">
              <div className="flex justify-between gap-2">
                <dt className="text-muted-foreground">Review quality</dt>
                <dd className="tnum font-medium">{s.quality?.toFixed(1) ?? "—"} / 5</dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt className="text-muted-foreground">Avg. turnaround</dt>
                <dd className="tnum font-medium">{s.turnaround != null ? `${Math.round(s.turnaround)} days` : "—"}</dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt className="text-muted-foreground">Reported acceptance</dt>
                <dd className="tnum font-medium">{s.accept_pct != null ? `${s.accept_pct}%` : "—"}</dd>
              </div>
            </dl>
          </div>
          <ul className="space-y-3">
            {venue.reviews.map((r) => (
              <li key={r.id} className="rounded-xl border bg-card p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <Stars value={r.rating} />
                  <Badge tone={r.outcome === "accepted" ? "green" : r.outcome === "rejected" ? "red" : "neutral"}>{r.outcome_label}</Badge>
                  {r.turnaround_days != null && <span className="text-xs text-muted-foreground">{r.turnaround_days} days to decision</span>}
                  <span className="ml-auto text-xs text-muted-foreground">
                    {r.author}
                    {r.mine && " (you)"} · {relativeTime(r.created_at)}
                  </span>
                </div>
                {r.comment && <p className="mt-2 whitespace-pre-line text-sm leading-6 text-foreground/90">{r.comment}</p>}
              </li>
            ))}
          </ul>
        </div>
      )}
      {session.authenticated && <ReviewDialog venue={venue} open={open} onOpenChange={setOpen} />}
    </section>
  );
}
