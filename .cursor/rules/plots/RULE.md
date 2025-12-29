---
alwaysApply: true
---
## Plotting Policy — Publication-Quality ECharts Visualizations

**Version**: 1.0.0 | **Last Updated**: 2025-12-29

When adding or modifying any plot/visualization in this project, agents MUST follow these guidelines to ensure scientific rigor, visual consistency, and publication-readiness.

---

## 1. Library & Technology Stack

| Requirement | Specification |
|-------------|---------------|
| **Default Library** | Apache ECharts (via `render_echarts()` helper) |
| **Fallback** | Plotly only when ECharts cannot meet a requirement |
| **Color Palette** | Use `SCIENTIFIC_COLORS` constant from `user_profile_tab.py` |
| **Rendering** | Local ECharts bundle from `node_modules/` |

```python
# Standard import pattern
from echarts_component import render_echarts

# Scientific color palette (defined in user_profile_tab.py)
SCIENTIFIC_COLORS = {
    "primary": "#2c3e50",
    "secondary": "#7f8c8d", 
    "accent": "#3498db",
    "success": "#27ae60",
    "warning": "#f39c12",
    "danger": "#e74c3c",
    "grid": "#ecf0f1",
    "text": "#2c3e50",
}
```

---

## 2. Chart Structure & Anatomy

Every publication-quality chart MUST include:

### 2.1 Title Block
```python
"title": {
    "text": "Primary Title — Clear and Descriptive",
    "subtext": "Context: reference ranges | thresholds | methodology notes",
    "left": "center",
    "textStyle": {"fontSize": 15, "fontWeight": "bold", "color": SCIENTIFIC_COLORS["text"]},
    "subtextStyle": {"fontSize": 10, "color": "#7f8c8d"},
},
```

### 2.2 Axis Configuration
```python
"xAxis": {
    "type": "category",
    "data": date_labels,
    "name": "Date",                    # Always label axes
    "nameLocation": "middle",
    "nameGap": 30,
    "axisLabel": {"rotate": 45, "fontSize": 9},
},
"yAxis": {
    "type": "value",
    "name": "Variable Name (unit)",    # Include units!
    "nameLocation": "middle",
    "nameGap": 45,
    "nameTextStyle": {"fontSize": 12, "fontWeight": "bold"},
    "splitLine": {"lineStyle": {"color": SCIENTIFIC_COLORS["grid"], "type": "dashed"}},
},
```

### 2.3 Grid & Layout
```python
"grid": {
    "left": "8%",                      # Accommodate axis labels
    "right": "5%",                     # Or "10%" for dual-axis
    "top": "15%",                      # Space for title + subtitle
    "bottom": "15%",                   # Space for legend + axis labels
    "containLabel": True,
},
```

### 2.4 Legend
```python
"legend": {
    "data": ["Series 1", "Series 2"],
    "bottom": 5,                       # Position at bottom
    "textStyle": {"fontSize": 10},
},
```

### 2.5 Tooltip
```python
"tooltip": {
    "trigger": "axis",
    "axisPointer": {"type": "cross"},  # Cross-hair for precision
},
```

### 2.6 Interactive Features
```python
"dataZoom": [{"type": "inside", "start": 0, "end": 100}],  # Pan/zoom
```

---

## 3. Reference Zones & Thresholds

### 3.1 Shaded Reference Zones (Stacked Area)
Use stacked invisible lines to create shaded bands:

```python
# Example: Normal range zone (e.g., 60-80 bpm)
{
    "name": "Normal Range",
    "type": "line",
    "data": [80] * len(dates),        # Upper bound
    "lineStyle": {"opacity": 0},
    "areaStyle": {"color": "rgba(46, 204, 113, 0.15)"},  # Green tint
    "stack": "zone_name",
    "symbol": "none",
    "silent": True,                    # Non-interactive
},
{
    "name": "_zone_base",              # Underscore = hidden from legend
    "type": "line", 
    "data": [60] * len(dates),        # Lower bound
    "lineStyle": {"opacity": 0},
    "areaStyle": {"color": "#fff"},   # White to "cut out" below
    "stack": "zone_name",
    "symbol": "none",
    "silent": True,
},
```

### 3.2 Threshold Lines
```python
{
    "name": "95% Threshold",
    "type": "line",
    "data": [95] * len(dates),
    "lineStyle": {"color": "#e74c3c", "width": 2, "type": "dashed"},
    "symbol": "none",
},
```

### 3.3 Population Mean Reference
```python
{
    "name": "Population Mean",
    "type": "line",
    "data": [hr_norms["mean"]] * len(dates),
    "lineStyle": {"color": "#95a5a6", "width": 2, "type": "dotted"},
    "symbol": "none",
},
```

---

## 4. Data Series Styling

### 4.1 Primary Data Line
```python
{
    "name": "Heart Rate",
    "type": "line",
    "data": hr_values,
    "symbol": "circle",
    "symbolSize": 7,
    "lineStyle": {"color": "#3498db", "width": 2.5},
    "itemStyle": {"color": "#3498db"},
},
```

