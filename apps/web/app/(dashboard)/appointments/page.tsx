"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { AppointmentT } from "@voxdesk/shared";
import { Badge, Card, Empty, statusTone } from "@/components/ui";

export default function AppointmentsPage() {
  const [items, setItems] = useState<AppointmentT[]>([]);

  useEffect(() => { api.appointments().then(setItems).catch(() => {}); }, []);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-white">Appointments</h1>
      <Card>
        {items.length === 0 ? (
          <Empty text="No appointments yet — they appear here when callers book through an agent." />
        ) : (
          <table className="w-full text-left text-sm">
            <thead className="text-slate-500">
              <tr>
                <th className="pb-2 font-medium">Contact</th>
                <th className="pb-2 font-medium">Phone</th>
                <th className="pb-2 font-medium">Starts</th>
                <th className="pb-2 font-medium">Ends</th>
                <th className="pb-2 font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-edge">
              {items.map((a) => (
                <tr key={a.id}>
                  <td className="py-3 text-slate-300">{a.contact_name || "Caller"}</td>
                  <td className="py-3 text-slate-400">{a.contact_phone}</td>
                  <td className="py-3 text-slate-400">{new Date(a.starts_at).toLocaleString()}</td>
                  <td className="py-3 text-slate-400">{new Date(a.ends_at).toLocaleTimeString()}</td>
                  <td className="py-3"><Badge tone={statusTone(a.status)}>{a.status}</Badge></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
