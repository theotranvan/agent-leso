"""Connecteur Scia Engineer via watched-folder + SAF.

Scia Engineer (Nemetschek) supporte nativement l'import/export SAF.
Principe similaire à Lesosai : on écrit le SAF dans un dossier surveillé,
l'opérateur ouvre Scia, calcule, et exporte un SAF enrichi.

Config :
  SCIA_WATCH_INPUT_DIR  : dossier d'entrée (/tmp/scia/in)
  SCIA_WATCH_OUTPUT_DIR : dossier de sortie (/tmp/scia/out)
  SCIA_POLL_INTERVAL_SECONDS : défaut 10
  SCIA_TIMEOUT_SECONDS : défaut 1800
"""
from __future__ import annotations

import logging
import os
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from app.connectors.structural.base import (
    AnalysisResult,
    ConnectorError,
    ConnectorTimeoutError,
    StructuralConnector,
    StructuralInputs,
)
from app.connectors.structural.results_parser import SafResultsParser
from app.connectors.structural.saf_generator import SafGenerator

logger = logging.getLogger(__name__)

DEFAULT_SCIA_INPUT: Final = "/tmp/scia/in"
DEFAULT_SCIA_OUTPUT: Final = "/tmp/scia/out"
DEFAULT_SCIA_POLL: Final = 10
DEFAULT_SCIA_TIMEOUT: Final = 1800


@dataclass(frozen=True)
class SciaConfig:
    input_dir: Path
    output_dir: Path
    poll_interval_seconds: int
    timeout_seconds: int


def load_scia_config() -> SciaConfig:
    return SciaConfig(
        input_dir=Path(os.environ.get("SCIA_WATCH_INPUT_DIR", DEFAULT_SCIA_INPUT)),
        output_dir=Path(os.environ.get("SCIA_WATCH_OUTPUT_DIR", DEFAULT_SCIA_OUTPUT)),
        poll_interval_seconds=int(os.environ.get("SCIA_POLL_INTERVAL_SECONDS", str(DEFAULT_SCIA_POLL))),
        timeout_seconds=int(os.environ.get("SCIA_TIMEOUT_SECONDS", str(DEFAULT_SCIA_TIMEOUT))),
    )


class SciaConnector(StructuralConnector):
    """IFC/modèle → SAF → Scia (externe) → SAF enrichi → double-check → AnalysisResult."""

    name = "scia_watched_folder"

    def __init__(self, config: SciaConfig | None = None) -> None:
        self.config = config or load_scia_config()
        self.saf_gen = SafGenerator()
        self.parser = SafResultsParser()

    def validate_inputs(self, inputs: StructuralInputs) -> list[str]:
        warnings = self.saf_gen.validate_inputs(inputs)
        if not self.config.input_dir.exists():
            self.config.input_dir.mkdir(parents=True, exist_ok=True)
        if not self.config.output_dir.exists():
            self.config.output_dir.mkdir(parents=True, exist_ok=True)
        if self.config.poll_interval_seconds < 1:
            raise ConnectorError("poll_interval_seconds doit être >= 1")
        if self.config.timeout_seconds < self.config.poll_interval_seconds:
            raise ConnectorError("timeout_seconds < poll_interval_seconds")
        return warnings

    def analyze(self, inputs: StructuralInputs) -> AnalysisResult:
        start = time.monotonic()
        warnings = self.validate_inputs(inputs)

        job_id = f"scia_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        input_path = self._write_saf(inputs, job_id)
        logger.info("Scia input écrit : %s", input_path)

        effective_timeout = min(inputs.timeout_seconds, self.config.timeout_seconds)
        result_path = self._wait_for_result(job_id, effective_timeout)
        logger.info("Scia result reçu : %s", result_path)

        # Parse + double-check
        result = self.parser.parse_and_check(
            saf_input=input_path,
            saf_output=result_path,
            model_data=inputs.model_data if inputs.model_data else {},
        )
        result.engine_used = self.name
        result.computation_seconds = time.monotonic() - start
        result.warnings = warnings + result.warnings
        result.raw_output["job_id"] = job_id
        result.raw_output["input_path"] = str(input_path)
        result.raw_output["output_path"] = str(result_path)
        return result

    def _write_saf(self, inputs: StructuralInputs, job_id: str) -> Path:
        xlsx_bytes = self.saf_gen.generate_saf_bytes(inputs)
        target = self.config.input_dir / f"{job_id}.xlsx"
        target.write_bytes(xlsx_bytes)

        import json as _json
        meta = {
            "job_id": job_id,
            "referentiel": inputs.referentiel,
            "exposure_class": inputs.exposure_class,
            "consequence_class": inputs.consequence_class,
            "seismic_zone": inputs.seismic_zone,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        (self.config.input_dir / f"{job_id}.json").write_text(
            _json.dumps(meta, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return target

    def _wait_for_result(self, job_id: str, timeout_seconds: int) -> Path:
        deadline = time.monotonic() + timeout_seconds
        poll = self.config.poll_interval_seconds
        attempts = 0

        while time.monotonic() < deadline:
            attempts += 1
            for path in sorted(self.config.output_dir.iterdir()):
                if not path.is_file():
                    continue
                if not path.name.startswith(job_id):
                    continue
                if path.suffix.lower() != ".xlsx":
                    continue
                if self._file_is_stable(path):
                    return path

            if attempts % 6 == 0:
                logger.info(
                    "Scia polling job=%s (%ds timeout)", job_id, timeout_seconds,
                )
            time.sleep(poll)

        raise ConnectorTimeoutError(
            f"Aucun résultat Scia pour job={job_id} après {timeout_seconds}s"
        )

    @staticmethod
    def _file_is_stable(path: Path, check_seconds: float = 2.0) -> bool:
        try:
            s1 = path.stat().st_size
            time.sleep(check_seconds)
            s2 = path.stat().st_size
            return s1 == s2 and s1 > 0
        except FileNotFoundError:
            return False
