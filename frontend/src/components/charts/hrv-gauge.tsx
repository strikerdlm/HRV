// Author: Dr Diego Malpica MD
"use client";

import * as React from "react";
import type { EChartsOption } from "echarts";
import { EChartsWrapper, SCIENTIFIC_COLORS } from "./echarts-wrapper";

interface HRVGaugeProps {
  title: string;
  value: number | null;
  unit: string;
  min?: number;
  max?: number;
  ranges?: {
    good: [number, number];
    normal: [number, number];
    caution: [number, number];
    poor: [number, number];
  };
  height?: number;
}

/**
 * Publication-quality HRV metric gauge
 * Two-ring design with color-coded risk zones
 */
export function HRVGauge({
  title,
  value,
  unit,
  min = 0,
  max = 100,
  ranges,
  height = 280,
}: HRVGaugeProps) {
  const displayValue = value ?? 0;
  
  // Default ranges if not provided
  const defaultRanges = ranges || {
    good: [0.75 * max, max],
    normal: [0.5 * max, 0.75 * max],
    caution: [0.25 * max, 0.5 * max],
    poor: [min, 0.25 * max],
  };

  // Determine color based on value
  const getColor = () => {
    if (value === null) return "#888";
    if (value >= defaultRanges.good[0]) return SCIENTIFIC_COLORS.success;
    if (value >= defaultRanges.normal[0]) return SCIENTIFIC_COLORS.primary;
    if (value >= defaultRanges.caution[0]) return SCIENTIFIC_COLORS.warning;
    return SCIENTIFIC_COLORS.danger;
  };

  const option: EChartsOption = {
    title: {
      text: title,
      left: "center",
      top: 10,
      textStyle: {
        fontSize: 14,
        fontWeight: "bold",
        color: SCIENTIFIC_COLORS.textPrimary,
      },
    },
    series: [
      // Background ring
      {
        type: "gauge",
        center: ["50%", "60%"],
        radius: "80%",
        startAngle: 200,
        endAngle: -20,
        min,
        max,
        splitNumber: 5,
        itemStyle: {
          color: "#e0e0e0",
        },
        progress: {
          show: false,
        },
        pointer: {
          show: false,
        },
        axisLine: {
          lineStyle: {
            width: 12,
            color: [
              [defaultRanges.poor[1] / max, SCIENTIFIC_COLORS.danger],
              [defaultRanges.caution[1] / max, SCIENTIFIC_COLORS.warning],
              [defaultRanges.normal[1] / max, SCIENTIFIC_COLORS.primary],
              [1, SCIENTIFIC_COLORS.success],
            ],
          },
        },
        axisTick: {
          show: false,
        },
        splitLine: {
          show: false,
        },
        axisLabel: {
          show: true,
          distance: 20,
          color: SCIENTIFIC_COLORS.textSecondary,
          fontSize: 10,
          formatter: (value: number) => value.toFixed(0),
        },
        detail: {
          show: false,
        },
      },
      // Value ring
      {
        type: "gauge",
        center: ["50%", "60%"],
        radius: "65%",
        startAngle: 200,
        endAngle: -20,
        min,
        max,
        itemStyle: {
          color: getColor(),
        },
        progress: {
          show: true,
          width: 10,
        },
        pointer: {
          show: true,
          length: "50%",
          width: 4,
          itemStyle: {
            color: getColor(),
          },
        },
        axisLine: {
          lineStyle: {
            width: 10,
            color: [[1, "rgba(0,0,0,0.05)"]],
          },
        },
        axisTick: {
          show: false,
        },
        splitLine: {
          show: false,
        },
        axisLabel: {
          show: false,
        },
        detail: {
          valueAnimation: true,
          offsetCenter: [0, "20%"],
          fontSize: 24,
          fontWeight: "bold",
          formatter: (val: number) =>
            value !== null ? `${val.toFixed(1)}` : "N/A",
          color: SCIENTIFIC_COLORS.textPrimary,
        },
        data: [{ value: displayValue }],
      },
    ],
    graphic: [
      {
        type: "text",
        left: "center",
        bottom: 20,
        style: {
          text: unit,
          fontSize: 12,
          fill: SCIENTIFIC_COLORS.textSecondary,
        },
      },
    ],
  };

  return <EChartsWrapper option={option} height={height} showToolbox={false} />;
}
