import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarPlus, Globe, List, Lock, Trash2 } from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";

import { CopyButton } from "@/components/common/copy-button";
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
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { VenueCard } from "@/components/venue/venue-card";
import { useDocumentTitle } from "@/hooks/use-document-title";
import { ApiError, api, errorMessage } from "@/lib/api";
import { keys } from "@/lib/query";
import type { VenueCard as Venue, VenueListSummary } from "@/lib/types";
import { NotFoundPage } from "@/pages/not-found";

interface ListDetail {
  list: VenueListSummary;
  owner: boolean;
  curator: string;
  share_url: string;
  calendar_url: string;
  venues: Venue[];
}

export function Component() {
  const { slug = "" } = useParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { data, error, isLoading, refetch } = useQuery({ queryKey: keys.list(slug), queryFn: () => api.get<ListDetail>(`/lists/${slug}/`) });
  useDocumentTitle(data?.list.name ?? "Venue list");
  const update = useMutation({
    mutationFn: (body: Partial<VenueListSummary>) => api.patch<ListDetail>(`/lists/${slug}/`, body),
    onSuccess: (d) => {
      qc.setQueryData(keys.list(slug), d);
      qc.invalidateQueries({ queryKey: keys.lists });
      toast.success(d.list.is_public ? "List is now public — anyone with the link can view it." : "List is now private.");
    },
    onError: (e) => toast.error(errorMessage(e)),
  });
  const remove = useMutation({
    mutationFn: () => api.delete<{ message: string }>(`/lists/${slug}/`),
    onSuccess: (r) => {
      toast.success(r.message);
      qc.invalidateQueries({ queryKey: keys.lists });
      navigate("/accounts/lists/");
    },
    onError: (e) => toast.error(errorMessage(e)),
  });

  if (error instanceof ApiError && error.status === 404) return <NotFoundPage what="list" />;
  if (error)
    return (
      <PageContainer>
        <ErrorState error={error} onRetry={() => refetch()} />
      </PageContainer>
    );
  if (isLoading || !data)
    return (
      <PageContainer>
        <Skeleton className="h-10 w-72" />
        <Skeleton className="mt-8 h-64 rounded-xl" />
      </PageContainer>
    );

  const { list } = data;
  return (
    <PageContainer>
      <PageHeader
        icon={List}
        eyebrow={data.owner ? "Your list" : `Curated by ${data.curator}`}
        title={list.name}
        description={list.description || `${data.venues.length} venues, sorted by next deadline.`}
        actions={
          <>
            {(list.is_public || data.owner) && (
              <Button variant="secondary" size="sm" asChild>
                <a href={data.calendar_url}>
                  <CalendarPlus aria-hidden="true" /> Calendar feed
                </a>
              </Button>
            )}
            {list.is_public && <CopyButton text={data.share_url} label="Copy share link" successMessage="Share link copied" />}
          </>
        }
      />
      {data.owner && (
        <div className="mb-6 flex flex-wrap items-center gap-4 rounded-xl border bg-card px-4 py-3 shadow-card">
          <div className="flex items-center gap-3">
            <Switch id="list-public" checked={list.is_public} onCheckedChange={(v) => update.mutate({ is_public: v })} disabled={update.isPending} />
            <Label htmlFor="list-public" className="flex items-center gap-1.5">
              {list.is_public ? (
                <Globe className="size-4 text-emerald-600" aria-hidden="true" />
              ) : (
                <Lock className="size-4 text-muted-foreground" aria-hidden="true" />
              )}
              {list.is_public ? "Public — anyone with the link can view" : "Private — only you can see this list"}
            </Label>
          </div>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="ghost" size="sm" className="ml-auto text-destructive hover:bg-destructive/10 hover:text-destructive">
                <Trash2 aria-hidden="true" /> Delete list
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogTitle>Delete “{list.name}”?</AlertDialogTitle>
              <AlertDialogDescription>The venues stay in the catalogue and your targets; only this list and its share link are removed.</AlertDialogDescription>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction destructive onClick={() => remove.mutate()}>
                  Delete list
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      )}
      {data.venues.length === 0 ? (
        <EmptyState
          icon={List}
          title="This list is empty"
          description={data.owner ? "Open any venue and tick this list in its “Lists” card." : "The curator hasn’t added venues yet."}
        >
          {data.owner && (
            <Button asChild>
              <Link to="/">Find venues</Link>
            </Button>
          )}
        </EmptyState>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {data.venues.map((v) => (
            <VenueCard key={v.slug} venue={v} />
          ))}
        </div>
      )}
    </PageContainer>
  );
}
