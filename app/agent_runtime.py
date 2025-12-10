"""
Structured configuration and bootstrap utilities for the OpenAI Agents SDK.

This module codifies the blueprint described in README.md for embedding
autonomous copilots (Solar-Physiology Correlator, Wearable Recovery Concierge,
Environmental Threat Watcher) into Mission Control - Flight Surgeon.

It provides:
    * Immutable dataclasses for tool definitions, MCP servers, and agent personas
    * A default runtime configuration aligned with the published roadmap
    * A lightweight AgentRuntime helper that can assemble request payloads
      and (optionally) submit them via the OpenAI Agents SDK when credentials
      are available

The goal is to keep the implementation deterministic and analyzable while
preparing the UI to surface upcoming autonomous capabilities.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

try:  # pragma: no cover - optional dependency
    from openai import OpenAI
except ImportError:  # pragma: no cover - optional dependency
    OpenAI = None  # type: ignore[assignment]

try:
    from app.logging_config import get_logger, log_exception
except ImportError:  # pragma: no cover - fallback for utilities
    from logging_config import get_logger, log_exception  # type: ignore

_LOGGER = get_logger(__name__)
_PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True, slots=True)
class AgentToolConfig:
    """Describe a tool that can be attached to an OpenAI Agent."""

    name: str
    tool_type: str
    description: str
    parameters: Mapping[str, Any] = field(default_factory=dict)
    requires_env: tuple[str, ...] = field(default_factory=tuple)

    def to_openai_spec(self) -> Dict[str, Any]:
        """Return the tool specification expected by the OpenAI API."""
        if self.tool_type == "builtin":
            return {"type": self.name}

        param_schema: Mapping[str, Any] = (
            self.parameters
            if self.parameters
            else {"type": "object", "properties": {}, "required": []}
        )
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": param_schema,
            },
        }


@dataclass(frozen=True, slots=True)
class MCPServerConfig:
    """Configuration for a Model Context Protocol server."""

    identifier: str
    root: Path
    mode: str
    description: str


@dataclass(frozen=True, slots=True)
class AgentPersonaConfig:
    """Mission-specific agent persona definition."""

    key: str
    display_name: str
    summary: str
    instructions: str
    tools: tuple[str, ...]
    default_temperature: float = 0.1


@dataclass(frozen=True, slots=True)
class AgentRuntimeConfig:
    """Aggregate configuration for the Agents SDK runtime."""

    model: str
    personas: Mapping[str, AgentPersonaConfig]
    toolbelt: Mapping[str, AgentToolConfig]
    mcp_servers: tuple[MCPServerConfig, ...]
    default_timeout: int = 90


class AgentRuntime:
    """Utility wrapper around the OpenAI Agents SDK."""

    def __init__(
        self,
        config: Optional[AgentRuntimeConfig] = None,
        *,
        client: Optional[Any] = None,
    ) -> None:
        self._config = config or build_default_agent_runtime_config()
        self._client = client or self._build_client()

    def _build_client(self) -> Optional[Any]:
        """Instantiate an OpenAI client when credentials are available."""
        if OpenAI is None:
            _LOGGER.info("OpenAI package not installed; agent runtime disabled")
            return None

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            _LOGGER.info("OPENAI_API_KEY not set; agent runtime inactive")
            return None

        return OpenAI(api_key=api_key)

    def is_available(self) -> bool:
        """Return True when the runtime can submit Agents SDK requests."""
        return self._client is not None

    def build_request_payload(
        self,
        persona_name: str,
        mission_context: Mapping[str, Any],
        user_prompt: str,
    ) -> Dict[str, Any]:
        """
        Assemble a deterministic request payload for the selected persona.
        """
        persona = self._select_persona(persona_name)
        tool_specs = [
            self._config.toolbelt[name].to_openai_spec()
            for name in persona.tools
            if name in self._config.toolbelt
        ]

        serialized_context = json.dumps(
            mission_context,
            indent=2,
            ensure_ascii=False,
            default=str,
        )

        instructions = (
            f"{persona.instructions}\n\n"
            f"Mission Context:\n{serialized_context}\n\n"
            "Respond with deterministic, fully-cited reasoning. "
            "Log every action you recommend."
        )

        metadata: Dict[str, Any] = {
            "persona": persona.key,
            "tools": list(persona.tools),
            "mission_context": dict(mission_context),
            "release": self._config.model,
        }

        return {
            "model": self._config.model,
            "instructions": instructions,
            "tools": tool_specs,
            "messages": [
                {"role": "system", "content": instructions},
                {"role": "user", "content": user_prompt},
            ],
            "metadata": metadata,
            "temperature": persona.default_temperature,
        }

    def run_agent(
        self,
        persona_name: str,
        mission_context: Mapping[str, Any],
        user_prompt: str,
    ) -> Any:
        """
        Submit a request to the Agents SDK (when credentials are configured).
        """
        if self._client is None:
            raise RuntimeError(
                "OpenAI client is unavailable. "
                "Set OPENAI_API_KEY to enable agent executions."
            )

        persona = self._select_persona(persona_name)
        payload = self.build_request_payload(persona_name, mission_context, user_prompt)

        try:
            response = self._client.responses.create(
                model=self._config.model,
                instructions=payload["instructions"],
                input=[{"role": "user", "content": user_prompt}],
                tools=payload["tools"],
                metadata=payload["metadata"],
                temperature=persona.default_temperature,
            )
        except Exception as exc:  # pragma: no cover - network/runtime failures
            log_exception(_LOGGER, "OpenAI Agents SDK request failed", exc)
            raise RuntimeError("OpenAI Agents SDK request failed") from exc

        return response

    def _select_persona(self, persona_name: str) -> AgentPersonaConfig:
        """Return the persona configuration, raising for unknown keys."""
        try:
            return self._config.personas[persona_name]
        except KeyError as exc:  # pragma: no cover - developer error
            raise ValueError(f"Unknown agent persona: {persona_name}") from exc


def build_default_agent_runtime_config() -> AgentRuntimeConfig:
    """Create the default runtime config aligned with the December 2025 plan."""
    toolbelt: Dict[str, AgentToolConfig] = {
        "code_interpreter": AgentToolConfig(
            name="code_interpreter",
            tool_type="builtin",
            description="Managed sandbox with numpy/pandas/scipy for RR arrays.",
        ),
        "file_search": AgentToolConfig(
            name="file_search",
            tool_type="builtin",
            description="Embeddings-backed search over manuals, WARP, and changelog.",
        ),
        "web_search": AgentToolConfig(
            name="web_search",
            tool_type="builtin",
            description="Mission-safe search (NASA ADS, SWPC, PubMed).",
        ),
        "wolfram_alpha": AgentToolConfig(
            name="wolfram_alpha",
            tool_type="function",
            description=(
                "Symbolic and numeric Wolfram Alpha reasoning for solar wind, "
                "ionospheric absorption, and countermeasure math."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Plain-language expression to evaluate.",
                    }
                },
                "required": ["query"],
            },
            requires_env=("WOLFRAM_APP_ID",),
        ),
        "e2b_simulator": AgentToolConfig(
            name="e2b_simulator",
            tool_type="function",
            description=(
                "Launch a deterministic E2B sandbox (Python 3.12) seeded with "
                "mission parameters for long-running simulations."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "scenario": {
                        "type": "string",
                        "description": "Short name describing the simulation goal.",
                    },
                    "duration_hours": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 72,
                        "description": "Expected runtime of the sandbox task.",
                    },
                },
                "required": ["scenario", "duration_hours"],
            },
            requires_env=("E2B_API_KEY",),
        ),
        "noaa_data_gateway": AgentToolConfig(
            name="noaa_data_gateway",
            tool_type="function",
            description=(
                "Read-only access to cached NOAA SWPC/DONKI feeds via the "
                "existing deterministic ingestion stack."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "resource": {
                        "type": "string",
                        "enum": ["kp_index", "dst", "solar_wind", "f10_7"],
                        "description": "Data stream to refresh or query.",
                    },
                    "hours": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 72,
                        "description": "Lookback window in hours.",
                    },
                },
                "required": ["resource"],
            },
        ),
    }

    mcp_servers = (
        MCPServerConfig(
            identifier="mcp://hrv-db",
            root=_PROJECT_ROOT / "hrv_users.db",
            mode="ro",
            description="SQLite views for RR uploads, cohort aggregates, and radiation logs.",
        ),
        MCPServerConfig(
            identifier="mcp://docs",
            root=_PROJECT_ROOT / "docs",
            mode="ro",
            description="Pinned commit of docs/Manual.md, WARP.md, and scientific PDFs.",
        ),
        MCPServerConfig(
            identifier="mcp://space-weather-cache",
            root=_PROJECT_ROOT / "app" / "data_cache" / "noaa_space",
            mode="ro",
            description="Stale-tolerant cache of NOAA/SWPC JSON bundles with TTL metadata.",
        ),
    )

    personas: Dict[str, AgentPersonaConfig] = {
        "solar_physiology_correlator": AgentPersonaConfig(
            key="solar_physiology_correlator",
            display_name="Solar-Physiology Correlator",
            summary=(
                "Scans RR intervals against NOAA/DONKI predictors, computes lag-aware "
                "correlations, and escalates |r|>0.6 findings (FDR q<0.05)."
            ),
            instructions=(
                "You align RR recordings with cached NOAA SWPC and DONKI feeds, "
                "compute Pearson/Spearman correlations across 0-72h lags, and "
                "recommend mitigations only when statistics are reproducible. "
                "Always cite NOAA bundle timestamps and retain raw artifacts in /tmp/agents."
            ),
            tools=("code_interpreter", "file_search", "noaa_data_gateway", "wolfram_alpha"),
            default_temperature=0.05,
        ),
        "wearable_recovery_concierge": AgentPersonaConfig(
            key="wearable_recovery_concierge",
            display_name="Wearable Recovery Concierge",
            summary=(
                "Transforms Garmin/Polar wellness data into operational prescriptions "
                "for hydration, EVA readiness, and countermeasures."
            ),
            instructions=(
                "Fuse Garmin wellness histories, user clinical baselines, and Manual norms "
                "to produce bounded, checklist-style recommendations. Validate every "
                "threshold against docs/Manual.md and cite relevant tables."
            ),
            tools=("file_search", "code_interpreter", "wolfram_alpha"),
            default_temperature=0.2,
        ),
        "environmental_threat_watcher": AgentPersonaConfig(
            key="environmental_threat_watcher",
            display_name="Environmental Threat Watcher",
            summary=(
                "Combines NOAA alerts, SpaceWeatherLive cache, and E2B radiation simulations "
                "to warn when atmospheric or geomagnetic disturbances endanger readiness."
            ),
            instructions=(
                "Continuously query cached NOAA data, SpaceWeatherLive summaries, and "
                "run E2B Monte Carlo jobs when significant anomalies appear. Output "
                "structured JSON with severity, evidence, and countermeasures. "
                "Never assume WAN availability—degrade gracefully to cached data."
            ),
            tools=(
                "web_search",
                "file_search",
                "noaa_data_gateway",
                "e2b_simulator",
                "wolfram_alpha",
            ),
            default_temperature=0.15,
        ),
    }

    model = os.getenv("OPENAI_AGENT_MODEL", "gpt-5.1-experimental")

    return AgentRuntimeConfig(
        model=model,
        personas=personas,
        toolbelt=toolbelt,
        mcp_servers=mcp_servers,
        default_timeout=90,
    )


__all__ = [
    "AgentRuntime",
    "AgentRuntimeConfig",
    "AgentPersonaConfig",
    "AgentToolConfig",
    "MCPServerConfig",
    "build_default_agent_runtime_config",
]
