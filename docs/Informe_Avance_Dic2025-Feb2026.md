# Informe de Avance — Mission Control / Flight Surgeon (HRV Analysis Suite)

**Autor:** Dr Diego Malpica MD  
**Período:** 1 de diciembre de 2025 — 9 de febrero de 2026  
**Destinatario:** Director del proyecto  
**Fecha del informe:** 9 de febrero de 2026  

---

## 1. Resumen ejecutivo

En el período reportado el proyecto pasó de la **versión 1.7.x** (inicios de diciembre 2025) a la **versión 1.15.0** (9 de febrero de 2026). Se consolidó una aplicación dual: **Streamlit (Research/Operational)** y un **frontend moderno TypeScript/Next.js** con API FastAPI, orientado a monitoreo de tripulación, medicina aeroespacial y entornos análogos (Antártida, altitud, EVA). Los avances se agrupan en: (1) motor de scheduling y rendimiento humano (IHPI, SAFTE, EVA Go/No-Go), (2) nuevos módulos fisiológicos (hidratación/termorregulación, SMS fisiológico, riesgo de trayectoria, VT/DFA-α1), (3) consola Flight Surgeon (nutrición, agua, altitud, ambiente extremo), (4) frontend Next.js con dashboards operativos y de investigación, (5) calidad de gráficos y UX (ECharts, ejes dinámicos, referencias científicas), y (6) estabilidad y rendimiento (modos Operational/Research, caché, tests).

---

## 2. Período y versiones (verificable)

| Métrica | Valor |
|--------|--------|
| **Versión inicial (período)** | 1.7.x (dic 2025) |
| **Versión final** | **1.15.0** (9 feb 2026) |
| **Releases en el período** | ~60+ entradas de CHANGELOG (1.7.x → 1.15.0) |
| **Rango de fechas CHANGELOG** | 2025-12-03 … 2026-02-09 |

Todas las fechas y versiones son comprobables en `CHANGELOG.md` del repositorio.

---

## 3. Métricas verificables del proyecto

| Métrica | Valor | Dónde verificar |
|--------|--------|------------------|
| **Tests unitarios (pytest)** | ~330+ casos en 28 archivos | `tests/test_*.py` |
| **Módulos Python principales (`app/`)** | ~80+ módulos (.py) | `app/*.py` y subcarpetas |
| **Páginas/rutas frontend (Next.js)** | 20+ rutas bajo `research/`, `scheduling/`, etc. | `frontend/src/app/` |
| **Componentes React/TS** | 15+ componentes (gauges, dashboards, paneles) | `frontend/src/components/` |
| **Endpoints API (FastAPI)** | 15+ bajo `/api/` y `/api/research/*` | `api/main.py`, `api/research_endpoints.py` |
| **Nuevos módulos científicos (período)** | ≥8 (scheduling_core, hydration_thermoregulation, physiological_sms, trajectory_risk, vt_analysis, environment_calculators, etc.) | `app/*.py` + CHANGELOG |
| **Tests añadidos en el período** | ≥107 (p. ej. test_scheduling_core, test_hydration_thermoregulation, test_physiological_sms, test_environment_calculators) | `tests/` + CHANGELOG |

---

## 4. Desarrollo por característica (solo avances del período)

### 4.1 Scheduling y rendimiento humano (IHPI / EVA / SAFTE)

- **Sistema de Crew Scheduling & Human Performance (v1.9.0, 29 dic 2025)**  
  - Módulos: `scheduling_core.py`, `scheduling_engine.py`, `scheduling_tab.py`.  
  - IHPI (Integrated Human Performance Indicator) de 8 componentes: SAFTE, PVT, alineación circadiana, HRV (lnRMSSD z), hidratación, energía, somnolencia, tarea específica.  
  - Matriz EVA Go/No-Go con puertas duras (SAFTE&lt;70, KSS≥8, sueño&lt;6 h, etc.) y zona HOLD 70–79.  
  - Tests: `tests/test_scheduling_core.py` (49 casos).

- **Frontend Scheduling (v1.9.16, 2 feb 2026)**  
  - App operativa en `/scheduling`: Status Dashboard (IHPI por tripulante), Schedule (actividades diarias), Crew Management (CRUD), Performance (IHPI y Go/No-Go).  
  - Editor de perfil en 5 secciones (Identity, Operational, Biometrics, Lifestyle, Medical).  
  - Selector de misión (Mission 1 / Mission 2) con base de datos por misión.

- **Integración SAFTE/FRMS y estabilidad (dic 2025)**  
  - Parámetros de riesgo (IHPI/EVA) actualizables solo con botón “Calculate”; previsión 24 h bajo demanda; uso de métricas Garmin ya importadas sin re-pedir credenciales.  
  - FRMS v2: Crew Risk Board, export CSV/JSON, decision log para auditoría.

