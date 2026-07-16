"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { IntegrationT } from "@voxdesk/shared";
import { Badge, Button, Card } from "@/components/ui";

const CATALOG = [
  { provider: "telnyx", name: "Telnyx", blurb: "Telephony — inbound numbers and call control." },
  { provider: "dograh", name: "Dograh", blurb: "Self-hosted voice engine driving realtime calls." },
  { provider: "google_calendar", name: "Google Calendar", blurb: "Book appointments into Google Calendar." },
  { provider: "outlook", name: "Outlook Calendar", blurb: "Book appointments into Microsoft 365." },
  { provider: "hubspot", name: "HubSpot", blurb: "Sync callers as CRM contacts." },
  { provider: "gohighlevel", name: "GoHighLevel", blurb: "Sync callers and appointments to GHL." },
  { provider: "webhook", name: "Webhooks", blurb: "Send call events to your own endpoint." },
];

export default function IntegrationsPage() {
  const [rows, setRows] = useState<IntegrationT[]>([]);

  const reload = useCallback(() => { api.integrations().then(setRows).catch(() => {}); }, []);
  useEffect(reload, [reload]);

  async function toggle(provider: string, active: boolean) {
    await api.upsertIntegration(provider, { provider, config: {}, is_active: active });
    reload();
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-white">Integrations</h1>
      <p className="max-w-2xl text-sm text-slate-400">
        Integrations run on placeholder credentials until production keys are configured in the
        backend environment (<code className="text-slate-300">.env</code>). Toggling here records the
        org-level preference.
      </p>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {CATALOG.map((item) => {
          const row = rows.find((r) => r.provider === item.provider);
          const active = row?.is_active ?? false;
          return (
            <Card key={item.provider}>
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2 font-medium text-slate-200">
                    {item.name}
                    <Badge tone={active ? "green" : "slate"}>{active ? "enabled" : "off"}</Badge>
                  </div>
                  <p className="mt-1 text-sm text-slate-500">{item.blurb}</p>
                </div>
              </div>
              <div className="mt-4">
                <Button variant={active ? "ghost" : "primary"} onClick={() => toggle(item.provider, !active)}>
                  {active ? "Disable" : "Enable"}
                </Button>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
