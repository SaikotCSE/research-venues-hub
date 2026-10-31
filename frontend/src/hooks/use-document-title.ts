import { useEffect } from "react";

/** Keep <title> in sync on client-side navigation ("Page · VenuePulse"). */
export function useDocumentTitle(title: string | null | undefined, { raw = false } = {}) {
  useEffect(() => {
    if (!title) return;
    document.title = raw ? title : `${title} · VenuePulse`;
  }, [title, raw]);
}
