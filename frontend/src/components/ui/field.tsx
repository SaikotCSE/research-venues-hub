import * as React from "react";

import { cn } from "@/lib/utils";

import { Label } from "./label";

interface FieldProps {
  label: React.ReactNode;
  htmlFor: string;
  error?: string[] | string;
  description?: React.ReactNode;
  className?: string;
  optional?: boolean;
  children: React.ReactElement;
}

/** Label + control + description + error message, wired with aria-describedby / aria-invalid. */
export function Field({ label, htmlFor, error, description, className, optional, children }: FieldProps) {
  const errors = Array.isArray(error) ? error : error ? [error] : [];
  const descId = description ? `${htmlFor}-desc` : undefined;
  const errId = errors.length ? `${htmlFor}-err` : undefined;
  const control = React.cloneElement(children, {
    id: htmlFor,
    "aria-invalid": errors.length ? true : undefined,
    "aria-describedby": [descId, errId].filter(Boolean).join(" ") || undefined,
  });
  return (
    <div className={cn("grid gap-1.5", className)}>
      <Label htmlFor={htmlFor} className="flex items-center gap-1.5">
        {label}
        {optional && <span className="text-xs font-normal text-muted-foreground">(optional)</span>}
      </Label>
      {control}
      {description && (
        <p id={descId} className="text-xs leading-5 text-muted-foreground">
          {description}
        </p>
      )}
      {errors.length > 0 && (
        <p id={errId} className="text-xs font-medium text-destructive" role="alert">
          {errors.join(" ")}
        </p>
      )}
    </div>
  );
}

export function FormError({ message }: { message?: string | null }) {
  if (!message) return null;
  return (
    <div role="alert" className="rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
      {message}
    </div>
  );
}
