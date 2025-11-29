"""
Mathematical models for simulating human circadian rhythms.

Implements key models from the circadian research literature:
- Forger99: Forger et al. (1999) - 3-state limit cycle pacemaker
- Jewett99: Kronauer et al. (1999) - Revised limit cycle oscillator
- Hannay19: Hannay et al. (2019) - Macroscopic amplitude-phase model
- Hannay19TP: Hannay et al. (2019) - Two-population variant

Original implementation: Arcascope (https://github.com/Arcascope/circadian)
"""

from __future__ import annotations

import warnings
from abc import ABC
from typing import Tuple

import numpy as np
from numpy.typing import NDArray
from scipy.signal import find_peaks

from .lights import LightSchedule


def _time_input_checking(time: NDArray) -> bool:
    """Validate time array input."""
    if not isinstance(time, np.ndarray):
        raise TypeError("time must be a numpy array")
    if time.ndim != 1:
        raise ValueError("time must be a 1D array")
    if not np.issubdtype(time.dtype, np.number):
        raise TypeError("time must be numeric")
    if not np.all(np.diff(time) > 0):
        raise ValueError("time must be monotonically increasing")
    return True


def _state_input_checking(state: NDArray, time: NDArray) -> bool:
    """Validate state array input."""
    if not isinstance(state, np.ndarray):
        raise TypeError("states must be a numpy array")
    if state.ndim < 1:
        raise ValueError("states must have at least 1 dimension")
    if state.ndim > 3:
        raise ValueError("states must have at most 3 dimensions")
    if state.shape[0] != len(time):
        raise ValueError("states must have the same length as time")
    if not np.issubdtype(state.dtype, np.number):
        raise TypeError("states must be numeric")
    return True


class DynamicalTrajectory:
    """Store solutions of differential equation models with time and states."""
    
    def __init__(self, time: NDArray, states: NDArray) -> None:
        _time_input_checking(time)
        _state_input_checking(states, time)
        
        self.time = time
        self.states = states
        self.num_states = states.shape[1]
        self.batch_size = states.shape[2] if states.ndim >= 3 else 1

    def __call__(self, timepoint: float) -> NDArray:
        """Return the state at time t, linearly interpolated."""
        if not isinstance(timepoint, (int, float)):
            raise TypeError("timepoint must be int or float")
        if timepoint < self.time[0] or timepoint > self.time[-1]:
            raise ValueError("timepoint must be within the time range")
        
        if self.batch_size == 1:
            values = np.zeros(self.num_states)
            for idx in range(self.num_states):
                values[idx] = np.interp(timepoint, self.time, self.states[..., idx])
        else:
            values = np.zeros((self.num_states, self.batch_size))
            for idx in range(self.num_states):
                for batch_idx in range(self.batch_size):
                    values[idx, batch_idx] = np.interp(
                        timepoint, self.time, self.states[..., idx, batch_idx]
                    )
        return values

    def __getitem__(self, time_idx: int) -> Tuple[float, NDArray]:
        """Return the time and state at index idx."""
        if not isinstance(time_idx, int):
            raise TypeError("idx must be int")
        if time_idx < -1 or time_idx >= len(self.time):
            raise ValueError(f"idx must be within 0 and {len(self.time)-1}, got {time_idx}")
        return self.time[time_idx], self.states[time_idx, ...]

    def __len__(self) -> int:
        return len(self.time)

    def get_batch(self, batch_idx: int) -> "DynamicalTrajectory":
        """Obtain the trajectory for a single batch."""
        if not isinstance(batch_idx, int):
            raise TypeError("batch_idx must be int")
        if batch_idx < -1 or batch_idx >= self.batch_size:
            raise ValueError(f"batch_idx must be within -1 and {self.batch_size-1}")
        if self.states.ndim >= 3:
            return DynamicalTrajectory(self.time, self.states[:, :, batch_idx])
        return DynamicalTrajectory(self.time, self.states)

    def __str__(self) -> str:
        time_str = np.array2string(self.time, precision=2, separator=", ", threshold=20)
        states_str = np.array2string(self.states, precision=2, separator=", ", threshold=20)
        return f"Time:\n{time_str}\nStates:\n{states_str}"


