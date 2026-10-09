"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export function useSpeechToText(value: string, onChange: (v: string) => void) {
  const recRef = useRef<any>(null);
  const wantRef = useRef(false);
  const baseRef = useRef("");
  const finalRef = useRef("");
  const valueRef = useRef(value);
  const onChangeRef = useRef(onChange);
  const [listening, setListening] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [supported, setSupported] = useState(true);

  valueRef.current = value;
  onChangeRef.current = onChange;

  const getSR = () =>
    typeof window === "undefined"
      ? null
      : (window as any).SpeechRecognition ||
        (window as any).webkitSpeechRecognition ||
        null;

  useEffect(() => {
    setSupported(!!getSR());
    return () => {
      wantRef.current = false;
      try {
        recRef.current?.abort();
      } catch {}
    };
  }, []);

  const push = (text: string) => {
    valueRef.current = text;
    onChangeRef.current(text);
  };

  const begin = () => {
    baseRef.current = valueRef.current;
    finalRef.current = "";
  };

  const start = useCallback(async () => {
    const SR = getSR();
    if (!SR) {
      setError("Voice input works in Chrome and Edge.");
      return;
    }
    setError(null);
    try {
      const s = await navigator.mediaDevices.getUserMedia({ audio: true });
      s.getTracks().forEach((t) => t.stop());
    } catch {
      setError("Microphone access is blocked. Allow it in your browser settings.");
      return;
    }
    const rec = new SR();
    rec.continuous = true;
    rec.interimResults = true;
    rec.maxAlternatives = 1;
    rec.lang = navigator.language || "en-US";
    rec.onstart = () => setListening(true);
    rec.onresult = (e: any) => {
      let interim = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const r = e.results[i];
        const t = r[0]?.transcript ?? "";
        if (r.isFinal) finalRef.current += t + " ";
        else interim += t;
      }
      const base = baseRef.current;
      const sep = base && !/\s$/.test(base) ? " " : "";
      push((base + sep + finalRef.current + interim).replace(/^\s+/, ""));
    };
    rec.onerror = (e: any) => {
      console.error("speech error", e.error, e.message);
      if (e.error === "no-speech" || e.error === "aborted") return;
      wantRef.current = false;
      setError(
        e.error === "not-allowed" || e.error === "service-not-allowed"
          ? "Microphone access is blocked. Allow it in your browser settings."
          : e.error === "audio-capture"
          ? "No microphone found."
          : e.error === "network"
          ? "Voice input needs an internet connection. Try Chrome."
          : "Voice input stopped (" + e.error + ").",
      );
    };
    rec.onend = () => {
      if (wantRef.current) {
        begin();
        try {
          rec.start();
        } catch {
          wantRef.current = false;
          setListening(false);
        }
      } else {
        setListening(false);
      }
    };
    recRef.current = rec;
    wantRef.current = true;
    begin();
    try {
      rec.start();
    } catch (err) {
      console.error(err);
      setError("Could not start voice input.");
    }
  }, []);

  const stop = useCallback(() => {
    wantRef.current = false;
    try {
      recRef.current?.stop();
    } catch {}
    setListening(false);
  }, []);

  return {
    listening,
    supported,
    error,
    start,
    stop,
    toggle: () => (listening ? stop() : start()),
  };
}