### 4.2 Trend Line (EWMA Smoothing)
```python
{
    "name": "7-Day Trend",
    "type": "line",
    "data": ewma_values,
    "symbol": "none",
    "lineStyle": {"color": "#2c3e50", "width": 2.5},
    "smooth": True,
},
```

### 4.3 Bar Chart with Gradient
```python
{
    "name": "Steps",
    "type": "bar",
    "data": steps_values,
    "itemStyle": {
        "color": {
            "type": "linear",
            "x": 0, "y": 0, "x2": 0, "y2": 1,
            "colorStops": [
                {"offset": 0, "color": "#3498db"},
                {"offset": 1, "color": "#2980b9"},
            ],
        },
        "borderRadius": [4, 4, 0, 0],  # Rounded top corners
    },
    "barMaxWidth": 25,
},
```

### 4.4 Forecast/Prediction Line
```python
{
    "name": "Forecast",
    "type": "line",
    "data": forecast_values,
    "lineStyle": {"color": "#27ae60", "width": 2.5, "type": "dashed"},
    "itemStyle": {"color": "#27ae60"},
    "symbol": "diamond",
    "symbolSize": 8,
},
```

### 4.5 Confidence Interval Band
```python
# Lower bound (invisible base)
{
    "name": "CI Lower",
    "type": "line",
    "data": lower_values,
    "lineStyle": {"opacity": 0},
    "areaStyle": {"opacity": 0},
    "symbol": "none",
    "stack": "confidence",
},
# Upper bound (shows the band)
{
    "name": "95% CI",
    "type": "line",
    "data": upper_diff_values,  # upper - lower for proper stacking
    "lineStyle": {"opacity": 0},
    "areaStyle": {"color": "rgba(46, 204, 113, 0.25)"},
    "symbol": "none",
    "stack": "confidence",
},
```

---

## 5. Gauge Charts

### 5.1 Semi-Circular Gauge (for scores 0-100)
```python
{
    "series": [{
        "type": "gauge",
        "startAngle": 180,
        "endAngle": 0,
        "min": 0,
        "max": 100,
        "splitNumber": 5,
        "radius": "90%",
        "center": ["50%", "70%"],
        "axisLine": {
            "lineStyle": {
                "width": 25,
                "color": [
                    [0.3, "#e74c3c"],   # 0-30: Red/Poor
                    [0.5, "#f39c12"],   # 30-50: Yellow/Fair
                    [0.7, "#3498db"],   # 50-70: Blue/Good
                    [1.0, "#27ae60"],   # 70-100: Green/Excellent
                ],
            },
        },
        "pointer": {
            "length": "55%",
            "width": 8,
            "itemStyle": {"color": "#2c3e50"},
        },
        "axisTick": {"length": 8, "lineStyle": {"color": "auto", "width": 2}},
        "splitLine": {"length": 15, "lineStyle": {"color": "auto", "width": 3}},
        "axisLabel": {
            "color": "#666",
            "fontSize": 11,
            "distance": -45,
            "formatter": "{value}",
        },
        "detail": {
            "valueAnimation": True,
            "formatter": "{value}",
            "fontSize": 28,
            "fontWeight": "bold",
            "color": color,
            "offsetCenter": [0, "20%"],
        },
        "title": {
            "offsetCenter": [0, "45%"],
            "fontSize": 14,
            "fontWeight": "bold",
            "color": color,
        },
        "data": [{"value": score, "name": "STATUS"}],
    }],
}
```

---

## 6. Radar Charts (Multi-Dimensional Comparison)

```python
{
    "radar": {
        "indicator": [
            {"name": "Component A", "max": 10},
            {"name": "Component B", "max": 10},
            {"name": "Component C", "max": 10},
        ],
        "shape": "polygon",
        "splitNumber": 5,
        "axisName": {"color": "#666", "fontSize": 10},
        "splitLine": {"lineStyle": {"color": SCIENTIFIC_COLORS["grid"]}},
        "splitArea": {
            "show": True,
            "areaStyle": {
                "color": ["rgba(39, 174, 96, 0.1)", "rgba(243, 156, 18, 0.1)", 
                          "rgba(230, 126, 34, 0.1)", "rgba(231, 76, 60, 0.1)"],
            },
        },
    },
    "series": [{
        "type": "radar",
        "data": [{
            "value": values,
            "name": "Score",
            "areaStyle": {"color": "rgba(52, 152, 219, 0.3)"},
            "lineStyle": {"color": "#3498db", "width": 2},
            "itemStyle": {"color": "#3498db"},
        }],
    }],
}
```

---

## 7. Polar Charts (24-Hour/Circadian)

