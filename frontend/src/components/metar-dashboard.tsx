// Author: Dr Diego Malpica MD
"use client";

import * as React from "react";
import { motion } from "framer-motion";
import { Plane, Wind, Eye, Thermometer, Gauge, Cloud, Search, RefreshCw } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { EChartsWrapper } from "@/components/charts";
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
// Wind compass gauge (no title per plot rules)
// ---------------------------------------------------------------------------

function buildWindGauge(deg: number, speed: number, unit: string): Record<string, unknown> {
  return {
    series: [{
      type: "gauge",
      min: 0,
      max: 360,
      splitNumber: 8,
      radius: "90%",
      startAngle: 90,
      endAngle: -270,
      axisLine: { lineStyle: { width: 8, color: [[1, "rgba(52,73,94,0.15)"]] } },
      pointer: { length: "65%", width: 5, itemStyle: { color: "#e74c3c" } },
      axisTick: { show: false },
      splitLine: { length: 10, lineStyle: { color: "#1a1a1a", width: 1.5 } },
      axisLabel: {
        color: "#1a1a1a",
        fontSize: 9,
        distance: 14,
        formatter: (v: number) => {
          const dirs: Record<number, string> = { 0: "N", 45: "NE", 90: "E", 135: "SE", 180: "S", 225: "SW", 270: "W", 315: "NW" };
          return dirs[v] || "";
        },
      },
      detail: {
        valueAnimation: true,
        formatter: `${speed} ${unit}\n{deg}`,
        color: "#1a1a1a",
        fontSize: 12,
        fontWeight: "bold",
        offsetCenter: [0, "75%"],
        rich: { deg: { fontSize: 9, color: "#888" } },
      },
      data: [{ value: deg, name: `${deg}deg` }],
      title: { show: false },
    }],
  };
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

            {/* Wind compass gauge */}
            <div className="mt-3 flex justify-center">
              <div className="w-40">
                <EChartsWrapper
                  option={buildWindGauge(windDir, windSpd, "kt") as any}
                  height={150}
                  showToolbox={false}
                />
              </div>
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
