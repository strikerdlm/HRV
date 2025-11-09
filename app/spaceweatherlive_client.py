from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Mapping, Optional, Tuple

import re
import requests
from bs4 import BeautifulSoup
from statistics import mean, median


DEFAULT_TIMEOUT_S: float = 12.0
BASE_URL: str = "https://www.spaceweatherlive.com"
HEADERS: Mapping[str, str] = {
	"User-Agent": (
		"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
		"AppleWebKit/537.36 (KHTML, like Gecko) "
		"Chrome/122.0 Safari/537.36"
	),
	"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
	"Accept-Language": "en-US,en;q=0.9",
}


def _create_session() -> requests.Session:
	"""
	Create a configured requests.Session with sane defaults.
	"""
	s = requests.Session()
	s.headers.update(HEADERS)
	return s


def _parse_float(text: str) -> Optional[float]:
	"""
	Extract the first float-like number from text.
	Examples:
	- "Kp5-" -> 5.0
	- "Speed: 456 km/sec" -> 456.0
	"""
	if not isinstance(text, str):
		return None
	# Replace unicode minus with hyphen if present
	clean = text.replace("−", "-")
	# Remove thousands separators
	clean = clean.replace(",", " ")
	m = re.search(r"(-?\d+(?:\.\d+)?)", clean)
	return float(m.group(1)) if m else None


def _parse_int(text: str) -> Optional[int]:
	"""
	Extract the first integer number from text.
	"""
	val = _parse_float(text)
	return int(val) if val is not None else None


def _parse_utc_timestamp(text: str) -> Optional[datetime]:
	"""
	Parse timestamps of the form 'YYYY/MM/DD HH:MM' into UTC datetimes.
	"""
	if not isinstance(text, str):
		return None
	candidate = text.strip()
	if not candidate:
		return None
	for pattern in ("%Y/%m/%d %H:%M", "%Y-%m-%d %H:%M", "%d %b %Y %H:%M"):
		try:
			parsed = datetime.strptime(candidate, pattern)
		except ValueError:
			continue
		return parsed.replace(tzinfo=timezone.utc)
	return None


def _normalise_header_name(text: str) -> str:
	"""
	Normalise table header labels for dictionary lookups.
	"""
	if not isinstance(text, str):
		return ""
	return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


@dataclass(slots=True, frozen=True)
class CMERecord:
	cactus_id: str
	onset_time_utc: Optional[datetime]
	duration_hours: Optional[float]
	position_angle_deg: Optional[float]
	angular_width_deg: Optional[float]
	velocity_kms: Optional[float]
	velocity_variation_kms: Optional[float]
	velocity_min_kms: Optional[float]
	velocity_max_kms: Optional[float]
	halo_class: Optional[str]

	def to_dict(self) -> Dict[str, object]:
		return {
			"cactus_id": self.cactus_id,
			"onset_time_utc": self.onset_time_utc.isoformat() if self.onset_time_utc else None,
			"duration_hours": self.duration_hours,
			"position_angle_deg": self.position_angle_deg,
			"angular_width_deg": self.angular_width_deg,
			"velocity_kms": self.velocity_kms,
			"velocity_variation_kms": self.velocity_variation_kms,
			"velocity_min_kms": self.velocity_min_kms,
			"velocity_max_kms": self.velocity_max_kms,
			"halo_class": self.halo_class,
		}


@dataclass(slots=True, frozen=True)
class SIDCUrsigramReport:
	issued_utc: Optional[datetime]
	bulletin_excerpt: Optional[str]
	cme_highlights: Optional[str]

	def to_dict(self) -> Dict[str, Optional[str]]:
		return {
			"issued_utc": self.issued_utc.isoformat() if self.issued_utc else None,
			"bulletin_excerpt": self.bulletin_excerpt,
			"cme_highlights": self.cme_highlights,
		}


@dataclass(slots=True, frozen=True)
class KpForecastEntry:
	day_label: str
	min_kp: Optional[float]
	max_kp: Optional[float]


@dataclass(slots=True, frozen=True)
class FlareProbabilities:
	c_class_pct: Optional[float]
	m_class_pct: Optional[float]
	x_class_pct: Optional[float]


