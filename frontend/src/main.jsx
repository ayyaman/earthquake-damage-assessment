import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { CircleMarker, GeoJSON, MapContainer, Popup, TileLayer } from "react-leaflet";
import {
  Activity,
  BarChart3,
  Building2,
  Flame,
  Home,
  Info,
  Layers,
  Moon,
  ShieldAlert
} from "lucide-react";
import "leaflet/dist/leaflet.css";
import "./styles.css";
import {
  calculateEarthquakeStats,
  fetchFaultLines,
  getEarthquakes,
  getMagnitudeColor
} from "./services/earthquakeService";

const API_BASE_URL = "http://127.0.0.1:8000";

function Shell({ activePage, setActivePage, children }) {
  const navItems = [
    ["home", "Ana Sayfa", Home],
    ["building", "Bina Hasar Analizi", Building2],
    ["risk", "Risk Analizi", ShieldAlert],
    ["regional", "Bölgesel Analiz", Layers],
    ["about", "Hakkında", Info]
  ];

  return (
    <main className="min-h-screen bg-[#07111f] text-slate-100">
      <div className="fixed inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(249,115,22,0.18),_transparent_28%),radial-gradient(circle_at_75%_10%,_rgba(14,165,233,0.12),_transparent_30%)]" />
      <div className="relative grid min-h-screen lg:grid-cols-[280px_1fr]">
        <aside className="border-b border-white/10 bg-slate-950/80 px-5 py-5 backdrop-blur lg:border-b-0 lg:border-r">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-orange-600">
              <Activity className="h-6 w-6" />
            </div>
            <div>
              <p className="text-sm font-semibold text-orange-300">DEPREM</p>
              <h1 className="text-lg font-bold leading-tight">Karar Destek Sistemi</h1>
            </div>
          </div>

          <nav className="mt-8 grid gap-2">
            {navItems.map(([id, label, Icon]) => (
              <button
                key={id}
                onClick={() => setActivePage(id)}
                className={`flex items-center gap-3 rounded-lg px-4 py-3 text-left text-sm font-semibold transition ${
                  activePage === id
                    ? "bg-orange-600 text-white"
                    : "text-slate-300 hover:bg-white/10 hover:text-white"
                }`}
              >
                <Icon className="h-5 w-5" />
                {label}
              </button>
            ))}
          </nav>

          <div className="mt-8 rounded-lg border border-white/10 bg-white/5 p-4 text-xs leading-5 text-slate-300">
            Bu sistem karar destek amaçlıdır. Harita katmanı ve yapay zekâ analizleri bağımsız çalışır.
          </div>
        </aside>

        <section className="px-5 py-6 lg:px-8">
          <header className="mb-6 rounded-xl border border-white/10 bg-white/5 p-5 shadow-2xl backdrop-blur">
            <p className="text-sm font-semibold uppercase tracking-[0.24em] text-orange-300">
              DEPREM KARAR DESTEK SİSTEMİ
            </p>
            <h2 className="mt-2 text-3xl font-bold md:text-4xl">
              Yapay zekâ destekli hasar analizi ve bölgesel önceliklendirme platformu
            </h2>
          </header>
          {children}
        </section>
      </div>
    </main>
  );
}

function Panel({ children, className = "" }) {
  return (
    <div className={`rounded-xl border border-white/10 bg-white/[0.06] p-5 shadow-xl backdrop-blur ${className}`}>
      {children}
    </div>
  );
}

function StatCard({ label, value, icon: Icon }) {
  return (
    <Panel>
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-400">{label}</p>
          <p className="mt-2 text-2xl font-bold text-white">{value}</p>
        </div>
        <Icon className="h-8 w-8 text-orange-300" />
      </div>
    </Panel>
  );
}

