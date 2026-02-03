// Author: Dr Diego Malpica MD
"use client";

import * as React from "react";
import ReactEChartsCore from "echarts-for-react/lib/core";
import * as echarts from "echarts/core";
import {
  LineChart,
  BarChart,
  GaugeChart,
  RadarChart,
  ScatterChart,
  HeatmapChart,
  PieChart,
} from "echarts/charts";
import {
  GridComponent,
  TooltipComponent,
  TitleComponent,
  LegendComponent,
  ToolboxComponent,
  DataZoomComponent,
  VisualMapComponent,
  MarkLineComponent,
  MarkAreaComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import type { EChartsOption } from "echarts";
import { cn } from "@/lib/utils";

// Register ECharts components
echarts.use([
  LineChart,
  BarChart,
  GaugeChart,
  RadarChart,
  ScatterChart,
  HeatmapChart,
  PieChart,
  GridComponent,
  TooltipComponent,
  TitleComponent,
  LegendComponent,
  ToolboxComponent,
  DataZoomComponent,
  VisualMapComponent,
  MarkLineComponent,
  MarkAreaComponent,
  CanvasRenderer,
]);

/**
 * Scientific color palette following publication standards
 * Based on project plots.mdc rules and Nature Research guidelines
 */
export const SCIENTIFIC_COLORS = {
  // Primary colors (semantic)
  primary: "#3498db",
  success: "#27ae60",
  warning: "#f39c12",
  danger: "#e74c3c",
  info: "#1abc9c",
  trend: "#2c3e50",
  
  // Extended palette for multi-series
  series: [
    "#3498db", // Blue
    "#27ae60", // Green
    "#e74c3c", // Red
    "#9b59b6", // Purple
    "#f39c12", // Orange
    "#1abc9c", // Teal
    "#34495e", // Dark gray
    "#e91e63", // Pink
  ],
  
  // Risk zones (with opacity for background shading)
  goodZone: "rgba(39, 174, 96, 0.1)",
  normalZone: "rgba(52, 152, 219, 0.1)",
  cautionZone: "rgba(243, 156, 18, 0.1)",
  poorZone: "rgba(231, 76, 60, 0.1)",
  
  // Text colors (NEVER use light/gray colors per project rules)
  textPrimary: "#1a1a1a",
  textSecondary: "#2c3e50",
  
  // Grid and axes
  gridLine: "rgba(44, 62, 80, 0.1)",
  axisLine: "#2c3e50",
  
  // Gauge structural elements (acceptable darker grays)
  gaugeTick: "#64748b",      // Slate-500 for tick marks
  gaugeSplit: "#475569",     // Slate-600 for split lines
  gaugeDisabled: "#94a3b8",  // Slate-400 for disabled states
};

interface EChartsWrapperProps {
  option: EChartsOption;
  height?: number | string;
  className?: string;
  loading?: boolean;
  showToolbox?: boolean;
  onChartReady?: (chart: any) => void;
}

/**
 * ECharts wrapper component following publication-quality standards
 * 
 * Features:
 * - Dark font colors (per project rules)
 * - Scientific color palette
 * - Export toolbox (PNG, SVG, data view)
 * - Responsive sizing
 */
export function EChartsWrapper({
  option,
  height = 380,
  className,
  loading = false,
  showToolbox = true,
  onChartReady,
}: EChartsWrapperProps) {
  const chartRef = React.useRef<ReactEChartsCore>(null);

  // Apply default styling per project rules
  const styledOption: EChartsOption = React.useMemo(() => {
    const baseOption: EChartsOption = {
      // Default text styles - NEVER use gray/light colors
      textStyle: {
        color: SCIENTIFIC_COLORS.textPrimary,
        fontFamily: "Inter, system-ui, sans-serif",
      },
      // Default title style
      title: {
        textStyle: {
          color: SCIENTIFIC_COLORS.textPrimary,
          fontWeight: "bold",
        },
        subtextStyle: {
          color: SCIENTIFIC_COLORS.textSecondary,
        },
        ...((option.title as any) || {}),
      },
      // Default tooltip
      tooltip: {
        trigger: "axis",
        backgroundColor: "#ffffff",
        borderColor: SCIENTIFIC_COLORS.axisLine,
        textStyle: {
          color: SCIENTIFIC_COLORS.textPrimary,
        },
        ...((option.tooltip as any) || {}),
      },
      // Default legend
      legend: {
        textStyle: {
          color: SCIENTIFIC_COLORS.textPrimary,
        },
        ...((option.legend as any) || {}),
      },
      // Default grid
      grid: {
        containLabel: true,
        left: 60,
        right: 40,
        top: 60,
        bottom: 60,
        ...((option.grid as any) || {}),
      },
      // Default colors
      color: SCIENTIFIC_COLORS.series,
      // Toolbox for exports (PNG 300+ DPI, SVG for vector)
      ...(showToolbox && {
        toolbox: {
          feature: {
            saveAsImage: {
              type: "png",
              pixelRatio: 3,  // 300+ DPI for publication
              title: "Save PNG (300 DPI)",
            },
            dataZoom: {
              title: { zoom: "Zoom", back: "Reset Zoom" },
            },
            dataView: {
              title: "View Data",
              lang: ["Data View", "Close", "Refresh"],
            },
            restore: {
              title: "Restore",
            },
          },
          right: 20,
          top: 20,
          iconStyle: {
            borderColor: SCIENTIFIC_COLORS.textSecondary,
          },
        },
      }),
      // Merge with provided option
      ...option,
    };

    // Apply dark colors and clean styling to axes
    if (option.xAxis) {
      baseOption.xAxis = applyAxisStyles(option.xAxis, true);
    }
    if (option.yAxis) {
      baseOption.yAxis = applyAxisStyles(option.yAxis, false);
    }

    return baseOption;
  }, [option, showToolbox]);

  return (
    <div className={cn("echarts-container", className)}>
      <ReactEChartsCore
        ref={chartRef}
        echarts={echarts}
        option={styledOption}
        style={{ height, width: "100%" }}
        showLoading={loading}
        loadingOption={{
          text: "Loading...",
          color: SCIENTIFIC_COLORS.primary,
          textColor: SCIENTIFIC_COLORS.textPrimary,
        }}
        onChartReady={onChartReady}
        notMerge
        lazyUpdate
      />
    </div>
  );
}

// Apply dark colors and clean styling to axis configuration (per project rules)
function applyAxisStyles(axis: any, isXAxis: boolean = false): any {
  if (Array.isArray(axis)) {
    return axis.map((a) => applyAxisStyles(a, isXAxis));
  }

  // Calculate smart interval for x-axis to prevent label overlap
  const axisLabelDefaults: Record<string, unknown> = {
    color: SCIENTIFIC_COLORS.textPrimary,
    fontSize: 11,
    hideOverlap: true,  // ECharts 5+ feature to hide overlapping labels
  };

  // For x-axis with category data, add auto-interval and rotation
  if (isXAxis) {
    const dataLength = axis.data?.length || 0;
    
    // Smart interval: show fewer labels when there's lots of data
    if (dataLength > 100) {
      axisLabelDefaults.interval = Math.ceil(dataLength / 10) - 1;
      axisLabelDefaults.rotate = 0; // Keep horizontal when showing few
    } else if (dataLength > 50) {
      axisLabelDefaults.interval = Math.ceil(dataLength / 15) - 1;
      axisLabelDefaults.rotate = 45;
      axisLabelDefaults.align = "right";
    } else if (dataLength > 20) {
      axisLabelDefaults.interval = Math.ceil(dataLength / 10) - 1;
      axisLabelDefaults.rotate = 0;
    }
    
    // For time/date labels, use more spacing
    if (axis.type === "time") {
      axisLabelDefaults.hideOverlap = true;
    }
  }

  return {
    ...axis,
    axisLine: {
      lineStyle: {
        color: SCIENTIFIC_COLORS.axisLine,
      },
      ...(axis.axisLine || {}),
    },
    axisLabel: {
      ...axisLabelDefaults,
      ...(axis.axisLabel || {}),
    },
    axisTick: {
      lineStyle: {
        color: SCIENTIFIC_COLORS.axisLine,
      },
      alignWithLabel: true,
      ...(axis.axisTick || {}),
    },
    splitLine: {
      lineStyle: {
        color: SCIENTIFIC_COLORS.gridLine,
      },
      ...(axis.splitLine || {}),
    },
  };
}

/**
 * Helper to calculate dynamic axis bounds
 * Per project rules: NEVER use hardcoded axis min/max that might clip data
 */
export function autoAxisBounds(
  ...values: (number | null | undefined)[]
): { min: number; max: number } {
  const validValues = values.filter(
    (v): v is number => v !== null && v !== undefined && !isNaN(v)
  );

  if (validValues.length === 0) {
    return { min: 0, max: 100 };
  }

  const minVal = Math.min(...validValues);
  const maxVal = Math.max(...validValues);
  const range = maxVal - minVal || 1;
  const padding = range * 0.15;

  return {
    min: Math.floor(minVal - padding),
    max: Math.ceil(maxVal + padding),
  };
}

export { echarts };
