import { useMutation } from "@tanstack/react-query";
import { AlertTriangle, Download, KeyRound, Mail, Settings } from "lucide-react";
import * as React from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { PageContainer, PageHeader } from "@/components/common/page";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Field, FormError } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { useDocumentTitle } from "@/hooks/use-document-title";
import { ApiError, api, errorMessage } from "@/lib/api";
import type { Session } from "@/lib/types";
import { PasswordInput } from "@/pages/auth/password-input";
import { useResetAfterAuth, useSession, useUpdateSession } from "@/providers/session";

function DeleteAccount() {
  const navigate = useNavigate();
  const reset = useResetAfterAuth();
  const [open, setOpen] = React.useState(false);
  const [password, setPassword] = React.useState("");
  const [confirm, setConfirm] = React.useState("");
  const del = useMutation({
    mutationFn: () => api.post<Session & { message: string }>("/me/delete/", { password, confirm }),
    onSuccess: (s) => {
      reset(s);
      toast.success(s.message);
      navigate("/");
    },
  });
  const fields = del.error instanceof ApiError ? del.error.fields : {};
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="destructive">Delete account…</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete your account?</DialogTitle>
          <DialogDescription>
            This permanently removes your profile, targets, notes, lists, papers, submissions, reviews and notifications. It cannot be undone.
          </DialogDescription>
        </DialogHeader>
        <form
          className="grid gap-4"
          onSubmit={(e) => {
            e.preventDefault();
            del.mutate();
          }}
        >
          <FormError message={del.error && !Object.keys(fields).length ? del.error.message : null} />
          <Field label="Confirm with your password" htmlFor="del-pw" error={fields.password}>
            <PasswordInput value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required />
          </Field>
          <Field
            label={
              <>
                Type <span className="font-mono">DELETE</span> to confirm
              </>
            }
            htmlFor="del-confirm"
            error={fields.confirm}
          >
            <Input value={confirm} onChange={(e) => setConfirm(e.target.value)} autoComplete="off" required />
          </Field>
          <DialogFooter>
            <Button type="button" variant="secondary" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="destructive" loading={del.isPending} disabled={confirm !== "DELETE" || !password}>
              Delete my account
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export function Component() {
  useDocumentTitle("Account settings");
  const session = useSession();
  const updateSession = useUpdateSession();
  const user = session.user!;
  const [email, setEmail] = React.useState(user.email);
  const change = useMutation({
    mutationFn: () => api.post<Session & { message: string }>("/me/email/", { email }),
    onSuccess: (s) => {
      updateSession(s);
      toast.success(s.message);
    },
  });
  const resend = useMutation({
    mutationFn: () => api.post<{ message: string }>("/auth/verify-email/resend/"),
    onSuccess: (r) => toast.success(r.message),
    onError: (e) => toast.error(errorMessage(e)),
  });
  const fields = change.error instanceof ApiError ? change.error.fields : {};
  return (
    <PageContainer size="narrow">
      <PageHeader icon={Settings} title="Account settings" description="Email, password, your data and account deletion." />
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>
              <Mail className="size-4 text-muted-foreground" aria-hidden="true" /> Email address
              {user.email && (user.email_verified ? <Badge tone="green">Confirmed</Badge> : <Badge tone="amber">Not confirmed</Badge>)}
            </CardTitle>
            <CardDescription>Used for reminders, digests and password resets. Changing it requires confirming the new address.</CardDescription>
          </CardHeader>
          <CardContent>
            <form
              className="flex flex-wrap items-start gap-3"
              onSubmit={(e) => {
                e.preventDefault();
                change.mutate();
              }}
            >
              <div className="min-w-[16rem] flex-1">
                <FormError message={change.error && !Object.keys(fields).length ? change.error.message : null} />
                <Field label="New email address" htmlFor="st-email" error={fields.email}>
                  <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" required />
                </Field>
              </div>
              <Button type="submit" className="mt-6" loading={change.isPending} disabled={email.trim().toLowerCase() === user.email.toLowerCase()}>
                Update email
              </Button>
            </form>
            {user.email && !user.email_verified && (
              <p className="mt-3 text-sm text-muted-foreground">
                Didn’t get the confirmation email?{" "}
                <Button variant="link" className="h-auto p-0 text-sm" onClick={() => resend.mutate()} disabled={resend.isPending}>
                  Send it again
                </Button>
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>
              <KeyRound className="size-4 text-muted-foreground" aria-hidden="true" /> Password
            </CardTitle>
            <CardDescription>Choose a strong password you don’t use elsewhere.</CardDescription>
          </CardHeader>
          <CardContent>
            <Button variant="secondary" asChild>
              <Link to="/accounts/password/change/">Change password</Link>
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>
              <Download className="size-4 text-muted-foreground" aria-hidden="true" /> Your data
            </CardTitle>
            <CardDescription>
              Download everything VenuePulse stores about you as JSON: profile, targets, notes, lists, papers, submissions, reviews and notifications.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button variant="secondary" asChild>
              <a href="/accounts/settings/export/" download>
                <Download aria-hidden="true" /> Export my data
              </a>
            </Button>
          </CardContent>
        </Card>

        <Card className="border-destructive/30">
          <CardHeader>
            <CardTitle className="text-destructive">
              <AlertTriangle className="size-4" aria-hidden="true" /> Danger zone
            </CardTitle>
            <CardDescription>Permanently delete your account and all associated data.</CardDescription>
          </CardHeader>
          <CardContent>
            <DeleteAccount />
          </CardContent>
        </Card>
      </div>
    </PageContainer>
  );
}
