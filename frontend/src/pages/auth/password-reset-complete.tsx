import { CheckCircle2 } from "lucide-react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";

import { AuthLayout } from "./auth-layout";

export function Component() {
  return (
    <AuthLayout title="Password updated" subtitle="Your password has been changed. You can log in with it now.">
      <CheckCircle2 className="size-10 text-emerald-600" aria-hidden="true" />
      <Button size="lg" className="mt-6 w-full" asChild>
        <Link to="/accounts/login/">Log in</Link>
      </Button>
    </AuthLayout>
  );
}