### 4.2 Espacio y clima (Space Weather, METAR, ambiente extremo)

- **Space Weather y EVA (dic 2025)**  
  - Dashboards EVA Radiation (barras normalizadas, zonas S/G) y Space Weather en tiempo real (gauges C/M/X flare, F10.7, CMEs).  
  - Semáforo EVA unificado: clearance Flight Surgeon + matriz radiación + escalas NOAA S/G, con estado CAUTION entre MONITOR y NO-GO.  
  - Auto-fetch NOAA SWPC para matriz de riesgo de radiación EVA.

- **METAR y monitoreo ambiental (v1.13.0, 7 feb 2026)**  
  - METAR decodificado en tiempo real (FAA AviationWeather.gov) con selector de estación (SKBO, SAWE, SCRM, etc.), gauge de viento, categoría de vuelo (VFR/MVFR/IFR/LIFR).  
  - ICE Station Monitor: 8 sensores simulados (temp, humedad, CO2, presión, PM2.5, ruido, luz, O2) para estación análoga/Antártida.  
  - Calculadoras: Wind Chill (NWS 2001), tiempo de congelación, WBGT (ISO 7243), Heat Index; integración OpenWeatherMap.  
  - API: `GET /api/research/metar/{icao}`, `GET /api/research/weather/{city}`, `GET /api/research/environment/ice-station`, `POST /api/research/environment/calculators`.

- **Modelo de jet lag (v1.13.0)**  
  - Resincronización circadiana (Waterhouse, Arendt): asimetría este/oeste, curva de recuperación, factor de rendimiento y modificador de readiness (±6 pts) integrado en el modelo operativo.

### 4.3 Módulos fisiológicos nuevos (backend + API)

- **Hidratación y termorregulación (v1.14.0, 9 feb 2026)**  
  - `hydration_thermoregulation.py`: tasa de sudor (6 niveles de actividad, Sawka et al.), ajuste WBGT (ISO 7243), temperatura central, Physiological Strain Index (PhSI), decremento de rendimiento (Cheuvront & Kenefick), clasificación de deshidratación, modificador de readiness para IHPI.  
  - Frontend: panel con 6 gauges tipo anillo (SVG), integración en Scheduling Readiness y Research Physiological Readiness.  
  - Tests: 40 casos en `tests/test_hydration_thermoregulation.py`.

- **SMS fisiológico (v1.12.0, 7 feb 2026)**  
  - `physiological_sms.py`: modificadores de PA/temperatura (ACC/AHA 2017, criterios clínicos), matrices SMS EVA (5×5, ICAO Doc 9859) y Flight (4×5, MIL-STD-882E), detección de riesgo G-LOC, integración USAF crew rest.  
  - API: `POST /api/research/readiness/{user_id}/vitals`, `GET /api/research/sms/eva`, `GET /api/research/sms/flight`.  
  - Páginas: Research Physiological Readiness (vitals, waterfall, heatmaps EVA/Flight), Scheduling Readiness (paneles Go/No-Go).  
  - Tests: 36 casos en `tests/test_physiological_sms.py`.

- **Riesgo de trayectoria / alarma de carga alostática (v1.11.0, 5 feb 2026)**  
  - `trajectory_risk.py`: tendencias EWMA 7 días (lnRMSSD, HR en reposo, sueño, DFA-α1), SWC (Plews, Buchheit), Physiological Strain Index compuesto, clasificación IMPROVING → CRITICAL, detección de riesgo compuesto (sueño+HRV), modificador de readiness (±8 pts) en el modelo de rendimiento operativo.

- **Estimación de umbral ventilatorio (VT) por DFA-α1 (v1.10.0, 5 feb 2026)**  
  - `vt_analysis.py`: DFA-α1, ventana deslizante 120 s, detección multi-parámetro (DFA-α1 60% + reserva de FC 30% + frecuencia respiratoria 10%), zonas de intensidad, corrección de artefactos.  
  - Página Research: `/research/ventilatory-threshold` con gráficos ECharts y referencias (Eronen, Gronwald, Rogers).  
  - API: `GET /api/research/vt/demo`, `POST /api/research/vt/analyze`.  
  - Integración: contribución VT como modificador acotado (±5 pts) en el modelo de readiness.

- **Calculadoras de ambiente (v1.13.0)**  
  - Tests: 31 casos en `tests/test_environment_calculators.py` (wind chill, WBGT, heat index, frostbite, clasificaciones frío/calor).

### 4.4 NASA Flight Surgeon Console (v1.15.0, 9 feb 2026)

