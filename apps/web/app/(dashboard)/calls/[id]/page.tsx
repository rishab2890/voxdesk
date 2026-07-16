"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { CallDetailT } from "@voxdesk/shared";
import { Badge, Card, statusTone } from "@/components/ui";

export default function CallDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [call, setCall] = useState<CallDetailT | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);

  useEffect(() => { api.call(id).then(setCall).catch(() => {}); }, [id]);
  useEffect(() => {
    if (!call?.has_recording) return;
    let url: string | null = null;
    api.recordingUrl(call.id).then((u) => { url = u; setAudioUrl(u); }).catch(() => {});
    return () => { if (url) URL.revokeObjectURL(url); };
  }, [call?.has_recording, call?.id]);

  if (!call) return <p className="text-slate-500">Loading…</p>;

  return (
    <div className="space-y-6">
      <div>
        <Link href="/calls" className="text-sm text-slate-500 hover:text-slate-300">← Calls</Link>
        <h1 className="mt-1 flex items-center gap-3 text-2xl font-semibold text-white">
          {call.caller_name || call.caller_number || "Unknown caller"}
          <Badge tone={statusTone(call.status)}>{call.status}</Badge>
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          {call.caller_name && `${call.caller_number} · `}
          {new Date(call.started_at).toLocaleString()} · {call.duration_seconds.toFixed(1)}s
          {call.transferred_to && ` · transferred to ${call.transferred_to}`}
        </p>
      </div>

      {call.has_recording && (
        <Card title="Recording">
          {audioUrl
            ? <audio controls src={audioUrl} className="w-full" />
            : <p className="text-sm text-slate-500">Loading audio…</p>}
        </Card>
      )}

      {call.summary && (
        <Card title={`Summary · intent: ${call.summary.intent}`}>
          <p className="text-sm text-slate-300">{call.summary.content}</p>
        </Card>
      )}

      <Card title="Transcript">
        <div className="space-y-3">
          {call.turns.map((t) => (
            <div key={t.position} className={`flex ${t.role === "caller" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[75%] rounded-2xl px-4 py-2 text-sm ${
                t.role === "caller" ? "bg-accent text-white" : "bg-edge text-slate-200"
              }`}>
                <div className="mb-0.5 text-[10px] uppercase tracking-wide opacity-60">{t.role}</div>
                {t.content}
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
