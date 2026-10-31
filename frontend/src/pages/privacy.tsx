import { Lock } from "lucide-react";
import { Link } from "react-router-dom";

import { PageContainer, PageHeader } from "@/components/common/page";
import { useDocumentTitle } from "@/hooks/use-document-title";

const STORAGE = [
  ["sessionid", "Cookie", "Keeps you logged in; links anonymous stars to your browser."],
  ["csrftoken", "Cookie", "Protects forms against cross-site request forgery."],
  ["vp-theme, vp-tz", "Local storage", "Your theme and timezone choice."],
  ["vp-compare, vp-recent", "Local storage", "Venues in your comparison tray and recently viewed venues."],
];

export function Component() {
  useDocumentTitle("Privacy");
  return (
    <PageContainer size="narrow">
      <PageHeader
        icon={Lock}
        eyebrow="Privacy"
        title="Your data, plainly explained"
        description="VenuePulse collects only what it needs to work. There are no advertising or analytics trackers, and every script, font and icon is served from this site — no third-party CDN sees your visits."
      />
      <div className="prose-app">
        <h2>What we store</h2>
        <ul>
          <li>
            <strong>Account:</strong> username, email address, a salted password hash, and profile details you choose to add (display name, affiliation,
            research interests, timezone, reminder preferences).
          </li>
          <li>
            <strong>Your work:</strong> starred venues and private notes, venue lists, saved searches, papers, submissions and checklists, experience reviews
            and correction suggestions you submit.
          </li>
          <li>
            <strong>Without an account:</strong> stars and notes are stored against a random identifier kept in your session cookie, and merged into your
            account if you sign up.
          </li>
          <li>
            <strong>Operational logs:</strong> request logs (IP address, path, timing, a request ID) kept briefly to keep the service secure and reliable.
          </li>
        </ul>
        <h2>Cookies & local storage</h2>
      </div>
      <div className="mt-3 overflow-hidden rounded-xl border bg-card shadow-card">
        <table className="w-full text-sm">
          <thead className="bg-surface text-left text-xs text-muted-foreground">
            <tr>
              <th scope="col" className="px-4 py-2.5 font-medium">
                Name
              </th>
              <th scope="col" className="px-4 py-2.5 font-medium">
                Type
              </th>
              <th scope="col" className="px-4 py-2.5 font-medium">
                Purpose
              </th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {STORAGE.map(([name, type, purpose]) => (
              <tr key={name}>
                <td className="px-4 py-2.5 font-mono text-[13px]">{name}</td>
                <td className="whitespace-nowrap px-4 py-2.5 text-muted-foreground">{type}</td>
                <td className="px-4 py-2.5">{purpose}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="prose-app">
        <h2>Email</h2>
        <p>
          We email you only for account security (confirmation and password resets), deadline reminders and the weekly digest — and reminders only after you
          confirm your address. Turn reminders and the digest off at any time on your profile.
        </p>
        <h2>What others can see</h2>
        <p>
          Everything is private by default. Venue lists you make public, and the display name on experience reviews you post, are visible to others. Your
          calendar-feed and API tokens are secrets — regenerate them on your <Link to="/accounts/profile/">profile</Link> if they leak.
        </p>
        <h2>You are in control</h2>
        <p>
          From <Link to="/accounts/settings/">account settings</Link> you can download a complete JSON export of your data, change your email or password, and
          permanently delete your account together with everything associated with it.
        </p>
      </div>
    </PageContainer>
  );
}
