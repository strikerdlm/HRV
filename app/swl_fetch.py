from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

from .spaceweatherlive_client import fetch_spaceweatherlive_snapshot
from .spaceweather_openai_fallback import extract_spaceweather_with_openai
import requests


def _fallback_openai_fetch() -> Optional[dict]:
	"""
	Try the OpenAI fallback by first downloading the same pages and asking the model to parse them.
	"""
    try:
        home_resp = requests.get("https://www.spaceweatherlive.com/", timeout=12)
        solar_resp = requests.get("https://www.spaceweatherlive.com/en/solar-activity.html", timeout=12)
        home_resp.raise_for_status()
        solar_resp.raise_for_status()
        snapshot = extract_spaceweather_with_openai(
            {"home": home_resp.text, "solar_activity": solar_resp.text}
        )
        return snapshot.to_dict() if snapshot else None
    except requests.RequestException:
        return None


def main() -> None:
	parser = argparse.ArgumentParser(description="Fetch a SpaceWeatherLive snapshot and save to JSON.")
	parser.add_argument(
		"--output",
		type=Path,
		default=Path(__file__).resolve().parents[1] / "data" / "spaceweatherlive_snapshot.json",
		help="Output JSON path (default: data/spaceweatherlive_snapshot.json)",
	)
	args = parser.parse_args()
	args.output.parent.mkdir(parents=True, exist_ok=True)

	try:
		snapshot = fetch_spaceweatherlive_snapshot()
		data = snapshot.to_dict()
	except Exception:
		# Fallback to OpenAI extraction if direct parsing fails
		fallback = _fallback_openai_fetch()
		if not fallback:
			raise
		data = fallback

	args.output.write_text(json.dumps(data, indent=2))
	print(f"Wrote SpaceWeatherLive snapshot to: {args.output}")


if __name__ == "__main__":
	main()


