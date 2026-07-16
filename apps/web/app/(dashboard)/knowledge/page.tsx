"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { DocumentT } from "@voxdesk/shared";
import { Badge, Button, Card, Empty, ErrorText, Input, statusTone } from "@/components/ui";

export default function KnowledgePage() {
  const [docs, setDocs] = useState<DocumentT[]>([]);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<{ content: string; score: number }[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const reload = useCallback(() => { api.documents().then(setDocs).catch(() => {}); }, []);
  useEffect(reload, [reload]);

  async function upload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      await api.uploadDocument(file);
      reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function search(e: React.FormEvent) {
    e.preventDefault();
    setResults(await api.retrieve(query));
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-white">Knowledge Base</h1>
        <div>
          <input ref={fileRef} type="file" accept=".pdf,.txt,.md,.csv" className="hidden" onChange={upload} />
          <Button onClick={() => fileRef.current?.click()} disabled={busy}>
            {busy ? "Uploading…" : "Upload document"}
          </Button>
        </div>
      </div>
      <ErrorText error={error} />

      <Card title="Documents">
        {docs.length === 0 ? (
          <Empty text="Upload PDFs or text files your AI receptionist should know." />
        ) : (
          <ul className="divide-y divide-edge">
            {docs.map((d) => (
              <li key={d.id} className="flex items-center justify-between py-3">
                <div>
                  <div className="text-sm font-medium text-slate-200">{d.filename}</div>
                  <div className="text-xs text-slate-500">{d.chunk_count} chunks · {new Date(d.created_at).toLocaleString()}</div>
                </div>
                <div className="flex items-center gap-3">
                  <Badge tone={statusTone(d.status)}>{d.status}</Badge>
                  <Button variant="danger" onClick={async () => { await api.deleteDocument(d.id); reload(); }}>
                    Delete
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card title="Test retrieval">
        <form onSubmit={search} className="flex items-end gap-3">
          <div className="flex-1">
            <Input label="Ask a question your callers might ask" value={query}
              onChange={(e) => setQuery(e.target.value)} required />
          </div>
          <Button type="submit">Search</Button>
        </form>
        {results && (
          <div className="mt-4 space-y-2">
            {results.length === 0 && <Empty text="No matching content." />}
            {results.map((r, i) => (
              <div key={i} className="rounded-lg border border-edge bg-surface p-3 text-sm text-slate-300">
                <span className="mr-2 text-xs text-accent-soft">score {r.score.toFixed(2)}</span>
                {r.content}
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
