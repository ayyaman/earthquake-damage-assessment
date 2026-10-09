const API_BASE_URL = "http://127.0.0.1:8000";

export async function getAfadEarthquakesLast24Hours() {
  const response = await fetch(`${API_BASE_URL}/earthquakes/last-24-hours?t=${Date.now()}`, {
    cache: "no-store"
  });
  if (!response.ok) {
    throw new Error("AFAD son 24 saat verisi alınamadı.");
  }
  const data = await response.json();
  if (!data.earthquakes?.length) {
    throw new Error("AFAD son 24 saat verisi boş döndü.");
  }
  return data;
}

export async function getAfadEarthquakesToday() {
  const response = await fetch(`${API_BASE_URL}/earthquakes/today`);
  if (!response.ok) {
    throw new Error("AFAD bugünkü deprem verisi alınamadı.");
  }
  const data = await response.json();
  if (!data.earthquakes?.length) {
    throw new Error("AFAD bugünkü deprem verisi boş döndü.");
  }
  return data;
}

export async function getLatestAfadEarthquakes() {
  const response = await fetch(`${API_BASE_URL}/earthquakes/latest`);
  if (!response.ok) {
    throw new Error("AFAD son depremler verisi alınamadı.");
  }
  return response.json();
}

export async function getSampleEarthquakes() {
  const response = await fetch("/data/sample_earthquakes.json");
  if (!response.ok) {
    throw new Error("Deprem verisi yüklenemedi.");
  }
  const data = await response.json();
  return {
    earthquakes: data.map(normalizeSampleEvent),
    source: "AFAD Verileri",
    recordCount: data.length,
    lastUpdated: new Date().toLocaleString("tr-TR"),
    error: ""
  };
}

export async function getEarthquakes() {
  return getAfadEarthquakesLast24Hours();
}

export async function fetchFaultLines() {
  const response = await fetch("/data/fault_lines.geojson");
  if (!response.ok) {
    throw new Error("Fay hattı GeoJSON verisi yüklenemedi.");
  }
  return response.json();
}

function normalizeSampleEvent(event) {
  return {
    id: String(event.id || event.earthquake_id || `${event.date}-${event.latitude}-${event.longitude}`),
    date: event.date || "",
    latitude: Number(event.latitude || 0),
    longitude: Number(event.longitude || 0),
    depth: Number(event.depth || 0),
    magnitude: Number(event.magnitude || 0),
    location: event.location || "Konum bilgisi yok",
    source: "AFAD Verileri"
  };
}

export function getMagnitudeColor(magnitude) {
  if (magnitude >= 5) return "#dc2626";
  if (magnitude >= 4) return "#f97316";
  if (magnitude >= 3) return "#facc15";
  return "#22c55e";
}

export function calculateEarthquakeStats(earthquakes) {
  if (!earthquakes.length) {
    return {
      total: 0,
      maxMagnitude: "Yok",
      averageMagnitude: "Yok",
      magnitudeFourPlus: 0,
      latestTime: "Yok"
    };
  }

  const magnitudes = earthquakes.map((item) => Number(item.magnitude || 0));
  const maxMagnitude = Math.max(...magnitudes);
  const averageMagnitude = magnitudes.reduce((sum, value) => sum + value, 0) / magnitudes.length;
  const latest = [...earthquakes].sort((a, b) => new Date(b.date) - new Date(a.date))[0];

  return {
    total: earthquakes.length,
    maxMagnitude: maxMagnitude.toFixed(1),
    averageMagnitude: averageMagnitude.toFixed(2),
    magnitudeFourPlus: earthquakes.filter((item) => Number(item.magnitude) >= 4).length,
    latestTime: latest?.date ? new Date(latest.date).toLocaleString("tr-TR") : "Yok"
  };
}