@dataclass(slots=True, frozen=True)
class SpaceWeatherSnapshot:
	timestamp_utc: datetime
	kp_forecast: List[KpForecastEntry]
	solar_wind_speed_kms: Optional[float]
	solar_wind_density_pcc: Optional[float]
	imf_bt_nt: Optional[float]
	imf_bz_nt: Optional[float]
	sunspot_number: Optional[int]
	f107_flux: Optional[float]
	flare_probabilities: FlareProbabilities
	cme_records: List[CMERecord] = field(default_factory=list)
	sidc_report: Optional[SIDCUrsigramReport] = None

	def to_dict(self) -> Dict[str, object]:
		return {
			"timestamp_utc": self.timestamp_utc.isoformat(),
			"kp_forecast": [
				{"day": k.day_label, "min_kp": k.min_kp, "max_kp": k.max_kp} for k in self.kp_forecast
			],
			"solar_wind_speed_kms": self.solar_wind_speed_kms,
			"solar_wind_density_pcc": self.solar_wind_density_pcc,
			"imf_bt_nt": self.imf_bt_nt,
			"imf_bz_nt": self.imf_bz_nt,
			"sunspot_number": self.sunspot_number,
			"f107_flux": self.f107_flux,
			"flare_probabilities": {
				"C": self.flare_probabilities.c_class_pct,
				"M": self.flare_probabilities.m_class_pct,
				"X": self.flare_probabilities.x_class_pct,
			},
			"cmes": [entry.to_dict() for entry in self.cme_records],
			"sidc_report": self.sidc_report.to_dict() if self.sidc_report else None,
			"cme_velocity_stats": self.cme_velocity_stats(),
		}

	def cme_velocity_stats(self) -> Dict[str, Optional[float]]:
		"""
		Compute summary statistics for CME velocities.
		"""
		if not self.cme_records:
			return {"count": 0, "mean": None, "median": None, "max": None}
		speeds = [entry.velocity_kms for entry in self.cme_records if entry.velocity_kms is not None]
		if not speeds:
			return {"count": len(self.cme_records), "mean": None, "median": None, "max": None}
		return {
			"count": len(speeds),
			"mean": float(mean(speeds)),
			"median": float(median(speeds)),
			"max": float(max(speeds)),
		}


def _fetch_html(session: requests.Session, path: str, timeout_s: float) -> str:
	resp = session.get(f"{BASE_URL}{path}", timeout=timeout_s)
	resp.raise_for_status()
	return resp.text


def _extract_kp_forecast_from_home(soup: BeautifulSoup) -> List[KpForecastEntry]:
	"""
	Parse the Kp-index forecast table from the home page snapshot when present.
	"""
	results: List[KpForecastEntry] = []
	# Look for a table with header containing "Kp-index forecast"
	header_el = soup.find(lambda tag: tag.name in ("h4", "h5", "h6") and "Kp-index forecast" in tag.get_text(strip=True))
	if not header_el:
		return results
	# The table is likely the next <table> after the header
	table = header_el.find_next("table")
	if not table:
		return results
	tbody = table.find("tbody") or table
	for tr in tbody.find_all("tr"):
		cells = [td.get_text(" ", strip=True) for td in tr.find_all(("td", "th"))]
		if len(cells) >= 3:
			day = cells[0]
			min_kp = _parse_float(cells[1])
			max_kp = _parse_float(cells[2])
			results.append(KpForecastEntry(day_label=day, min_kp=min_kp, max_kp=max_kp))
	return results


def _extract_realtime_solar_wind_from_home(soup: BeautifulSoup) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
	"""
	Parse the real-time solar wind speed, density and IMF Bt/Bz from the home page panels.
	Returns (speed_kms, density_pcc, bt_nt, bz_nt).
	"""
	text = soup.get_text(" ", strip=True)
	# Speed
	speed = None
	m_speed = re.search(r"Speed:\s*([0-9]+(?:\.[0-9]+)?)\s*km/sec", text, re.IGNORECASE)
	if m_speed:
		speed = float(m_speed.group(1))
	# Density
	density = None
	m_density = re.search(r"Density:\s*([0-9]+(?:\.[0-9]+)?)\s*p/cm3", text, re.IGNORECASE)
	if m_density:
		density = float(m_density.group(1))
	# Bt
	bt = None
	m_bt = re.search(r"Bt:\s*([\-−]?[0-9]+(?:\.[0-9]+)?)\s*nT", text, re.IGNORECASE)
	if m_bt:
		bt = _parse_float(m_bt.group(1))
	# Bz
	bz = None
	m_bz = re.search(r"Bz:\s*([\-−]?[0-9]+(?:\.[0-9]+)?)\s*nT", text, re.IGNORECASE)
	if m_bz:
		bz = _parse_float(m_bz.group(1))
	return speed, density, bt, bz


