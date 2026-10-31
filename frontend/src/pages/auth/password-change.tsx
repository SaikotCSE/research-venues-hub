import { useMutation } from "@tanstack/react-query";
import { KeyRound } from "lucide-react";
import * as React from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { PageContainer, PageHeader } from "@/components/common/page";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Field, FormError } from "@/components/ui/field";
import { useDocumentTitle } from "@/hooks/use-document-title";
import { ApiError, api } from "@/lib/api";

import { PasswordInput } from "./password-input";

export function Component() {
  useDocumentTitle("Change password");
  const navigate = useNavigate();
  const [form, setForm] = React.useState({ old_password: "", new_password1: "", new_password2: "" });
  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) => setForm((f) => ({ ...f, [key]: e.target.value }));
  const change = useMutation({
    mutationFn: () => api.post("/auth/password-change/", form),
    onSuccess: () => {
      toast.success("Your password was changed");
      navigate("/accounts/settings/");
    },
  });
  const fields = change.error instanceof ApiError ? change.error.fields : {};
  return (
    <PageContainer size="narrow">
      <PageHeader icon={KeyRound} title="Change password" description="You’ll stay signed in on this device." />
      <Card>
        <CardContent className="p-6">
          <form
            className="grid max-w-md gap-4"
            onSubmit={(e) => {
              e.preventDefault();
              change.mutate();
            }}
          >
            <FormError message={change.error && !Object.keys(fields).length ? change.error.message : null} />
            <Field label="Current password" htmlFor="pc-old" error={fields.old_password}>
              <PasswordInput value={form.old_password} onChange={set("old_password")} autoComplete="current-password" required autoFocus />
            </Field>
            <Field label="New password" htmlFor="pc-new1" error={fields.new_password1} description="At least 8 characters; not entirely numeric or too common.">
              <PasswordInput value={form.new_password1} onChange={set("new_password1")} autoComplete="new-password" required />
            </Field>
            <Field label="Confirm new password" htmlFor="pc-new2" error={fields.new_password2}>
              <PasswordInput value={form.new_password2} onChange={set("new_password2")} autoComplete="new-password" required />
            </Field>
            <div className="mt-2 flex gap-2">
              <Button type="submit" loading={change.isPending}>
                Update password
              </Button>
              <Button variant="ghost" asChild>
                <Link to="/accounts/settings/">Cancel</Link>
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </PageContainer>
  );
}