function SituationMap() {
  const [earthquakes, setEarthquakes] = useState([]);
  const [faultLines, setFaultLines] = useState(null);
  const [error, setError] = useState("");
  const [dataSource, setDataSource] = useState("Yükleniyor");
  const [lastUpdated, setLastUpdated] = useState("");

  useEffect(() => {
    async function loadMapData() {
      try {
        const [earthquakeResponse, faultData] = await Promise.all([
          getEarthquakes(),
          fetchFaultLines()
        ]);
        setEarthquakes(earthquakeResponse.earthquakes || []);
        setDataSource("AFAD Verileri");
        setLastUpdated(earthquakeResponse.lastUpdated || new Date().toLocaleString("tr-TR"));
        setError("");
        setFaultLines(faultData);
      } catch (err) {
        setEarthquakes([]);
        setDataSource("AFAD Verileri");
        setLastUpdated(new Date().toLocaleString("tr-TR"));
        setError("Canlı deprem verisi alınamadı. Backend sunucusunun çalıştığından emin olun.");
      }
    }
    loadMapData();
    const refreshTimer = window.setInterval(loadMapData, 60000);
    return () => window.clearInterval(refreshTimer);
  }, []);

  const stats = useMemo(() => calculateEarthquakeStats(earthquakes), [earthquakes]);

  return (
    <section className="space-y-5">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <h3 className="text-2xl font-bold">Durumsal Farkındalık Katmanı</h3>
          <p className="mt-2 text-sm text-slate-300">
            Türkiye genelindeki deprem aktiviteleri harita üzerinde gösterilmektedir.
          </p>
        </div>
        <div className="flex flex-wrap gap-2 text-xs text-slate-300">
          <span className="rounded-full border border-emerald-400/30 bg-emerald-500/10 px-3 py-1 text-emerald-300">
            {dataSource}
          </span>
          <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1">
            Son Güncelleme: {lastUpdated || "Yükleniyor"}
          </span>
        </div>
      </div>
      {error && <p className="text-sm text-red-300">{error}</p>}

      <div className="grid gap-4 md:grid-cols-5">
        <StatCard label="Son 24 saatteki deprem sayısı" value={stats.total} icon={Activity} />
        <StatCard label="En büyük deprem" value={stats.maxMagnitude} icon={Flame} />
        <StatCard label="Ortalama büyüklük" value={stats.averageMagnitude} icon={BarChart3} />
        <StatCard label="4.0+ deprem" value={stats.magnitudeFourPlus} icon={ShieldAlert} />
        <StatCard label="En son deprem" value={stats.latestTime} icon={Moon} />
      </div>

      <Panel className="overflow-hidden p-0">
        <div className="h-[520px]">
          <MapContainer center={[39.0, 35.0]} zoom={6} scrollWheelZoom className="h-full w-full">
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            {faultLines && (
              <GeoJSON
                data={faultLines}
                style={{ color: "#f97316", weight: 3, opacity: 0.62 }}
                onEachFeature={(feature, layer) => {
                  layer.bindTooltip(feature.properties?.name || "Fay hatti");
                }}
              />
            )}
            {earthquakes.map((item) => (
              <CircleMarker
                key={item.id}
                center={[item.latitude, item.longitude]}
                radius={6 + Number(item.magnitude || 0) * 1.8}
                pathOptions={{
                  color: "#0f172a",
                  weight: 1,
                  fillColor: getMagnitudeColor(Number(item.magnitude)),
                  fillOpacity: 0.88
                }}
              >
                <Popup>
                  <strong>{item.location}</strong>
                  <br />
                  Büyüklük: {item.magnitude}
                  <br />
                  Derinlik: {item.depth} km
                  <br />
                  Tarih: {new Date(item.date).toLocaleString("tr-TR")}
                  <br />
                  Kaynak: {item.source || dataSource}
                </Popup>
              </CircleMarker>
            ))}
          </MapContainer>
        </div>
      </Panel>

      <Panel>
        <div className="flex flex-col gap-3 text-sm text-slate-300 md:flex-row md:items-center md:justify-between">
          <p>Deprem büyüklükleri renk aralıklarına göre gösterilmektedir.</p>
          <div className="flex flex-wrap gap-2">
            <Legend color="#22c55e" label="0.0-2.9" />
            <Legend color="#facc15" label="3.0-3.9" />
            <Legend color="#f97316" label="4.0-4.9" />
            <Legend color="#dc2626" label="5.0+" />
          </div>
        </div>
      </Panel>
    </section>
  );
}

function Legend({ color, label }) {
  return (
    <span className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1">
      <span className="h-3 w-3 rounded-full" style={{ backgroundColor: color }} />
      {label}
    </span>
  );
}

