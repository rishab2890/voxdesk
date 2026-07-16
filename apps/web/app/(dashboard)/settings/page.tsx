"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { MemberT, OrgT } from "@voxdesk/shared";
import { Badge, Button, Card, Empty, ErrorText, Input } from "@/components/ui";

export default function SettingsPage() {
  const [org, setOrg] = useState<OrgT | null>(null);
  const [members, setMembers] = useState<MemberT[]>([]);
  const [invite, setInvite] = useState({ email: "", name: "", password: "", role: "member" });
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const reload = useCallback(() => {
    api.org().then(setOrg).catch(() => {});
    api.members().then(setMembers).catch(() => {});
  }, []);
  useEffect(reload, [reload]);

  async function saveOrg(e: React.FormEvent) {
    e.preventDefault();
    if (!org) return;
    await api.updateOrg({ name: org.name, industry: org.industry });
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  async function sendInvite(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api.invite(invite);
      setInvite({ email: "", name: "", password: "", role: "member" });
      reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invite failed");
    }
  }

  return (
    <div className="max-w-3xl space-y-6">
      <h1 className="text-2xl font-semibold text-white">Settings</h1>

      <Card title="Organization">
        {org && (
          <form onSubmit={saveOrg} className="space-y-4">
            <Input label="Business name" value={org.name} onChange={(e) => setOrg({ ...org, name: e.target.value })} />
            <Input label="Industry" value={org.industry} onChange={(e) => setOrg({ ...org, industry: e.target.value })} />
            <div className="flex items-center gap-3">
              <Button type="submit">Save</Button>
              {saved && <span className="text-sm text-green-400">Saved ✓</span>}
            </div>
          </form>
        )}
      </Card>

      <Card title="Team members">
        {members.length === 0 ? <Empty text="No members." /> : (
          <ul className="divide-y divide-edge">
            {members.map((m) => (
              <li key={m.id} className="flex items-center justify-between py-3 text-sm">
                <div>
                  <span className="text-slate-200">{m.user.name || m.user.email}</span>
                  <span className="ml-2 text-slate-500">{m.user.email}</span>
                </div>
                <Badge tone={m.role === "owner" ? "indigo" : "slate"}>{m.role}</Badge>
              </li>
            ))}
          </ul>
        )}
        <form onSubmit={sendInvite} className="mt-4 grid gap-3 border-t border-edge pt-4 md:grid-cols-2">
          <Input label="Email" type="email" value={invite.email} required
            onChange={(e) => setInvite({ ...invite, email: e.target.value })} />
          <Input label="Name" value={invite.name}
            onChange={(e) => setInvite({ ...invite, name: e.target.value })} />
          <Input label="Temporary password" type="password" minLength={8} value={invite.password} required
            onChange={(e) => setInvite({ ...invite, password: e.target.value })} />
          <label className="block text-sm">
            <span className="mb-1 block text-slate-400">Role</span>
            <select value={invite.role} onChange={(e) => setInvite({ ...invite, role: e.target.value })}
              className="w-full rounded-lg border border-edge bg-surface px-3 py-2 text-slate-200">
              <option value="member">Member</option>
              <option value="admin">Admin</option>
            </select>
          </label>
          <ErrorText error={error} />
          <div className="md:col-span-2"><Button type="submit">Add member</Button></div>
        </form>
      </Card>
    </div>
  );
}
