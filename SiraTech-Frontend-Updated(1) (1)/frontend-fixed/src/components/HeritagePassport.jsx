import React, { useEffect, useState } from "react";
import { Award, Compass, Headphones, History, Lock, MapPin, Trophy, X } from "lucide-react";
import { getGamificationProfile } from "../services/api";

const ICONS = {
  heritage_explorer: Compass,
  hidden_gem_hunter: MapPin,
  time_traveler: History,
  story_listener: Headphones,
  saudi_heritage_explorer: Award
};

export default function HeritagePassport({ userId = "current-user" }) {
  const [open, setOpen] = useState(false);
  const [profile, setProfile] = useState(null);
  const [error, setError] = useState("");

  const refresh = () => {
    setError("");
    getGamificationProfile(userId).then(setProfile).catch((err) => setError(err.message));
  };

  useEffect(refresh, [userId]);

  const xp = profile?.total_xp ?? 0;
  const level = Math.floor(xp / 500) + 1;
  const progress = ((xp % 500) / 500) * 100;
  const badgeCatalog = [
    ["heritage_explorer", "Heritage Explorer", `Discovered ${profile?.discovered_landmarks?.count ?? 0} landmarks.`],
    ["hidden_gem_hunter", "Hidden Gem Hunter", `Identified ${profile?.hidden_gems?.count ?? 0} hidden gems.`],
    ["time_traveler", "Time Traveler", `Viewed ${profile?.historical_images_viewed?.count ?? 0} historical images.`],
    ["story_listener", "Story Listener", `Listened to ${profile?.stories_listened?.count ?? 0} narrated stories.`],
    ["saudi_heritage_explorer", "Saudi Heritage Explorer", `Explored ${profile?.distinct_locations_explored?.length ?? 0} locations.`]
  ];
  const unlocked = new Set((profile?.badges || []).map((b) => b.code));

  return <>
    <button className="passport-trigger" onClick={() => { setOpen(true); refresh(); }}><Trophy size={14} /> Level {level} · {xp} XP</button>
    {open && <div className="modal" onClick={() => setOpen(false)}>
      <div className="passport" onClick={(e) => e.stopPropagation()}>
        <header><strong><Trophy size={18} /> Heritage Passport</strong><button onClick={() => setOpen(false)}><X size={17} /></button></header>
        <div className="passport-body">
          {error && <div className="error">{error}</div>}
          <div className="level-card"><span>Level {level} Explorer</span><h2>{xp} XP</h2><div className="progress"><i style={{ width: `${progress}%` }} /></div><small>{xp % 500} / 500 XP to Level {level + 1}</small></div>
          <div className="stats">
            <div><Compass size={15}/><b>{profile?.discovered_landmarks?.count ?? 0}</b><small>Landmarks</small></div>
            <div><MapPin size={15}/><b>{profile?.hidden_gems?.count ?? 0}</b><small>Hidden Gems</small></div>
            <div><Headphones size={15}/><b>{profile?.stories_listened?.count ?? 0}</b><small>Stories</small></div>
          </div>
          <h3>Badges</h3>
          <div className="badges">{badgeCatalog.map(([code, title, description]) => {
            const Icon = ICONS[code] || Award;
            const isUnlocked = unlocked.has(code);
            return <div key={code} className={`badge ${isUnlocked ? "unlocked" : "locked"}`}>
              <div className="badge-icon"><Icon size={18}/>{!isUnlocked && <Lock size={11}/>}</div>
              <div><strong>{title}</strong><span className="badge-state">{isUnlocked ? "Unlocked" : "Locked"}</span><p>{description}</p></div>
            </div>;
          })}</div>
        </div>
      </div>
    </div>}
  </>;
}
