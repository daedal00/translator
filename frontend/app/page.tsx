"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

export default function Home() {
  const router = useRouter();
  const [code, setCode] = useState("");
  const [error, setError] = useState("");

  function handleJoin(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = code.trim().toUpperCase();
    if (trimmed.length < 4) {
      setError("Enter the code shown on screen.");
      return;
    }
    router.push(`/s/${trimmed}`);
  }

  return (
    <main className="min-h-screen flex flex-col items-center justify-center px-4">
      <h1 className="text-3xl font-bold mb-2">Sermon Translator</h1>
      <p className="text-gray-500 mb-8 text-center">Follow along in your language, live.</p>

      <form onSubmit={handleJoin} className="flex flex-col gap-3 w-full max-w-xs">
        <input
          className="border rounded-lg px-4 py-3 text-2xl text-center uppercase tracking-widest font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="ABC123"
          maxLength={8}
          value={code}
          onChange={(e) => {
            setCode(e.target.value.toUpperCase());
            setError("");
          }}
          autoFocus
        />
        {error && <p className="text-red-500 text-sm text-center">{error}</p>}
        <button
          type="submit"
          className="bg-blue-600 hover:bg-blue-700 text-white rounded-lg py-3 font-semibold transition-colors"
        >
          Join
        </button>
      </form>

      <Link href="/admin" className="mt-12 text-sm text-gray-400 hover:text-gray-600">
        Church admin login →
      </Link>
    </main>
  );
}
