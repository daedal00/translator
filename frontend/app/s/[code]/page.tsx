"use client";

import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { CaptionMsg, SessionSocket } from "@/lib/ws";

const LANGS: Record<string, string> = {
  en: "English", ko: "한국어", es: "Español", zh: "中文",
  fr: "Français", de: "Deutsch", pt: "Português", ar: "العربية",
  vi: "Tiếng Việt", tl: "Filipino",
};

const BIBLE_TRANSLATIONS = ["KJV", "NIV", "ESV", "NLT", "NASB"];

type Caption = { text: string; verse: CaptionMsg["verse"] };

export default function SessionPage() {
  const { code } = useParams<{ code: string }>();
  const [lang, setLang] = useState("en");
  const [bibleTrans, setBibleTrans] = useState("KJV");
  const [captions, setCaptions] = useState<Caption[]>([]);
  const [connected, setConnected] = useState(false);
  const [ended, setEnded] = useState(false);
  const socketRef = useRef<SessionSocket | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const socket = new SessionSocket(code, lang);
    socketRef.current = socket;

    socket.onMessage = (msg) => {
      if (msg.type === "caption") {
        const text = msg.translations[lang] ?? msg.translations[msg.source_lang] ?? "";
        if (text) setCaptions((prev) => [...prev.slice(-49), { text, verse: msg.verse }]);
      } else if (msg.type === "joined") {
        setConnected(true);
      } else if (msg.type === "session_ended") {
        setEnded(true);
      }
    };

    socket.onDisconnect = () => setConnected(false);
    socket.connect();

    return () => socket.close();
  }, [code]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [captions]);

  function changeLang(newLang: string) {
    setLang(newLang);
    socketRef.current?.setLang(newLang);
  }

  return (
    <main className="min-h-screen flex flex-col max-w-2xl mx-auto px-4 py-6">
      <header className="flex items-center justify-between mb-4 gap-2 flex-wrap">
        <span className="font-mono text-sm text-gray-400">{code}</span>

        <div className="flex gap-2 flex-wrap">
          <select
            value={lang}
            onChange={(e) => changeLang(e.target.value)}
            className="border rounded px-2 py-1 text-sm"
          >
            {Object.entries(LANGS).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </select>

          <select
            value={bibleTrans}
            onChange={(e) => setBibleTrans(e.target.value)}
            className="border rounded px-2 py-1 text-sm"
          >
            {BIBLE_TRANSLATIONS.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>

        <span className={`w-2 h-2 rounded-full ${connected ? "bg-green-500" : "bg-gray-400"}`} title={connected ? "Connected" : "Reconnecting..."} />
      </header>

      {ended && (
        <div className="text-center text-gray-500 py-8">Session has ended. Thank you!</div>
      )}

      <div className="flex-1 flex flex-col gap-3 overflow-y-auto">
        {captions.map((c, i) => (
          <div key={i} className="flex flex-col gap-2">
            <p className="text-lg leading-relaxed">{c.text}</p>
            {c.verse && (
              <blockquote className="border-l-4 border-blue-400 pl-3 italic text-gray-600 text-base">
                <p>{c.verse.text}</p>
                <cite className="not-italic text-sm text-blue-500">
                  {c.verse.reference} ({c.verse.translation})
                </cite>
              </blockquote>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {!connected && !ended && (
        <p className="text-center text-sm text-gray-400 mt-4">Connecting…</p>
      )}
    </main>
  );
}
