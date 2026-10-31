import { useMutation, useQueryClient } from "@tanstack/react-query";
import { BellRing, BookmarkPlus } from "lucide-react";
import * as React from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Field, FormError } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { ApiError, api } from "@/lib/api";
import { keys } from "@/lib/query";
import type { Chip } from "@/lib/types";
import { useSession } from "@/providers/session";

export function SaveSearchDialog({ query, chips }: { query: string; chips: Chip[] }) {
  const session = useSession();
  const qc = useQueryClient();
  const [open, setOpen] = React.useState(false);
  const [name, setName] = React.useState("");
  const [alert, setAlert] = React.useState(true);
  const save = useMutation({
    mutationFn: () => api.post<{ message: string }>("/me/searches/", { name, querystring: query, alert }),
    onSuccess: (r) => {
      toast.success(r.message);
      qc.invalidateQueries({ queryKey: keys.dashboard });
      qc.invalidateQueries({ queryKey: keys.searches });
      setOpen(false);
    },
  });
  React.useEffect(() => {
    if (open)
      setName(
        chips
          .map((c) => c.label)
          .join(", ")
          .slice(0, 80) || "All venues",
      );
  }, [open, chips]);
  const fields = save.error instanceof ApiError ? save.error.fields : {};

  if (!session.authenticated)
    return (
      <Button variant="secondary" size="sm" asChild>
        <Link to={`/accounts/login/?next=${encodeURIComponent(`/?${query}`)}`}>
          <BookmarkPlus aria-hidden="true" /> Save search
        </Link>
      </Button>
    );

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="secondary" size="sm">
          <BookmarkPlus aria-hidden="true" /> Save search
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Save this search</DialogTitle>
          <DialogDescription>Re-run it from your dashboard, and optionally get notified when new venues match.</DialogDescription>
        </DialogHeader>
        <form
          className="grid gap-4"
          onSubmit={(e) => {
            e.preventDefault();
            save.mutate();
          }}
        >
          <FormError message={save.error && !Object.keys(fields).length ? save.error.message : null} />
          <Field label="Name" htmlFor="ss-name" error={fields.name}>
            <Input value={name} onChange={(e) => setName(e.target.value)} maxLength={80} required autoFocus />
          </Field>
          <div className="flex items-start justify-between gap-4 rounded-lg border bg-surface p-3">
            <div>
              <Label htmlFor="ss-alert" className="flex items-center gap-1.5">
                <BellRing className="size-3.5 text-muted-foreground" aria-hidden="true" /> Alert me about new matches
              </Label>
              <p className="mt-1 text-xs text-muted-foreground">We check daily and add a notification when more venues match.</p>
            </div>
            <Switch id="ss-alert" checked={alert} onCheckedChange={setAlert} />
          </div>
          <DialogFooter>
            <Button type="button" variant="secondary" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={save.isPending}>
              Save search
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
