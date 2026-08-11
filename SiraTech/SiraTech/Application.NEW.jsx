import React, { useEffect, useState } from "react";
import { Landmark, RefreshCw, Sparkles, MapPin, Mic, Volume2 } from "lucide-react";
import { getLandmark, recordDiscovery } from "./services/api";
import AvatarVoiceGuide from "./components/AvatarVoiceGuide";
import GuideChat from "./components/GuideChat";
import HiddenGemScanner from "./components/HiddenGemScanner";
import SeeThePast from "./components/SeeThePast";
import HeritagePassport from "./components/HeritagePassport";

const HERITAGE_SITES = [
  { id: "lm-alula", name: { EN: "AlUla", AR: "العلا" }, unesco: true },
  { id: "lm-diriyah", name: { EN: "Diriyah", AR: "الدرعية" }, unesco: true },
  { id: "lm-albalad", name: { EN: "Historic Jeddah (Al-Balad)", AR: "جدة التاريخية" }, unesco: true },
];

export default function App() {
  const [language, setLanguage] = useState("EN");
  const [selectedSiteId, setSelectedSiteId] = useState("lm-alula");
  const [landmark, setLandmark] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const loadLandmarkData = (siteId) => {
    setLoading(true);
    setError("");
    getLandmark(siteId)
      .then(async (data) => {
        setLandmark(data);
        try {
          await recordDiscovery({ type: "landmark", itemId: siteId });
        } catch (e) {
          // Silently handle non-critical discovery record errors
        }
      })
      .catch((err) => setError(err.message || "Failed to load heritage data"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadLandmarkData(selectedSiteId);
  }, [selectedSiteId]);

  const toggleLanguage = () => {
    setLanguage((prev) => (prev === "EN" ? "AR" : "EN"));
  };

  return (
    <div className={`app-container ${language === "AR" ? "rtl" : "ltr"}`} dir={language === "AR" ? "rtl" : "ltr"}>
      {/* Global Top App Bar */}
      <header className="topbar">
        <div className="brand-group">
          <div className="brand">
            <Sparkles size={18} className="brand-icon" /> SiraTech
          </div>
          <span className="brand-subtitle">AI Heritage Guide</span>
        </div>
        <div className="top-actions">
          <button className="btn-lang-toggle" onClick={toggleLanguage}>
            {language === "EN" ? "العربية" : "English"}
          </button>
          <HeritagePassport />
        </div>
      </header>

      {/* Hero Banner Header */}
      <section className="hero-banner">
        <div className="hero-content">
          <span className="eyebrow">SAUDI HERITAGE · REIMAGINED BY AI</span>
          <h1>Walk through 1,300 years of Saudi heritage.</h1>
          <p>
            Explore AlUla, Diriyah, and Historic Jeddah with Noura — your AI guide who speaks, listens, and reads stories aloud.
          </p>
        </div>
      </section>

      {error && <div className="error-banner">{error}</div>}

      {/* Main 3-Column Dashboard Grid matching Reference Layout */}
      <div className="dashboard-grid">
        
        {/* COLUMN 1: Map Explorer & Site Selector */}
        <div className="grid-column col-map">
          <div className="section-header">
            <h2>Explore</h2>
            <span className="site-count">3 heritage sites</span>
          </div>

          {/* SVG Saudi Map Card */}
          <div className="map-card">
            <div className="map-viewport">
              <svg viewBox="0 0 800 600" className="saudi-map-svg">
                <path
                  className="land-mass"
                  d="M150,120 L350,80 L550,150 L700,250 L650,450 L450,550 L250,500 L100,350 Z"
                />
                {/* Map Pins */}
                <g className={`map-pin ${selectedSiteId === "lm-alula" ? "active" : ""}`} onClick={() => setSelectedSiteId("lm-alula")}>
                  <circle cx="230" cy="180" r="10" className="pin-dot" />
                  <text x="210" y="165" className="pin-label">AlUla</text>
                </g>
                <g className={`map-pin ${selectedSiteId === "lm-diriyah" ? "active" : ""}`} onClick={() => setSelectedSiteId("lm-diriyah")}>
                  <circle cx="420" cy="270" r="10" className="pin-dot" />
                  <text x="400" y="255" className="pin-label">Diriyah</text>
                </g>
                <g className={`map-pin ${selectedSiteId === "lm-albalad" ? "active" : ""}`} onClick={() => setSelectedSiteId("lm-albalad")}>
                  <circle cx="210" cy="360" r="10" className="pin-dot" />
                  <text x="130" y="380" className="pin-label">Historic Jeddah (Al-Balad)</text>
                </g>
              </svg>
            </div>

            {/* Quick Site Switcher Pills */}
            <div className="site-pills">
              {HERITAGE_SITES.map((site) => (
                <button
                  key={site.id}
                  className={`pill-btn ${selectedSiteId === site.id ? "active" : ""}`}
                  onClick={() => setSelectedSiteId(site.id)}
                >
                  {site.name[language]}
                </button>
              ))}
            </div>
          </div>

          {/* Active Site Preview Metadata */}
          <div className="active-site-card">
            <div className="site-card-header">
              <h3>{landmark?.name?.[language] || HERITAGE_SITES.find((s) => s.id === selectedSiteId)?.name[language]}</h3>
              <span className="badge-unesco">UNESCO</span>
            </div>
            <p className="site-desc">
              {landmark?.description?.[language] || "Explore ancient Nabataean rock-cut tombs and timeless trade roads."}
            </p>
          </div>
        </div>

        {/* COLUMN 2: Voice Avatar & Live AI Chat */}
        <div className="grid-column col-guide">
          <AvatarVoiceGuide
            landmarkId={selectedSiteId}
            guideTextEN={landmark?.description?.EN}
            guideTextAR={landmark?.description?.AR}
            language={language}
          />
          <GuideChat landmarkId={selectedSiteId} language={language} />
        </div>

        {/* COLUMN 3: Visual Time Travel, Camera Scanner & Gamification */}
        <div className="grid-column col-interactive">
          <SeeThePast landmarkId={selectedSiteId} />
          <HiddenGemScanner landmarkId={selectedSiteId} language={language} />
        </div>

      </div>
    </div>
  );
}