"""Connecteur Lesosai en mode watched-folder.

Principe :
1. BET Agent écrit un fichier d'entrée (gbXML ou XML natif Lesosai) dans INPUT_DIR
2. L'opérateur (humain ou script Lesosai) ouvre Lesosai, importe, calcule, exporte
   le rapport CECB XML dans OUTPUT_DIR avec le même identifiant.
3. Ce connecteur poll OUTPUT_DIR toutes les 10 secondes jusqu'à 30 min par défaut.
4. Quand le fichier résultat apparaît, il est parsé via CecbParser.

Config (variables d'environnement) :
  LESOSAI_WATCH_INPUT_DIR  : dossier où écrire les inputs (par défaut /tmp/lesosai/in)
  LESOSAI_WATCH_OUTPUT_DIR : dossier où Lesosai dépose les résultats (/tmp/lesosai/out)
  LESOSAI_POLL_INTERVAL_SECONDS : défaut 10
  LESOSAI_TIMEOUT_SECONDS : défaut 1800 (30 min)

Ce connecteur convient au scénario B du plan V2 (E4tech Lausanne sans API publique).
"""
from __future__ import annotations

import logging
import os
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from app.connectors.thermic.base import (
    ConnectorError,
    ConnectorTimeoutError,
    SimulationResult,
    ThermicConnector,
    ThermicInputs,
)
from app.connectors.thermic.cecb_parser import CecbParser
from app.connectors.thermic.gbxml_generator import GbxmlGenerator

logger = logging.getLogger(__name__)

DEFAULT_INPUT_DIR: Final = "/tmp/lesosai/in"
DEFAULT_OUTPUT_DIR: Final = "/tmp/lesosai/out"
DEFAULT_POLL_SECONDS: Final = 10
DEFAULT_TIMEOUT_SECONDS: Final = 1800
RESULT_EXTENSIONS: Final = (".xml", ".cecb")


@dataclass(frozen=True)
class LesosaiWatchedFolderConfig:
    input_dir: Path
    output_dir: Path
    poll_interval_seconds: int
    timeout_seconds: int


def load_config() -> LesosaiWatchedFolderConfig:
    return LesosaiWatchedFolderConfig(
        input_dir=Path(os.environ.get("LESOSAI_WATCH_INPUT_DIR", DEFAULT_INPUT_DIR)),
        output_dir=Path(os.environ.get("LESOSAI_WATCH_OUTPUT_DIR", DEFAULT_OUTPUT_DIR)),
        poll_interval_seconds=int(os.environ.get("LESOSAI_POLL_INTERVAL_SECONDS", str(DEFAULT_POLL_SECONDS))),
        timeout_seconds=int(os.environ.get("LESOSAI_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS))),
    )


class LesosaiFileConnector(ThermicConnector):
    """Écrit l'input dans un dossier surveillé, attend la réponse, parse le CECB."""

    name = "lesosai_watched_folder"

    def __init__(self, config: LesosaiWatchedFolderConfig | None = None) -> None:
        self.config = config or load_config()
        self.gbxml = GbxmlGenerator()
        self.cecb = CecbParser()

    def validate_inputs(self, inputs: ThermicInputs) -> list[str]:
        warnings = self.gbxml.validate_inputs(inputs)
        if not self.config.input_dir.exists():
            self.config.input_dir.mkdir(parents=True, exist_ok=True)
            warnings.append(f"INPUT_DIR créé : {self.config.input_dir}")
        if not self.config.output_dir.exists():
            self.config.output_dir.mkdir(parents=True, exist_ok=True)
            warnings.append(f"OUTPUT_DIR créé : {self.config.output_dir}")
        if self.config.poll_interval_seconds < 1:
            raise ConnectorError("poll_interval_seconds doit être >= 1")
        if self.config.timeout_seconds < self.config.poll_interval_seconds:
            raise ConnectorError("timeout_seconds < poll_interval_seconds")
        return warnings

    def simulate(self, inputs: ThermicInputs) -> SimulationResult:
        start = time.monotonic()
        warnings = self.validate_inputs(inputs)

        job_id = self._new_job_id()
        input_file = self._write_input(inputs, job_id)
        logger.info("Lesosai input écrit : %s", input_file)

        effective_timeout = min(inputs.timeout_seconds, self.config.timeout_seconds)
        result_file = self._wait_for_result(job_id, effective_timeout)
        logger.info("Lesosai result reçu : %s (après %.1fs)", result_file, time.monotonic() - start)

        # Parsing via CecbParser - on passe le même ThermicInputs mais avec le path résultat
        parse_inputs = ThermicInputs(
            ifc_path=result_file,
            canton=inputs.canton,
            affectation=inputs.affectation,
            operation_type=inputs.operation_type,
            standard=inputs.standard,
            sre_m2=inputs.sre_m2,
            heating_vector=inputs.heating_vector,
            hypotheses=inputs.hypotheses,
            timeout_seconds=inputs.timeout_seconds,
        )
        result = self.cecb.simulate(parse_inputs)

        result.engine_used = self.name
        result.computation_seconds = time.monotonic() - start
        result.warnings = warnings + result.warnings + [
            f"Traitement via watched-folder : input={input_file.name}, output={result_file.name}",
        ]
        result.raw_output["job_id"] = job_id
        result.raw_output["input_file"] = str(input_file)
        result.raw_output["result_file"] = str(result_file)
        return result

    @staticmethod
    def _new_job_id() -> str:
        return f"betagent_{int(time.time())}_{uuid.uuid4().hex[:8]}"

    def _write_input(self, inputs: ThermicInputs, job_id: str) -> Path:
        """Génère le gbXML et l'écrit dans INPUT_DIR avec nommage conventionnel."""
        xml_bytes = self.gbxml.generate_gbxml_bytes(inputs)
        filename = f"{job_id}.gbxml"
        target = self.config.input_dir / filename
        target.write_bytes(xml_bytes)

        # Fichier sidecar .json pour faciliter l'identification côté opérateur
        import json
        meta = {
            "job_id": job_id,
            "source_ifc": str(inputs.ifc_path),
            "canton": inputs.canton,
            "affectation": inputs.affectation,
            "operation_type": inputs.operation_type,
            "standard": inputs.standard,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        (self.config.input_dir / f"{job_id}.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return target

    def _wait_for_result(self, job_id: str, timeout_seconds: int) -> Path:
        """Poll OUTPUT_DIR jusqu'à trouver un fichier commençant par job_id."""
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
                if path.suffix.lower() not in RESULT_EXTENSIONS:
                    continue
                # Check que le fichier est stable (pas en cours d'écriture)
                if self._file_is_stable(path):
                    return path

            elapsed = int(timeout_seconds - (deadline - time.monotonic()))
            if attempts % 6 == 0:  # log toutes les ~60s
                logger.info(
                    "Lesosai polling attente job=%s (%ds écoulés / %ds timeout)",
                    job_id, elapsed, timeout_seconds,
                )
            time.sleep(poll)

        raise ConnectorTimeoutError(
            f"Aucun résultat Lesosai reçu pour job={job_id} après {timeout_seconds}s "
            f"(OUTPUT_DIR={self.config.output_dir})"
        )

    @staticmethod
    def _file_is_stable(path: Path, check_seconds: float = 2.0) -> bool:
        """Vérifie que la taille du fichier ne change pas sur check_seconds."""
        try:
            size1 = path.stat().st_size
            time.sleep(check_seconds)
            size2 = path.stat().st_size
            return size1 == size2 and size1 > 0
        except FileNotFoundError:
            return False
