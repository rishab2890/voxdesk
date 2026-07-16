"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { api, getToken, setToken } from "@/lib/api";
import type { OrgT } from "@voxdesk/shared";

const NAV = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/agents", label: "Agents" },
  { href: "/calls", label: "Calls" },
  { href: "/knowledge", label: "Knowledge Base" },
  { href: "/appointments", label: "Appointments" },
  { href: "/integrations", label: "Integrations" },
  { href: "/settings", label: "Settings" },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [org, setOrg] = useState<OrgT | null>(null);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    api.org().then(setOrg).catch(() => {});
  }, [router]);

  return (
    <div className="flex min-h-screen">
      <aside className="flex w-60 shrink-0 flex-col border-r border-edge bg-panel">
        <div className="px-5 py-6 text-xl font-bold text-white">
          Vox<span className="text-accent-soft">Desk</span>
        </div>
        <nav className="flex-1 space-y-1 px-3">
          {NAV.map(({ href, label }) => (
            <Link key={href} href={href}
              className={`block rounded-lg px-3 py-2 text-sm transition ${
                pathname.startsWith(href) ? "bg-accent text-white" : "text-slate-400 hover:bg-edge hover:text-slate-200"
              }`}>
              {label}
            </Link>
          ))}
        </nav>
        <div className="border-t border-edge p-4 text-sm">
          <div className="truncate font-medium text-slate-300">{org?.name ?? "…"}</div>
          <button onClick={() => { setToken(null); router.push("/login"); }}
            className="mt-1 text-slate-500 hover:text-slate-300">
            Sign out
          </button>
        </div>
      </aside>
      <main className="flex-1 overflow-x-auto p-8">{children}</main>
    </div>
  );
}
