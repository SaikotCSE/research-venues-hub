import { CalendarPlus, ChevronDown, Download, FileJson, FileSpreadsheet, Rss } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export function ExportMenu({ query, scope }: { query: string; scope?: "targets" }) {
  const qs = [query, scope ? `scope=${scope}` : ""].filter(Boolean).join("&");
  const suffix = qs ? `?${qs}` : "";
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="secondary" size="sm">
          <Download aria-hidden="true" />
          Export
          <ChevronDown className="opacity-60" aria-hidden="true" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-64">
        <DropdownMenuLabel>{scope ? "Exports include your targets only" : "Exports use the current filters"}</DropdownMenuLabel>
        <DropdownMenuItem asChild>
          <a href={`/export/csv/${suffix}`} download>
            <FileSpreadsheet aria-hidden="true" /> CSV spreadsheet
          </a>
        </DropdownMenuItem>
        <DropdownMenuItem asChild>
          <a href={`/export/json/${suffix}`} download>
            <FileJson aria-hidden="true" /> JSON with all cycles
          </a>
        </DropdownMenuItem>
        {!scope && (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuItem asChild>
              <a href={`/calendar.ics${suffix}`}>
                <CalendarPlus aria-hidden="true" /> Subscribe in your calendar (.ics)
              </a>
            </DropdownMenuItem>
            <DropdownMenuItem asChild>
              <a href={`/feed/deadlines.atom${suffix}`}>
                <Rss aria-hidden="true" /> Atom feed
              </a>
            </DropdownMenuItem>
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
