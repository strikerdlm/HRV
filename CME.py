"""
Multi-event space weather calculator for Pythonista (iOS)
Fetches X-ray, proton, solar wind, and CME forecast data from NOAA SWPC
Computes arrival times for Bogotá, Colombia (UTC-5) and recommends EKG capture windows

Data sources (JSON indices):
  - GOES primary JSON products (X-ray, protons, etc.): /json/goes/primary/[web:33]
  - Real-time solar wind at L1: /products/solar-wind/plasma-1-day.json[web:6]
  - ENLIL CME time series (if available): /json/enlil_time_series.json[web:21]
"""

import requests
import datetime
import math

# ---- CONFIG ----

BASE_URL = "https://services.swpc.noaa.gov"

ENDPOINTS = {
    "xray_1day": f"{BASE_URL}/json/goes/primary/xrays-1-day.json",
    "proton_1day": f"{BASE_URL}/json/goes/primary/integral-protons-1-day.json",
    "solar_wind": f"{BASE_URL}/products/solar-wind/plasma-1-day.json",
    "enlil_forecast": f"{BASE_URL}/json/enlil_time_series.json",  # may not always exist
}

L1_EARTH_DISTANCE_KM = 1_500_000.0
BOGOTA_TZ = datetime.timezone(datetime.timedelta(hours=-5))


# ---- HELPER FUNCTIONS ----

def parse_iso_utc(ts: str) -> datetime.datetime:
    """Parse ISO 8601 timestamp with optional 'Z' suffix to aware UTC datetime."""
    if not isinstance(ts, str):
        raise ValueError(f"Expected ISO timestamp string, got {repr(ts)}")
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return datetime.datetime.fromisoformat(ts).astimezone(datetime.timezone.utc)


def utc_to_bogota(dt_utc: datetime.datetime) -> datetime.datetime:
    return dt_utc.astimezone(BOGOTA_TZ)