- **Componente:** `frontend/src/components/flight-surgeon-console.tsx`.  
- **Pestañas:**  
  - **Nutrition:** BMR Mifflin-St Jeor, TEE con multiplicadores (PAL NASA JSC-63555, frío Castellani & Young, altitud Butterfield), macronutrientes NASA-STD-3001, micronutrientes (Smith & Zwart).  
  - **Water:** Requerimiento diario (IOM baseline, actividad Sawka, altitud, frío), guía de electrolitos.  
  - **Altitude Physiology:** SpO2/FC en reposo por altitud, reducción VO2max, aclimatación, Lake Louise (AMS), prevención lesión por frío (WMS 2019).  
  - **Overview:** Resumen de valoración, indicadores de riesgo, protocolo de monitoreo (10 ítems), umbrales crew-care (peso, USG, SpO2, FC, RMSSD, sueño).  
- **Visualizaciones:** 5 gráficos ECharts (Energy Expenditure, Macronutrient Radar, Water Stacked Bar, Altitude Physiology dual-axis, Environmental Stress Heatmap) en paneles flotantes expandibles.  
- Referencias científicas integradas (NASA-STD-3001 Vol. 2 Rev B, Lane, Smith & Zwart, Castellani, Butterfield, Roach, IOM, Freund, etc.).

### 4.5 Frontend TypeScript/Next.js y API

- **Arranque (v1.9.14, 30 ene 2026)**  
  - Frontend en `frontend/`: cliente API (`lib/api.ts`, `lib/research-api.ts`), dashboard, Research Hub (Space Weather, HRV, correlaciones sol-HRV, Garmin), componentes ECharts según estándares del proyecto.  
  - Backend FastAPI: `/api/health`, `/api/users`, `/api/experiments`, `/api/space-weather`, `/api/research/*` (space-weather/current, hrv/analyze, correlations, garmin).  
  - Script: `start-frontend.ps1` (FastAPI + Next.js). Puertos: API 8180, frontend 3100.

- **Páginas Research (v1.9.15–1.9.17)**  
  - Time Series, Frequency, Nonlinear, HRF, Windowed, Readiness, ANS Tests, Fatigue, Circadian, Population Norms, Unified Timeline, Export Center, Science/References.  
  - Tests ANS: ratio 30:15, Valsalva, E:I respiración profunda con gauges e interpretación.  
  - Garmin: auto-load credentials (localStorage), sincronización opcional al cargar, series 30 días (HRV, RHR, sueño, SpO2, estrés, respiración), scatter de correlaciones, arquitectura de sueño.

- **Deprecación Reflex:** Eliminado Reflex v2 en favor del frontend Next.js (reflex_app/, Dockerfile.reflex, requirements_reflex.txt eliminados según CHANGELOG).

### 4.6 Gráficos y visualización (publication-quality)

