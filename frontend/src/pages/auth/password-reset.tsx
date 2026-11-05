import { useMutation } from "@tanstack/react-query";
import * as React from "react";
import { Link, useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Field, FormError } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { ApiError, api } from "@/lib/api";

import { AuthLayout } from "./auth-layout";
import { CodeInput, type CodeSent, ResendCode, useCodeSent } from "./code-step";
import { PasswordInput } from "./password-input";

export function Component() {
  const navigate = useNavigate();
  const [email, setEmail] = React.useState("");
  const [code, setCode] = React.useState("");
  const [p1, setP1] = React.useState("");
  const [p2, setP2] = React.useState("");
  const [sent, setSent] = useCodeSent();

  // Step 1: email → a code is sent if an account uses it (the answer is the same either way).
  const request = useMutation({
    mutationFn: () => api.post<CodeSent>("/auth/password-reset/", { email }),
    onSuccess: (data) => {
      setCode("");
      setSent(data);
    },
  });
  // Step 2: code + new password.
  const confirm = useMutation({
    mutationFn: () => api.post("/auth/password-reset/confirm/", { code, new_password1: p1, new_password2: p2 }),
    onSuccess: () => navigate("/accounts/password/reset/complete/"),
  });

  if (sent) {
    const fields = confirm.error instanceof ApiError ? confirm.error.fields : {};
    return (
      <AuthLayout
        title="Choose a new password"
        subtitle={
          <>
            If an account uses <strong className="font-medium text-foreground">{sent.email}</strong>, we sent it a 6-digit code. Enter it with your new
            password. It expires in {Math.round(sent.expires_in / 60)} minutes.
          </>
        }
        footer={
          <button
            type="button"
            className="link"
            onClick={() => {
              setSent(null);
              confirm.reset();
            }}
          >
            Use a different email
          </button>
        }
      >
        <form
          className="grid gap-4"
          onSubmit={(e) => {
            e.preventDefault();
            confirm.mutate();
          }}
        >
          <FormError message={confirm.error && !Object.keys(fields).length ? confirm.error.message : null} />
          <Field label="Code from the email" htmlFor="pr-code" error={fields.code}>
            <CodeInput value={code} onValueChange={setCode} required autoFocus />
          </Field>
          <Field label="New password" htmlFor="pr-p1" error={fields.new_password1} description="At least 8 characters; not entirely numeric or too common.">
            <PasswordInput value={p1} onChange={(e) => setP1(e.target.value)} autoComplete="new-password" required />
          </Field>
          <Field label="Confirm new password" htmlFor="pr-p2" error={fields.new_password2}>
            <PasswordInput value={p2} onChange={(e) => setP2(e.target.value)} autoComplete="new-password" required />
          </Field>
          <Button type="submit" size="lg" className="w-full" loading={confirm.isPending}>
            Set new password
          </Button>
          <ResendCode
            purpose="password_reset"
            availableAt={sent.resendAt}
            onSent={(data) => {
              setCode("");
              confirm.reset();
              setSent(data);
            }}
          />
        </form>
      </AuthLayout>
    );
  }

  const fields = request.error instanceof ApiError ? request.error.fields : {};
  return (
    <AuthLayout
      title="Reset your password"
      subtitle="Enter the email address of your account and we’ll send you a code to choose a new password."
      footer={
        <Link to="/accounts/login/" className="link">
          Back to log in
        </Link>
      }
    >
      <form
        className="grid gap-4"
        onSubmit={(e) => {
          e.preventDefault();
          request.mutate();
        }}
      >
        <FormError message={request.error && !Object.keys(fields).length ? request.error.message : null} />
        <Field label="Email" htmlFor="pr-email" error={fields.email}>
          <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" required autoFocus />
        </Field>
        <Button type="submit" size="lg" className="w-full" loading={request.isPending}>
          Send code
        </Button>
      </form>
    </AuthLayout>
  );
}
