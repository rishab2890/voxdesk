"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, setToken } from "@/lib/api";
import { Button, ErrorText, Input } from "@/components/ui";

export default function RegisterPage() {
  const router = useRouter();
  const [form, setForm] = useState({ name: "", email: "", password: "", organization_name: "" });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function set(field: keyof typeof form) {
    return (e: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, [field]: e.target.value });
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const token = await api.register(form);
      setToken(token.access_token);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center p-6">
      <form onSubmit={submit} className="w-full max-w-sm space-y-4 rounded-2xl border border-edge bg-panel p-8">
        <div className="mb-6 text-center">
          <div className="text-2xl font-bold text-white">Vox<span className="text-accent-soft">Desk</span></div>
          <p className="mt-1 text-sm text-slate-400">Create your workspace</p>
        </div>
        <Input label="Your name" value={form.name} onChange={set("name")} required />
        <Input label="Business name" value={form.organization_name} onChange={set("organization_name")} required />
        <Input label="Email" type="email" value={form.email} onChange={set("email")} required />
        <Input label="Password (8+ characters)" type="password" minLength={8} value={form.password} onChange={set("password")} required />
        <ErrorText error={error} />
        <Button type="submit" disabled={busy}>{busy ? "Creating…" : "Create account"}</Button>
        <p className="text-sm text-slate-500">
          Have an account? <Link href="/login" className="text-accent-soft hover:underline">Sign in</Link>
        </p>
      </form>
    </main>
  );
}
