"""
Health Endpoints - Phase 7: Observability and Performance
Health checks, readiness probes, liveness probes for Kubernetes.
"""

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any


class HealthStatus(Enum):
    """Health status values."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ComponentHealth:
    """Health status of a component."""

    name: str
    status: HealthStatus
    message: str = ""
    details: dict = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}


class ReadinessProbe:
    """Readiness probe checks if service can handle requests."""

    def __init__(self):
        self._checks = []

    def add_check(self, name: str, check_fn):
        """Add a readiness check."""
        self._checks.append((name, check_fn))

    def check(self) -> ComponentHealth:
        """Run all readiness checks."""
        all_healthy = True
        details = {}

        for name, check_fn in self._checks:
            try:
                result = check_fn()
                details[name] = {"status": "ok" if result else "failed"}
                if not result:
                    all_healthy = False
            except Exception as e:
                details[name] = {"status": "error", "error": str(e)}
                all_healthy = False

        status = HealthStatus.HEALTHY if all_healthy else HealthStatus.DEGRADED

        return ComponentHealth(
            name="readiness",
            status=status,
            message="Ready to serve traffic" if all_healthy else "Not ready",
            details=details,
        )


class LivenessProbe:
    """Liveness probe checks if service is alive."""

    def __init__(self):
        self._checks = []

    def add_check(self, name: str, check_fn):
        """Add a liveness check."""
        self._checks.append((name, check_fn))

    def check(self) -> ComponentHealth:
        """Run all liveness checks."""
        all_healthy = True
        details = {}

        for name, check_fn in self._checks:
            try:
                result = check_fn()
                details[name] = {"status": "ok" if result else "failed"}
                if not result:
                    all_healthy = False
            except Exception as e:
                details[name] = {"status": "error", "error": str(e)}
                all_healthy = False

        status = HealthStatus.HEALTHY if all_healthy else HealthStatus.UNHEALTHY

        return ComponentHealth(
            name="liveness",
            status=status,
            message="Service is alive" if all_healthy else "Service needs restart",
            details=details,
        )


class HealthChecker:
    """
    Main health checker with all probes.
    """

    def __init__(self, wiki_path: str = "knowledge/wiki"):
        self.wiki_path = wiki_path
        self.readiness_probe = ReadinessProbe()
        self.liveness_probe = LivenessProbe()
        self._setup_default_checks()

    def _setup_default_checks(self):
        """Setup default health checks."""
        self.readiness_probe.add_check("index_available", self._check_index_exists)
        self.readiness_probe.add_check("wiki_accessible", self._check_wiki_accessible)

        self.liveness_probe.add_check("process_alive", self._check_process_alive)

    def _check_index_exists(self) -> bool:
        """Check if index file exists."""
        index_path = Path(".metadata") / "keyword_index.json"
        return index_path.exists()

    def _check_wiki_accessible(self) -> bool:
        """Check if wiki directory is accessible."""
        wiki_dir = Path(self.wiki_path)
        if not wiki_dir.exists():
            return False
        return os.access(wiki_dir, os.R_OK)

    def _check_process_alive(self) -> bool:
        """Check if process is alive."""
        return True

    def check_readiness(self) -> ComponentHealth:
        """Check readiness."""
        return self.readiness_probe.check()

    def check_liveness(self) -> ComponentHealth:
        """Check liveness."""
        return self.liveness_probe.check()

    def get_health(self) -> dict:
        """Get complete health status."""
        readiness = self.check_readiness()
        liveness = self.check_liveness()

        overall = HealthStatus.HEALTHY
        if liveness.status == HealthStatus.UNHEALTHY:
            overall = HealthStatus.UNHEALTHY
        elif readiness.status == HealthStatus.DEGRADED:
            overall = HealthStatus.DEGRADED

        return {
            "status": overall.value,
            "readiness": {
                "status": readiness.status.value,
                "message": readiness.message,
                "details": readiness.details,
            },
            "liveness": {
                "status": liveness.status.value,
                "message": liveness.message,
                "details": liveness.details,
            },
        }

    def is_ready(self) -> bool:
        """Quick check if service is ready."""
        return self.check_readiness().status == HealthStatus.HEALTHY

    def is_alive(self) -> bool:
        """Quick check if service is alive."""
        return self.check_liveness().status == HealthStatus.HEALTHY
