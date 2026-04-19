"use client";

import { useState } from "react";
import { startAudioStream } from "@/lib/webrtc";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const LANGS: Record<string, string> = {
  ko: "Korean", en: "English", es: "Spanish", zh: "Chinese",
  fr: "French", de: "German", pt: "Portuguese", ar: "Arabic",
  vi: "Vietnamese", tl: "Filipino",
};

type Session = { id: number; code: string; title: string; source_lang: string; is_live: boolean; attendees: number };

export default function AdminPage() {
  const [view, setView] = useState<"login" | "register" | "dashboard">("login");
  const [token, setToken] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [orgName, setOrgName] = useState("");
  const [error, setError] = useState("");
  const [sessions, setSessions] = useState<Session[]>([]);
  const [newTitle, setNewTitle] = useState("");
  const [newLang, setNewLang] = useState("ko");
  const [streaming, setStreaming] = useState<Record<string, () => void>>({});

  async function post(path: string, body: object, authToken?: string) {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (authToken) headers["Authorization"] = `Bearer ${authToken}`;
    const res = await fetch(`${API_URL}${path}`, { method: "POST", headers, body: JSON.stringify(body) });
    if (!res.ok) {
      const { detail } = await res.json().catch(() => ({ detail: "Error" }));
      throw new Error(detail);
    }
    return res.json();
  }

  async function get(path: string) {
    const res = await fetch(`${API_URL}${path}`, { headers: { Authorization: `Bearer ${token}` } });
    if (!res.ok) throw new Error("Request failed");
    return res.json();
  }

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const data = await post("/auth/login", { email, password });
      setToken(data.access_token);
      const s = await get("/sessions");
      setSessions(s);
      setView("dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    }
  }

  async function handleRegister(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const data = await post("/auth/register", { org_name: orgName, email, password });
      setToken(data.access_token);
      setSessions([]);
      setView("dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    }
  }

  async function createSession(e: React.FormEvent) {
    e.preventDefault();
    const data = await post("/sessions", { title: newTitle, source_lang: newLang }, token);
    setSessions((prev) => [data, ...prev]);
    setNewTitle("");
  }

  async function startSession(code: string) {
    await post(`/sessions/${code}/start`, {}, token);
    setSessions((prev) => prev.map((s) => (s.code === code ? { ...s, is_live: true } : s)));
    const stop = await startAudioStream(code, token);
    setStreaming((prev) => ({ ...prev, [code]: stop }));
  }

  async function endSession(code: string) {
    streaming[code]?.();
    setStreaming((prev) => { const n = { ...prev }; delete n[code]; return n; });
    await post(`/sessions/${code}/end`, {}, token);
    setSessions((prev) => prev.map((s) => (s.code === code ? { ...s, is_live: false } : s)));
  }

  if (view === "login" || view === "register") {
    return (
      <main className="min-h-screen flex items-center justify-center px-4">
        <form onSubmit={view === "login" ? handleLogin : handleRegister} className="flex flex-col gap-3 w-full max-w-sm">
          <h1 className="text-2xl font-bold mb-2">{view === "login" ? "Admin Login" : "Register"}</h1>
          {view === "register" && (
            <input className="border rounded px-3 py-2" placeholder="Organization name" value={orgName} onChange={(e) => setOrgName(e.target.value)} required />
          )}
          <input type="email" className="border rounded px-3 py-2" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          <input type="password" className="border rounded px-3 py-2" placeholder="Password (12+ chars)" value={password} onChange={(e) => setPassword(e.target.value)} required />
          {error && <p className="text-red-500 text-sm">{error}</p>}
          <button type="submit" className="bg-blue-600 text-white rounded py-2 font-semibold hover:bg-blue-700 transition-colors">
            {view === "login" ? "Login" : "Create account"}
          </button>
          <button type="button" className="text-sm text-gray-400" onClick={() => setView(view === "login" ? "register" : "login")}>
            {view === "login" ? "New organization? Register" : "Already have an account? Login"}
          </button>
        </form>
      </main>
    );
  }

  return (
    <main className="max-w-2xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-6">Sessions</h1>

      <form onSubmit={createSession} className="flex gap-2 mb-8 flex-wrap">
        <input className="border rounded px-3 py-2 flex-1 min-w-0" placeholder="Sermon title" value={newTitle} onChange={(e) => setNewTitle(e.target.value)} />
        <select value={newLang} onChange={(e) => setNewLang(e.target.value)} className="border rounded px-2 py-2">
          {Object.entries(LANGS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <button type="submit" className="bg-blue-600 text-white rounded px-4 py-2 font-semibold hover:bg-blue-700 transition-colors whitespace-nowrap">
          New Session
        </button>
      </form>

      <div className="flex flex-col gap-4">
        {sessions.map((s) => (
          <div key={s.id} className="border rounded-lg p-4 flex items-center justify-between gap-4">
            <div>
              <p className="font-semibold">{s.title || "Untitled"}</p>
              <p className="font-mono text-xl tracking-widest text-blue-600">{s.code}</p>
              <p className="text-sm text-gray-400">{LANGS[s.source_lang]} • {s.attendees} attendees</p>
            </div>
            <div className="flex gap-2">
              {!s.is_live ? (
                <button onClick={() => startSession(s.code)} className="bg-green-600 text-white rounded px-3 py-1 text-sm hover:bg-green-700 transition-colors">
                  Start
                </button>
              ) : (
                <button onClick={() => endSession(s.code)} className="bg-red-600 text-white rounded px-3 py-1 text-sm hover:bg-red-700 transition-colors">
                  End
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </main>
  );
}
