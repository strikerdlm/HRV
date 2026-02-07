// Author: Dr Diego Malpica MD
"use client";

import * as React from "react";
import { motion } from "framer-motion";
import { Plane, Wind, Eye, Thermometer, Gauge, Cloud, Search, RefreshCw, Navigation } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { fetchMETAR, fetchWeather } from "@/lib/research-api";
import type { METARResponse, WeatherResponse } from "@/types/research";
import { RISK_LEVEL_COLORS } from "@/types/research";

// ---------------------------------------------------------------------------
// Default stations
// ---------------------------------------------------------------------------

const DEFAULT_STATIONS = [
  { icao: "SKBO", label: "Bogota, Colombia" },
  { icao: "SAWE", label: "Marambio, Antarctica" },
  { icao: "SCRM", label: "King George Is., Antarctica" },
];

// ---------------------------------------------------------------------------
// SVG Wind Compass (large, clear, with degree markings)
// ---------------------------------------------------------------------------

function WindCompass({ deg, speed, gust, unit }: { deg: number; speed: number; gust?: number | null; unit: string }) {
  const r = 90; // radius of compass
  const cx = 110;
  const cy = 110;
  const tickR = r - 2;
  const labelR = r - 18;
  const arrowLen = r - 25;

  // Cardinal and intercardinal directions
  const directions = [
    { angle: 0, label: "N", major: true },
    { angle: 45, label: "NE", major: false },
    { angle: 90, label: "E", major: true },
    { angle: 135, label: "SE", major: false },
    { angle: 180, label: "S", major: true },
    { angle: 225, label: "SW", major: false },
    { angle: 270, label: "W", major: true },
    { angle: 315, label: "NW", major: false },
  ];

  // Degree tick marks every 10 degrees
  const ticks: Array<{ angle: number; len: number }> = [];
  for (let a = 0; a < 360; a += 10) {
    ticks.push({ angle: a, len: a % 30 === 0 ? 10 : 5 });
  }

  // Convert wind direction to radians (meteorological: 0=N, clockwise)
  const arrowRad = ((deg - 90) * Math.PI) / 180;
  const ax = cx + arrowLen * Math.cos(arrowRad);
  const ay = cy + arrowLen * Math.sin(arrowRad);

  // Arrow head
  const headSize = 8;
  const headAngle1 = arrowRad + Math.PI * 0.85;
  const headAngle2 = arrowRad - Math.PI * 0.85;
  const h1x = ax + headSize * Math.cos(headAngle1);
  const h1y = ay + headSize * Math.sin(headAngle1);
  const h2x = ax + headSize * Math.cos(headAngle2);
  const h2y = ay + headSize * Math.sin(headAngle2);

  // Speed color
  const speedColor = speed >= 25 ? "#e74c3c" : speed >= 15 ? "#f39c12" : "#2c3e50";

  return (
    <div className="flex flex-col items-center">
      <svg width="220" height="220" viewBox="0 0 220 220">
        {/* Outer circle */}
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="#2c3e50" strokeWidth="2" opacity="0.2" />
        <circle cx={cx} cy={cy} r={r - 1} fill="none" stroke="#2c3e50" strokeWidth="0.5" opacity="0.1" />

        {/* Degree ticks */}
        {ticks.map(({ angle, len }) => {
          const rad = ((angle - 90) * Math.PI) / 180;
          const x1 = cx + tickR * Math.cos(rad);
          const y1 = cy + tickR * Math.sin(rad);
          const x2 = cx + (tickR - len) * Math.cos(rad);
          const y2 = cy + (tickR - len) * Math.sin(rad);
          return (
            <line key={angle} x1={x1} y1={y1} x2={x2} y2={y2}
              stroke="#2c3e50" strokeWidth={len > 5 ? 1.5 : 0.8} opacity={len > 5 ? 0.6 : 0.3} />
          );
        })}

        {/* Direction labels */}
        {directions.map(({ angle, label, major }) => {
          const rad = ((angle - 90) * Math.PI) / 180;
          const lx = cx + labelR * Math.cos(rad);
          const ly = cy + labelR * Math.sin(rad);
          return (
            <text key={label} x={lx} y={ly}
              textAnchor="middle" dominantBaseline="central"
              fill="#1a1a1a" fontSize={major ? 13 : 10} fontWeight={major ? "bold" : "normal"}>
              {label}
            </text>
          );
        })}

        {/* Wind arrow */}
        <line x1={cx} y1={cy} x2={ax} y2={ay}
          stroke={speedColor} strokeWidth="3" strokeLinecap="round" />
        <polygon points={`${ax},${ay} ${h1x},${h1y} ${h2x},${h2y}`}
          fill={speedColor} />

        {/* Center dot */}
        <circle cx={cx} cy={cy} r="4" fill={speedColor} />

        {/* Center text: speed */}
        <text x={cx} y={cy + 28} textAnchor="middle" fill="#1a1a1a" fontSize="18" fontWeight="bold">
          {speed} {unit}
        </text>
        {gust && (
          <text x={cx} y={cy + 42} textAnchor="middle" fill="#e74c3c" fontSize="11" fontWeight="bold">
            G{gust} {unit}
          </text>
        )}
        <text x={cx} y={cy - 22} textAnchor="middle" fill="#2c3e50" fontSize="11">
          {deg === 0 ? "VRB" : `${deg}`}
        </text>
      </svg>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export function METARDashboard() {
  const [icao, setIcao] = React.useState("SKBO");
  const [inputIcao, setInputIcao] = React.useState("SKBO");
  const [metarData, setMetarData] = React.useState<METARResponse | null>(null);
  const [weatherData, setWeatherData] = React.useState<WeatherResponse | null>(null);
  const [loading, setLoading] = React.useState(false);

  const doFetch = React.useCallback(async (station: string) => {
    setLoading(true);
    try {
      const [metar, weather] = await Promise.all([
        fetchMETAR(station),
        fetchWeather(station), // Use ICAO as city fallback
      ]);
      setMetarData(metar);
      setWeatherData(weather);
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => { doFetch(icao); }, [icao, doFetch]);

  // Auto-refresh every 10 minutes
  React.useEffect(() => {
    const interval = setInterval(() => doFetch(icao), 10 * 60_000);
    return () => clearInterval(interval);
  }, [icao, doFetch]);

  const handleSearch = () => {
    const clean = inputIcao.trim().toUpperCase();
    if (clean.length === 4) setIcao(clean);
  };

  const m = metarData?.metar as Record<string, any> | null;
  const raw = m?.rawOb ?? m?.rawMETAR ?? m?.raw ?? null;

  // Extract METAR fields
  const temp = m?.temp ?? m?.temperature ?? null;
  const dewp = m?.dewp ?? m?.dewpoint ?? null;
  const windDir = m?.wdir ?? m?.windDirection ?? 0;
  const windSpd = m?.wspd ?? m?.windSpeed ?? 0;
  const windGust = m?.wgst ?? m?.windGust ?? null;
  const vis = m?.visib ?? m?.visibility ?? null;
  const altim = m?.altim ?? m?.altimeter ?? null;
  const fltCat = m?.fltCat ?? m?.flightCategory ?? null;

  const fltCatColors: Record<string, string> = {
    VFR: "#27ae60",
    MVFR: "#3498db",
    IFR: "#e74c3c",
    LIFR: "#8e44ad",
  };

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <CardTitle className="flex items-center gap-2">
            <Plane className="h-5 w-5 text-blue-500" />
            Aviation Weather (METAR)
          </CardTitle>
          {fltCat && (
            <Badge style={{ backgroundColor: fltCatColors[fltCat] || "#888", color: "#fff" }}>
              {fltCat}
            </Badge>
          )}
        </div>
        <CardDescription>Real-time decoded METAR from AviationWeather.gov</CardDescription>
      </CardHeader>
      <CardContent>
        {/* Station Selector */}
        <div className="flex gap-2 mb-3">
          <Input
            value={inputIcao}
            onChange={(e) => setInputIcao(e.target.value.toUpperCase())}
            placeholder="ICAO (e.g., SKBO)"
            className="w-28 font-mono text-sm"
            maxLength={4}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          />
          <Button size="sm" variant="outline" onClick={handleSearch} disabled={loading}>
            <Search className="h-3.5 w-3.5" />
          </Button>
          {DEFAULT_STATIONS.map((s) => (
            <Button
              key={s.icao}
              size="sm"
              variant={icao === s.icao ? "default" : "ghost"}
              className="text-xs hidden md:inline-flex"
              onClick={() => { setIcao(s.icao); setInputIcao(s.icao); }}
            >
              {s.icao}
            </Button>
          ))}
        </div>

        {metarData?.error && !m && (
          <p className="text-sm text-red-500 mb-2">{metarData.error}</p>
        )}

        {m && (
          <>
            {/* Raw METAR */}
            {raw && (
              <div className="bg-muted/50 p-2 rounded font-mono text-xs mb-3 break-all">
                {String(raw)}
              </div>
            )}

            {/* Decoded fields */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div className="p-2 rounded-lg border text-center">
                <Thermometer className="h-4 w-4 mx-auto mb-1 text-red-500" />
                <p className="text-[10px] text-muted-foreground">Temperature</p>
                <p className="text-lg font-bold">{temp != null ? `${temp}C` : "N/A"}</p>
                <p className="text-[10px] text-muted-foreground">Dew: {dewp != null ? `${dewp}C` : "N/A"}</p>
              </div>
              <div className="p-2 rounded-lg border text-center">
                <Wind className="h-4 w-4 mx-auto mb-1 text-blue-500" />
                <p className="text-[10px] text-muted-foreground">Wind</p>
                <p className="text-lg font-bold">{windSpd} kt</p>
                <p className="text-[10px] text-muted-foreground">
                  {windDir}deg {windGust ? `G${windGust}kt` : ""}
                </p>
              </div>
              <div className="p-2 rounded-lg border text-center">
                <Eye className="h-4 w-4 mx-auto mb-1 text-green-500" />
                <p className="text-[10px] text-muted-foreground">Visibility</p>
                <p className="text-lg font-bold">{vis != null ? `${vis}` : "N/A"}</p>
                <p className="text-[10px] text-muted-foreground">SM</p>
              </div>
              <div className="p-2 rounded-lg border text-center">
                <Gauge className="h-4 w-4 mx-auto mb-1 text-amber-500" />
                <p className="text-[10px] text-muted-foreground">Altimeter</p>
                <p className="text-lg font-bold">{altim != null ? altim : "N/A"}</p>
                <p className="text-[10px] text-muted-foreground">inHg</p>
              </div>
            </div>

            {/* Wind Compass — large SVG with degree markings */}
            <div className="mt-3">
              <WindCompass deg={windDir} speed={windSpd} gust={windGust} unit="kt" />
            </div>

            {/* Environment indices from weather data */}
            {weatherData?.indices && (
              <div className="grid grid-cols-2 gap-2 mt-3">
                <div className="p-2 rounded-lg border text-center" style={{ borderColor: RISK_LEVEL_COLORS[weatherData.indices.cold_risk] || "#ddd" }}>
                  <p className="text-[10px] text-muted-foreground">Wind Chill</p>
                  <p className="text-sm font-bold">{weatherData.indices.wind_chill_c}C</p>
                  <Badge className="text-[9px]" style={{ backgroundColor: RISK_LEVEL_COLORS[weatherData.indices.cold_risk] || "#888", color: "#fff" }}>
                    {weatherData.indices.cold_risk}
                  </Badge>
                </div>
                <div className="p-2 rounded-lg border text-center" style={{ borderColor: RISK_LEVEL_COLORS[weatherData.indices.heat_risk] || "#ddd" }}>
                  <p className="text-[10px] text-muted-foreground">Heat Stress (WBGT)</p>
                  <p className="text-sm font-bold">{weatherData.indices.wbgt_c}C</p>
                  <Badge className="text-[9px]" style={{ backgroundColor: RISK_LEVEL_COLORS[weatherData.indices.heat_risk] || "#888", color: "#fff" }}>
                    {weatherData.indices.heat_risk}
                  </Badge>
                </div>
              </div>
            )}
          </>
        )}

        {loading && !m && (
          <div className="text-center py-6 text-muted-foreground text-sm">Loading METAR...</div>
        )}
      </CardContent>
    </Card>
  );
}
