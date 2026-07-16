"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { AgentT, CallT } from "@voxdesk/shared";
import { Badge, Button, Card, Empty, ErrorText, Input, statusTone } from "@/components/ui";

const PAGE_SIZE = 20;

export default function CallsPage() {
  const [calls, setCalls] = useState<CallT[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [agents, setAgents] = useState<AgentT[]>([]);
  const [utterance, setUtterance] = useState("I'd like to book an appointment tomorrow");
  const [agentId, setAgentId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const reload = useCallback(() => {
    api.calls(offset, PAGE_SIZE).then((page) => { setCalls(page.items); setTotal(page.total); }).catch(() => {});
  }, [offset]);
  useEffect(reload, [reload]);
  useEffect(() => { api.agents().then((a) => { setAgents(a); if (a[0]) setAgentId(a[0].id); }).catch(() => {}); }, []);

  async function simulate() {
    setBusy(true);
    setError(null);
    try {
      await api.simulateCall({ agent_id: agentId, utterances: [utterance] });
      reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Simulation failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-white">Calls</h1>

      <Card title="Simulate a call (runs the full voice pipeline on placeholder providers)">
        <div className="flex flex-wrap items-end gap-3">
          <label className="block text-sm">
            <span className="mb-1 block text-slate-400">Agent</span>
            <select value={agentId} onChange={(e) => setAgentId(e.target.value)}
              className="rounded-lg border border-edge bg-surface px-3 py-2 text-slate-200">
              {agents.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
            </select>
          </label>
          <div className="min-w-72 flex-1">
            <Input label="Caller says…" value={utterance} onChange={(e) => setUtterance(e.target.value)} />
          </div>
          <Button onClick={simulate} disabled={busy || !agentId}>{busy ? "Calling…" : "Simulate"}</Button>
        </div>
        <div className="mt-2"><ErrorText error={agents.length === 0 ? "Create an agent first." : error} /></div>
      </Card>

      <Card title={`Call history (${total})`}>
        {calls.length === 0 ? (
          <Empty text="No calls yet." />
        ) : (
          <table className="w-full text-left text-sm">
            <thead className="text-slate-500">
              <tr>
                <th className="pb-2 font-medium">Caller</th>
                <th className="pb-2 font-medium">Started</th>
                <th className="pb-2 font-medium">Duration</th>
                <th className="pb-2 font-medium">Status</th>
                <th />
              </tr>
            </thead>
            <tbody className="divide-y divide-edge">
              {calls.map((c) => (
                <tr key={c.id}>
                  <td className="py-3 text-slate-300">
                    {c.caller_name ? `${c.caller_name} · ${c.caller_number}` : c.caller_number || "Unknown"}
                  </td>
                  <td className="py-3 text-slate-400">{new Date(c.started_at).toLocaleString()}</td>
                  <td className="py-3 text-slate-400">{c.duration_seconds.toFixed(1)}s</td>
                  <td className="py-3"><Badge tone={statusTone(c.status)}>{c.status}</Badge></td>
                  <td className="py-3 text-right">
                    <Link href={`/calls/${c.id}`} className="text-accent-soft hover:underline">Transcript →</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {total > PAGE_SIZE && (
          <div className="mt-4 flex gap-2">
            <Button variant="ghost" disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>Previous</Button>
            <Button variant="ghost" disabled={offset + PAGE_SIZE >= total}
              onClick={() => setOffset(offset + PAGE_SIZE)}>Next</Button>
          </div>
        )}
      </Card>
    </div>
  );
}
