"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { AgentT } from "@voxdesk/shared";
import { Badge, Button, Card, Empty, ErrorText, Input, TextArea } from "@/components/ui";

const BLANK: Partial<AgentT> = {
  name: "", greeting: "Hello! How can I help you today?",
  system_prompt: "You are a helpful receptionist.", voice: "kokoro-default",
  language: "en-US", transfer_number: "", transfer_after_booking: false, is_active: true,
};

export default function AgentsPage() {
  const [agents, setAgents] = useState<AgentT[]>([]);
  const [editing, setEditing] = useState<Partial<AgentT> | null>(null);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(() => { api.agents().then(setAgents).catch(() => {}); }, []);
  useEffect(reload, [reload]);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!editing) return;
    setError(null);
    try {
      if (editing.id) await api.updateAgent(editing.id, editing);
      else await api.createAgent(editing);
      setEditing(null);
      reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    }
  }

  async function remove(id: string) {
    await api.deleteAgent(id);
    reload();
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-white">Agents</h1>
        <Button onClick={() => setEditing({ ...BLANK })}>New agent</Button>
      </div>

      {editing && (
        <Card title={editing.id ? "Edit agent" : "New agent"}>
          <form onSubmit={save} className="grid gap-4 md:grid-cols-2">
            <Input label="Name" value={editing.name ?? ""} required
              onChange={(e) => setEditing({ ...editing, name: e.target.value })} />
            <Input label="Transfer number (human fallback)" value={editing.transfer_number ?? ""}
              placeholder="+15551234567"
              onChange={(e) => setEditing({ ...editing, transfer_number: e.target.value })} />
            <Input label="Voice" value={editing.voice ?? ""}
              onChange={(e) => setEditing({ ...editing, voice: e.target.value })} />
            <Input label="Language" value={editing.language ?? ""}
              onChange={(e) => setEditing({ ...editing, language: e.target.value })} />
            <div className="md:col-span-2">
              <TextArea label="Greeting" rows={2} value={editing.greeting ?? ""}
                onChange={(e) => setEditing({ ...editing, greeting: e.target.value })} />
            </div>
            <div className="md:col-span-2">
              <TextArea label="System prompt (personality & rules)" rows={4} value={editing.system_prompt ?? ""}
                onChange={(e) => setEditing({ ...editing, system_prompt: e.target.value })} />
            </div>
            <label className="flex items-center gap-2 text-sm text-slate-300 md:col-span-2">
              <input type="checkbox" checked={editing.transfer_after_booking ?? false}
                onChange={(e) => setEditing({ ...editing, transfer_after_booking: e.target.checked })}
                className="h-4 w-4 accent-indigo-500" />
              Transfer to a human after the caller books (hand-off for conversion)
            </label>
            <ErrorText error={error} />
            <div className="flex gap-2 md:col-span-2">
              <Button type="submit">Save</Button>
              <Button variant="ghost" onClick={() => setEditing(null)}>Cancel</Button>
            </div>
          </form>
        </Card>
      )}

      <Card>
        {agents.length === 0 ? (
          <Empty text="No agents yet. Create your first AI receptionist." />
        ) : (
          <ul className="divide-y divide-edge">
            {agents.map((a) => (
              <li key={a.id} className="flex items-center justify-between py-3">
                <div>
                  <div className="flex items-center gap-2 text-sm font-medium text-slate-200">
                    {a.name}
                    <Badge tone={a.is_active ? "green" : "slate"}>{a.is_active ? "active" : "inactive"}</Badge>
                  </div>
                  <div className="mt-0.5 max-w-xl truncate text-sm text-slate-500">{a.greeting}</div>
                </div>
                <div className="flex gap-2">
                  <Button variant="ghost" onClick={() => setEditing(a)}>Edit</Button>
                  <Button variant="danger" onClick={() => remove(a.id)}>Delete</Button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
