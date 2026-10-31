import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Globe, List, Lock, Plus } from "lucide-react";
import * as React from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { EmptyState, ErrorState, PageContainer, PageHeader } from "@/components/common/page";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Field, FormError } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { useDocumentTitle } from "@/hooks/use-document-title";
import { ApiError, api } from "@/lib/api";
import { keys } from "@/lib/query";
import type { VenueListSummary } from "@/lib/types";

function NewListDialog() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [open, setOpen] = React.useState(false);
  const [form, setForm] = React.useState({ name: "", description: "", is_public: false });
  const create = useMutation({
    mutationFn: () => api.post<{ list: VenueListSummary; message: string }>("/lists/", form),
    onSuccess: (r) => {
      toast.success(r.message);
      qc.invalidateQueries({ queryKey: keys.lists });
      setOpen(false);
      navigate(`/accounts/lists/${r.list.slug}/`);
    },
  });
  const fields = create.error instanceof ApiError ? create.error.fields : {};
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Plus aria-hidden="true" /> New list
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create a list</DialogTitle>
          <DialogDescription>Collect venues for a project, a lab or a reading group. Public lists get a shareable link and calendar feed.</DialogDescription>
        </DialogHeader>
        <form
          className="grid gap-4"
          onSubmit={(e) => {
            e.preventDefault();
            create.mutate();
          }}
        >
          <FormError message={create.error && !Object.keys(fields).length ? create.error.message : null} />
          <Field label="Name" htmlFor="nl-name" error={fields.name}>
            <Input
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              maxLength={80}
              required
              autoFocus
              placeholder="e.g. Vision venues 2027"
            />
          </Field>
          <Field label="Description" htmlFor="nl-desc" error={fields.description} optional>
            <Input value={form.description} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} maxLength={300} />
          </Field>
          <div className="flex items-center justify-between gap-4 rounded-lg border bg-surface p-3">
            <Label htmlFor="nl-public">Public — anyone with the link can view</Label>
            <Switch id="nl-public" checked={form.is_public} onCheckedChange={(v) => setForm((f) => ({ ...f, is_public: v }))} />
          </div>
          <DialogFooter>
            <Button type="button" variant="secondary" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={create.isPending}>
              Create list
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export function Component() {
  useDocumentTitle("My lists");
  const { data, error, isLoading, refetch } = useQuery({ queryKey: keys.lists, queryFn: () => api.get<{ results: VenueListSummary[] }>("/lists/") });
  return (
    <PageContainer size="default">
      <PageHeader
        icon={List}
        title="My lists"
        description="Named, shareable collections of venues — each with its own calendar feed."
        actions={<NewListDialog />}
      />
      {error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-32 rounded-xl" />
          ))}
        </div>
      ) : !data?.results.length ? (
        <EmptyState icon={List} title="No lists yet" description="Create a list here, or add venues to lists from any venue page." />
      ) : (
        <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data.results.map((l) => (
            <li key={l.slug}>
              <Link
                to={`/accounts/lists/${l.slug}/`}
                className="flex h-full flex-col rounded-xl border bg-card p-5 shadow-card transition-[box-shadow,transform] hover:-translate-y-0.5 hover:shadow-lift"
              >
                <div className="flex items-start justify-between gap-3">
                  <h2 className="font-semibold">{l.name}</h2>
                  {l.is_public ? (
                    <Badge tone="green">
                      <Globe aria-hidden="true" /> Public
                    </Badge>
                  ) : (
                    <Badge tone="neutral">
                      <Lock aria-hidden="true" /> Private
                    </Badge>
                  )}
                </div>
                {l.description && <p className="mt-1.5 line-clamp-2 text-sm text-muted-foreground">{l.description}</p>}
                <p className="mt-auto pt-4 text-sm font-medium text-muted-foreground">
                  {l.count ?? 0} venue{l.count === 1 ? "" : "s"}
                </p>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </PageContainer>
  );
}
