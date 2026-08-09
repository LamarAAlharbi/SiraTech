import React, { useCallback, useEffect, useRef, useState } from "react";
import { AlertCircle, Languages, Pause, Play, RefreshCw, Sparkles, Square, Volume2 } from "lucide-react";
import { recordDiscovery, textToSpeech } from "../services/api";

export default function AvatarVoiceGuide({ guideTextEN, guideTextAR, landmarkId = "lm-albalad", userId = "current-user" }) {
  const [language, setLanguage] = useState("EN");
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState("");
  const [provider, setProvider] = useState("");
  const audioRef = useRef(null);
  const urlRef = useRef(null);
  const requestIdRef = useRef(0);

  const textEN = guideTextEN || "This view shows the traditional coral-stone architecture and wood-carved Roshan balconies characteristic of Historic Jeddah.";
  const textAR = guideTextAR || "يُظهر هذا المشهد الهندسة المعمارية التقليدية المبنية من الأحجار المرجانية والرواشين الخشبية المزخرفة التي تميز جدة التاريخية.";
  const activeText = language === "AR" ? textAR : textEN;

  const cleanup = useCallback(() => {
    requestIdRef.current += 1;
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.src = "";
      audioRef.current = null;
    }
    if (urlRef.current) {
      URL.revokeObjectURL(urlRef.current);
      urlRef.current = null;
    }
  }, []);

  useEffect(() => () => cleanup(), [cleanup]);

  const stop = () => {
    cleanup();
    setStatus("idle");
    setProvider("");
    setError("");
  };

  const play = async () => {
    if (status === "paused" && audioRef.current) {
      try {
        await audioRef.current.play();
        return;
      } catch {
        stop();
      }
    }

    const requestId = ++requestIdRef.current;
    cleanup();
    const currentRequest = ++requestIdRef.current;
    setStatus("loading");
    setError("");

    try {
      const blob = await textToSpeech({ text: activeText, language });
      if (currentRequest !== requestIdRef.current) return;
      if (!(blob instanceof Blob) || blob.size === 0) throw new Error("The TTS server returned empty audio.");

      const url = URL.createObjectURL(blob);
      urlRef.current = url;
      const audio = new Audio(url);
      audioRef.current = audio;

      audio.onplay = () => setStatus("playing");
      audio.onpause = () => {
        if (!audio.ended) setStatus("paused");
      };
      audio.onended = async () => {
        try { await recordDiscovery({ userId, type: "story", itemId: `${landmarkId}:${language}:${activeText.slice(0, 40)}` }); } catch {}
        if (urlRef.current === url) {
          URL.revokeObjectURL(url);
          urlRef.current = null;
        }
        audioRef.current = null;
        setStatus("idle");
      };
      audio.onerror = () => setError("The generated audio could not be played.");

      await audio.play();
      setProvider("Backend TTS");
    } catch (err) {
      if (currentRequest !== requestIdRef.current) return;
      cleanup();
      setStatus("error");
      setError(err.message || "Real voice generation failed. Check the backend and Gemini API configuration.");
    }
  };

  const pause = () => {
    if (audioRef.current) audioRef.current.pause();
  };

  const switchLanguage = () => {
    stop();
    setLanguage((value) => (value === "EN" ? "AR" : "EN"));
  };

  return (
    <section className="voice-card">
      <div className="voice-head">
        <div className={`avatar ${status === "playing" ? "speaking" : ""}`}>
          <div className="avatar-face">S</div>
          {status === "playing" && <div className="equalizer"><i /><i /><i /></div>}
        </div>
        <div className="voice-title">
          <strong><Sparkles size={14} /> SiraTech Heritage Guide</strong>
          <span className={`status ${status}`}>{status === "loading" ? "Generating real voice…" : status === "playing" ? `Speaking · ${language}` : status === "paused" ? "Paused" : status === "error" ? "Voice unavailable" : "Ready"}</span>
        </div>
        <button className="lang-button" onClick={switchLanguage} disabled={status === "loading"}>
          <Languages size={14} /> {language}
        </button>
      </div>

      <p className={language === "AR" ? "arabic" : ""}>{activeText}</p>

      {error && <div className="error"><AlertCircle size={15} /><span>{error}</span><button onClick={play}>Retry</button></div>}
      {provider && !error && <div className="provider-pill"><Volume2 size={13} /> {provider}</div>}

      <div className="voice-controls">
        {status === "playing" ? (
          <button onClick={pause}><Pause size={15} /> Pause</button>
        ) : (
          <button className="primary" onClick={play} disabled={status === "loading"}>
            {status === "loading" ? <RefreshCw size={15} className="spin" /> : <Play size={15} />}
            {status === "paused" ? "Resume" : "Play Voice"}
          </button>
        )}
        {(status === "playing" || status === "paused") && <button className="danger" onClick={stop}><Square size={15} /> Stop</button>}
      </div>
    </section>
  );
}
