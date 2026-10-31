import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ListPlus, Plus } from "lucide-react";
import * as React from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, errorMessage } from "@/lib/api";
import { keys } from "@/lib/query";
import type { VenueDetail } from "@/lib/types";

export function ListsCard({ venue }: { venue: VenueDetail }) {
  const qc = useQueryClient();
  const [name, setName] = React.useState("");
  const lists = venue.me.lists ?? [];
  const refresh = () => {
    qc.invalidateQueries({ queryKey: keys.venue(venue.slug) });
    qc.invalidateQueries({ queryKey: keys.lists });
    qc.invalidateQueries({ queryKey: ["list"] });
  };
  const toggle = useMutation({
    mutationFn: ({ slug, member }: { slug: string; member: boolean }) => api.post<{ message: string }>(`/lists/${slug}/venues/${venue.slug}/`, { member }),
    onMutate: ({ slug, member }) => {
      qc.setQueryData<VenueDetail>(keys.venue(venue.slug), (old) =>
        old ? { ...old, me: { ...old.me, lists: (old.me.lists ?? []).map((l) => (l.slug === slug ? { ...l, member } : l)) } } : old,
      );
    },
    onSuccess: (r) => toast.success(r.message),
    onError: (e) => toast.error(errorMessage(e)),
    onSettled: refresh,
  });
  const create = useMutation({
    mutationFn: () => api.post<{ message: string }>("/lists/", { name, venue: venue.slug }),
    onSuccess: (r) => {
      toast.success(r.message);
      setName("");
      refresh();
    },
    onError: (e) => toast.error(errorMessage(e)),
  });
  return (
    <Card>
      <CardHeader>
        <CardTitle as="h2">
          <ListPlus className="size-4 text-muted-foreground" aria-hidden="true" /> Lists
        </CardTitle>
        <CardDescription>
          Group venues into shareable collections.{" "}
          <Link to="/accounts/lists/" className="link">
            Manage lists
          </Link>
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {lists.length > 0 && (
          <ul className="space-y-1">
            {lists.map((l) => (
              <li key={l.slug} className="flex items-center gap-2.5 rounded-md px-1 py-1 hover:bg-accent/60">
                <Checkbox id={`list-${l.slug}`} checked={l.member} onCheckedChange={(c) => toggle.mutate({ slug: l.slug, member: c === true })} />
                <Label htmlFor={`list-${l.slug}`} className="flex-1 cursor-pointer truncate font-normal">
                  {l.name}
                </Label>
              </li>
            ))}
          </ul>
        )}
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (name.trim()) create.mutate();
          }}
        >
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="New list name"
            aria-label="New list name"
            maxLength={80}
            className="h-8 text-[13px]"
          />
          <Button type="submit" size="sm" variant="secondary" loading={create.isPending} disabled={!name.trim()}>
            <Plus aria-hidden="true" /> Add
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
