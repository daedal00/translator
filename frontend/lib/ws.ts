const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const WS_URL = API_URL.replace(/^http/, "ws");

export type CaptionMsg = {
  type: "caption";
  translations: Record<string, string>;
  source_lang: string;
  verse: { reference: string; text: string; translation: string } | null;
};

export type SystemMsg = { type: "joined"; code: string; lang: string } | { type: "session_ended" };

export type Msg = CaptionMsg | SystemMsg;

export class SessionSocket {
  private ws: WebSocket | null = null;
  private lang: string;
  private code: string;
  private closed = false;
  onMessage: (msg: Msg) => void = () => {};
  onDisconnect: () => void = () => {};

  constructor(code: string, lang: string) {
    this.code = code;
    this.lang = lang;
  }

  connect() {
    if (this.closed) return;
    this.ws = new WebSocket(`${WS_URL}/ws/${this.code}?lang=${this.lang}`);

    this.ws.onmessage = (e) => {
      try {
        this.onMessage(JSON.parse(e.data) as Msg);
      } catch (err) {
        console.error("WS parse error", err);
      }
    };

    this.ws.onclose = () => {
      this.onDisconnect();
      if (!this.closed) setTimeout(() => this.connect(), 3000);
    };
  }

  setLang(lang: string) {
    this.lang = lang;
    this.ws?.send(JSON.stringify({ type: "set_lang", lang }));
  }

  close() {
    this.closed = true;
    this.ws?.close();
    this.ws = null;
  }
}