def _parameter_input_checking(parameters: dict) -> bool:
    """Validate parameters dictionary."""
    if not isinstance(parameters, dict):
        raise TypeError("parameters must be a dictionary")
    if len(parameters) == 0:
        raise ValueError("parameters must not be empty")
    for key, value in parameters.items():
        if not isinstance(key, str):
            raise TypeError("keys of parameters must be strings")
        if not isinstance(value, (int, float, type(None))):
            raise TypeError("values of parameters must be numeric or None")
    return True


def _positive_int_checking(number: int, name: str) -> bool:
    """Validate positive integer."""
    if not isinstance(number, int):
        raise TypeError(f"{name} must be an integer")
    if number < 1:
        raise ValueError(f"{name} must be positive")
    return True


def _initial_condition_input_checking(initial_condition: NDArray, num_states: int) -> bool:
    """Validate initial condition array."""
    if not isinstance(initial_condition, np.ndarray):
        raise TypeError("initial_condition must be a numpy array")
    if not np.issubdtype(initial_condition.dtype, np.number):
        raise TypeError("initial_condition must be numeric")
    if initial_condition.shape[0] != num_states:
        raise ValueError(f"initial_condition must have length {num_states}")
    if np.any(np.isnan(initial_condition)):
        raise ValueError("initial_condition must not contain NaNs")
    return True


def _model_input_checking(input_arr: NDArray, num_inputs: int, time: NDArray) -> bool:
    """Validate model input array."""
    if not isinstance(input_arr, np.ndarray):
        raise TypeError("input must be a numpy array")
    if not np.issubdtype(input_arr.dtype, np.number):
        raise TypeError("input must be numeric")
    if input_arr.shape[0] != len(time):
        raise ValueError(f"input's first dimension must have length {len(time)}")
    if num_inputs > 1 and input_arr.shape[1] != num_inputs:
        raise ValueError(f"input must have {num_inputs} columns")
    if np.any(np.isnan(input_arr)):
        raise ValueError("input must not contain NaNs")
    return True


def _light_input_checking(light: NDArray) -> bool:
    """Validate light input array."""
    if not isinstance(light, np.ndarray):
        raise TypeError("light must be a numpy array")
    if light.ndim != 1:
        raise ValueError("light must be a 1D array")
    if not np.issubdtype(light.dtype, np.number):
        raise TypeError("light must be numeric")
    if np.any(np.isnan(light)):
        raise ValueError("light must not contain NaNs")
    if not np.all(light >= 0):
        raise ValueError("light intensity must be nonnegative")
    return True


def _check_cbtmin_spacing(cbtmin_times: NDArray, min_spacing: float = 6.0) -> None:
    """Check if the spacing between cbtmin markers is valid."""
    if len(cbtmin_times) > 1:
        cbtmin_spacing = np.diff(cbtmin_times)
        if np.any(cbtmin_spacing < min_spacing):
            warnings.warn(
                f"CBTmin markers spaced by less than {min_spacing} hours detected."
            )