def _extract_flare_probabilities(soup: BeautifulSoup) -> FlareProbabilities:
	"""
	Parse C/M/X flare probabilities from the Solar activity page.
	"""
	# Look for a table near "Flare probability"
	header_el = soup.find(lambda tag: tag.name in ("h4", "h5", "h6") and "Flare probability" in tag.get_text(strip=True))
	if not header_el:
		# Try generic text search
		header_el = soup.find(string=re.compile(r"Flare probability", re.IGNORECASE))
		if header_el:
			header_el = header_el.parent
	c_val = m_val = x_val = None
	if header_el:
		table = header_el.find_next("table")
		if table:
			tbody = table.find("tbody") or table
			for tr in tbody.find_all("tr"):
				cells = [td.get_text(" ", strip=True) for td in tr.find_all(("td", "th"))]
				if not cells:
					continue
				row_name = cells[0].strip().lower()
				if row_name.startswith("c-class") and len(cells) > 1:
					c_val = _parse_float(cells[1])
				elif row_name.startswith("m-class") and len(cells) > 1:
					m_val = _parse_float(cells[1])
				elif row_name.startswith("x-class") and len(cells) > 1:
					x_val = _parse_float(cells[1])
	return FlareProbabilities(c_class_pct=c_val, m_class_pct=m_val, x_class_pct=x_val)


def _extract_latest_cmes(soup: BeautifulSoup) -> List[CMERecord]:
	"""
	Parse the CACTus latest CME table into CMERecord entries.
	"""
	target_heading = soup.find(
		lambda tag: tag.name in ("h2", "h3", "h4") and "latest cmes" in tag.get_text(strip=True).lower()
	)
	table = target_heading.find_next("table") if target_heading else soup.find("table")
	if not table:
		return []
	header_map: Dict[str, int] = {}
	header_rows = table.find_all("tr")
	for tr in header_rows[:2]:
		cells = tr.find_all(["th", "td"])
		for idx, cell in enumerate(cells):
			name = _normalise_header_name(cell.get_text(" ", strip=True))
			if name and name not in header_map:
				header_map[name] = idx

	def _cell(cells: List[str], *keys: str) -> Optional[str]:
		for key in keys:
			idx = header_map.get(key)
			if idx is not None and idx < len(cells):
				return cells[idx]
		return None

	results: List[CMERecord] = []
	for tr in table.find_all("tr"):
		cells = [td.get_text(" ", strip=True) for td in tr.find_all(("td", "th"))]
		if not cells:
			continue
		cme_id_raw = _cell(cells, "cme")
		if not cme_id_raw or not re.match(r"^\d+$", cme_id_raw.strip()):
			continue
		onset_text = _cell(cells, "onset time")
		duration_text = _cell(cells, "duration")
		angle_text = _cell(cells, "angle")
		width_text = _cell(cells, "angular width", "width")
		velocity_text = _cell(cells, "velocity")
		variation_text = _cell(cells, "variation")
		min_text = _cell(cells, "min", "min.")
		max_text = _cell(cells, "max", "max.")
		halo_text = _cell(cells, "halo", "halo?")
		record = CMERecord(
			cactus_id=cme_id_raw.strip(),
			onset_time_utc=_parse_utc_timestamp(onset_text or ""),
			duration_hours=_parse_float(duration_text or ""),
			position_angle_deg=_parse_float(angle_text or ""),
			angular_width_deg=_parse_float(width_text or ""),
			velocity_kms=_parse_float(velocity_text or ""),
			velocity_variation_kms=_parse_float(variation_text or ""),
			velocity_min_kms=_parse_float(min_text or ""),
			velocity_max_kms=_parse_float(max_text or ""),
			halo_class=halo_text.strip() if halo_text else None,
		)
		results.append(record)
	return results


