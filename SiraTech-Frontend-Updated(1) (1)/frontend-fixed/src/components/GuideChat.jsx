import React, { useState } from "react";
import { MessageCircle, Send, Sparkles } from "lucide-react";
import { askGuide } from "../services/api";

export default function GuideChat({ landmarkId, language = "EN" }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e) {
    e.preventDefault();
    const prompt = input.trim();
    if (!prompt || loading) return;
    const next = [...messages, { role: "user", text: prompt }];
    setMessages(next);
    setInput("");
    setLoading(true);
    try {
      const result = await askGuide({
        prompt,
        language,
        landmarkId,
        context: next.slice(-8).map((m) => ({ role: m.role, content: m.text }))
      });
      setMessages((prev) => [...prev, { role: "assistant", text: result.answer || result.message || "No answer returned." }]);
    } catch (err) {
      setMessages((prev) => [...prev, { role: "error", text: err.message }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="panel chat-panel">
      <div className="panel-title"><MessageCircle size={17} /> Ask the AI Guide <Sparkles size={14} /></div>
      <div className="messages">
        {messages.length === 0 && <div className="empty">Ask about the history, architecture, or culture of this landmark.</div>}
        {messages.map((message, index) => <div key={index} className={`message ${message.role}`}><span>{message.text}</span></div>)}
        {loading && <div className="message assistant"><span>Thinking…</span></div>}
      </div>
      <form onSubmit={submit} className="chat-form">
        <input value={input} onChange={(e) => setInput(e.target.value)} placeholder={language === "AR" ? "اسأل المرشد..." : "Ask the guide..."} />
        <button disabled={loading || !input.trim()}><Send size={15} /></button>
      </form>
    </section>
  );
}
