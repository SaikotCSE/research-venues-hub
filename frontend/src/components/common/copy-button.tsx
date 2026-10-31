import { Check, Copy } from "lucide-react";
import * as React from "react";
import { toast } from "sonner";

import { Button, type ButtonProps } from "@/components/ui/button";
import { copyText } from "@/lib/utils";

export function CopyButton({
  text,
  label = "Copy",
  successMessage = "Copied to clipboard",
  ...props
}: { text: string; label?: string; successMessage?: string } & ButtonProps) {
  const [copied, setCopied] = React.useState(false);
  React.useEffect(() => {
    if (!copied) return;
    const id = window.setTimeout(() => setCopied(false), 1800);
    return () => window.clearTimeout(id);
  }, [copied]);
  return (
    <Button
      variant="secondary"
      size="sm"
      {...props}
      onClick={async () => {
        if (await copyText(text)) {
          setCopied(true);
          toast.success(successMessage);
        } else toast.error("Couldn’t copy — select the text and copy it manually.");
      }}
    >
      {copied ? <Check aria-hidden="true" /> : <Copy aria-hidden="true" />}
      {copied ? "Copied" : label}
    </Button>
  );
}
