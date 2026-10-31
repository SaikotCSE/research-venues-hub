import { useMutation } from "@tanstack/react-query";
import * as React from "react";
import { Link, useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Field, FormError } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { ApiError, api } from "@/lib/api";

import { AuthLayout } from "./auth-layout";

export function Component() {
  const navigate = useNavigate();
  const [email, setEmail] = React.useState("");
  const reset = useMutation({ mutationFn: () => api.post("/auth/password-reset/", { email }), onSuccess: () => navigate("/accounts/password/reset/sent/") });
  const fields = reset.error instanceof ApiError ? reset.error.fields : {};
  return (
    <AuthLayout
      title="Reset your password"
      subtitle="Enter the email address of your account and we’ll send you a link to choose a new password."
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
          reset.mutate();
        }}
      >
        <FormError message={reset.error && !Object.keys(fields).length ? reset.error.message : null} />
        <Field label="Email" htmlFor="pr-email" error={fields.email}>
          <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" required autoFocus />
        </Field>
        <Button type="submit" size="lg" className="w-full" loading={reset.isPending}>
          Send reset link
        </Button>
      </form>
    </AuthLayout>
  );
}
