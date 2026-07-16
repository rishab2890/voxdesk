"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { AnalyticsT, CallT } from "@voxdesk/shared";
import { Badge, Card, Empty, Stat, statusTone } from "@/components/ui";

export default function DashboardPage() {
  const [stats, setStats] = useState<AnalyticsT | null>(null);
  const [recent, setRecent] = useState<CallT[]>([]);

  useEffect(() => {
    api.analytics().then(setStats).catch(() => {});
    api.calls(0, 5).then((page) => setRecent(page.items)).catch(() => {});
  }, []);

  const maxPerDay = Math.max(1, ...(stats?.calls_per_day.map((d) => d.count) ?? [1]));

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-white">Dashboard</h1>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
        <Stat label="Total calls" value={stats?.total_calls ?? "–"} />
        <Stat label="Completed" value={stats?.completed_calls ?? "–"} />
        <Stat label="Transferred" value={stats?.transferred_calls ?? "–"} />
        <Stat label="Avg duration (s)" value={stats?.avg_duration_seconds ?? "–"} />
        <Stat label="Appointments" value={stats?.appointments_booked ?? "–"} />
      </div>

      <Card title="Calls per day">
        {stats && stats.calls_per_day.length > 0 ? (
          <div className="flex h-32 items-end gap-2">
            {stats.calls_per_day.map((d) => (
              <div key={d.day} className="flex flex-1 flex-col items-center gap-1" title={`${d.day}: ${d.count}`}>
                <div className="w-full rounded-t bg-accent"
                  style={{ height: `${Math.max(6, (d.count / maxPerDay) * 100)}%` }} />
                <span className="text-[10px] text-slate-500">{d.day.slice(5)}</span>
              </div>
            ))}
          </div>
        ) : (
          <Empty text="No calls yet — simulate one from the Calls page." />
        )}
      </Card>

      <Card title="Recent calls">
        {recent.length === 0 ? (
          <Empty text="No calls yet." />
        ) : (
          <ul className="divide-y divide-edge">
            {recent.map((c) => (
              <li key={c.id}>
                <Link href={`/calls/${c.id}`} className="flex items-center justify-between py-3 hover:bg-edge/40">
                  <span className="text-sm text-slate-300">{c.caller_number || "Unknown caller"}</span>
                  <span className="flex items-center gap-3 text-sm text-slate-500">
                    {new Date(c.started_at).toLocaleString()}
                    <Badge tone={statusTone(c.status)}>{c.status}</Badge>
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
