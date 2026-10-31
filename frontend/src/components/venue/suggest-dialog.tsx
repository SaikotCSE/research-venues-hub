import { useMutation } from "@tanstack/react-query";
import * as React from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Field, FormError } from "@/components/ui/field";
import { Input, Textarea } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ApiError, api, errorMessage } from "@/lib/api";
import type { Cycle } from "@/lib/types";

const FIELDS = [
  { value: "abstract_deadline", label: "Abstract deadline" },
  { value: "submission_deadline", label: "Submission deadline" },
  { value: "notification_date", label: "Notification date" },
  { value: "camera_ready_date", label: "Camera-ready date" },
];

function toLocalInput(iso: string | null) {
  return iso ? iso.slice(0, 16) : "";
}

export function SuggestDialog({ cycle, onClose }: { cycle: Cycle | null; onClose: () => void }) {
  const [field, setField] = React.useState("submission_deadline");
  const [value, setValue] = React.useState("");
  const [source, setSource] = React.useState("");
  const [note, setNote] = React.useState("");
  React.useEffect(() => {
    if (cycle) {
      setField("submission_deadline");
      setValue(toLocalInput(cycle.submission_deadline));
      setSource(cycle.source_url || "");
      setNote("");
    }
  }, [cycle]);
  const submit = useMutation({
    mutationFn: () => api.post<{ message: string }>(`/cycles/${cycle!.id}/suggestions/`, { field, new_value: value, source_url: source, note }),
    onSuccess: (r) => {
      toast.success(r.message);
      onClose();
    },
  });
  const fields = submit.error instanceof ApiError ? submit.error.fields : {};
  return (
    <Dialog open={!!cycle} onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Suggest a correction{cycle ? ` · ${cycle.label}` : ""}</DialogTitle>
          <DialogDescription>Times are interpreted as UTC. Include a link to the official call so an editor can verify it.</DialogDescription>
        </DialogHeader>
        <form
          className="grid gap-4"
          onSubmit={(e) => {
            e.preventDefault();
            submit.mutate();
          }}
        >
          <FormError message={submit.error && !Object.keys(fields).length ? errorMessage(submit.error) : null} />
          <Field label="Date to correct" htmlFor="sg-field" error={fields.field}>
            <Select
              value={field}
              onValueChange={(f) => {
                setField(f);
                if (cycle) setValue(toLocalInput(cycle[f as keyof Cycle] as string | null));
              }}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {FIELDS.map((f) => (
                  <SelectItem key={f.value} value={f.value}>
                    {f.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>
          <Field label="Correct value (UTC)" htmlFor="sg-value" error={fields.new_value}>
            <Input type="datetime-local" value={value} onChange={(e) => setValue(e.target.value)} required />
          </Field>
          <Field label="Source URL" htmlFor="sg-source" error={fields.source_url} optional>
            <Input type="url" inputMode="url" placeholder="https://…" value={source} onChange={(e) => setSource(e.target.value)} />
          </Field>
          <Field label="Note for the editors" htmlFor="sg-note" error={fields.note} optional>
            <Textarea rows={2} maxLength={300} value={note} onChange={(e) => setNote(e.target.value)} />
          </Field>
          <DialogFooter>
            <Button type="button" variant="secondary" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" loading={submit.isPending}>
              Submit suggestion
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