```python
{
    "angleAxis": {
        "type": "category",
        "data": ["00:00", "01:00", ..., "23:00"],
        "startAngle": 90,
        "axisLabel": {"fontSize": 8, "interval": 2},
    },
    "radiusAxis": {
        "min": 0,
        "max": 100,
        "axisLabel": {"show": False},
        "splitLine": {"lineStyle": {"color": SCIENTIFIC_COLORS["grid"]}},
    },
    "polar": {"radius": ["20%", "75%"]},
    "series": [{
        "type": "bar",
        "data": hourly_values,
        "coordinateSystem": "polar",
        "itemStyle": {"color": {"type": "linear", ...}},
    }],
}
```

---

## 8. Scientific Documentation Requirements

### 8.1 Every Chart MUST Have:
1. **Title** with descriptive text
2. **Subtitle** with methodology/reference context
3. **Axis labels** with units
4. **Legend** (when multiple series)
5. **Tooltip** with formatted values

### 8.2 Below Each Chart, Include:
```python
st.markdown(
    "*Brief interpretation with clinical context. "
    "Reference to evidence-based guidelines.* "
    "*(Author et al., Year)*"
)
```

### 8.3 Citation Format
Always cite evidence-based sources:
- Task Force (1996) - HRV standards
- Shaffer & Ginsberg (2017) - HRV overview
- WHO guidelines - SpO₂, steps
- NSF (2015) - Sleep duration
- McEwen (1998) - Allostatic load

---

## 9. Age-Stratified Normative Data

When displaying physiological metrics, use age-stratified reference ranges:

```python
# Example: RMSSD norms by age
AGE_RMSSD_NORMS = {
    "20-29": {"p5": 20, "p25": 35, "mean": 45, "p75": 60, "p95": 90},
    "30-39": {"p5": 15, "p25": 28, "mean": 38, "p75": 52, "p95": 75},
    # ... etc
}

def _get_age_rmssd_norms(age: int) -> dict:
    """Return RMSSD norms for the given age."""
    if age < 30: return AGE_RMSSD_NORMS["20-29"]
    if age < 40: return AGE_RMSSD_NORMS["30-39"]
    # ... etc
```

---

## 10. EWMA Smoothing for Trend Lines

Use Exponential Weighted Moving Average for smooth trend visualization:

```python
def _ewma_smooth(data: np.ndarray, span: int = 7) -> np.ndarray:
    """Apply EWMA smoothing with NaN handling."""
    alpha = 2 / (span + 1)
    result = np.full_like(data, np.nan, dtype=float)
    last_valid = np.nan
    for i, val in enumerate(data):
        if not np.isnan(val):
            if np.isnan(last_valid):
                last_valid = val
            else:
                last_valid = alpha * val + (1 - alpha) * last_valid
        result[i] = last_valid
    return result
```

---

## 11. Export Requirements

Every plot MUST support export at highest quality:

| Format | Use Case | Quality |
|--------|----------|---------|
| **SVG** | Vector graphics, publications | Lossless |
| **PDF** | Print, journals | Vector |
| **PNG** | Web, presentations | 300+ DPI |
| **HTML** | Interactive sharing | Full interactivity |
| **CSV/JSON** | Data export | Raw values |

---

## 12. Chart Height Standards

| Chart Type | Recommended Height |
|------------|-------------------|
| Line/Bar trend | 380px |
| Gauge (semi-circular) | 280px |
| Radar chart | 280px |
| Polar/24-hour | 320px |
| Dual-axis complex | 400px |

---

## 13. Color Semantics

Maintain consistent color meanings across all charts:

| Meaning | Color | Hex |
|---------|-------|-----|
| **Excellent/Good/Low Risk** | Green | `#27ae60` |
| **Normal/Balanced** | Blue | `#3498db` |
| **Moderate/Caution** | Yellow/Orange | `#f39c12` |
| **Poor/High Risk** | Red | `#e74c3c` |
| **Trend lines** | Dark gray | `#2c3e50` |
| **Reference/Population** | Light gray | `#95a5a6` |
| **Grid lines** | Very light gray | `#ecf0f1` |

---

## 14. Function Naming Convention

Chart builder functions should follow this pattern:

```python
def _build_{metric}_{chart_type}_chart(
    dates: List[str],
    values: Optional[List[float]] = None,
    age: int = 35,  # For age-stratified norms
    title: str = "Default Title",
) -> Dict[str, Any]:
    """Build publication-quality {description} chart.
    
    References:
    - {Citation for methodology}
    - {Citation for reference values}
    
    Args:
        dates: Date labels for x-axis.
        values: Metric values.
        age: Subject age for normative context.
        title: Chart title.
        
    Returns:
        ECharts option dictionary.
    """
```

---

## 15. Checklist for New Charts

Before committing a new chart, verify:

- [ ] Title and subtitle present with methodology context
- [ ] All axes labeled with units
- [ ] Reference zones/thresholds included where applicable
- [ ] Age-stratified norms used (if physiological metric)
- [ ] EWMA trend line included (for time series)
- [ ] Tooltip shows formatted values with units
- [ ] Legend positioned at bottom
- [ ] Color semantics match project standards
- [ ] Caption below chart with scientific interpretation
- [ ] Citation(s) included for reference values
- [ ] Interactive zoom enabled
- [ ] Chart height appropriate for content
