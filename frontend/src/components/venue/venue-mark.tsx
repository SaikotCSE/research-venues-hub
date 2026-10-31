import { cn } from "@/lib/utils";

const GRADIENTS = [
  "from-indigo-500 to-violet-600",
  "from-sky-500 to-indigo-600",
  "from-emerald-500 to-teal-600",
  "from-amber-500 to-orange-600",
  "from-rose-500 to-pink-600",
  "from-fuchsia-500 to-purple-600",
  "from-cyan-500 to-blue-600",
  "from-lime-500 to-emerald-600",
];

function hash(text: string) {
  let h = 0;
  for (let i = 0; i < text.length; i++) h = (h * 31 + text.charCodeAt(i)) | 0;
  return Math.abs(h);
}

/** "CVPR" stays whole; longer names shorten to initials ("USENIX ATC" → "UA") or three letters ("RECOMB" → "REC"). */
export function monogram(acronym: string, max = 4) {
  const clean = acronym.replace(/[^A-Za-z0-9 ]/g, "").trim();
  const compact = clean.replace(/ /g, "");
  if (compact.length <= max) return compact.toUpperCase() || "?";
  const words = clean.split(/\s+/).filter(Boolean);
  if (words.length > 1)
    return words
      .map((w) => w[0])
      .join("")
      .slice(0, max)
      .toUpperCase();
  return compact.slice(0, Math.min(3, max)).toUpperCase();
}

/** Monogram tile giving each venue a stable visual identity. */
export function VenueMark({ acronym, className, size = "md" }: { acronym: string; className?: string; size?: "sm" | "md" | "lg" | "xl" }) {
  const letters = monogram(acronym, size === "sm" ? 2 : 4);
  const dims = {
    sm: "size-7 rounded-md text-[10px]",
    md: "size-10 rounded-lg text-[11px]",
    lg: "size-12 rounded-xl text-sm",
    xl: "size-16 rounded-2xl text-base",
  }[size];
  return (
    <span
      aria-hidden="true"
      className={cn(
        "grid shrink-0 select-none place-items-center bg-gradient-to-br font-bold uppercase tracking-tight text-white shadow-sm ring-1 ring-inset ring-white/15",
        GRADIENTS[hash(acronym) % GRADIENTS.length],
        dims,
        className,
      )}
    >
      {letters}
    </span>
  );
}
