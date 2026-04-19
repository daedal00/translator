const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function startAudioStream(sessionCode: string, token: string): Promise<() => void> {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

  const pc = new RTCPeerConnection({
    iceServers: [{ urls: "stun:stun.l.google.com:19302" }],
  });

  stream.getAudioTracks().forEach((track) => pc.addTrack(track, stream));

  const offer = await pc.createOffer();
  await pc.setLocalDescription(offer);

  await new Promise<void>((resolve) => {
    if (pc.iceGatheringState === "complete") return resolve();
    pc.addEventListener("icegatheringstatechange", () => {
      if (pc.iceGatheringState === "complete") resolve();
    });
  });

  const res = await fetch(`${API_URL}/ingest/offer`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({
      sdp: pc.localDescription!.sdp,
      type: pc.localDescription!.type,
      session_code: sessionCode,
    }),
  });

  if (!res.ok) throw new Error("Failed to start audio stream");

  const answer = await res.json();
  await pc.setRemoteDescription(answer as RTCSessionDescriptionInit);

  return () => {
    stream.getTracks().forEach((t) => t.stop());
    pc.close();
  };
}