class CircadianModel(ABC):
    """Abstract base class for circadian models."""
    
    def __init__(
        self,
        default_params: dict,
        num_states: int,
        num_inputs: int,
        default_initial_condition: NDArray,
    ) -> None:
        _parameter_input_checking(default_params)
        _positive_int_checking(num_states, "num_states")
        _positive_int_checking(num_inputs, "num_inputs")
        _initial_condition_input_checking(default_initial_condition, num_states)
        
        self._default_params = default_params
        self._parameters = default_params.copy()
        for param_name, param_val in default_params.items():
            setattr(self, param_name, param_val)
        self._num_states = num_states
        self._num_inputs = num_inputs
        self._default_initial_condition = default_initial_condition
        self._trajectory: DynamicalTrajectory | None = None
        self._initial_condition = default_initial_condition
        self._min_marker_distance_in_hours = 13.0

    @property
    def parameters(self) -> dict:
        return self._parameters

    @parameters.setter
    def parameters(self, value: dict) -> None:
        for param_name, param_val in value.items():
            setattr(self, param_name, param_val)
        self._parameters = value

    @property
    def trajectory(self) -> DynamicalTrajectory | None:
        return self._trajectory

    @trajectory.setter
    def trajectory(self, value: DynamicalTrajectory) -> None:
        self._trajectory = value

    @property
    def initial_condition(self) -> NDArray:
        return self._initial_condition

    @initial_condition.setter
    def initial_condition(self, value: NDArray) -> None:
        self._initial_condition = value

    def derv(self, t: float, state: NDArray, input_val: NDArray) -> NDArray:
        """Right-hand-side of the differential equation."""
        raise NotImplementedError("derv must be implemented by subclass")

    def step_rk4(
        self, t: float, state: NDArray, input_val: NDArray, dt: float
    ) -> NDArray:
        """Integrate using fourth-order Runge-Kutta."""
        k1 = self.derv(t, state, input_val)
        k2 = self.derv(t, state + k1 * dt / 2.0, input_val)
        k3 = self.derv(t, state + k2 * dt / 2.0, input_val)
        k4 = self.derv(t, state + k3 * dt, input_val)
        return state + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)

    def integrate(
        self,
        time: NDArray,
        initial_condition: NDArray | None = None,
        input_arr: NDArray | None = None,
    ) -> DynamicalTrajectory:
        """Solve the model for specific timepoints."""
        _time_input_checking(time)
        if input_arr is None:
            raise ValueError("input must be provided")
        _model_input_checking(input_arr, self._num_inputs, time)
        
        if initial_condition is None:
            initial_condition = self._default_initial_condition
        else:
            _initial_condition_input_checking(initial_condition, self._num_states)
        
        self._initial_condition = initial_condition
        n = len(time)
        sol = np.zeros((n, *initial_condition.shape))
        sol[0, ...] = initial_condition
        state = initial_condition.copy()

        for idx in range(1, n):
            t = time[idx]
            dt = t - time[idx - 1]
            input_value = input_arr[idx, ...]
            state = self.step_rk4(t, state, input_value, dt)
            sol[idx, ...] = state

        self._trajectory = DynamicalTrajectory(time, sol)
        return self._trajectory

    def __call__(
        self,
        time: NDArray,
        initial_condition: NDArray | None = None,
        input_arr: NDArray | None = None,
    ) -> DynamicalTrajectory:
        """Wrapper to integrate."""
        return self.integrate(time, initial_condition, input_arr)

    def phase(
        self, trajectory: DynamicalTrajectory | None = None, time: float | None = None
    ) -> float | NDArray:
        """Calculate the phase of the model."""
        raise NotImplementedError("phase must be implemented by subclass")

    def amplitude(
        self, trajectory: DynamicalTrajectory | None = None, time: float | None = None
    ) -> float | NDArray:
        """Calculate the amplitude of the model."""
        raise NotImplementedError("amplitude must be implemented by subclass")

    def cbt(self, trajectory: DynamicalTrajectory | None = None) -> NDArray:
        """Find core body temperature minimum markers."""
        raise NotImplementedError("cbt must be implemented by subclass")

    def dlmos(self, trajectory: DynamicalTrajectory | None = None) -> NDArray:
        """Find Dim Light Melatonin Onset markers."""
        raise NotImplementedError("dlmos must be implemented by subclass")

    def equilibrate(
        self, time: NDArray, input_arr: NDArray, num_loops: int = 10
    ) -> NDArray:
        """Equilibrate the model by looping the given schedule."""
        _time_input_checking(time)
        _model_input_checking(input_arr, self._num_inputs, time)
        _positive_int_checking(num_loops, "num_loops")

        initial_condition = self._default_initial_condition.copy()
        dlmos_list = []
        
        for _ in range(num_loops):
            sol = self.integrate(time, initial_condition, input_arr).states
            dlmos_list.append(self.dlmos())
            initial_condition = sol[-1, ...]

        # Check equilibration
        if len(dlmos_list) >= 2 and len(dlmos_list[-1]) > 0 and len(dlmos_list[-2]) > 0:
            is_equilibrated = np.all(
                np.isclose(dlmos_list[-1][-1], dlmos_list[-2][-1], atol=1e-3)
            )
            if not is_equilibrated:
                warnings.warn("Model did not equilibrate. Try increasing num_loops.")

        return sol[-1, ...]


