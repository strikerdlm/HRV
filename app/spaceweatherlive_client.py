from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Mapping, Optional, Tuple

import re
import requests
from bs4 import BeautifulSoup


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

	# Basic sanity: allow partial data, but require at least one core section
	if not kp_forecast and all(v is None for v in (speed, density, bt, bz, sunspot_number, f107)):
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
	)


