"""Research-grade PVT administration via PsychoPy (desktop).

This is the non-browser alternative to the web-based PVT test. PsychoPy
has been independently validated for sub-millisecond stimulus timing
precision [Garaizar & Vadillo 2014, DOI 10.1371/journal.pone.0112033],
making it the open-source research-grade choice for contexts where the
browser's ≈5-10 ms RT precision (Anwyl-Irvine et al. 2020, DOI
10.3758/s13428-020-01501-5) is insufficient.

Installation
------------

    pip install psychopy>=2024.1

PsychoPy pulls in a large dependency graph (pyglet, wxPython, numpy,
scipy, …). Recommended: use a dedicated conda env:

    conda create -n pvt-desktop python=3.11
    conda activate pvt-desktop
    pip install psychopy

Usage
-----

    python app/pvt_desktop.py --variant PVT-B --user demo-operator
    python app/pvt_desktop.py --variant PVT-5 --out session.json
    python app/pvt_desktop.py --variant PVT-10 --post http://localhost:8180/api/pvt/sessions

The desktop driver:
  1. Generates a validated ISI schedule via app.pvt_core.generate_isi_schedule
  2. Administers the session at full-screen with PsychoPy's
     clock.Clock() (sub-ms resolution) and waits for keyboard events
     via event.waitKeys()
  3. Scores the session via app.pvt_core.score_session (same canonical
     scoring as the web version)
  4. Writes results to JSON and optionally POSTs to /api/pvt/sessions

The scoring logic lives exclusively in app.pvt_core; this module is
purely an alternative administration surface.

Author: Dr Diego Malpica MD
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Ensure app directory is on path when run as a script
_HERE = Path(__file__).resolve()
_PROJECT_ROOT = _HERE.parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from app.pvt_core import (  # noqa: E402
    FALSE_START_THRESHOLD_MS,
    PVTSession,
    PVTTrial,
    PVTVariant,
    generate_isi_schedule,
    operational_gate,
    score_session,
    variant_defaults,
)


# ---------------------------------------------------------------------------
# Optional dependency: psychopy. Imported lazily so the rest of the module
# remains importable on systems without PsychoPy installed (e.g. CI).
# ---------------------------------------------------------------------------

def _import_psychopy():
    try:
        from psychopy import core, event, visual  # type: ignore
    except ImportError as exc:  # pragma: no cover - optional dep
        raise RuntimeError(
            "PsychoPy is required for the desktop PVT. Install with: "
            "'pip install psychopy>=2024.1'. See module docstring for "
            "a recommended conda env setup."
        ) from exc
    return core, event, visual


# ---------------------------------------------------------------------------
# Administration loop
# ---------------------------------------------------------------------------

def run_session(
    variant: PVTVariant,
    user_id: Optional[str] = None,
    device_label: str = "psychopy-desktop",
    full_screen: bool = True,
    response_keys: tuple[str, ...] = ("space", "return"),
) -> PVTSession:
    """Run a PVT session on the desktop via PsychoPy.

    Returns a PVTSession ready for scoring by app.pvt_core.score_session.
    """
    core, event, visual = _import_psychopy()

    defaults = variant_defaults(variant)
    duration_ms = defaults["duration_min"] * 60 * 1000.0
    schedule = generate_isi_schedule(variant)

    win = visual.Window(
        fullscr=full_screen,
        color=(-0.9, -0.9, -0.9),
        units="norm",
        waitBlanking=True,
    )
    instructions = visual.TextStim(
        win,
        text=(
            f"{variant.value} — Psychomotor Vigilance Task\n\n"
            f"Duration: {defaults['duration_min']} minutes\n"
            f"ISI range: {defaults['isi_min_s']}-{defaults['isi_max_s']} s\n"
            f"Lapse threshold: {defaults['lapse_threshold_ms']:.0f} ms\n\n"
            "Press SPACE as soon as you see the counter.\n"
            "Do not anticipate — false starts are flagged.\n\n"
            "Press SPACE to begin."
        ),
        height=0.06,
        wrapWidth=1.8,
        color="white",
    )
    counter = visual.TextStim(
        win, text="", height=0.2, color=(1.0, 0.3, 0.2),
    )
    feedback_ok = visual.TextStim(
        win, text="✓", height=0.25, color=(0.2, 1.0, 0.3),
    )
    feedback_false = visual.TextStim(
        win, text="FALSE START",
        height=0.12, color=(1.0, 0.8, 0.2),
    )

    instructions.draw()
    win.flip()
    event.waitKeys(keyList=list(response_keys))

    session_clock = core.Clock()  # PsychoPy high-precision clock
    trials: list[PVTTrial] = []
    trial_idx = 0

    while session_clock.getTime() * 1000.0 < duration_ms and trial_idx < len(schedule):
        isi_ms = schedule[trial_idx]
        # Clear screen during ISI
        win.flip()
        # Detect anticipatory responses during ISI
        isi_start = core.getTime()
        anticipatory_keys = event.waitKeys(
            maxWait=isi_ms / 1000.0,
            keyList=list(response_keys),
            timeStamped=session_clock,
        )
        if anticipatory_keys:
            # False start
            trials.append(PVTTrial(
                index=trial_idx,
                isi_ms=isi_ms,
                stimulus_onset_ms=session_clock.getTime() * 1000.0,
                rt_ms=None,
                anticipatory=True,
            ))
            feedback_false.draw()
            win.flip()
            core.wait(0.75)
            trial_idx += 1
            continue

        # Draw stimulus, flip, record precise onset via waitBlanking
        stim_onset_s = session_clock.getTime()
        counter.text = "000"
        counter.draw()
        win.flip()  # post-flip; win's waitBlanking ensures tight onset
        stim_flip_s = session_clock.getTime()

        # Spin: update counter and poll for keypress every frame until
        # response or 30-s window.
        response_deadline_s = stim_flip_s + 30.0
        rt_ms: Optional[float] = None
        while core.getTime() < response_deadline_s:
            elapsed_ms = (session_clock.getTime() - stim_flip_s) * 1000.0
            # Update counter text every ~16 ms (~60 fps)
            counter.text = f"{int(elapsed_ms):03d}"
            counter.draw()
            win.flip()
            keys = event.getKeys(keyList=list(response_keys), timeStamped=session_clock)
            if keys:
                key, key_time_s = keys[0]
                rt_ms = (key_time_s - stim_flip_s) * 1000.0
                break
            if elapsed_ms > 30000:
                break

        trials.append(PVTTrial(
            index=trial_idx,
            isi_ms=isi_ms,
            stimulus_onset_ms=stim_flip_s * 1000.0,
            rt_ms=rt_ms,
            anticipatory=False,
        ))

        # Feedback
        if rt_ms is not None and rt_ms >= FALSE_START_THRESHOLD_MS:
            feedback_ok.draw()
            win.flip()
            core.wait(0.35)
        trial_idx += 1

    # Farewell
    farewell = visual.TextStim(
        win, text="Session complete.", height=0.08, color="white",
    )
    farewell.draw()
    win.flip()
    core.wait(1.0)
    win.close()

    return PVTSession(
        variant=variant,
        duration_min=defaults["duration_min"],
        trials=tuple(trials),
        user_id=user_id,
        started_at=datetime.now(timezone.utc),
        ended_at=datetime.now(timezone.utc),
        device_label=device_label,
        software_version="pvt_desktop v1 / psychopy",
    )


# ---------------------------------------------------------------------------
# CLI driver
# ---------------------------------------------------------------------------

def _serialise_trials(session: PVTSession) -> list[dict]:
    return [
        {
            "index": t.index,
            "isi_ms": t.isi_ms,
            "stimulus_onset_ms": t.stimulus_onset_ms,
            "rt_ms": t.rt_ms,
            "anticipatory": t.anticipatory,
        }
        for t in session.trials
    ]


def _post_session(
    url: str,
    session: PVTSession,
    metrics: dict,
    timeout_s: float = 10.0,
) -> None:
    try:
        import urllib.request
        import urllib.error
    except ImportError as exc:  # pragma: no cover
        print(f"[warn] urllib unavailable: {exc}", file=sys.stderr)
        return

    body = {
        "variant": session.variant.value,
        "duration_min": session.duration_min,
        "lapse_threshold_ms": metrics.get("lapse_threshold_ms"),
        "user_id": session.user_id,
        "device_label": session.device_label,
        "software_version": session.software_version,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "ended_at": session.ended_at.isoformat() if session.ended_at else None,
        "trials": _serialise_trials(session),
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            resp_body = resp.read().decode("utf-8")
            print(f"[post] {resp.status} {resp.reason}")
            print(f"[post] {resp_body[:200]}")
    except urllib.error.URLError as exc:
        print(f"[post] failed: {exc}", file=sys.stderr)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Research-grade PVT administration (PsychoPy desktop).",
    )
    parser.add_argument(
        "--variant", choices=[v.value for v in PVTVariant], default="PVT-B",
        help="PVT variant (default: PVT-B)",
    )
    parser.add_argument("--user", dest="user_id", default=None, help="User ID string")
    parser.add_argument("--out", default=None, help="Path to save JSON result")
    parser.add_argument("--post", default=None, help="URL to POST the session to")
    parser.add_argument("--windowed", action="store_true", help="Run windowed instead of full-screen")
    args = parser.parse_args(argv)

    variant = PVTVariant(args.variant)

    session = run_session(
        variant=variant,
        user_id=args.user_id,
        full_screen=not args.windowed,
    )
    metrics = score_session(session)
    gate = operational_gate(metrics)

    print("\n" + "=" * 60)
    print(f"PVT Desktop result — {variant.value}")
    print("=" * 60)
    print(f"  user            : {session.user_id or '-'}")
    print(f"  trials          : {metrics['n_trials']}")
    print(f"  valid           : {metrics['n_valid_trials']}")
    print(f"  lapses          : {metrics['n_lapses']}")
    print(f"  major lapses    : {metrics['n_major_lapses']}")
    print(f"  false starts    : {metrics['n_false_starts']}")
    print(f"  mean RT (ms)    : {_fmt(metrics['mean_rt_ms'])}")
    print(f"  median RT (ms)  : {_fmt(metrics['median_rt_ms'])}")
    print(f"  1/RT (s^-1)     : {_fmt(metrics['mean_response_speed_per_s'], 3)}")
    print(f"  pvt_lapses_3min : {metrics['pvt_lapses_3min']}")
    print(f"  DECISION        : {gate['decision']}")
    for reason in gate["reasons"]:
        print(f"    - {reason}")

    if args.out:
        out_path = Path(args.out).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "session": {
                "variant": session.variant.value,
                "duration_min": session.duration_min,
                "user_id": session.user_id,
                "device_label": session.device_label,
                "software_version": session.software_version,
                "started_at": session.started_at.isoformat() if session.started_at else None,
                "ended_at": session.ended_at.isoformat() if session.ended_at else None,
                "trials": _serialise_trials(session),
            },
            "metrics": metrics,
            "gate": gate,
        }
        with out_path.open("w") as f:
            json.dump(payload, f, indent=2)
        print(f"\n[out] wrote {out_path}")

    if args.post:
        _post_session(args.post, session, metrics)

    return 0


def _fmt(x: Optional[float], digits: int = 1) -> str:
    return f"{x:.{digits}f}" if x is not None else "-"


if __name__ == "__main__":
    raise SystemExit(main())