class Forger99(CircadianModel):
    """Forger et al. (1999) 3-state limit cycle pacemaker model."""

    def __init__(self, params: dict | None = None):
        default_params = {
            "taux": 24.2,
            "mu": 0.23,
            "G": 33.75,
            "alpha_0": 0.05,
            "beta": 0.0075,
            "p": 0.50,
            "I0": 9500.0,
            "k": 0.55,
            "cbt_to_dlmo": 7.0,
        }
        default_ic = np.array([-0.0843259, -1.09607546, 0.45584306])
        super().__init__(default_params, num_states=3, num_inputs=1, default_initial_condition=default_ic)
        if params:
            self.parameters = params

    def integrate(
        self,
        time: NDArray,
        initial_condition: NDArray | None = None,
        input_arr: NDArray | None = None,
    ) -> DynamicalTrajectory:
        if input_arr is not None:
            _light_input_checking(input_arr)
        return super().integrate(time, initial_condition, input_arr)

    def __repr__(self) -> str:
        return "Forger99"

    def __str__(self) -> str:
        return "Forger99"

    def derv(self, t: float, state: NDArray, input_val: float) -> NDArray:
        x, xc, n = state[0, ...], state[1, ...], state[2, ...]
        light = input_val

        alpha = self.alpha_0 * pow(light / self.I0, self.p)
        Bhat = self.G * (1.0 - n) * alpha * (1 - 0.4 * x) * (1 - 0.4 * xc)
        mu_term = self.mu * (xc - 4.0 / 3.0 * pow(xc, 3.0))
        taux_term = pow(24.0 / (0.99669 * self.taux), 2.0) + self.k * Bhat

        dydt = np.zeros_like(state)
        dydt[0, ...] = np.pi / 12.0 * (xc + Bhat)
        dydt[1, ...] = np.pi / 12.0 * (mu_term - x * taux_term)
        dydt[2, ...] = 60.0 * (alpha * (1.0 - n) - self.beta * n)
        return dydt

    def phase(
        self, trajectory: DynamicalTrajectory | None = None, time: float | None = None
    ) -> float | NDArray:
        if trajectory is None:
            trajectory = self.trajectory
        if trajectory is None:
            raise ValueError("No trajectory available")
            
        if time is None:
            x = trajectory.states[:, 0]
            y = -1.0 * trajectory.states[:, 1]
        else:
            state = trajectory(time)
            x, y = state[0], -1.0 * state[1]
        return np.angle(x + 1j * y)

    def amplitude(
        self, trajectory: DynamicalTrajectory | None = None, time: float | None = None
    ) -> float | NDArray:
        if trajectory is None:
            trajectory = self.trajectory
        if trajectory is None:
            raise ValueError("No trajectory available")
            
        if time is None:
            x = trajectory.states[:, 0]
            y = -1.0 * trajectory.states[:, 1]
        else:
            state = trajectory(time)
            x, y = state[0], -1.0 * state[1]
        return np.sqrt(x**2 + y**2)

    def cbt(self, trajectory: DynamicalTrajectory | None = None) -> NDArray:
        if trajectory is None:
            trajectory = self.trajectory
        if trajectory is None:
            raise ValueError("No trajectory available")
            
        dt = np.diff(trajectory.time)[0]
        inverted_x = -1 * trajectory.states[:, 0]
        cbt_min_idxs, _ = find_peaks(
            inverted_x, distance=np.ceil(self._min_marker_distance_in_hours / dt)
        )
        cbtmin_times = trajectory.time[cbt_min_idxs]
        _check_cbtmin_spacing(cbtmin_times)
        return cbtmin_times

    def dlmos(self, trajectory: DynamicalTrajectory | None = None) -> NDArray:
        if trajectory is None:
            trajectory = self.trajectory
        return self.cbt(trajectory) - self.cbt_to_dlmo


