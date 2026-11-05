import { useMutation } from "@tanstack/react-query";
import * as React from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api, errorMessage } from "@/lib/api";
import { cn } from "@/lib/utils";

export type CodePurpose = "signup" | "password_reset";

/** The API's answer after emailing a one-time code. */
export interface CodeSent {
  ok: true;
  email: string;
  message: string;
  expires_in: number;
  resend_in: number;
}

export const CODE_LENGTH = 6;

type CodeInputProps = Omit<React.InputHTMLAttributes<HTMLInputElement>, "value" | "onChange"> & {
  value: string;
  onValueChange: (value: string) => void;
};

/** Six-digit code field: numeric keypad on phones, one-time-code autofill, and pasting "123 456" works. */
export function CodeInput({ value, onValueChange, className, ...props }: CodeInputProps) {
  return (
    <Input
      value={value}
      onChange={(e) => onValueChange(e.target.value.replace(/\D/g, "").slice(0, CODE_LENGTH))}
      inputMode="numeric"
      autoComplete="one-time-code"
      spellCheck={false}
      placeholder={"0".repeat(CODE_LENGTH)}
      className={cn("h-12 text-center font-mono text-2xl tabular-nums tracking-[0.4em] placeholder:text-muted-foreground/40", className)}
      {...props}
    />
  );
}

function secondsUntil(time: number) {
  return Math.max(0, Math.ceil((time - Date.now()) / 1000));
}

function useCountdown(until: number) {
  const [left, setLeft] = React.useState(() => secondsUntil(until));
  React.useEffect(() => {
    setLeft(secondsUntil(until));
    const timer = window.setInterval(() => {
      const s = secondsUntil(until);
      setLeft(s);
      if (s === 0) window.clearInterval(timer);
    }, 1000);
    return () => window.clearInterval(timer);
  }, [until]);
  return left;
}

/** "Send a new code" link, disabled with a countdown until the server will accept another request. */
export function ResendCode({ purpose, availableAt, onSent }: { purpose: CodePurpose; availableAt: number; onSent: (data: CodeSent) => void }) {
  const wait = useCountdown(availableAt);
  const resend = useMutation({
    mutationFn: () => api.post<CodeSent>("/auth/code/resend/", { purpose }),
    onSuccess: (data) => {
      toast.success(data.message);
      onSent(data);
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
  return (
    <p className="text-center text-sm text-muted-foreground" aria-live="polite">
      No email? Check your spam folder, or{" "}
      {wait > 0 ? (
        <span>request a new code in {wait}s.</span>
      ) : (
        <Button type="button" variant="link" className="text-sm" loading={resend.isPending} onClick={() => resend.mutate()}>
          send a new code
        </Button>
      )}
    </p>
  );
}

/** Remember when a code was sent so the resend countdown survives re-renders. */
export function useCodeSent() {
  const [sent, setSent] = React.useState<(CodeSent & { resendAt: number }) | null>(null);
  const update = React.useCallback((data: CodeSent | null) => setSent(data && { ...data, resendAt: Date.now() + data.resend_in * 1000 }), []);
  return [sent, update] as const;
}
