import { cn } from "@/lib/utils";

import { CopyButton } from "./copy-button";

export function CodeBlock({ code, label, className, wrap = false }: { code: string; label?: string; className?: string; wrap?: boolean }) {
  return (
    <div className={cn("overflow-hidden rounded-xl border border-zinc-800 bg-zinc-950 text-zinc-100 dark:border-white/10 dark:bg-black/40", className)}>
      <div className="flex items-center justify-between gap-2 border-b border-white/10 py-1.5 pl-4 pr-1.5">
        <span className="text-[11px] font-medium uppercase tracking-wider text-zinc-400">{label ?? "Snippet"}</span>
        <CopyButton text={code} size="xs" variant="ghost" className="text-zinc-300 hover:bg-white/10 hover:text-white" />
      </div>
      <pre className={cn("scrollbar-thin overflow-x-auto p-4 text-[12.5px] leading-6", wrap && "whitespace-pre-wrap break-all")}>
        <code className="font-mono">{code}</code>
      </pre>
    </div>
  );
}
