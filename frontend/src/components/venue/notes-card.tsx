import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Check, Loader2, NotebookPen } from "lucide-react";
import * as React from "react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/input";
import { useDebounced } from "@/hooks/use-debounce";
import { api, errorMessage } from "@/lib/api";
import { keys } from "@/lib/query";
import type { VenueDetail } from "@/lib/types";

/** Private notes about a venue, saved automatically as you type. */
export function NotesCard({ slug, initial }: { slug: string; initial: string }) {
  const qc = useQueryClient();
  const [note, setNote] = React.useState(initial);
  const [dirty, setDirty] = React.useState(false);
  const debounced = useDebounced(note, 800);
  const save = useMutation({
    mutationFn: (text: string) => api.put<{ note: string; updated_at: string }>(`/venues/${slug}/note/`, { note: text }),
    onSuccess: (r) => {
      setDirty(false);
      qc.setQueryData<VenueDetail>(keys.venue(slug), (old) => (old ? { ...old, me: { ...old.me, note: r.note, note_updated_at: r.updated_at } } : old));
      qc.invalidateQueries({ queryKey: keys.targets });
    },
  });
  React.useEffect(() => {
    if (dirty) save.mutate(debounced);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debounced]);

  return (
    <Card>
      <CardHeader>
        <CardTitle as="h2">
          <NotebookPen className="size-4 text-muted-foreground" aria-hidden="true" /> My notes
        </CardTitle>
        <CardDescription>Private to you{" "}— synced to your account when signed in.</CardDescription>
      </CardHeader>
      <CardContent>
        <label htmlFor="venue-note" className="sr-only">
          Notes about this venue
        </label>
        <Textarea
          id="venue-note"
          rows={5}
          value={note}
          maxLength={5000}
          placeholder="Reviewer feedback, template quirks, co-author plans…"
          onChange={(e) => {
            setNote(e.target.value);
            setDirty(true);
          }}
        />
        <p className="mt-2 flex h-4 items-center gap-1.5 text-xs text-muted-foreground" aria-live="polite">
          {save.isPending ? (
            <>
              <Loader2 className="size-3 animate-spin" aria-hidden="true" /> Saving…
            </>
          ) : save.isError ? (
            <span className="text-destructive">{errorMessage(save.error)}</span>
          ) : save.isSuccess && !dirty ? (
            <>
              <Check className="size-3 text-emerald-600" aria-hidden="true" /> Saved
            </>
          ) : dirty ? (
            "Unsaved changes"
          ) : null}
        </p>
      </CardContent>
    </Card>
  );
}
