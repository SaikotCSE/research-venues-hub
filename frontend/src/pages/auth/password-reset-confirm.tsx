import { useMutation } from "@tanstack/react-query";
import { AlertTriangle } from "lucide-react";
import * as React from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Field, FormError } from "@/components/ui/field";
import { ApiError, api } from "@/lib/api";
import { boot } from "@/lib/boot";

import { AuthLayout } from "./auth-layout";
import { PasswordInput } from "./password-input";

export function Component() {
  const { uid = "" } = useParams();
  const navigate = useNavigate();
  const valid = boot.page === "password_reset_confirm" ? (boot.extra.reset?.valid ?? false) : true;
  const [p1, setP1] = React.useState("");
  const [p2, setP2] = React.useState("");
  const confirm = useMutation({
    mutationFn: () => api.post("/auth/password-reset/confirm/", { uid, new_password1: p1, new_password2: p2 }),
    onSuccess: () => navigate("/accounts/password/reset/complete/"),
  });
  const fields = confirm.error instanceof ApiError ? confirm.error.fields : {};
  if (!valid)
    return (
      <AuthLayout title="This link has expired" subtitle="Password reset links work once and expire after 24 hours.">
        <div className="flex gap-3 rounded-xl border border-amber-300/60 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-400/20 dark:bg-amber-400/10 dark:text-amber-200">
          <AlertTriangle className="size-5 shrink-0" aria-hidden="true" />
          Request a new link and use it straight away.
        </div>
        <Button className="mt-6 w-full" asChild>
          <Link to="/accounts/password/reset/">Request a new link</Link>
        </Button>
      </AuthLayout>
    );
  return (
    <AuthLayout title="Choose a new password" subtitle="Pick something you don’t use anywhere else.">
      <form
        className="grid gap-4"
        onSubmit={(e) => {
          e.preventDefault();
          confirm.mutate();
        }}
      >
        <FormError message={confirm.error && !Object.keys(fields).length ? confirm.error.message : null} />
        <Field label="New password" htmlFor="rc-p1" error={fields.new_password1} description="At least 8 characters; not entirely numeric or too common.">
          <PasswordInput value={p1} onChange={(e) => setP1(e.target.value)} autoComplete="new-password" required autoFocus />
        </Field>
        <Field label="Confirm new password" htmlFor="rc-p2" error={fields.new_password2}>
          <PasswordInput value={p2} onChange={(e) => setP2(e.target.value)} autoComplete="new-password" required />
        </Field>
        <Button type="submit" size="lg" className="w-full" loading={confirm.isPending}>
          Set new password
        </Button>
      </form>
    </AuthLayout>
  );
}
