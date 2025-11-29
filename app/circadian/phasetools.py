"""
Tools for extracting phase information from time series data.

Implements cosinor analysis methods for estimating circadian phase from
periodic signals such as temperature, activity, or melatonin rhythms.

Original implementation: Arcascope (https://github.com/Arcascope/circadian)
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


__all__ = ["cosinor", "cosinor_phase", "cosinor_goals"]


def cosinor(
    t: NDArray,
    y: NDArray,
    tau: float = 24.0,
) -> NDArray:
    """Estimate cosinor coefficients for a periodic signal.
    
    Cosinor analysis fits a cosine function to the data to extract
    amplitude and phase information. This function returns the sine
    and cosine coefficients (a1, a2) which can be used to compute
    amplitude and phase.
    
    The fitted model is: y(t) = M + A*cos(ωt - φ)
    where ω = 2π/τ
    
    Args:
        t: Time vector (same units as tau, typically hours).
        y: Signal vector (same length as t).
        tau: Period of cosinor analysis (default 24.0 for circadian).
        
    Returns:
        Array [a1, a2] where:
        - a1: Sine coefficient
        - a2: Cosine coefficient
        
        Amplitude A = sqrt(a1² + a2²)
        Phase φ = atan2(a1, a2)
        
    Example:
        >>> t = np.linspace(0, 48, 1000)
        >>> y = np.cos(2*np.pi*t/24 - np.pi/4) + np.random.randn(1000)*0.1
        >>> coeffs = cosinor(t, y, tau=24.0)
        >>> phase = cosinor_phase(coeffs)
    """
    if len(t) != len(y):
        raise ValueError("t and y must have the same length")
    if tau <= 0:
        raise ValueError("tau must be positive")
    
    omega = 2 * np.pi / tau
    sin_transform = np.sin(omega * t)
    cos_transform = np.cos(omega * t)
    
    # Project signal onto sine and cosine basis
    a1 = np.dot(y, sin_transform) / np.dot(sin_transform, sin_transform)
    a2 = np.dot(y, cos_transform) / np.dot(cos_transform, cos_transform)
    
    return np.array([a1, a2])


def cosinor_phase(a: NDArray) -> float:
    """Extract phase from cosinor coefficients.
    
    Converts the [a1, a2] coefficients from cosinor() to a phase angle.
    
    Args:
        a: Array [a1, a2] from cosinor() function.
        
    Returns:
        Phase angle in radians (-π to π).
        
    Example:
        >>> coeffs = cosinor(t, y, tau=24.0)
        >>> phase_rad = cosinor_phase(coeffs)
        >>> phase_hours = phase_rad * 12 / np.pi  # Convert to hours
    """
    z = a[1] + complex(0, 1) * a[0]
    return float(np.angle(z))


def cosinor_amplitude(a: NDArray) -> float:
    """Extract amplitude from cosinor coefficients.
    
    Args:
        a: Array [a1, a2] from cosinor() function.
        
    Returns:
        Amplitude of the fitted cosine.
    """
    return float(np.sqrt(a[0]**2 + a[1]**2))


def cosinor_goals(
    t: NDArray,
    y: NDArray,
    tau: float = 24.0,
) -> NDArray:
    """Estimate cosinor coefficients using orthogonalized basis.
    
    This variant uses QR decomposition to orthogonalize the basis functions,
    which can provide more numerically stable estimates when the time samples
    are not uniformly distributed.
    
    Args:
        t: Time vector (same units as tau).
        y: Signal vector.
        tau: Period of cosinor analysis (default 24.0 for circadian).
        
    Returns:
        Array [a1, a2] - cosinor coefficients.
        
    Note:
        Results may differ slightly from cosinor() due to the orthogonalization
        process, but both methods should give similar phase estimates.
    """
    if len(t) != len(y):
        raise ValueError("t and y must have the same length")
    if tau <= 0:
        raise ValueError("tau must be positive")
    
    omega = 2 * np.pi / tau
    A = np.stack((np.ones(len(t)), np.sin(omega * t), np.cos(omega * t)), axis=1)
    
    Q, _ = np.linalg.qr(A)
    x1 = Q[:, 1]
    x2 = Q[:, 2]
    
    z = (
        complex(0, 1) * np.dot(x1, y) / np.dot(x1, np.sin(omega * t))
        + np.dot(x2, y) / np.dot(x2, np.cos(omega * t))
    )
    
    return np.array([z.imag, z.real])


def cosinor_fit(
    t: NDArray,
    y: NDArray,
    tau: float = 24.0,
) -> dict:
    """Complete cosinor analysis returning all fit parameters.
    
    Fits a cosinor model: y(t) = mesor + amplitude * cos(ωt - acrophase)
    
    Args:
        t: Time vector in hours.
        y: Signal vector.
        tau: Period in hours (default 24.0).
        
    Returns:
        Dictionary with:
        - 'mesor': Mean level of the rhythm
        - 'amplitude': Peak-to-mesor amplitude
        - 'acrophase': Time of peak in hours (0-tau)
        - 'acrophase_rad': Acrophase in radians
        - 'coefficients': Raw [a1, a2] coefficients
        - 'r_squared': Coefficient of determination
        
    Example:
        >>> result = cosinor_fit(times, temperatures, tau=24.0)
        >>> print(f"Peak time: {result['acrophase']:.1f} hours")
        >>> print(f"Amplitude: {result['amplitude']:.2f}")
    """
    if len(t) != len(y):
        raise ValueError("t and y must have the same length")
    
    coeffs = cosinor(t, y, tau)
    
    mesor = float(np.mean(y))
    amplitude = cosinor_amplitude(coeffs)
    acrophase_rad = cosinor_phase(coeffs)
    
    # Convert phase to time (hours)
    # Note: acrophase is when cos(ωt - φ) = 1, i.e., ωt = φ
    acrophase = (acrophase_rad * tau / (2 * np.pi)) % tau
    
    # Calculate R-squared
    omega = 2 * np.pi / tau
    y_fit = mesor + amplitude * np.cos(omega * t - acrophase_rad)
    ss_res = np.sum((y - y_fit) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
    
    return {
        'mesor': mesor,
        'amplitude': amplitude,
        'acrophase': acrophase,
        'acrophase_rad': acrophase_rad,
        'coefficients': coeffs,
        'r_squared': r_squared,
    }

