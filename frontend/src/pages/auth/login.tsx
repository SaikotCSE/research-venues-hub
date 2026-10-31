import { useMutation } from "@tanstack/react-query";
import * as React from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Field, FormError } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { ApiError, api } from "@/lib/api";
import type { Session } from "@/lib/types";
import { useResetAfterAuth } from "@/providers/session";

import { AuthLayout, goTo, useNextParam } from "./auth-layout";
import { PasswordInput } from "./password-input";

export function Component() {
  const navigate = useNavigate();
  const reset = useResetAfterAuth();
  const next = useNextParam("/accounts/");
  const [username, setUsername] = React.useState("");
  const [password, setPassword] = React.useState("");
  const login = useMutation({
    mutationFn: () => api.post<Session & { next: string }>("/auth/login/", { username, password, next }),
    onSuccess: (s) => {
      reset(s);
      toast.success(`Welcome back, ${s.user?.name ?? username}`);
      goTo(navigate, s.next);
    },
  });
  const fields = login.error instanceof ApiError ? login.error.fields : {};
  return (
    <AuthLayout
      title="Welcome back"
      subtitle="Log in to sync your targets, reminders and submission tracker."
      footer={
        <>
          New to VenuePulse?{" "}
          <Link to={`/accounts/signup/${next !== "/accounts/" ? `?next=${encodeURIComponent(next)}` : ""}`} className="link">
            Create a free account
          </Link>
        </>
      }
    >
      <form
        className="grid gap-4"
        onSubmit={(e) => {
          e.preventDefault();
          login.mutate();
        }}
      >
        <FormError message={login.error && !Object.keys(fields).length ? login.error.message : null} />
        <Field label="Username" htmlFor="login-username" error={fields.username}>
          <Input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            autoCapitalize="none"
            spellCheck={false}
            required
            autoFocus
          />
        </Field>
        <div className="grid gap-1.5">
          <Field label="Password" htmlFor="login-password" error={fields.password}>
            <PasswordInput value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required />
          </Field>
          <Link to="/accounts/password/reset/" className="link justify-self-end text-xs font-normal">
            Forgot password?
          </Link>
        </div>
        <Button type="submit" size="lg" className="mt-2 w-full" loading={login.isPending}>
          Log in
        </Button>
      </form>
    </AuthLayout>
  );
}
