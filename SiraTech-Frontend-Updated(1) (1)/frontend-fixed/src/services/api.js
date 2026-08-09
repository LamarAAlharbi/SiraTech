const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/$/, "");

async function request(path, options = {}) {
  const isFormData = options.body instanceof FormData;
  const headers = {
    ...(isFormData ? {} : { "Content-Type": "application/json" }),
    ...(options.headers || {})
  };

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers
  });

  if (!response.ok) {
    const data = await response.json().catch(() => null);
    const message = data?.error?.message || data?.message || `API error ${response.status}`;
    throw new Error(message);
  }

  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("audio/")) return response.blob();
  return response.json();
}

export const getHealth = () => request("/../health");

export async function getLandmarks({ locationId, category, unesco } = {}) {
  const params = new URLSearchParams();
  if (locationId) params.set("location_id", locationId);
  if (category) params.set("category", category);
  if (unesco) params.set("unesco", "true");
  const query = params.toString();
  return request(`/v1/landmarks${query ? `?${query}` : ""}`);
}

export function getLandmark(landmarkId = "lm-albalad") {
  return request(`/v1/landmarks/${encodeURIComponent(landmarkId)}`);
}

export function getLocations(region) {
  return request(`/v1/locations${region ? `?region=${encodeURIComponent(region)}` : ""}`);
}

export function askGuide({ prompt, language = "EN", landmarkId, context = [] }) {
  return request("/guide/chat", {
    method: "POST",
    body: JSON.stringify({
      user_message: prompt,
      language: language.toLowerCase(),
      landmark_id: landmarkId,
      context
    })
  });
}

export function analyzeImage({ imageBlob, landmarkId, language = "EN", latitude, longitude }) {
  const formData = new FormData();
  formData.append("image", imageBlob);
  formData.append("language", language.toLowerCase());
  if (landmarkId) formData.append("landmark_id", landmarkId);
  if (latitude != null && longitude != null) {
    formData.append("latitude", String(latitude));
    formData.append("longitude", String(longitude));
  }
  return request("/vision/analyze", { method: "POST", body: formData });
}

export function getHistoricalImages(landmarkId, tag) {
  return request(`/history/landmarks/${encodeURIComponent(landmarkId)}${tag ? `?tag=${encodeURIComponent(tag)}` : ""}`);
}

export function getHistoricalImage(imageId) {
  return request(`/history/images/${encodeURIComponent(imageId)}`);
}

export function textToSpeech({ text, language = "EN", voice }) {
  return request("/tts", {
    method: "POST",
    body: JSON.stringify({
      text,
      language: language.toLowerCase(),
      ...(voice ? { voice } : {})
    })
  });
}

export function getGamificationProfile(userId = "current-user") {
  return request(`/gamification/profile/${encodeURIComponent(userId)}`);
}

export function recordDiscovery({ userId = "current-user", type, itemId, locationId }) {
  return request("/gamification/discover", {
    method: "POST",
    body: JSON.stringify({
      user_id: userId,
      type,
      item_id: itemId,
      ...(locationId ? { location_id: locationId } : {})
    })
  });
}

export function getImage(imageId) {
  return request(`/v1/images/${encodeURIComponent(imageId)}`);
}
