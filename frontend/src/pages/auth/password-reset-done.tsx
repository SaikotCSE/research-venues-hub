import { MailCheck } from "lucide-react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";

import { AuthLayout } from "./auth-layout";

export function Component() {
  return (
    <AuthLayout title="Check your email" subtitle="If an account exists for that address, a reset link is on its way. It’s valid for 24 hours and works once.">
      <div className="rounded-xl border bg-surface p-5 text-sm leading-6 text-muted-foreground">
        <MailCheck className="mb-3 size-6 text-brand-text" aria-hidden="true" />
        Nothing after a few minutes? Check your spam folder, or make sure you used the address you signed up with.
      </div>
      <Button variant="secondary" className="mt-6 w-full" asChild>
        <Link to="/accounts/login/">Back to log in</Link>
      </Button>
    </AuthLayout>
  );
}