class Hannay19(CircadianModel):
    """Hannay et al. (2019) macroscopic amplitude-phase model."""

    def __init__(self, params: dict | None = None):
        default_params = {
            "tau": 23.84,
            "K": 0.06358,
            "gamma": 0.024,
            "Beta1": -0.09318,
            "A1": 0.3855,
            "A2": 0.1977,
            "BetaL1": -0.0026,
            "BetaL2": -0.957756,
            "sigma": 0.0400692,
            "G": 33.75,
            "alpha_0": 0.05,
            "delta": 0.0075,
            "p": 1.5,
            "I0": 9325.0,
            "cbt_to_dlmo": 7.0,
        }
        default_ic = np.array([0.82041911, 1.71383697, 0.52318122])
        super().__init__(default_params, num_states=3, num_inputs=1, default_initial_condition=default_ic)
        if params:
            self.parameters = params

    def integrate(
        self,
        time: NDArray,
        initial_condition: NDArray | None = None,
        input_arr: NDArray | None = None,
    ) -> DynamicalTrajectory:
        if input_arr is not None:
            _light_input_checking(input_arr)
        return super().integrate(time, initial_condition, input_arr)

    def __repr__(self) -> str:
        return "Hannay19"

    def __str__(self) -> str:
        return "Hannay19"

    def derv(self, t: float, state: NDArray, input_val: float) -> NDArray:
        R, Psi, n = state[0, ...], state[1, ...], state[2, ...]
        light = input_val

        alpha = self.alpha_0 * pow(light, self.p) / (pow(light, self.p) + self.I0)
        Bhat = self.G * (1.0 - n) * alpha

        A1_amp = self.A1 * 0.5 * Bhat * (1.0 - pow(R, 4.0)) * np.cos(Psi + self.BetaL1)
        A2_amp = self.A2 * 0.5 * Bhat * R * (1.0 - pow(R, 8.0)) * np.cos(2.0 * Psi + self.BetaL2)
        LightAmp = A1_amp + A2_amp

        A1_phase = self.A1 * Bhat * 0.5 * (pow(R, 3.0) + 1.0 / R) * np.sin(Psi + self.BetaL1)
        A2_phase = self.A2 * Bhat * 0.5 * (1.0 + pow(R, 8.0)) * np.sin(2.0 * Psi + self.BetaL2)
        LightPhase = self.sigma * Bhat - A1_phase - A2_phase

        dydt = np.zeros_like(state)
        dydt[0, ...] = -self.gamma * R + self.K * np.cos(self.Beta1) / 2.0 * R * (1.0 - pow(R, 4.0)) + LightAmp
        dydt[1, ...] = 2 * np.pi / self.tau + self.K / 2.0 * np.sin(self.Beta1) * (1 + pow(R, 4.0)) + LightPhase
        dydt[2, ...] = 60.0 * (alpha * (1.0 - n) - self.delta * n)
        return dydt

    def phase(
        self, trajectory: DynamicalTrajectory | None = None, time: float | None = None
    ) -> float | NDArray:
        if trajectory is None:
            trajectory = self.trajectory
        if trajectory is None:
            raise ValueError("No trajectory available")
            
        if time is None:
            x = np.cos(trajectory.states[:, 1])
            y = np.sin(trajectory.states[:, 1])
        else:
            state = trajectory(time)
            x, y = np.cos(state[1]), np.sin(state[1])
        return np.angle(x + 1j * y)

    def amplitude(
        self, trajectory: DynamicalTrajectory | None = None, time: float | None = None
    ) -> float | NDArray:
        if trajectory is None:
            trajectory = self.trajectory
        if trajectory is None:
            raise ValueError("No trajectory available")
            
        if time is None:
            return trajectory.states[:, 0]
        return trajectory(time)[0]

    def cbt(self, trajectory: DynamicalTrajectory | None = None) -> NDArray:
        if trajectory is None:
            trajectory = self.trajectory
        if trajectory is None:
            raise ValueError("No trajectory available")
            
        dt = np.diff(trajectory.time)[0]
        inverted_x = -np.cos(trajectory.states[:, 1])
        cbt_min_idxs, _ = find_peaks(
            inverted_x, distance=np.ceil(self._min_marker_distance_in_hours / dt)
        )
        cbtmin_times = trajectory.time[cbt_min_idxs]
        _check_cbtmin_spacing(cbtmin_times)
        return cbtmin_times

    def dlmos(self, trajectory: DynamicalTrajectory | None = None) -> NDArray:
        if trajectory is None:
            trajectory = self.trajectory
        return self.cbt(trajectory) - self.cbt_to_dlmo


