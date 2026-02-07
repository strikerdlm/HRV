// Author: Dr Diego Malpica MD
"use client";

import * as React from "react";
import { motion } from "framer-motion";
import { Thermometer, Droplets, Wind, Gauge, Volume2, Sun, Atom, RefreshCw } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { fetchICEStation } from "@/lib/research-api";
import type { ICEStationResponse } from "@/types/research";

// ---------------------------------------------------------------------------
// SVG Ring Gauge (matching IHPI gauge style per plot rules)
// ---------------------------------------------------------------------------

function RingGauge({
  value,
  min,
  max,
  unit,
  label,
  icon: Icon,
  status,
}: {
  value: number;
  min: number;
  max: number;
  unit: string;
  label: string;
  icon: React.ElementType;
  status: "normal" | "warning" | "danger";
}) {
  const pct = Math.max(0, Math.min(1, (value - min) / (max - min)));
  const circumference = 2 * Math.PI * 32; // r=32
  const strokeColor = status === "normal" ? "#27ae60" : status === "warning" ? "#f39c12" : "#e74c3c";
  const bgOpacity = status === "normal" ? "0.15" : status === "warning" ? "0.15" : "0.2";
  const textColor = status === "normal" ? "text-green-600" : status === "warning" ? "text-yellow-600" : "text-red-600";

  return (
    <motion.div
      className="flex flex-col items-center p-2"
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3 }}
    >
      <div className="relative w-20 h-20">
        <svg className="w-full h-full transform -rotate-90" viewBox="0 0 80 80">
          {/* Background ring */}
          <circle
            cx="40" cy="40" r="32"
            fill="none"
            stroke={strokeColor}
            strokeWidth="6"
            opacity={bgOpacity}
          />
          {/* Progress ring */}
          <circle
            cx="40" cy="40" r="32"
            fill="none"
            stroke={strokeColor}
            strokeWidth="6"
            strokeDasharray={`${pct * circumference} ${circumference}`}
            strokeLinecap="round"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`text-sm font-bold ${textColor}`}>{value}</span>
          <span className="text-[8px] text-muted-foreground">{unit}</span>
        </div>
      </div>
      <div className="flex items-center gap-1 mt-1">
        <Icon className="h-3 w-3 text-muted-foreground" />
        <span className="text-[10px] text-muted-foreground font-medium">{label}</span>
      </div>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export function ICEStationMonitor() {
  const [data, setData] = React.useState<ICEStationResponse | null>(null);
  const [loading, setLoading] = React.useState(false);

  const fetchData = React.useCallback(async () => {
    setLoading(true);
    try {
      const result = await fetchICEStation();
      if (result) setData(result);
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => { fetchData(); }, [fetchData]);

  React.useEffect(() => {
    const interval = setInterval(fetchData, 60_000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const r = data?.readings;

  function getStatus(value: number, warnLow: number | null, warnHigh: number | null): "normal" | "warning" | "danger" {
    if (warnLow != null && value < warnLow) return "danger";
    if (warnHigh != null && value > warnHigh) return "danger";
    return "normal";
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Atom className="h-5 w-5 text-cyan-500" />
            ICE Station Environment
          </CardTitle>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-xs">Simulated</Badge>
            <button onClick={fetchData} className="p-1 hover:bg-muted rounded" type="button" disabled={loading}>
              <RefreshCw className={`h-3.5 w-3.5 text-muted-foreground ${loading ? "animate-spin" : ""}`} />
            </button>
          </div>
        </div>
        <CardDescription>Isolated Confined Environment monitoring (Antarctic analog)</CardDescription>
      </CardHeader>
      <CardContent>
        {!r ? (
          <p className="text-sm text-muted-foreground text-center py-4">Loading sensor data...</p>
        ) : (
          <div className="grid grid-cols-4 gap-1">
            <RingGauge value={r.temperature_c} min={10} max={35} unit="C" label="Temp" icon={Thermometer} status={getStatus(r.temperature_c, 16, 28)} />
            <RingGauge value={r.humidity_pct} min={0} max={100} unit="%" label="Humidity" icon={Droplets} status={getStatus(r.humidity_pct, 20, 70)} />
            <RingGauge value={r.co2_ppm} min={300} max={2000} unit="ppm" label="CO2" icon={Wind} status={r.co2_ppm > 1500 ? "danger" : r.co2_ppm > 1000 ? "warning" : "normal"} />
            <RingGauge value={r.pressure_hpa} min={920} max={1060} unit="hPa" label="Pressure" icon={Gauge} status={getStatus(r.pressure_hpa, 950, null)} />
            <RingGauge value={r.pm25_ugm3} min={0} max={100} unit="ug/m3" label="PM2.5" icon={Wind} status={r.pm25_ugm3 > 50 ? "danger" : r.pm25_ugm3 > 25 ? "warning" : "normal"} />
            <RingGauge value={r.noise_db} min={0} max={100} unit="dB" label="Noise" icon={Volume2} status={r.noise_db > 70 ? "danger" : r.noise_db > 50 ? "warning" : "normal"} />
            <RingGauge value={r.light_lux} min={0} max={600} unit="lux" label="Light" icon={Sun} status={r.light_lux < 100 ? "warning" : "normal"} />
            <RingGauge value={r.o2_pct} min={18} max={22} unit="%" label="O2" icon={Atom} status={r.o2_pct < 19.5 ? "danger" : "normal"} />
          </div>
        )}
      </CardContent>
    </Card>
  );
}
