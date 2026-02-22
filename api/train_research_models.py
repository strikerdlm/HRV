# Author: Dr Diego Malpica MD
"""
Offline trainer for research model artifacts.

This script generates calibrated model artifacts used at runtime by:
- /api/research/vigilance/{user_id}
- /api/research/flight-fatigue/{user_id}

Design notes:
- Deterministic synthetic bootstrap training (fixed random seed)
- No runtime dependency on external ML libraries
- Outputs JSON artifacts under api/model_artifacts/
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np

_SEED = 424242


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def _softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - np.max(logits, axis=1, keepdims=True)
    exp_logits = np.exp(shifted)
    denom = np.sum(exp_logits, axis=1, keepdims=True)
    return exp_logits / np.clip(denom, 1e-12, None)


def _train_test_split(
    x: np.ndarray,
    y: np.ndarray,
    train_frac: float = 0.8,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    n = x.shape[0]
    train_n = int(max(1, min(n - 1, round(train_frac * n))))
    return x[:train_n], x[train_n:], y[:train_n], y[train_n:]


def _accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean(y_true == y_pred))


def _binary_precision_recall_f1(y_true: np.ndarray, y_pred: np.ndarray) -> Tuple[float, float, float]:
    tp = float(np.sum((y_true == 1) & (y_pred == 1)))
    fp = float(np.sum((y_true == 0) & (y_pred == 1)))
    fn = float(np.sum((y_true == 1) & (y_pred == 0)))
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2.0 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return precision, recall, f1


def _macro_f1(y_true: np.ndarray, y_pred: np.ndarray, n_classes: int) -> float:
    f1_values: List[float] = []
    for cls in range(n_classes):
        y_t = (y_true == cls).astype(int)
        y_p = (y_pred == cls).astype(int)
        _, _, f1 = _binary_precision_recall_f1(y_t, y_p)
        f1_values.append(f1)
    return float(np.mean(f1_values))


def _cohen_kappa(y_true: np.ndarray, y_pred: np.ndarray, n_classes: int) -> float:
    conf = np.zeros((n_classes, n_classes), dtype=float)
    for i in range(y_true.shape[0]):
        conf[int(y_true[i]), int(y_pred[i])] += 1.0
    total = np.sum(conf)
    if total <= 0:
        return 0.0
    po = float(np.trace(conf) / total)
    row_marg = np.sum(conf, axis=1) / total
    col_marg = np.sum(conf, axis=0) / total
    pe = float(np.sum(row_marg * col_marg))
    if pe >= 1.0:
        return 0.0
    return float((po - pe) / max(1e-12, 1.0 - pe))


def _train_binary_logistic(
    x: np.ndarray,
    y: np.ndarray,
    *,
    epochs: int = 600,
    learning_rate: float = 0.04,
    l2: float = 1e-3,
) -> Tuple[np.ndarray, float]:
    n_samples, n_features = x.shape
    w = np.zeros(n_features, dtype=float)
    b = 0.0
    for _ in range(epochs):
        logits = x @ w + b
        probs = _sigmoid(logits)
        error = probs - y
        grad_w = (x.T @ error) / n_samples + l2 * w
        grad_b = float(np.mean(error))
        w -= learning_rate * grad_w
        b -= learning_rate * grad_b
    return w, b


def _train_multiclass_softmax(
    x: np.ndarray,
    y: np.ndarray,
    n_classes: int,
    *,
    epochs: int = 900,
    learning_rate: float = 0.03,
    l2: float = 1e-3,
) -> Tuple[np.ndarray, np.ndarray]:
    n_samples, n_features = x.shape
    w = np.zeros((n_features, n_classes), dtype=float)
    b = np.zeros(n_classes, dtype=float)
    y_onehot = np.eye(n_classes, dtype=float)[y]
    for _ in range(epochs):
        logits = x @ w + b
        probs = _softmax(logits)
        error = probs - y_onehot
        grad_w = (x.T @ error) / n_samples + l2 * w
        grad_b = np.mean(error, axis=0)
        w -= learning_rate * grad_w
        b -= learning_rate * grad_b
    return w, b


def _build_vigilance_dataset(rng: np.random.Generator, n_samples: int = 7000) -> Tuple[np.ndarray, np.ndarray]:
    # Features: rmssd_drop_z, sdnn_drop_z, hr_rise_z, pnn50_drop_z, safte_penalty, sample_factor
    rmssd_drop = rng.gamma(shape=1.8, scale=0.7, size=n_samples)
    sdnn_drop = rng.gamma(shape=1.6, scale=0.6, size=n_samples)
    hr_rise = rng.gamma(shape=1.7, scale=0.65, size=n_samples)
    pnn50_drop = rng.gamma(shape=1.5, scale=0.7, size=n_samples)
    safte_penalty = rng.uniform(0.0, 1.5, size=n_samples)
    sample_factor = rng.uniform(0.25, 1.0, size=n_samples)
    x = np.column_stack(
        [rmssd_drop, sdnn_drop, hr_rise, pnn50_drop, safte_penalty, sample_factor]
    ).astype(float)
    latent = (
        -1.05
        + 0.95 * rmssd_drop
        + 0.55 * sdnn_drop
        + 0.75 * hr_rise
        + 0.45 * pnn50_drop
        + 0.65 * safte_penalty
        - 0.25 * sample_factor
        + rng.normal(0.0, 0.32, size=n_samples)
    )
    p_low = _sigmoid(latent)
    y = (rng.uniform(0.0, 1.0, size=n_samples) < p_low).astype(int)
    return x, y


def _build_flight_dataset(rng: np.random.Generator, n_samples: int = 9000) -> Tuple[np.ndarray, np.ndarray]:
    # Features: effectiveness_term, sleep_term, rmssd_term, sdnn_term, hr_term, lfhf_term
    effectiveness_term = rng.normal(0.0, 0.8, size=n_samples)
    sleep_term = rng.normal(0.0, 0.9, size=n_samples)
    rmssd_term = rng.normal(0.0, 0.85, size=n_samples)
    sdnn_term = rng.normal(0.0, 0.8, size=n_samples)
    hr_term = rng.normal(0.0, 0.9, size=n_samples)
    lfhf_term = rng.normal(0.0, 0.7, size=n_samples)
    x = np.column_stack(
        [effectiveness_term, sleep_term, rmssd_term, sdnn_term, hr_term, lfhf_term]
    ).astype(float)

    low_score = (
        0.20
        + 1.45 * effectiveness_term
        - 1.25 * sleep_term
        + 0.85 * rmssd_term
        + 0.55 * sdnn_term
        - 0.45 * np.maximum(hr_term, 0.0)
        - 0.25 * np.maximum(lfhf_term, 0.0)
    )
    mod_score = (
        0.55
        - 0.25 * np.abs(effectiveness_term)
        + 0.10 * np.clip(sleep_term, 0.0, 1.0)
        - 0.20 * np.abs(rmssd_term)
        - 0.15 * np.abs(hr_term)
    )
    high_score = (
        0.35
        - 1.55 * effectiveness_term
        + 1.35 * sleep_term
        - 0.95 * rmssd_term
        - 0.55 * sdnn_term
        + 0.70 * np.maximum(hr_term, 0.0)
        + 0.40 * np.maximum(lfhf_term, 0.0)
    )
    logits = np.column_stack([low_score, mod_score, high_score])
    logits = logits + rng.normal(0.0, 0.22, size=logits.shape)
    probs = _softmax(logits)
    draws = rng.uniform(0.0, 1.0, size=n_samples)
    cdf = np.cumsum(probs, axis=1)
    y = np.zeros(n_samples, dtype=int)
    for i in range(n_samples):
        y[i] = int(np.searchsorted(cdf[i], draws[i], side="right"))
    return x, y


@dataclass(frozen=True, slots=True)
class TrainOutputs:
    vigilance_artifact: Dict[str, object]
    fatigue_artifact: Dict[str, object]


def train_research_models(seed: int = _SEED) -> TrainOutputs:
    rng = np.random.default_rng(seed)
    now = datetime.now(timezone.utc).isoformat()

    # -----------------------------
    # Vigilance (binary low-vigilance)
    # -----------------------------
    x_v, y_v = _build_vigilance_dataset(rng)
    x_v_train, x_v_test, y_v_train, y_v_test = _train_test_split(x_v, y_v, train_frac=0.82)
    w_v, b_v = _train_binary_logistic(x_v_train, y_v_train, epochs=700, learning_rate=0.04, l2=8e-4)
    p_v = _sigmoid(x_v_test @ w_v + b_v)
    y_v_pred = (p_v >= 0.5).astype(int)
    p_prec, p_rec, p_f1 = _binary_precision_recall_f1(y_v_test, y_v_pred)
    vigilance_metrics = {
        "accuracy": round(_accuracy(y_v_test, y_v_pred), 4),
        "precision_low": round(p_prec, 4),
        "recall_low": round(p_rec, 4),
        "f1_low": round(p_f1, 4),
    }
    vigilance_artifact: Dict[str, object] = {
        "model_id": "windowed_vigilance_calibrated",
        "model_version": "windowed_hrv_calibrated_v2",
        "trained_at_utc": now,
        "source": "offline_synthetic_bootstrap_v1",
        "feature_order": [
            "rmssd_drop_z",
            "sdnn_drop_z",
            "hr_rise_z",
            "pnn50_drop_z",
            "safte_penalty",
            "sample_factor",
        ],
        "coefficients": [round(float(v), 6) for v in w_v.tolist()],
        "intercept": round(float(b_v), 6),
        "threshold_low": 0.66,
        "threshold_medium": 0.38,
        "smoothing_alpha": 0.3,
        "confidence_bias": 0.35,
        "confidence_sep_weight": 0.45,
        "confidence_sample_weight": 0.2,
        "metrics": vigilance_metrics,
        "references": [
            "doi:10.1093/sleep/zsae199",
            "doi:10.1161/01.CIR.93.5.1043",
        ],
        "notes": "Deterministic synthetic bootstrap fit; replace with cohort-specific training dataset when available.",
    }

    # -----------------------------
    # Flight fatigue (multiclass)
    # -----------------------------
    x_f, y_f = _build_flight_dataset(rng)
    x_f_train, x_f_test, y_f_train, y_f_test = _train_test_split(x_f, y_f, train_frac=0.82)
    w_f, b_f = _train_multiclass_softmax(
        x_f_train,
        y_f_train,
        n_classes=3,
        epochs=1000,
        learning_rate=0.03,
        l2=8e-4,
    )
    probs_f = _softmax(x_f_test @ w_f + b_f)
    y_f_pred = np.argmax(probs_f, axis=1)
    fatigue_metrics = {
        "accuracy": round(_accuracy(y_f_test, y_f_pred), 4),
        "macro_f1": round(_macro_f1(y_f_test, y_f_pred, n_classes=3), 4),
        "kappa": round(_cohen_kappa(y_f_test, y_f_pred, n_classes=3), 4),
    }
    fatigue_artifact: Dict[str, object] = {
        "model_id": "flight_fatigue_multifeature_calibrated",
        "model_version": "multifeature_calibrated_v2",
        "trained_at_utc": now,
        "source": "offline_synthetic_bootstrap_v1",
        "feature_order": [
            "effectiveness_term",
            "sleep_term",
            "rmssd_term",
            "sdnn_term",
            "hr_term",
            "lfhf_term",
        ],
        "class_labels": ["low", "moderate", "high"],
        "class_coefficients": {
            "low": [round(float(v), 6) for v in w_f[:, 0].tolist()],
            "moderate": [round(float(v), 6) for v in w_f[:, 1].tolist()],
            "high": [round(float(v), 6) for v in w_f[:, 2].tolist()],
        },
        "class_intercepts": {
            "low": round(float(b_f[0]), 6),
            "moderate": round(float(b_f[1]), 6),
            "high": round(float(b_f[2]), 6),
        },
        "temperature": 1.0,
        "metrics": fatigue_metrics,
        "references": [
            "doi:10.3389/fnins.2025.1621638",
            "doi:10.3389/fnrgo.2025.1672492",
            "doi:10.1161/01.CIR.93.5.1043",
        ],
        "notes": "Deterministic synthetic bootstrap fit; replace with cohort-specific training dataset when available.",
    }

    return TrainOutputs(
        vigilance_artifact=vigilance_artifact,
        fatigue_artifact=fatigue_artifact,
    )


def write_artifacts(output_dir: Path, outputs: TrainOutputs) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    vigilance_path = output_dir / "vigilance_model.json"
    fatigue_path = output_dir / "flight_fatigue_model.json"
    with vigilance_path.open("w", encoding="utf-8") as handle:
        json.dump(outputs.vigilance_artifact, handle, indent=2)
        handle.write("\n")
    with fatigue_path.open("w", encoding="utf-8") as handle:
        json.dump(outputs.fatigue_artifact, handle, indent=2)
        handle.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train offline research model artifacts.")
    parser.add_argument(
        "--output-dir",
        default=str(Path(__file__).resolve().parent / "model_artifacts"),
        help="Directory for generated artifact JSON files",
    )
    parser.add_argument("--seed", type=int, default=_SEED, help="Deterministic RNG seed")
    args = parser.parse_args()

    outputs = train_research_models(seed=args.seed)
    out_dir = Path(args.output_dir).resolve()
    write_artifacts(out_dir, outputs)
    print(f"Artifacts written to: {out_dir}")


if __name__ == "__main__":
    main()