class Hannay19TP(CircadianModel):
    """Hannay et al. (2019) two-population model."""

    def __init__(self, params: dict | None = None):
        default_params = {
            "tauV": 24.25,
            "tauD": 24.0,
            "Kvv": 0.05,
            "Kdd": 0.04,
            "Kvd": 0.05,
            "Kdv": 0.01,
            "gamma": 0.024,
            "A1": 0.440068,
            "A2": 0.159136,
            "BetaL": 0.06452,
            "BetaL2": -1.38935,
            "sigma": 0.0477375,
            "G": 33.75,
            "alpha_0": 0.05,
            "delta": 0.0075,
            "p": 1.5,
            "I0": 9325.0,
            "cbt_to_dlmo": 7.0,
        }
        default_ic = np.array([0.82423745, 0.82304996, 1.75233424, 1.863457, 0.52318122])
        super().__init__(default_params, num_states=5, num_inputs=1, default_initial_condition=default_ic)
        if params:
            self.parameters = params

    def integrate(
        self,
        time: NDArray,
        initial_condition: NDArray | None = None,
        input_arr: NDArray | None = None,
    ) -> DynamicalTrajectory:
        if input_arr is not None:
            _light_input_checking(input_arr)
        return super().integrate(time, initial_condition, input_arr)

    def __repr__(self) -> str:
        return "Hannay19TP"

    def __str__(self) -> str:
        return "Hannay19TP"

    def derv(self, t: float, state: NDArray, input_val: float) -> NDArray:
        Rv, Rd, Psiv, Psid, n = state[0], state[1], state[2], state[3], state[4]
        light = input_val

        alpha = self.alpha_0 * pow(light, self.p) / (pow(light, self.p) + self.I0)
        Bhat = self.G * (1.0 - n) * alpha

        A1_amp = self.A1 * 0.5 * Bhat * (1.0 - pow(Rv, 4.0)) * np.cos(Psiv + self.BetaL)
        A2_amp = self.A2 * 0.5 * Bhat * Rv * (1.0 - pow(Rv, 8.0)) * np.cos(2.0 * Psiv + self.BetaL2)
        LightAmp = A1_amp + A2_amp

        A1_phase = self.A1 * Bhat * 0.5 * (pow(Rv, 3.0) + 1.0 / Rv) * np.sin(Psiv + self.BetaL)
        A2_phase = self.A2 * Bhat * 0.5 * (1.0 + pow(Rv, 8.0)) * np.sin(2.0 * Psiv + self.BetaL2)
        LightPhase = self.sigma * Bhat - A1_phase - A2_phase

        dydt = np.zeros_like(state)
        dydt[0] = -self.gamma * Rv + self.Kvv / 2.0 * Rv * (1 - pow(Rv, 4.0)) + \
                  self.Kdv / 2.0 * Rd * (1 - pow(Rv, 4.0)) * np.cos(Psid - Psiv) + LightAmp
        dydt[1] = -self.gamma * Rd + self.Kdd / 2.0 * Rd * (1 - pow(Rd, 4.0)) + \
                  self.Kvd / 2.0 * Rv * (1.0 - pow(Rd, 4.0)) * np.cos(Psid - Psiv)
        dydt[2] = 2.0 * np.pi / self.tauV + self.Kdv / 2.0 * Rd * (pow(Rv, 3.0) + 1.0 / Rv) * np.sin(Psid - Psiv) + LightPhase
        dydt[3] = 2.0 * np.pi / self.tauD - self.Kvd / 2.0 * Rv * (pow(Rd, 3.0) + 1.0 / Rd) * np.sin(Psid - Psiv)
        dydt[4] = 60.0 * (alpha * (1.0 - n) - self.delta * n)
        return dydt

    def phase(
        self, trajectory: DynamicalTrajectory | None = None, time: float | None = None
    ) -> float | NDArray:
        if trajectory is None:
            trajectory = self.trajectory
        if trajectory is None:
            raise ValueError("No trajectory available")
            
        if time is None:
            x = np.cos(trajectory.states[:, 2])
            y = np.sin(trajectory.states[:, 2])
        else:
            state = trajectory(time)
            x, y = np.cos(state[2]), np.sin(state[2])
        return np.angle(x + 1j * y)

    def amplitude(
        self, trajectory: DynamicalTrajectory | None = None, time: float | None = None
    ) -> float | NDArray:
        if trajectory is None:
            trajectory = self.trajectory
        if trajectory is None:
            raise ValueError("No trajectory available")
            
        if time is None:
            return trajectory.states[:, 0]
        return trajectory(time)[0]

    def cbt(self, trajectory: DynamicalTrajectory | None = None) -> NDArray:
        if trajectory is None:
            trajectory = self.trajectory
        if trajectory is None:
            raise ValueError("No trajectory available")
            
        dt = np.diff(trajectory.time)[0]
        inverted_x = -np.cos(trajectory.states[:, 2])
        cbt_min_idxs, _ = find_peaks(
            inverted_x, distance=np.ceil(self._min_marker_distance_in_hours / dt)
        )
        cbtmin_times = trajectory.time[cbt_min_idxs]
        _check_cbtmin_spacing(cbtmin_times)
        return cbtmin_times

    def dlmos(self, trajectory: DynamicalTrajectory | None = None) -> NDArray:
        if trajectory is None:
            trajectory = self.trajectory
        return self.cbt(trajectory) - self.cbt_to_dlmo