def format_dt(dt: datetime.datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S %Z")


def safe_float(val, default=float('nan')):
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


# ---- X-RAY ANALYSIS (PHOTONS) ----

def fetch_xray_data():
    """
    Fetch latest GOES X-ray flux for both bands (0.05–0.4 nm and 0.1–0.8 nm).

    xrays-1-day.json is a LIST OF DICTS, e.g.:
      [{"time_tag": "...", "flux": ..., "energy": "0.1-0.8nm", ...}, ...][web:13]
    """
    resp = requests.get(ENDPOINTS["xray_1day"], timeout=10)
    resp.raise_for_status()
    data = resp.json()

    if not isinstance(data, list):
        return None, None
    if len(data) == 0:
        return None, None

    short_band = None  # 0.05–0.4 nm
    long_band = None   # 0.1–0.8 nm

    # Walk from the end to get the most recent of each band
    for record in reversed(data):
        if not isinstance(record, dict):
            continue
        energy = record.get("energy", "")
        if short_band is None and energy == "0.05-0.4nm":
            short_band = record
        if long_band is None and energy == "0.1-0.8nm":
            long_band = record
        if short_band is not None and long_band is not None:
            break

    return short_band, long_band


def classify_xray_flux(flux_short, flux_long):
    """
    Classify X-ray flare level using GOES 1–8 Å band (0.1–0.8 nm) by preference,
    falling back to the short band if needed.[web:13]
    """
    fs = safe_float(flux_short)
    fl = safe_float(flux_long)
    # Choose the larger of the two channels as a proxy
    if math.isnan(fs) and math.isnan(fl):
        return "No data", "N/A"

    if math.isnan(fs):
        flux = fl
    elif math.isnan(fl):
        flux = fs
    else:
        flux = max(fs, fl)

    if flux <= 0:
        return "No data", "N/A"

    # Standard NOAA flare classes by 1–8 Å peak flux[web:13]
    if flux >= 1e-3:
        cls = f"X{flux/1e-3:.1f}"
        risk = "EXTREME ionospheric disturbance; high SEP/CME potential"
    elif flux >= 1e-4:
        cls = f"M{flux/1e-4:.1f}"
        risk = "Strong ionospheric effects; moderate SEP/CME risk"
    elif flux >= 1e-5:
        cls = f"C{flux/1e-5:.1f}"
        risk = "Minor ionospheric effects; low SEP risk"
    elif flux >= 1e-6:
        cls = f"B{flux/1e-6:.1f}"
        risk = "Background solar activity"
    else:
        cls = f"A{flux/1e-7:.1f}"
        risk = "Quiet Sun"

    return cls, risk


def analyze_xrays():
    """Analyze X-ray data and return status dict."""
    short_band, long_band = fetch_xray_data()
    if short_band is None and long_band is None:
        return {"status": "No X-ray data available"}

    # Use long band (0.1–0.8 nm) timing if available, else short band
    ref = long_band or short_band
    t_obs = parse_iso_utc(ref["time_tag"])

    flux_short = safe_float(short_band["flux"]) if short_band else float("nan")
    flux_long = safe_float(long_band["flux"]) if long_band else float("nan")

    cls, risk = classify_xray_flux(flux_short, flux_long)

    return {
        "status": "active",
        "time_utc": t_obs,
        "time_bogota": utc_to_bogota(t_obs),
        "class": cls,
        "flux_short": flux_short,  # 0.05–0.4 nm
        "flux_long": flux_long,    # 0.1–0.8 nm
        "risk": risk,
        "eta_note": "Photon events are effectively instantaneous: detection ≈ effect at Earth."
    }


# ---- PROTON ANALYSIS (SEPs, >10 MeV) ----

def fetch_proton_data():
    """
    Fetch GOES integral proton flux.

    integral-protons-1-day.json is a LIST OF DICTS with 'time_tag' and multiple
    energy channels per record.[web:33][web:73]
    """
    try:
        resp = requests.get(ENDPOINTS["proton_1day"], timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return None

    if not isinstance(data, list):
        return None
    if len(data) == 0:
        return None

    return data


def extract_p10_flux(record):
    """
    Try to extract >10 MeV proton flux from a single integral-proton record.

    Strategy:
      - Prefer keys containing '>=10', '10 MeV', 'p10'.
      - Otherwise, choose the maximum numeric field as a rough proxy.
    """
    if not isinstance(record, dict):
        return float("nan")

    ignore = {"time_tag", "satellite", "energy", "id", "data_time"}
    candidates = []

    for k, v in record.items():
        if k in ignore:
            continue
        if isinstance(v, (int, float, str)):
            val = safe_float(v, default=float("nan"))
        else:
            continue
        candidates.append((k, val))

    if len(candidates) == 0:
        return float("nan")

    priority = []
    others = []
    for k, v in candidates:
        name = str(k).lower()
        if ">=10" in name or "10 mev" in name or "p10" in name:
            priority.append((k, v))
        else:
            others.append((k, v))

    if len(priority) > 0:
        return priority[0][1]

    vals = [v for _, v in others if not math.isnan(v)]
    if len(vals) == 0:
        return float("nan")
    return max(vals)


def classify_sep_event(p10_flux):
    """
    Classify Solar Energetic Particle event based on >10 MeV proton flux (pfu),
    approximately using NOAA S-scale thresholds.[web:35]
    """
    if math.isnan(p10_flux) or p10_flux < 10:
        return "No SEP event", "Background radiation"
    elif p10_flux < 100:
        return "S1 (Minor)", "Small dose increase at altitude; minor satellite effects"
    elif p10_flux < 1000:
        return "S2 (Moderate)", "Elevated dose at high altitudes; possible HF comms issues"
    elif p10_flux < 10000:
        return "S3 (Strong)", "Radiation hazard to astronauts; significant aviation constraints"
    elif p10_flux < 100000:
        return "S4 (Severe)", "High radiation exposure; major satellite and aviation impacts"
    else:
        return "S5 (Extreme)", "Extreme radiation environment"


def analyze_protons():
    """Analyze proton data and return status dict."""
    data = fetch_proton_data()
    if data is None:
        return {"status": "No proton data available"}

    # Find most recent record with a valid time_tag
    ref = None
    for rec in reversed(data):
        if isinstance(rec, dict) and "time_tag" in rec:
            ref = rec
            break

    if ref is None:
        return {"status": "No usable proton record"}

    t_obs = parse_iso_utc(ref["time_tag"])
    p10 = extract_p10_flux(ref)
    cls, risk = classify_sep_event(p10)

    return {
        "status": "active",
        "time_utc": t_obs,
        "time_bogota": utc_to_bogota(t_obs),
        "class": cls,
        "flux_pfu": p10,
        "risk": risk,
        "eta_note": "SEPs at GOES (geostationary) are essentially concurrent with Earth exposure."
    }


# ---- SOLAR WIND ANALYSIS (L1 PLASMA, CMEs/HSS) ----

def fetch_solar_wind():
    """
    Fetch latest solar wind from L1 (DSCOVR, etc.).

    plasma-1-day.json format:
      [
        ["time_tag", "density", "speed", "temperature"],
        ["YYYY-MM-DDThh:mm:ssZ", density, speed, temperature],
        ...
      ][web:6]
    """
    resp = requests.get(ENDPOINTS["solar_wind"], timeout=10)
    resp.raise_for_status()
    data = resp.json()

    if not isinstance(data, list):
        return None
    if len(data) < 2:
        return None

    header = data[0]
    last_row = data[-1]
    if not isinstance(header, list):
        return None
    if not isinstance(last_row, list):
        return None

    return dict(zip(header, last_row))


def classify_solar_wind(speed, density):
    """Classify solar wind regime around L1."""
    if speed < 350:
        return "Slow solar wind", "Low geomagnetic activity"
    elif speed < 500:
        return "Normal solar wind", "Background to mildly disturbed"
    elif speed < 700:
        return "High-speed stream / weak CME", "Moderate storm potential"
    else:
        txt = "Strong CME shock / extreme stream"
        if density is not None and not math.isnan(density) and density > 20:
            txt += " with high density"
        return txt, "High storm potential"


def analyze_solar_wind():
    """Analyze solar wind and compute L1→Earth ETA."""
    sw = fetch_solar_wind()
    if sw is None:
        return {"status": "No solar wind data available"}

    t_meas = parse_iso_utc(sw["time_tag"])
    speed = safe_float(sw.get("speed", 0))
    density = safe_float(sw.get("density"))
    temp = safe_float(sw.get("temperature"))

    if speed <= 0 or math.isnan(speed):
        return {"status": "Invalid solar wind speed"}

    travel_sec = L1_EARTH_DISTANCE_KM / speed
    eta_utc = t_meas + datetime.timedelta(seconds=travel_sec)
    eta_bogota = utc_to_bogota(eta_utc)

    cls, risk = classify_solar_wind(speed, density)

    # Bulk kinetic energy per proton
    m_p = 1.6726219e-27  # kg
    v_m_s = speed * 1000.0
    energy_joule = 0.5 * m_p * v_m_s * v_m_s
    keV = energy_joule / 1.602176634e-16

    return {
        "status": "active",
        "measurement_time_utc": t_meas,
        "measurement_time_bogota": utc_to_bogota(t_meas),
        "speed_km_s": speed,
        "density_cm3": density,
        "temperature_K": temp,
        "class": cls,
        "risk": risk,
        "travel_minutes": travel_sec / 60.0,
        "eta_utc": eta_utc,
        "eta_bogota": eta_bogota,
        "proton_energy_keV": keV
    }


# ---- CME FORECAST (ENLIL) ----

def fetch_enlil_forecast():
    """Fetch WSA-ENLIL time series forecast, if available.[web:21]"""
    try:
        resp = requests.get(ENDPOINTS["enlil_forecast"], timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data
    except Exception:
        return None


def analyze_cme_forecast():
    """
    Parse ENLIL forecast for upcoming CME arrivals.

    JSON structure is model-specific; here we heuristically look for future times
    with elevated speed or density to flag possible arrivals.[web:21]
    """
    enlil = fetch_enlil_forecast()
    if enlil is None:
        return {"status": "No CME forecast available"}
    if len(enlil) < 2:
        return {"status": "No CME forecast available"}

    now = datetime.datetime.now(datetime.timezone.utc)
    future_events = []

    # Assume first row is header; subsequent rows are data
    for entry in enlil[1:]:
        if not isinstance(entry, list):
            continue
        if len(entry) < 2:
            continue
        try:
            t_str = entry[0]
            t_forecast = parse_iso_utc(t_str)
            if t_forecast <= now:
                continue

            speed = safe_float(entry[1])
            density = safe_float(entry[2]) if len(entry) > 2 else float("nan")

            if speed > 500 or (not math.isnan(density) and density > 15):
                future_events.append({
                    "time_utc": t_forecast,
                    "time_bogota": utc_to_bogota(t_forecast),
                    "speed_km_s": speed,
                    "density_cm3": density
                })
        except Exception:
            continue

    if len(future_events) == 0:
        return {"status": "No significant CME predicted in next 24–48 h"}

    earliest = min(future_events, key=lambda x: x["time_utc"])
    delta_h = (earliest["time_utc"] - now).total_seconds() / 3600.0

    return {
        "status": "CME arrival predicted",
        "eta_utc": earliest["time_utc"],
        "eta_bogota": earliest["time_bogota"],
        "hours_from_now": delta_h,
        "predicted_speed": earliest["speed_km_s"],
        "predicted_density": earliest["density_cm3"],
        "note": "Based on WSA-ENLIL model forecast (operational CME propagation model)."
    }


# ---- EKG RECOMMENDATION ENGINE ----

def ekg_recommendation(events):
    """Generate EKG monitoring recommendations based on combined event context."""
    recommendations = []

    # X-rays (photon events)
    xray = events.get("xray", {})
    if xray.get("status") == "active":
        cls = xray.get("class", "")
        if isinstance(cls, str) and cls.startswith("X"):
            recommendations.append(
                "IMMEDIATE: X-class flare detected. High probability of SEP/CME within hours. "
                "Begin continuous EKG monitoring now for acute autonomic responses."
            )
        elif isinstance(cls, str) and cls.startswith("M"):
            recommendations.append(
                "ALERT: M-class flare detected. Monitor for SEP arrival in next 1–6 hours. "
                "Prepare EKG device for potential session."
            )

    # SEPs (protons)
    proton = events.get("proton", {})
    if proton.get("status") == "active":
        flux = proton.get("flux_pfu", 0.0)
        if not math.isnan(flux) and flux >= 10:
            recommendations.append(
                f"ACTIVE SEP EVENT ({proton['class']}): Elevated radiation environment. "
                f"Recommended EKG capture during the event and for 24 h post-peak."
            )

    # Solar wind (L1 plasma / CME shock)
    sw = events.get("solar_wind", {})
    if sw.get("status") == "active":
        minutes = sw.get("travel_minutes", 999.0)
        speed = sw.get("speed_km_s", 0.0)
        if minutes < 10:
            recommendations.append(
                "IMMINENT: Solar wind disturbance arriving within 10 minutes. "
                "Start EKG capture NOW if studying acute magnetospheric coupling effects."
            )
        elif minutes < 60:
            recommendations.append(
                f"NEAR-TERM: Disturbance ETA in {minutes:.0f} min. "
                f"Begin EKG monitoring within next 30 min and continue 2–3 h post-arrival."
            )
        elif minutes < 180 and speed > 600:
            recommendations.append(
                f"ELEVATED STREAM: High-speed solar wind (ETA {minutes/60.0:.1f} h). "
                f"Plan EKG session starting 1 h before through 4 h after arrival."
            )

    # CME forecast (Sun→Earth lead)
    cme = events.get("cme_forecast", {})
    if cme.get("status") == "CME arrival predicted":
        hours = cme.get("hours_from_now", 999.0)
        if hours < 12:
            recommendations.append(
                f"CME FORECAST: Model predicts arrival in {hours:.1f} h. "
                f"Extended EKG protocol: start 2 h before, continue 6 h after arrival."
            )
        elif hours < 48:
            recommendations.append(
                f"CME EN ROUTE: Predicted arrival in {hours:.1f} h. "
                f"Recheck forecast in 12 h; prepare extended monitoring protocol."
            )

    if len(recommendations) == 0:
        recommendations.append(
            "BACKGROUND CONDITIONS: No immediate space-weather alerts. "
            "Routine baseline EKG capture recommended for control data."
        )

    return recommendations


# ---- MAIN ----

def main():
    print("=" * 60)
    print("SPACE WEATHER EKG MONITORING CALCULATOR")
    print("Location: Bogotá, Colombia (UTC-5)")
    print("Data source: NOAA SWPC")
    print("=" * 60)
    print()

    events = {}

    # X-ray analysis (photons)
    print("→ Analyzing X-ray flux...")
    events["xray"] = analyze_xrays()
    xr = events["xray"]
    if xr.get("status") == "active":
        print(f"  Time (Bogotá): {format_dt(xr['time_bogota'])}")
        print(f"  Class: {xr['class']}")
        print(f"  Risk: {xr['risk']}")
        print(f"  Note: {xr['eta_note']}")
    else:
        print(f"  {xr.get('status')}")
    print()

    # Proton analysis (SEPs)
    print("→ Analyzing energetic proton flux...")
    events["proton"] = analyze_protons()
    pr = events["proton"]
    if pr.get("status") == "active":
        print(f"  Time (Bogotá): {format_dt(pr['time_bogota'])}")
        print(f"  Event: {pr['class']}")
        flux = pr.get("flux_pfu", float("nan"))
        if not math.isnan(flux):
            print(f"  Approx >10 MeV flux: {flux:.2f} pfu")
        print(f"  Risk: {pr['risk']}")
        print(f"  Note: {pr['eta_note']}")
    else:
        print(f"  {pr.get('status')}")
    print()

    # Solar wind analysis (L1 plasma, CME/HSS)
    print("→ Analyzing solar wind at L1...")
    events["solar_wind"] = analyze_solar_wind()
    sw = events["solar_wind"]
    if sw.get("status") == "active":
        print(f"  Measurement (Bogotá): {format_dt(sw['measurement_time_bogota'])}")
        print(f"  Speed: {sw['speed_km_s']:.0f} km/s")
        dens = sw.get("density_cm3")
        if dens is not None and not math.isnan(dens):
            print(f"  Density: {dens:.1f} cm−3")
        print(f"  Classification: {sw['class']}")
        print(f"  Risk: {sw['risk']}")
        print(f"  L1→Earth travel time: {sw['travel_minutes']:.1f} minutes")
        print(f"  ETA at Earth (Bogotá): {format_dt(sw['eta_bogota'])}")
        print(f"  Bulk proton energy: {sw['proton_energy_keV']:.2f} keV")
    else:
        print(f"  {sw.get('status')}")
    print()

    # CME forecast analysis (model Sun→Earth)
    print("→ Checking CME forecast (WSA-ENLIL)...")
    events["cme_forecast"] = analyze_cme_forecast()
    cme = events["cme_forecast"]
    if cme.get("status") == "CME arrival predicted":
        print(f"  Predicted arrival (Bogotá): {format_dt(cme['eta_bogota'])}")
        print(f"  Time from now: {cme['hours_from_now']:.1f} hours")
        ps = cme.get("predicted_speed", float("nan"))
        if not math.isnan(ps):
            print(f"  Predicted speed: {ps:.0f} km/s")
        print(f"  {cme['note']}")
    else:
        print(f"  {cme.get('status')}")
    print()

    # ===== NEW: EXPECTED HIT TIMES (SUMMARY) =====
    print("=" * 60)
    print("EXPECTED IMPACT TIMES (Bogotá local)")
    print("=" * 60)

    # Photons (flare X-rays/EUV): effect is essentially at observation time
    if xr.get("status") == "active":
        print(f"- Photon/X-ray impact time: {format_dt(xr['time_bogota'])} "
              "(flare radiation already at Earth)")

    # SEPs: onset ≈ hit time at geostationary orbit / near-Earth
    if pr.get("status") == "active":
        print(f"- SEP (proton) onset time: {format_dt(pr['time_bogota'])} "
              "(energetic particle environment at Earth)")

    # L1 plasma / CME shock: ETA from L1 to magnetosphere
    if sw.get("status") == "active":
        print(f"- Solar-wind/CME plasma impact (from L1): {format_dt(sw['eta_bogota'])}")

    # Model Sun→Earth CME arrival (if available)
    if cme.get("status") == "CME arrival predicted":
        print(f"- Model CME arrival (Sun→Earth): {format_dt(cme['eta_bogota'])} "
              f"(~{cme['hours_from_now']:.1f} h from now)")

    print()

    # EKG recommendations
    print("=" * 60)
    print("EKG MONITORING RECOMMENDATIONS")
    print("=" * 60)
    recommendations = ekg_recommendation(events)
    for i, rec in enumerate(recommendations, 1):
        print(f"{i}. {rec}")
        print()

    print("=" * 60)
    print("ADVISORY: Research tool only, not a medical device.")
    print("Follow IRB/ethical guidelines for human-subject monitoring.")
    print("=" * 60)


if __name__ == "__main__":
    main()
