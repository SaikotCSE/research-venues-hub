import { Compass, Search } from "lucide-react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { useDocumentTitle } from "@/hooks/use-document-title";
import { usePalette } from "@/providers/palette";

export function NotFoundPage({ what = "page" }: { what?: "page" | "venue" | "list" | "submission" }) {
  const palette = usePalette();
  useDocumentTitle(what === "venue" ? "Venue not found" : "Page not found");
  return (
    <div className="mx-auto flex max-w-xl flex-col items-center px-4 py-24 text-center">
      <p className="tnum bg-gradient-to-br from-indigo-500 to-violet-600 bg-clip-text text-7xl font-bold tracking-tighter text-transparent">404</p>
      <h1 className="mt-4 text-2xl font-semibold tracking-tight sm:text-3xl">
        {what === "venue" ? "We couldn’t find that venue" : what === "list" ? "This list is private or doesn’t exist" : "We couldn’t find that page"}
      </h1>
      <p className="mt-3 text-muted-foreground">
        {what === "venue"
          ? "It may have been renamed, or the link might be mistyped. Search the catalogue instead."
          : "The link may be broken or the page may have moved."}
      </p>
      <div className="mt-8 flex flex-wrap justify-center gap-3">
        <Button asChild>
          <Link to="/">
            <Compass aria-hidden="true" /> Explore venues
          </Link>
        </Button>
        <Button variant="secondary" onClick={() => palette.setOpen(true)}>
          <Search aria-hidden="true" /> Search
        </Button>
      </div>
    </div>
  );
}

export const Component = NotFoundPage;