class Jewett99(CircadianModel):
    """Kronauer et al. (1999) revised limit cycle oscillator model."""

    def __init__(self, params: dict | None = None):
        default_params = {
            "taux": 24.2,
            "mu": 0.13,
            "G": 19.875,
            "beta": 0.013,
            "k": 0.55,
            "q": 1.0 / 3,
            "I0": 9500,
            "p": 0.6,
            "alpha_0": 0.16,
            "phi_ref": 0.8,
            "cbt_to_dlmo": 7.0,
        }
        default_ic = np.array([-0.10097101, -1.21985662, 0.50529415])
        super().__init__(default_params, num_states=3, num_inputs=1, default_initial_condition=default_ic)
        if params:
            self.parameters = params

    def integrate(
        self,
        time: NDArray,
        initial_condition: NDArray | None = None,
        input_arr: NDArray | None = None,
    ) -> DynamicalTrajectory:
        if input_arr is not None:
            _light_input_checking(input_arr)
        return super().integrate(time, initial_condition, input_arr)

    def __repr__(self) -> str:
        return "Jewett99"

    def __str__(self) -> str:
        return "Jewett99"

    def derv(self, t: float, state: NDArray, input_val: float) -> NDArray:
        x, xc, n = state[0, ...], state[1, ...], state[2, ...]
        light = input_val

        alpha = self.alpha_0 * (light / self.I0) ** self.p
        Bhat = self.G * alpha * (1 - n) * (1 - 0.4 * x) * (1 - 0.4 * xc)
        mu_term = self.mu * (1.0 / 3.0 * x + 4.0 / 3.0 * x**3 - 256.0 / 105.0 * x**7)
        taux_term = pow(24.0 / (0.99729 * self.taux), 2) + self.k * Bhat

        dydt = np.zeros_like(state)
        dydt[0, ...] = np.pi / 12 * (xc + mu_term + Bhat)
        dydt[1, ...] = np.pi / 12 * (self.q * Bhat * xc - x * taux_term)
        dydt[2, ...] = 60.0 * (alpha * (1 - n) - self.beta * n)
        return dydt

    def phase(
        self, trajectory: DynamicalTrajectory | None = None, time: float | None = None
    ) -> float | NDArray:
        if trajectory is None:
            trajectory = self.trajectory
        if trajectory is None:
            raise ValueError("No trajectory available")
            
        if time is None:
            x = trajectory.states[:, 0]
            y = -1.0 * trajectory.states[:, 1]
        else:
            state = trajectory(time)
            x, y = state[0], -1.0 * state[1]
        return np.angle(x + 1j * y)

    def amplitude(
        self, trajectory: DynamicalTrajectory | None = None, time: float | None = None
    ) -> float | NDArray:
        if trajectory is None:
            trajectory = self.trajectory
        if trajectory is None:
            raise ValueError("No trajectory available")
            
        if time is None:
            x = trajectory.states[:, 0]
            y = -1.0 * trajectory.states[:, 1]
        else:
            state = trajectory(time)
            x, y = state[0], -1.0 * state[1]
        return np.sqrt(x**2 + y**2)

    def cbt(self, trajectory: DynamicalTrajectory | None = None) -> NDArray:
        if trajectory is None:
            trajectory = self.trajectory
        if trajectory is None:
            raise ValueError("No trajectory available")
            
        dt = np.diff(trajectory.time)[0]
        inverted_x = -1 * trajectory.states[:, 0]
        cbt_min_idxs, _ = find_peaks(
            inverted_x, distance=np.ceil(self._min_marker_distance_in_hours / dt)
        )
        cbtmin_times = trajectory.time[cbt_min_idxs] + self.phi_ref
        _check_cbtmin_spacing(cbtmin_times)
        return cbtmin_times

    def dlmos(self, trajectory: DynamicalTrajectory | None = None) -> NDArray:
        if trajectory is None:
            trajectory = self.trajectory
        return self.cbt(trajectory) - self.cbt_to_dlmo

