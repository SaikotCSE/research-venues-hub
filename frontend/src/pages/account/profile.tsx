import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { UserRound } from "lucide-react";
import * as React from "react";
import { toast } from "sonner";

import { ErrorState, PageContainer, PageHeader } from "@/components/common/page";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, FormError } from "@/components/ui/field";
import { Input, NativeSelect, Textarea } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { useDocumentTitle } from "@/hooks/use-document-title";
import { ApiError, api } from "@/lib/api";
import { keys } from "@/lib/query";
import { browserTimeZone } from "@/lib/time";
import type { Session } from "@/lib/types";

interface Profile {
  display_name: string;
  affiliation: string;
  research_interests: string;
  timezone: string;
  email_reminders: boolean;
  reminder_days: string;
  weekly_digest: boolean;
  email: string;
  email_verified: boolean;
  username: string;
}

type Editable = Pick<Profile, "display_name" | "affiliation" | "research_interests" | "timezone" | "email_reminders" | "reminder_days" | "weekly_digest">;

export function Component() {
  useDocumentTitle("Profile");
  const qc = useQueryClient();
  const { data, error, isLoading, refetch } = useQuery({ queryKey: keys.profile, queryFn: () => api.get<Profile>("/me/profile/") });
  const [form, setForm] = React.useState<Editable | null>(null);
  React.useEffect(() => {
    if (data)
      setForm({
        display_name: data.display_name,
        affiliation: data.affiliation,
        research_interests: data.research_interests,
        timezone: data.timezone,
        email_reminders: data.email_reminders,
        reminder_days: data.reminder_days,
        weekly_digest: data.weekly_digest,
      });
  }, [data]);
  const zones = React.useMemo(() => {
    try {
      return (Intl as unknown as { supportedValuesOf: (k: string) => string[] }).supportedValuesOf("timeZone");
    } catch {
      return [browserTimeZone, "UTC"];
    }
  }, []);
  const save = useMutation({
    mutationFn: (body: Editable) => api.put<Profile>("/me/profile/", body),
    onSuccess: (p) => {
      qc.setQueryData(keys.profile, p);
      qc.setQueryData<Session>(keys.session, (old) =>
        old?.user ? { ...old, user: { ...old.user, name: p.display_name || p.username, timezone: p.timezone } } : old,
      );
      qc.invalidateQueries({ queryKey: keys.dashboard });
      toast.success("Profile saved");
    },
  });
  const fields = save.error instanceof ApiError ? save.error.fields : {};
  const set = <K extends keyof Editable>(key: K, value: Editable[K]) => setForm((f) => (f ? { ...f, [key]: value } : f));

  if (error)
    return (
      <PageContainer size="default">
        <ErrorState error={error} onRetry={() => refetch()} />
      </PageContainer>
    );
  if (isLoading || !data || !form)
    return (
      <PageContainer size="default">
        <Skeleton className="h-10 w-60" />
        <Skeleton className="mt-8 h-96 rounded-xl" />
      </PageContainer>
    );

  return (
    <PageContainer size="default">
      <PageHeader icon={UserRound} title="Profile" description={`Signed in as ${data.username}${data.email ? ` · ${data.email}` : ""}`} />
      <div className="max-w-3xl">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            save.mutate(form);
          }}
        >
          <Card>
            <CardHeader>
              <CardTitle>Research &amp; reminders</CardTitle>
              <CardDescription>Your interests power recommendations; the timezone is used for every date you see and every reminder we send.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4">
              <FormError message={save.error && !Object.keys(fields).length ? save.error.message : null} />
              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="Display name" htmlFor="pf-name" error={fields.display_name} optional>
                  <Input value={form.display_name} onChange={(e) => set("display_name", e.target.value)} maxLength={80} />
                </Field>
                <Field label="Affiliation" htmlFor="pf-aff" error={fields.affiliation} optional>
                  <Input value={form.affiliation} onChange={(e) => set("affiliation", e.target.value)} maxLength={120} placeholder="University or lab" />
                </Field>
              </div>
              <Field
                label="Research interests"
                htmlFor="pf-interests"
                error={fields.research_interests}
                description="Comma-separated keywords, e.g. “computer vision, 3D reconstruction, robotics”."
              >
                <Textarea rows={3} value={form.research_interests} onChange={(e) => set("research_interests", e.target.value)} maxLength={300} />
              </Field>
              <Field label="Timezone" htmlFor="pf-tz" error={fields.timezone}>
                <NativeSelect value={form.timezone} onChange={(e) => set("timezone", e.target.value)}>
                  {[...new Set([form.timezone, ...zones])].map((z) => (
                    <option key={z} value={z}>
                      {z.replace(/_/g, " ")}
                    </option>
                  ))}
                </NativeSelect>
              </Field>
              <div className="grid gap-3 rounded-xl border bg-surface p-4">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <Label htmlFor="pf-reminders">Email reminders</Label>
                    <p className="mt-1 text-xs text-muted-foreground">
                      Before abstract and paper deadlines of starred venues and tracked submissions
                      {data.email_verified ? "" : " — confirm your email first"}.
                    </p>
                  </div>
                  <Switch id="pf-reminders" checked={form.email_reminders} onCheckedChange={(v) => set("email_reminders", v)} />
                </div>
                <Field label="Remind me this many days before" htmlFor="pf-days" error={fields.reminder_days} description="Comma-separated, between 1 and 365.">
                  <Input
                    value={form.reminder_days}
                    onChange={(e) => set("reminder_days", e.target.value)}
                    disabled={!form.email_reminders}
                    inputMode="numeric"
                    className="max-w-[12rem]"
                  />
                </Field>
                <div className="flex items-start justify-between gap-4 border-t pt-3">
                  <div>
                    <Label htmlFor="pf-digest">Weekly digest</Label>
                    <p className="mt-1 text-xs text-muted-foreground">A Monday summary of upcoming deadlines for your targets.</p>
                  </div>
                  <Switch id="pf-digest" checked={form.weekly_digest} onCheckedChange={(v) => set("weekly_digest", v)} />
                </div>
              </div>
            </CardContent>
            <CardFooter className="justify-end">
              <Button type="submit" loading={save.isPending}>
                Save profile
              </Button>
            </CardFooter>
          </Card>
        </form>
      </div>
    </PageContainer>
  );
}
