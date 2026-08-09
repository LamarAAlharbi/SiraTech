import React, { useEffect, useState } from "react";
import { Landmark, RefreshCw, Sparkles } from "lucide-react";
import { getLandmark, recordDiscovery } from "./services/api";
import AvatarVoiceGuide from "./components/AvatarVoiceGuide";
import GuideChat from "./components/GuideChat";
import HiddenGemScanner from "./components/HiddenGemScanner";
import SeeThePast from "./components/SeeThePast";
import HeritagePassport from "./components/HeritagePassport";

export default function App() {
  const [language, setLanguage] = useState("EN");
  const [landmark, setLandmark] = useState(null);
  const [error, setError] = useState("");

  const load = () => {
    setError("");
    getLandmark("lm-albalad").then(async (data) => { setLandmark(data); try { await recordDiscovery({ type: "landmark", itemId: "lm-albalad" }); } catch {} }).catch((err) => setError(err.message));
  };
  useEffect(load, []);

  return <main className="app">
    <header className="topbar"><div><div className="brand"><Sparkles size={18}/> SiraTech</div><span>AI Heritage Guide</span></div><div className="top-actions"><button onClick={() => setLanguage((v) => v === "EN" ? "AR" : "EN")}>{language}</button><HeritagePassport/></div></header>
    <section className="hero"><div><span className="eyebrow"><Landmark size={14}/> Historic Jeddah</span><h1>{landmark?.name?.[language] || "Historic Jeddah (Al-Balad)"}</h1><p>{landmark?.description?.[language] || "Explore Saudi heritage with an AI-powered cultural guide."}</p></div><button onClick={load} className="refresh"><RefreshCw size={15}/> Refresh</button></section>
    {error && <div className="error page-error">{error}</div>}
    <div className="grid">
      <div className="main-column">
        <AvatarVoiceGuide landmarkId="lm-albalad" guideTextEN={landmark?.description?.EN} guideTextAR={landmark?.description?.AR}/>
        <GuideChat landmarkId="lm-albalad" language={language}/>
      </div>
      <aside className="side-column">
        <SeeThePast landmarkId="lm-albalad"/>
        <HiddenGemScanner landmarkId="lm-albalad" language={language}/>
      </aside>
    </div>
  </main>;
}
