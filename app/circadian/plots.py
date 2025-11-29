"""
Plotting utilities for circadian rhythm visualization.

Provides publication-ready plots for:
- Actograms (double-plotted activity/light raster plots)
- Phase markers (DLMO, CBT minimum)
- Amplitude and phase time series
- Torus/stroboscopic phase portraits

Original implementation: Arcascope (https://github.com/Arcascope/circadian)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Tuple

import numpy as np
from numpy.typing import NDArray
from scipy.ndimage import gaussian_filter1d


@dataclass
class Actogram:
    """Double-plotted actogram for visualizing circadian patterns.
    
    An actogram displays time series data (typically light or activity)
    rasterized by circadian day, with each row representing one day.
    Double-plotting repeats data to show patterns spanning midnight.
    
    Attributes:
        time: Time array in hours from start.
        values: Data values (light in lux, activity counts, etc.).
        ax: Matplotlib axes for plotting.
        threshold: Value above which data is shown as "active/light".
        period: Circadian period for wrapping (hours, default 24).
        opacity: Fill opacity for active regions.
        color: Fill color for active regions.
        smooth: Whether to apply Gaussian smoothing.
        sigma: Smoothing kernel width [x_sigma, y_sigma].
    """
    
    time: NDArray
    values: Optional[NDArray] = None
    ax: Any = None
    threshold: float = 10.0
    period: float = 24.0
    opacity: float = 0.8
    color: str = "black"
    smooth: bool = True
    sigma: Tuple[float, float] = (2.0, 2.0)
    light_vals: Optional[NDArray] = None  # Alias for values (backward compat)
    
    def __post_init__(self) -> None:
        """Initialize and render the actogram."""
        # Handle light_vals alias
        if self.values is None and self.light_vals is not None:
            self.values = self.light_vals
        
        if self.values is None:
            raise ValueError("Must provide values (or light_vals) array")
        
        if self.ax is None:
            import matplotlib.pyplot as plt
            _, self.ax = plt.subplots(figsize=(10, 8))
        
        self._render()
    
    def _render(self) -> None:
        """Render the actogram on the axes."""
        time = np.asarray(self.time, dtype=np.float64)
        values = np.asarray(self.values, dtype=np.float64)
        
        if len(time) != len(values):
            raise ValueError("time and values must have same length")
        
        # Apply smoothing if requested
        if self.smooth and self.sigma[0] > 0:
            values = gaussian_filter1d(values, sigma=self.sigma[0])
        
        # Determine number of days
        total_hours = time[-1] - time[0]
        num_days = int(np.ceil(total_hours / self.period))
        
        # Rasterize data into day x hour matrix
        hours_per_day = int(self.period)
        dt = np.diff(time).mean() if len(time) > 1 else 0.1
        bins_per_day = int(self.period / dt)
        
        # Create raster matrix
        raster = np.zeros((num_days, bins_per_day * 2))  # Double-plotted
        
        for day_idx in range(num_days):
            day_start = time[0] + day_idx * self.period
            day_end = day_start + self.period
            
            # Get data for this day
            mask = (time >= day_start) & (time < day_end)
            day_time = time[mask] - day_start
            day_vals = values[mask]
            
            if len(day_time) > 0:
                # Bin into raster
                bin_indices = (day_time / self.period * bins_per_day).astype(int)
                bin_indices = np.clip(bin_indices, 0, bins_per_day - 1)
                
                for bi, val in zip(bin_indices, day_vals):
                    raster[day_idx, bi] = max(raster[day_idx, bi], val)
                    # Double-plot (second copy offset by period)
                    raster[day_idx, bi + bins_per_day] = max(
                        raster[day_idx, bi + bins_per_day], val
                    )
        
        # Apply vertical smoothing if requested
        if self.smooth and self.sigma[1] > 0:
            raster = gaussian_filter1d(raster, sigma=self.sigma[1], axis=0)
        
        # Threshold and plot
        binary_raster = (raster >= self.threshold).astype(float) * self.opacity
        
        extent = [0, self.period * 2, num_days, 0]
        self.ax.imshow(
            binary_raster,
            aspect="auto",
            extent=extent,
            cmap="Greys",
            vmin=0,
            vmax=1,
            interpolation="nearest",
        )
        
        # Style axes
        self.ax.set_xlabel("Hour of Day")
        self.ax.set_ylabel("Day")
        self.ax.set_xlim(0, self.period * 2)
        self.ax.set_xticks(np.arange(0, self.period * 2 + 1, 6))
        self.ax.axvline(self.period, color="gray", linestyle="--", alpha=0.5)
        
        self._raster = raster
        self._num_days = num_days
    
    def plot_phasemarker(
        self,
        marker_times: NDArray,
        color: str = "blue",
        error: Optional[NDArray] = None,
        alpha: float = 0.8,
        marker: str = "o",
        markersize: float = 5,
        label: Optional[str] = None,
    ) -> None:
        """Overlay phase markers (e.g., DLMO, CBT minimum) on the actogram.
        
        Args:
            marker_times: Times of phase markers in hours from start.
            color: Marker color.
            error: Optional error bars (± hours).
            alpha: Marker transparency.
            marker: Marker symbol.
            markersize: Marker size.
            label: Legend label.
        """
        marker_times = np.asarray(marker_times, dtype=np.float64)
        
        # Convert to day/hour coordinates
        time_offset = self.time[0]
        relative_times = marker_times - time_offset
        
        days = relative_times / self.period
        hours = np.mod(relative_times, self.period)
        
        # Plot on first and second halves (double-plotted)
        self.ax.scatter(
            hours, days, c=color, marker=marker, s=markersize**2,
            alpha=alpha, zorder=10, label=label,
        )
        self.ax.scatter(
            hours + self.period, days, c=color, marker=marker, s=markersize**2,
            alpha=alpha, zorder=10,
        )
        
        # Add error bars if provided
        if error is not None:
            error = np.asarray(error, dtype=np.float64)
            self.ax.errorbar(
                hours, days, xerr=error, fmt="none",
                ecolor=color, alpha=alpha * 0.5, capsize=2, zorder=9,
            )
            self.ax.errorbar(
                hours + self.period, days, xerr=error, fmt="none",
                ecolor=color, alpha=alpha * 0.5, capsize=2, zorder=9,
            )


def plot_actogram(
    time: NDArray,
    values: NDArray,
    threshold: float = 10.0,
    period: float = 24.0,
    ax: Any = None,
    **kwargs: Any,
) -> Actogram:
    """Convenience function to create an actogram plot.
    
    Args:
        time: Time array in hours.
        values: Data values (light, activity, etc.).
        threshold: Threshold for light/dark classification.
        period: Circadian period (hours).
        ax: Optional matplotlib axes.
        **kwargs: Additional arguments passed to Actogram.
        
    Returns:
        Actogram instance.
    """
    return Actogram(
        time=time,
        values=values,
        threshold=threshold,
        period=period,
        ax=ax,
        **kwargs,
    )


def plot_mae(
    true_phases: NDArray,
    predicted_phases: NDArray,
    period: float = 24.0,
    ax: Any = None,
) -> Tuple[Any, float]:
    """Plot mean absolute error between true and predicted phase markers.
    
    Args:
        true_phases: True phase marker times (hours).
        predicted_phases: Predicted phase marker times (hours).
        period: Circadian period for wrapping.
        ax: Optional matplotlib axes.
        
    Returns:
        Tuple of (axes, mean_absolute_error).
    """
    import matplotlib.pyplot as plt
    
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 6))
    
    true_phases = np.asarray(true_phases, dtype=np.float64)
    predicted_phases = np.asarray(predicted_phases, dtype=np.float64)
    
    # Calculate circular error
    errors = np.mod(predicted_phases - true_phases + period/2, period) - period/2
    mae = float(np.mean(np.abs(errors)))
    
    # Plot
    ax.scatter(true_phases % period, predicted_phases % period, alpha=0.6)
    ax.plot([0, period], [0, period], "k--", alpha=0.3, label="Perfect prediction")
    ax.set_xlabel("True Phase (hours)")
    ax.set_ylabel("Predicted Phase (hours)")
    ax.set_title(f"Phase Prediction (MAE = {mae:.2f} hours)")
    ax.legend()
    ax.set_xlim(0, period)
    ax.set_ylim(0, period)
    
    return ax, mae


def plot_torus(
    phase: NDArray,
    amplitude: NDArray,
    ax: Any = None,
    color: str = "blue",
    alpha: float = 0.5,
) -> Any:
    """Plot circadian trajectory on a torus representation.
    
    Args:
        phase: Phase array in radians.
        amplitude: Amplitude array.
        ax: Optional matplotlib axes (3D).
        color: Line color.
        alpha: Line transparency.
        
    Returns:
        Matplotlib 3D axes.
    """
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
    
    if ax is None:
        fig = plt.figure(figsize=(10, 10))
        ax = fig.add_subplot(111, projection="3d")
    
    # Convert to torus coordinates
    R = 2.0  # Major radius
    r = amplitude  # Minor radius (amplitude)
    
    x = (R + r * np.cos(phase)) * np.cos(phase / 12 * np.pi)
    y = (R + r * np.cos(phase)) * np.sin(phase / 12 * np.pi)
    z = r * np.sin(phase)
    
    ax.plot(x, y, z, color=color, alpha=alpha, linewidth=0.5)
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_zlabel("Z")
    ax.set_title("Circadian Trajectory (Torus)")
    
    return ax


class Stroboscopic:
    """Stroboscopic plot for visualizing phase dynamics.
    
    Shows phase samples at regular intervals, useful for identifying
    entrainment patterns and phase drift.
    """
    
    def __init__(
        self,
        phases: NDArray,
        sample_period: float = 24.0,
        ax: Any = None,
    ) -> None:
        """Initialize stroboscopic plot.
        
        Args:
            phases: Phase values in radians.
            sample_period: Sampling period for stroboscopic view.
            ax: Optional matplotlib axes.
        """
        import matplotlib.pyplot as plt
        
        self.phases = np.asarray(phases, dtype=np.float64)
        self.sample_period = sample_period
        self.ax = ax or plt.gca()
        
        self._render()
    
    def _render(self) -> None:
        """Render the stroboscopic plot."""
        # Convert phases to unit circle coordinates
        x = np.cos(self.phases)
        y = np.sin(self.phases)
        
        # Color by sequence index
        colors = np.arange(len(self.phases))
        
        self.ax.scatter(x, y, c=colors, cmap="viridis", alpha=0.6, s=10)
        
        # Draw unit circle
        theta = np.linspace(0, 2 * np.pi, 100)
        self.ax.plot(np.cos(theta), np.sin(theta), "k-", alpha=0.2)
        
        # Mark cardinal directions
        for angle, label in [(0, "0"), (np.pi/2, "π/2"), (np.pi, "π"), (3*np.pi/2, "3π/2")]:
            self.ax.plot(np.cos(angle), np.sin(angle), "ko", markersize=5)
            self.ax.annotate(
                label,
                (1.15 * np.cos(angle), 1.15 * np.sin(angle)),
                ha="center",
                va="center",
            )
        
        self.ax.set_xlim(-1.3, 1.3)
        self.ax.set_ylim(-1.3, 1.3)
        self.ax.set_aspect("equal")
        self.ax.set_title(f"Stroboscopic Phase Plot (T = {self.sample_period} h)")
        self.ax.axis("off")