function UploadBox({ label, file, setFile }) {
  const [isDragging, setIsDragging] = useState(false);

  function handleDrop(event) {
    event.preventDefault();
    setIsDragging(false);
    const selectedFile = event.dataTransfer.files?.[0];
    if (selectedFile) setFile(selectedFile);
  }

  return (
    <label
      onDragOver={(event) => {
        event.preventDefault();
        setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
      className={`flex min-h-40 cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed px-5 py-8 text-center transition ${
        isDragging ? "border-orange-400 bg-orange-500/10" : "border-white/20 bg-slate-950/50 hover:border-orange-300"
      }`}
    >
      <input type="file" accept="image/*" className="hidden" onChange={(event) => setFile(event.target.files?.[0] || null)} />
      <span className="text-sm font-semibold text-white">{label}</span>
      <span className="mt-2 text-sm text-slate-400">{file ? file.name : "Sürükle bırak veya seç"}</span>
    </label>
  );
}

function ImagePreviewCard({ title, file, imageUrl, alt }) {
  const [previewUrl, setPreviewUrl] = useState("");
  const displayUrl = imageUrl || previewUrl;

  useEffect(() => {
    if (!file || imageUrl) {
      setPreviewUrl("");
      return;
    }

    const objectUrl = URL.createObjectURL(file);
    setPreviewUrl(objectUrl);

    return () => URL.revokeObjectURL(objectUrl);
  }, [file, imageUrl]);

  return (
    <div className="rounded-lg border border-white/10 bg-slate-950/45 p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h4 className="text-sm font-bold text-white">{title}</h4>
      </div>
      <div className="flex aspect-[4/3] items-center justify-center overflow-hidden rounded-lg border border-white/10 bg-slate-900/80">
        {displayUrl ? (
          <img src={displayUrl} alt={alt || title} className="h-full w-full object-contain" />
        ) : (
          <span className="px-4 text-center text-sm text-slate-400">Henüz görsel yüklenmedi.</span>
        )}
      </div>
    </div>
  );
}

function LoadingButton({ loading, children, ...props }) {
  return (
    <button
      {...props}
      disabled={loading || props.disabled}
      className="inline-flex h-11 items-center justify-center rounded-lg bg-orange-600 px-5 text-sm font-semibold text-white transition hover:bg-orange-500 disabled:cursor-not-allowed disabled:opacity-60"
    >
      {loading ? <span className="h-5 w-5 animate-spin rounded-full border-2 border-white/40 border-t-white" /> : children}
    </button>
  );
}

function ModuleCards({ setActivePage }) {
  const modules = [
    {
      id: "building",
      title: "Bina Hasar Analizi",
      description: "Tek bina görüntüsünden hasar seviyesini sınıflandırır.",
      outputs: ["Hasar Yok", "Hasarlı", "Yıkılmış"],
      icon: Building2
    },
    {
      id: "risk",
      title: "Risk Analizi",
      description: "Bina hasar seviyesi, bina tipi ve zaman bilgisine göre kayıp aralıkları üretir.",
      outputs: ["Tahmini nüfus", "Olası can kaybı", "Tahmini ekonomik kayıp", "Risk seviyesi"],
      icon: ShieldAlert
    },
    {
      id: "regional",
      title: "Bölgesel Analiz",
      description: "Afet öncesi ve sonrası uydu görüntülerinden değişim skoru üretir.",
      outputs: ["Bölgesel değişim skoru", "Öncelik seviyesi", "Değişim haritası"],
      icon: Layers
    }
  ];

  return (
    <section className="space-y-5">
      <div>
        <h3 className="text-2xl font-bold">Yapay Zekâ Analiz Katmanı</h3>
        <p className="mt-2 text-sm text-slate-300">
          Bina hasarı, risk durumu ve bölgesel değişim analizleri bu bölümde sunulmaktadır.
        </p>
      </div>
      <div className="grid gap-5 lg:grid-cols-3">
        {modules.map((module) => (
          <Panel key={module.id} className="flex flex-col">
            <module.icon className="h-9 w-9 text-orange-300" />
            <h4 className="mt-4 text-xl font-bold">{module.title}</h4>
            <p className="mt-2 text-sm leading-6 text-slate-300">{module.description}</p>
            <div className="mt-4 flex flex-wrap gap-2">
              {module.outputs.map((output) => (
                <span key={output} className="rounded-full bg-white/10 px-3 py-1 text-xs text-slate-200">
                  {output}
                </span>
              ))}
            </div>
            <button
              onClick={() => setActivePage(module.id)}
              className="mt-6 h-10 rounded-lg bg-white/10 text-sm font-semibold hover:bg-white/15"
            >
              Modülü aç
            </button>
          </Panel>
        ))}
      </div>
    </section>
  );
}

function HomePage({ setActivePage }) {
  return (
    <div className="space-y-8">
      <SituationMap />
      <ModuleCards setActivePage={setActivePage} />
    </div>
  );
}

function BuildingDamageAnalysis({ onDamageResult }) {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submit() {
    if (!file) return;
    setLoading(true);
    setError("");
    setResult(null);

    const formData = new FormData();
    formData.append("image", file);

    try {
      const response = await fetch(`${API_BASE_URL}/predict-building-damage`, { method: "POST", body: formData });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Bina hasar analizi tamamlanamadı.");
      setResult(data);
      onDamageResult?.(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="space-y-5">
      <PageTitle title="Bina Hasar Analizi" />
      <div className="grid gap-5 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
        <Panel className="space-y-4">
          <h3 className="text-lg font-bold text-white">Yüklenen Görsel</h3>
          <UploadBox label="Bina veya enkaz görüntüsü" file={file} setFile={setFile} />
          <ImagePreviewCard title="Görsel Önizleme" file={file} alt="Yüklenen bina görseli" />
          <LoadingButton loading={loading} disabled={!file} onClick={submit}>Analiz Et</LoadingButton>
        </Panel>

        <Panel>
          <h3 className="text-lg font-bold text-white">Analiz Sonuçları</h3>
          {result ? (
            <div className="mt-4 space-y-5">
              <div className="rounded-lg border border-orange-400/20 bg-orange-500/10 p-4">
                <p className="text-sm text-slate-300">Hasar Seviyesi</p>
                <h4 className="mt-1 text-3xl font-bold text-orange-300">{damageLabel(result.predicted_class)}</h4>
              </div>

              <div>
                <div className="flex items-center justify-between gap-4">
                  <p className="text-sm font-semibold text-slate-200">Güven Oranı</p>
                  <span className="text-lg font-bold text-white">%{result.confidence}</span>
                </div>
                <Progress value={result.confidence} />
              </div>

              <div>
                <h4 className="text-sm font-bold text-white">Olasılık Dağılımı</h4>
                <div className="mt-3 grid gap-3 sm:grid-cols-3 lg:grid-cols-1 xl:grid-cols-3">
                  {Object.entries(result.probabilities).map(([name, value]) => (
                    <MetricCard key={name} label={damageLabel(name)} value={`%${value}`} />
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="mt-4 flex min-h-80 items-center justify-center rounded-lg border border-dashed border-white/15 bg-slate-950/45 px-6 text-center text-sm text-slate-400">
              Analiz sonucu burada gösterilecektir.
            </div>
          )}
        </Panel>
      </div>
      {error && <p className="rounded-lg bg-red-950/60 p-3 text-sm text-red-200">Hata: {error}</p>}
    </section>
  );
}

function RiskAnalysis({ buildingDamageResult }) {
  const aiDamageLevel = buildingDamageResult?.damage_level || buildingDamageResult?.predicted_class || "";
  const [form, setForm] = useState({
    damage_level: aiDamageLevel || "damaged",
    time_of_day: "night",
    building_type: "residential",
    occupancy_range: "auto"
  });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!aiDamageLevel) return;
    setForm((current) => ({ ...current, damage_level: aiDamageLevel }));
  }, [aiDamageLevel]);

  function updateField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function submit() {
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const response = await fetch(`${API_BASE_URL}/risk-analysis`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form)
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Risk analizi tamamlanamadı.");
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  const fields = {
    damage_level: ["no_damage", "damaged", "collapsed"],
    time_of_day: ["day", "night"],
    building_type: ["residential", "office", "school", "hospital", "shopping_mall"],
    occupancy_range: ["auto", "low", "medium", "high"]
  };

  const riskColor = {
    very_low: "text-emerald-400",
    low: "text-lime-400",
    medium: "text-yellow-300",
    high: "text-orange-400",
    critical: "text-red-400"
  };

  return (
    <section className="space-y-5">
      <PageTitle title="Risk Analizi" />
      <Panel>
        <div className="grid gap-4 sm:grid-cols-2">
          {Object.entries(fields).map(([field, options]) => (
            <label key={field} className="block">
              <span className="text-sm font-medium text-slate-200">{fieldLabel(field)}</span>
              <select
                value={form[field]}
                onChange={(event) => updateField(field, event.target.value)}
                className="mt-2 h-11 w-full rounded-lg border border-white/10 bg-slate-950 px-3 text-sm text-white"
              >
                {options.map((option) => <option key={option} value={option}>{optionLabel(option)}</option>)}
              </select>
              {field === "occupancy_range" && <span className="mt-2 block text-xs text-slate-400">Otomatik seçim bina tipi ve zamana göre hesaplanır.</span>}
            </label>
          ))}
        </div>
        <div className="mt-5">
          <LoadingButton loading={loading} onClick={submit}>Risk çıktısı üret</LoadingButton>
        </div>
      </Panel>
      {error && <p className="rounded-lg bg-red-950/60 p-3 text-sm text-red-200">Hata: {error}</p>}
      {result && (
        <div className="space-y-4">
          <Panel>
            <p className="text-xs uppercase tracking-wide text-slate-400">Tahmini Ekonomik Kayıp Aralığı</p>
            <p className="mt-2 text-3xl font-bold text-orange-300">{result.economic_loss_range_try}</p>
          </Panel>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <MetricCard label="Tahmini Nüfus Aralığı" value={result.estimated_population_range} />
            <MetricCard label="Olası Can Kaybı Aralığı" value={result.estimated_casualty_range} />
            <MetricCard label="Risk Seviyesi" value={levelLabel(result.risk_level)} valueClass={riskColor[result.risk_level]} />
            <MetricCard label="Ekonomik Kayıp Seviyesi" value={levelLabel(result.economic_loss_level)} valueClass={riskColor[result.economic_loss_level]} />
          </div>
          <div className="grid gap-4 sm:grid-cols-3">
            <MetricCard label="Yapısal Kayıp" value={result.economic_loss_breakdown.structural_loss} />
            <MetricCard label="Enkaz Kaldırma Maliyeti" value={result.economic_loss_breakdown.debris_removal} />
            <MetricCard label="İç Mekân Kaybı" value={result.economic_loss_breakdown.interior_loss} />
          </div>
        </div>
      )}
    </section>
  );
}

function RegionalAnalysis() {
  const [preImage, setPreImage] = useState(null);
  const [postImage, setPostImage] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submit() {
    if (!preImage || !postImage) return;
    setLoading(true);
    setResult(null);
    setError("");

    const formData = new FormData();
    formData.append("pre_image", preImage);
    formData.append("post_image", postImage);

    try {
      const response = await fetch(`${API_BASE_URL}/predict-regional-damage`, { method: "POST", body: formData });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Bölgesel analiz tamamlanamadı.");
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  const priorityColor = {
    very_low: "text-emerald-400",
    low: "text-lime-400",
    medium: "text-yellow-300",
    high: "text-orange-400",
    very_high: "text-red-400"
  };

  return (
    <section className="space-y-5">
      <PageTitle title="Bölgesel Analiz" />
      <Panel className="space-y-5">
        <div className="grid gap-4 md:grid-cols-2">
          <UploadBox label="Afet öncesi uydu görüntüsü" file={preImage} setFile={setPreImage} />
          <UploadBox label="Afet sonrası uydu görüntüsü" file={postImage} setFile={setPostImage} />
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          <ImagePreviewCard title="Afet Öncesi Görüntü" file={preImage} alt="Afet öncesi görüntü" />
          <ImagePreviewCard title="Afet Sonrası Görüntü" file={postImage} alt="Afet sonrası görüntü" />
        </div>
        <LoadingButton loading={loading} disabled={!preImage || !postImage} onClick={submit}>Bölgeyi analiz et</LoadingButton>
      </Panel>
      {error && <p className="rounded-lg bg-red-950/60 p-3 text-sm text-red-200">Hata: {error}</p>}
      {result && (
        <div className="space-y-5">
          <Panel>
            <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
              <div>
                <p className="text-sm text-slate-400">Öncelik Seviyesi</p>
                <h3 className={`mt-1 text-3xl font-bold ${priorityColor[result.priority_level]}`}>{levelLabel(result.priority_level)} öncelik</h3>
              </div>
              <div className="min-w-60">
                <div className="flex items-center justify-between gap-4 text-sm">
                  <span className="font-semibold text-slate-200">Bölgesel Hasar Skoru</span>
                  <span className="font-bold text-white">{result.regional_damage_score}</span>
                </div>
                <Progress value={Number(result.regional_damage_score || 0) * 100} />
              </div>
            </div>
            <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <MetricCard label="Bölgesel Hasar Skoru" value={result.regional_damage_score} />
            <MetricCard label="Öncelik Seviyesi" value={levelLabel(result.priority_level)} valueClass={priorityColor[result.priority_level]} />
            <MetricCard label="Değişim Alanı Oranı" value={result.change_area_ratio} />
            <MetricCard label="Şiddetli Değişim Oranı" value={result.severe_change_ratio} />
            <MetricCard label="Etkilenen Bölge Sayısı" value={result.affected_region_count} />
            <MetricCard label="Piksel Farkı" value={result.pixel_difference} />
            <MetricCard label="Yapısal Benzerlik Değişimi" value={result.ssim_change} />
            <MetricCard label="Görsel Özellik Değişimi" value={result.deep_feature_difference} />
            </div>
          </Panel>

          <Panel>
            <h3 className="text-lg font-bold text-white">Değişim Haritası</h3>
            <div className="mt-4 flex min-h-[320px] items-center justify-center overflow-hidden rounded-lg border border-white/10 bg-slate-950/45">
              {result.heatmap_url ? (
                <img src={`${API_BASE_URL}${result.heatmap_url}`} alt="Değişim haritası" className="max-h-[560px] w-full object-contain" />
              ) : (
                <span className="px-4 text-center text-sm text-slate-400">Henüz görsel yüklenmedi.</span>
              )}
            </div>
            <p className="mt-4 text-sm leading-6 text-slate-300">
              Değişim haritası, afet öncesi ve sonrası görüntüler arasındaki yoğun farklılaşan bölgeleri görselleştirir.
              Sıcak renkler, değişimin daha yoğun olduğu alanları ifade eder.
            </p>
          </Panel>
        </div>
      )}
    </section>
  );
}

function AboutPage() {
  return (
    <section className="space-y-5">
      <PageTitle title="Hakkında" />
      <Panel>
        <p className="leading-7 text-slate-300">
          Deprem Karar Destek Sistemi; deprem aktivitelerini harita üzerinde gösteren, bina hasarını
          görsel üzerinden analiz eden, risk değerlendirmesi yapan ve afet öncesi/sonrası uydu
          görüntülerinden bölgesel değişimi yorumlayan bir karar destek platformudur.
        </p>
      </Panel>
    </section>
  );
}

function PageTitle({ title, text }) {
  return (
    <div>
      <h3 className="text-2xl font-bold">{title}</h3>
      {text && <p className="mt-2 text-sm text-slate-300">{text}</p>}
    </div>
  );
}

function MetricCard({ label, value, valueClass = "text-white" }) {
  return (
    <Panel>
      <p className="text-xs uppercase tracking-wide text-slate-400">{label}</p>
      <p className={`mt-2 text-lg font-bold ${valueClass}`}>{value}</p>
    </Panel>
  );
}

function Progress({ value }) {
  const width = Math.max(0, Math.min(100, Number(value) || 0));
  return (
    <div className="mt-4 h-3 overflow-hidden rounded-full bg-slate-800">
      <div className="h-full rounded-full bg-orange-500" style={{ width: `${width}%` }} />
    </div>
  );
}

function App() {
  const [activePage, setActivePage] = useState("home");
  const [buildingDamageResult, setBuildingDamageResult] = useState(null);

  return (
    <Shell activePage={activePage} setActivePage={setActivePage}>
      {activePage === "home" && <HomePage setActivePage={setActivePage} />}
      {activePage === "building" && <BuildingDamageAnalysis onDamageResult={setBuildingDamageResult} />}
      {activePage === "risk" && <RiskAnalysis buildingDamageResult={buildingDamageResult} />}
      {activePage === "regional" && <RegionalAnalysis />}
      {activePage === "about" && <AboutPage />}
    </Shell>
  );
}

createRoot(document.getElementById("root")).render(<App />);

function damageLabel(value) {
  const labels = {
    no_damage: "Hasar Yok",
    damaged: "Hasarlı",
    collapsed: "Yıkılmış"
  };
  return labels[value] || value;
}

function levelLabel(value) {
  const labels = {
    very_low: "Çok Düşük",
    low: "Düşük",
    medium: "Orta",
    high: "Yüksek",
    very_high: "Çok Yüksek",
    critical: "Kritik"
  };
  return labels[value] || value;
}

function optionLabel(value) {
  const labels = {
    no_damage: "Hasar Yok",
    damaged: "Hasarlı",
    collapsed: "Yıkılmış",
    day: "Gündüz",
    night: "Gece",
    residential: "Konut",
    office: "Ofis",
    school: "Okul",
    hospital: "Hastane",
    shopping_mall: "Alışveriş Merkezi",
    auto: "Otomatik",
    low: "Düşük",
    medium: "Orta",
    high: "Yüksek"
  };
  return labels[value] || value;
}

function fieldLabel(value) {
  const labels = {
    damage_level: "Hasar Seviyesi",
    time_of_day: "Zaman Dilimi",
    building_type: "Bina Türü",
    occupancy_range: "Doluluk Seviyesi"
  };
  return labels[value] || value;
}