def _extract_sidc_ursigram(soup: BeautifulSoup) -> SIDCUrsigramReport:
	"""
	Extract CME-related commentary from the SIDC Ursigram bulletin.
	"""
	target = soup.find(
		lambda tag: tag.name in ("article", "div", "section")
		and "ursigram" in tag.get_text(strip=True).lower()
	)
	text_block = target.get_text("\n", strip=True) if target else soup.get_text("\n", strip=True)
	if not text_block:
		return SIDCUrsigramReport(issued_utc=None, bulletin_excerpt=None, cme_highlights=None)
	lines = [line.strip() for line in text_block.splitlines() if line.strip()]
	issued_candidate = next((line for line in lines if re.search(r"\b\d{4}/\d{2}/\d{2}\b", line)), None)
	issued_dt = _parse_utc_timestamp(issued_candidate or "")
	cme_lines = [line for line in lines if "cme" in line.lower()]
	cme_excerpt = " ".join(cme_lines[:3]) if cme_lines else None
	excerpt = " ".join(lines[:6]) if lines else None
	return SIDCUrsigramReport(issued_utc=issued_dt, bulletin_excerpt=excerpt, cme_highlights=cme_excerpt)


def _extract_todays_sun_metrics(soup: BeautifulSoup) -> Tuple[Optional[int], Optional[float]]:
	"""
	Parse Today's Sun panel for Sunspot number and 10.7 cm flux.
	"""
	header_el = soup.find(lambda tag: tag.name in ("h4", "h5", "h6") and "Today's Sun" in tag.get_text(strip=True))
	sunspot_number = None
	f107 = None
	if header_el:
		table = header_el.find_next("table")
		if table:
			tbody = table.find("tbody") or table
			for tr in tbody.find_all("tr"):
				cells = [td.get_text(" ", strip=True) for td in tr.find_all(("td", "th"))]
				if len(cells) >= 2:
					label = cells[0].strip().lower()
					value_text = cells[1]
					if "sunspot number" in label:
						sunspot_number = _parse_int(value_text)
					elif "10.7cm" in label or "10.7 cm" in label or "radio flux" in label:
						f107 = _parse_float(value_text)
	return sunspot_number, f107


def fetch_spaceweatherlive_snapshot(timeout_s: float = DEFAULT_TIMEOUT_S) -> SpaceWeatherSnapshot:
	"""
	Fetch a minimal, robust snapshot of relevant SpaceWeatherLive metrics for HRV comparison.

	Returns
	-------
	SpaceWeatherSnapshot
		Parsed metrics including Kp forecast, solar wind speed/density, IMF Bt/Bz,
		sunspot number, F10.7 flux, and C/M/X flare probabilities.

	Raises
	------
	requests.RequestException
		If any HTTP request fails (network errors, timeouts, non-2xx).
	ValueError
		If required sections cannot be parsed at all from the pages.
	"""
	session = _create_session()

	home_html = _fetch_html(session, "/", timeout_s)
	home_soup = BeautifulSoup(home_html, "html.parser")

	kp_forecast = _extract_kp_forecast_from_home(home_soup)
	speed, density, bt, bz = _extract_realtime_solar_wind_from_home(home_soup)

	# Solar activity details (probabilities, Today's Sun)
	solar_activity_html = _fetch_html(session, "/en/solar-activity.html", timeout_s)
	solar_soup = BeautifulSoup(solar_activity_html, "html.parser")
	flare_probs = _extract_flare_probabilities(solar_soup)
	sunspot_number, f107 = _extract_todays_sun_metrics(solar_soup)

	# CACTus CME detections
	cme_html = _fetch_html(session, "/en/solar-activity/latest-cmes.html", timeout_s)
	cme_soup = BeautifulSoup(cme_html, "html.parser")
	cme_records = _extract_latest_cmes(cme_soup)

	# SIDC Ursigram bulletin
	ursigram_html = _fetch_html(session, "/en/reports/sidc-ursigram.html", timeout_s)
	ursigram_soup = BeautifulSoup(ursigram_html, "html.parser")
	sidc_report = _extract_sidc_ursigram(ursigram_soup)

	# Basic sanity: allow partial data, but require at least one core section
	if not kp_forecast and all(
		v is None for v in (speed, density, bt, bz, sunspot_number, f107)
	) and not cme_records:
		raise ValueError("Failed to parse any SpaceWeatherLive metrics; page structure may have changed.")

	return SpaceWeatherSnapshot(
		timestamp_utc=datetime.now(timezone.utc),
		kp_forecast=kp_forecast,
		solar_wind_speed_kms=speed,
		solar_wind_density_pcc=density,
		imf_bt_nt=bt,
		imf_bz_nt=bz,
		sunspot_number=sunspot_number,
		f107_flux=f107,
		flare_probabilities=flare_probs,
		cme_records=cme_records,
		sidc_report=sidc_report,
	)


