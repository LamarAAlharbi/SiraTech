import React, { useEffect, useState } from "react";
import { History, Loader2 } from "lucide-react";
import { getHistoricalImages, recordDiscovery } from "../services/api";

export default function SeeThePast({ landmarkId, userId = "current-user" }) {
  const [data, setData] = useState(null);
  const [index, setIndex] = useState(0);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!landmarkId) return;
    setError(""); setData(null); setIndex(0);
    getHistoricalImages(landmarkId).then(setData).catch((err) => setError(err.message));
  }, [landmarkId]);

  const record = data?.results?.[index];
  useEffect(() => {
    if (!record?.id) return;
    recordDiscovery({ userId, type: "historical_image", itemId: record.id }).catch(() => {});
  }, [record?.id, userId]);

  const imageSrc = record?.image_url || (record?.image_path ? `/${record.image_path}` : null);
  return <section className="panel history-panel">
    <div className="panel-title"><History size={17}/> See the Past</div>
    {error && <div className="error">{error}</div>}
    {!data && !error && <Loader2 className="spin"/>}
    {record && <>
      {imageSrc ? <div className="past-image"><img src={imageSrc} alt={record.title || "Historical view"}/></div> : <div className="past-image no-image">Sample historical image unavailable</div>}
      <div className="history-meta"><strong>{record.title}</strong><span>{record.year_or_period || "Historical"}</span></div>
      <p>{record.description || ""}</p>
      {data.results.length > 1 && <input type="range" min="0" max={data.results.length - 1} value={index} onChange={(e) => setIndex(Number(e.target.value))}/>}
      {data.sample_data !== "none" && <small className="sample-note">{data.sample_data_notice}</small>}
    </>}
  </section>;
}
