import React, { useState } from "react";
import { Camera, CheckCircle2, Image as ImageIcon, Loader2, MapPin } from "lucide-react";
import { analyzeImage, getLandmark, recordDiscovery } from "../services/api";

export default function HiddenGemScanner({ landmarkId, language = "EN" }) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  async function scan(file) {
    if (!file) return;
    setLoading(true); setError(""); setResult(null);
    try {
      const response = await analyzeImage({ imageBlob: file, landmarkId, language });
      let verifiedLandmark = null;
      if (response.possible_landmark_id) verifiedLandmark = await getLandmark(response.possible_landmark_id);
      if (response.possible_landmark_id) {
        await recordDiscovery({ userId: "current-user", type: "hidden_gem", itemId: response.possible_landmark_id, locationId: verifiedLandmark?.location_id });
      }
      setResult({ ...response, verifiedLandmark });
    } catch (err) { setError(err.message); }
    finally { setLoading(false); }
  }

  return <section className="panel scanner">
    <div className="panel-title"><Camera size={17}/> Hidden Gem Scanner</div>
    <label className="upload"><ImageIcon size={24}/><span>{loading ? "Analyzing image…" : "Choose a landmark photo"}</span><input type="file" accept="image/jpeg,image/png,image/webp" disabled={loading} onChange={(e) => scan(e.target.files?.[0])}/></label>
    {loading && <Loader2 className="spin"/>}
    {error && <div className="error">{error}</div>}
    {result && <div className="scan-result"><CheckCircle2 size={18}/><div><strong>{result.possible_landmark_name || result.landmark_name || "Possible match found"}</strong><p>{result.description || result.message || "The image was analyzed successfully."}</p>{result.verifiedLandmark?.name && <small><MapPin size={12}/> Verified record loaded</small>}</div></div>}
  </section>;
}