- **Reglas críticas (dic 2025)**  
  - Helper `_auto_axis_bounds()` para que ningún gráfico recorte datos con min/max fijos.  
  - Fuentes y textos en color oscuro (#1a1a1a), no grises claros.  
  - Gauges: estilo anillo SVG (dos anillos, número centrado), no speedometer ECharts para dashboards modernos.

- **Bloques actualizados con ECharts de calidad publicación:**  
  - HRV × Actividad (series temporales, dispersión con regresión y correlación).  
  - Historial de valoraciones (fatiga/somnolencia, PANAS).  
  - Radiación (dosis con zonas NASA-STD-3001).  
  - Estrés/PNS, duración de sueño (NSF 7–9 h).  
  - Actividad y movimiento (WHO 8k–10k pasos), FC y estrés, sueño y recuperación, respiración y SpO2, Body Battery.  
  - Historial HRV: RMSSD/SDNN dual-axis, tendencia FC, LF/HF, índices autonómicos, lnRMSSD con bandas de referencia.  
  - HRV en perfil: RMSSD con rangos por edad, tachograma RR, PSD, histograma RR.  
  - Exportación: PNG/SVG/PDF/HTML/spec JSON desde ECharts.

### 4.7 Experiencia de usuario y estabilidad (Streamlit)

- **Modos Operational vs Research (v1.8.41–1.8.45)**  
  - Entradas: `operational_app.py`, `research_app.py`. Operational: perfil + espacio sin correlaciones/ML pesados; Research: HRV/HRF, NOAA, correlaciones, ML.  
  - Bloqueos en performance_utils para que en Operational no se activen descargas ni cómputos pesados.

- **Rendimiento y caché**  
  - Caché por hash (datos + configuración) para reutilizar resultados de HRV; carga de perfil sin payloads RR grandes; RR Library Loader y “Load + Analyze”; persistencia de uploads en sesión.  
  - Progreso visual: HRV (hrv_progress.py) y Space Weather (space_weather_progress.py) con pasos y tiempo.  
  - Modo “low-end”: toggles para espectrograma, no lineal, ML, ventanas, dominio frecuencia; toggles para NOAA, DONKI, Space Weather, GPT.  
  - Parámetro por defecto de puntos en gráficos: 500; downsampling antes de listas para Time Series y espectrograma.

- **Espacio y perfil**  
  - Space Weather/NOAA: carga desde caché primero; fetch bajo demanda; formularios para evitar reruns; timeouts acotados.  
  - User Profile: navegación por selectbox en lugar de tabs anidados para evitar renderizado completo en cada rerun; Garmin autofill para sueño/chronotype en Profile Tools y NASA Nutrition; timezone Bogotá (UTC-5) y “hours since waking” automático.

- **Streamlit**  
  - Versión fijada 1.36.0; `fileWatcherType = "poll"` para OneDrive; `fastReruns = false`; CORS restrictivo en Reflex (antes de deprecar).  
  - Correcciones: expansores anidados sustituidos por `<details>` o secciones; SessionInfo/toast mitigados con CSS y configuración.

### 4.8 Otras funcionalidades del período

- **Polar H10 BLE (v1.8.84):** Grabación de intervalos RR en tiempo real vía BLE (Polar H10/H9/OH1, Garmin HRM, Wahoo TICKR), formato una línea por RR (ms), sección en User Profile para invitados y usuarios.  
- **Agentic Reports (v1.8.83):** Informes “Graduate” y “Doctoral” con GPT-5.2 (code_interpreter, web_search, high reasoning), recopilación de perfil/HRV/Profile Tools, fallback local si API no disponible.  
- **Advanced HRV Analytics (v1.8.82):** Estadística descriptiva, normalidad, comparaciones, referencias por edad, tendencias, anomalías, patrones, integración Garmin, soporte de decisión clínica con semáforos.  
- **Wearable Analytics (v1.8.81):** Body Battery (Holt-Winters), Allostatic Load, ritmo circadiano, predicción de estrés, recuperación.  
- **Radiation Exposure (v1.8.80):** 10 entornos de radiación, dosis acumulada, EVA Go/No-Go con espacio, NASA STD-3001.  
- **Space Analytics (v1.8.54+):** Pestaña dedicada HRV/HRF vs NOAA; ventanas de influencia CME (DONKI); correlaciones baseline/evento/recuperación; ML (ElasticNet, RF, XGBoost, LightGBM, SHAP); formularios y consola de cómputo para evitar “fade”.  
- **Profile Tools Engine (v1.8.23):** Recovery, readiness, SAFTE, HRV personalizado, previsión de rendimiento; UI en Clinical Profile.  
- **Métricas HRV ampliadas (v1.8.68):** LnRMSSD, CVI, CSI, pNNx, SDANN, SDNNi, TINN mejorado; gauge_builder con umbrales.  
- **Garmin:** Integración Vivosmart 5 (FIT/JSON), tabla `garmin_daily_metrics`, batch uploads, gauges por dominio (actividad, FC/estrés, sueño, SpO2/respiración, Body Battery).  
- **Polar AccessLink (v1.8.5):** OAuth, VO2max, tablas `polar_credentials` y `vo2max_history`.  
- **PANAS (v1.8.3):** Escala 20 ítems, EN/ES, gauges y tendencias en historial de valoraciones.  
- **Workspaces por misión (v1.8.28):** `crew/Mission 1/`, `crew/Mission 2/` con DB y subjects; predictor de rendimiento operativo (SAFTE+HRV) con GO/CAUTION/NO-GO.  
- **Schema de perfil (v1.12.0):** Columnas para PA/temperatura basal y tiempos de medición para SMS fisiológico.

---

## 5. Resumen técnico

- **Stack:** Python 3.12, Streamlit 1.36.0, FastAPI, Next.js/TypeScript, ECharts, SQLite por usuario/misión, conda `hrv-py312`.  
- **Calidad:** CHANGELOG con referencias científicas (APA/DOI) en módulos nuevos; tests añadidos para scheduling, hidratación, SMS fisiológico, calculadoras de ambiente; reglas de gráficos en `.cursor/rules/plots.mdc` y RULE.md.  
- **Seguridad/robustez:** CORS restrictivo; timeouts en todas las llamadas de red; sin API keys en código (uso de `.env`); validación de entradas y manejo de errores explícito.

---

## 6. Referencias de verificación

- **Changelog:** `CHANGELOG.md` (formato Keep a Changelog; versiones 1.7.x–1.15.0).  
- **Arquitectura:** `WARP.md`, `README.md`, `docs/Manual.md`.  
- **Tests:** `pytest tests/` (ejecutar en entorno `hrv-py312`).  
- **Frontend:** `frontend/` (Next.js), `start-frontend.ps1`.  
- **API:** `api/main.py`, `api/research_endpoints.py`.

---

*Informe generado a partir del CHANGELOG y estructura del repositorio. Métricas de tests y archivos corresponden al estado del código en el período indicado.*
