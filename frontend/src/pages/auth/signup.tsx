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
import { CodeInput, type CodeSent, ResendCode, useCodeSent } from "./code-step";
import { PasswordInput } from "./password-input";

export function Component() {
  const navigate = useNavigate();
  const reset = useResetAfterAuth();
  const next = useNextParam("/accounts/profile/");
  const [form, setForm] = React.useState({ username: "", email: "", password1: "", password2: "" });
  const [code, setCode] = React.useState("");
  const [sent, setSent] = useCodeSent();
  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) => setForm((f) => ({ ...f, [key]: e.target.value }));

  // Step 1: details → the server emails a code (no account exists yet).
  const signup = useMutation({
    mutationFn: () => api.post<CodeSent>("/auth/signup/", form),
    onSuccess: (data) => {
      setCode("");
      setSent(data);
    },
  });
  // Step 2: the code → the account is created with its email confirmed, and we're logged in.
  const verify = useMutation({
    mutationFn: () => api.post<Session & { next: string; message: string }>("/auth/signup/verify/", { code, next }),
    onSuccess: (s) => {
      reset(s);
      toast.success(s.message, { description: "Add a few research interests to get personalised recommendations." });
      goTo(navigate, s.next);
    },
  });

  if (sent) {
    const fields = verify.error instanceof ApiError ? verify.error.fields : {};
    return (
      <AuthLayout
        title="Check your email"
        subtitle={
          <>
            We sent a 6-digit code to <strong className="font-medium text-foreground">{sent.email}</strong>. Enter it to finish creating your account. It
            expires in {Math.round(sent.expires_in / 60)} minutes.
          </>
        }
        footer={
          <>
            Wrong address?{" "}
            <button
              type="button"
              className="link"
              onClick={() => {
                setSent(null);
                verify.reset();
              }}
            >
              Change your details
            </button>
          </>
        }
      >
        <form
          className="grid gap-4"
          onSubmit={(e) => {
            e.preventDefault();
            verify.mutate();
          }}
        >
          <FormError message={verify.error && !Object.keys(fields).length ? verify.error.message : null} />
          <Field label="Confirmation code" htmlFor="su-code" error={fields.code}>
            <CodeInput value={code} onValueChange={setCode} required autoFocus />
          </Field>
          <Button type="submit" size="lg" className="w-full" loading={verify.isPending}>
            Verify and create account
          </Button>
          <ResendCode
            purpose="signup"
            availableAt={sent.resendAt}
            onSent={(data) => {
              setCode("");
              verify.reset();
              setSent(data);
            }}
          />
        </form>
      </AuthLayout>
    );
  }

  const fields = signup.error instanceof ApiError ? signup.error.fields : {};
  return (
    <AuthLayout
      title="Create your account"
      subtitle="Free forever. Sync starred venues across devices and get reminded before every deadline."
      footer={
        <>
          Already have an account?{" "}
          <Link to="/accounts/login/" className="link">
            Log in
          </Link>
        </>
      }
    >
      <form
        className="grid gap-4"
        onSubmit={(e) => {
          e.preventDefault();
          signup.mutate();
        }}
      >
        <FormError message={signup.error && !Object.keys(fields).length ? signup.error.message : null} />
        <Field label="Username" htmlFor="su-username" error={fields.username} description="Letters, digits and @ . + - _ only.">
          <Input
            value={form.username}
            onChange={set("username")}
            autoComplete="username"
            autoCapitalize="none"
            spellCheck={false}
            required
            autoFocus
            maxLength={150}
          />
        </Field>
        <Field label="Email" htmlFor="su-email" error={fields.email} description="We'll email you a code to confirm it. We never share it.">
          <Input type="email" value={form.email} onChange={set("email")} autoComplete="email" required />
        </Field>
        <Field label="Password" htmlFor="su-password1" error={fields.password1} description="At least 8 characters; not entirely numeric or too common.">
          <PasswordInput value={form.password1} onChange={set("password1")} autoComplete="new-password" required />
        </Field>
        <Field label="Confirm password" htmlFor="su-password2" error={fields.password2}>
          <PasswordInput value={form.password2} onChange={set("password2")} autoComplete="new-password" required />
        </Field>
        <Button type="submit" size="lg" className="mt-2 w-full" loading={signup.isPending}>
          Continue
        </Button>
        <p className="text-center text-xs text-muted-foreground">
          By signing up you agree to our{" "}
          <Link to="/privacy/" className="link">
            privacy policy
          </Link>
          .
        </p>
      </form>
    </AuthLayout>
  );
}
