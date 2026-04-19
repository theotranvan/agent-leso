"""Parser CECB XML v5 → SimulationResult.

CECB (Certificat Énergétique Cantonal des Bâtiments) est le standard suisse
de certification énergétique des bâtiments. L'export v5 est un XML structuré
contenant les résultats de calcul SIA 380/1 + classification A→G.

Champs extraits :
- Qh : besoin de chaleur pour chauffage (kWh/m²·an)
- Ep / Et : énergie primaire totale
- Classe globale enveloppe + globale (A→G)
- IDC calculé (kWh/m²·an)
- SRE du bâtiment
- Affectation

Le schéma CECB n'étant pas publiquement normalisé de façon exhaustive, ce parser
est tolérant aux variations de balises (tags alternatifs acceptés pour chaque champ).
"""
from __future__ import annotations

import logging
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.connectors.thermic.base import (
    ConnectorError,
    EnergyClass,
    SimulationResult,
    ThermicConnector,
    ThermicInputs,
    limite_qh_for_affectation,
)

logger = logging.getLogger(__name__)


@dataclass
class CecbRawData:
    """Données brutes extraites du XML avant normalisation."""

    qh_kwh_m2_an: float | None = None
    ep_kwh_m2_an: float | None = None
    et_kwh_m2_an: float | None = None
    idc_kwh_m2_an: float | None = None
    sre_m2: float | None = None
    class_envelope: str | None = None
    class_global: str | None = None
    affectation: str | None = None
    canton: str | None = None
    cecb_id: str | None = None


# Tags alternatifs pour chaque champ - ordre de préférence
TAG_CANDIDATES: dict[str, list[str]] = {
    "qh": ["Qh", "QH", "BesoinChaleur", "HeatingDemand", "qh_kwh_m2"],
    "ep": ["Ep", "EP", "EnergiePrimaire", "PrimaryEnergy", "ep_kwh_m2"],
    "et": ["Et", "ET", "EnergieTotale", "TotalEnergy", "et_kwh_m2"],
    "idc": ["IDC", "IndiceDepenseChaleur", "idc_kwh_m2", "idc_mj_m2"],
    "sre": ["SRE", "Sre", "SurfaceReferenceEnergetique", "ReferenceArea", "sre_m2"],
    "class_envelope": ["ClasseEnveloppe", "EnvelopeClass", "classe_enveloppe"],
    "class_global": ["ClasseGlobale", "GlobalClass", "classe_globale", "Classification"],
    "affectation": ["Affectation", "Usage", "BuildingUse", "categorie"],
    "canton": ["Canton", "canton"],
    "cecb_id": ["NumeroCECB", "CecbId", "CertificateId", "id"],
}


class CecbParser(ThermicConnector):
    """Parse un CECB XML v5 et retourne un SimulationResult."""

    name = "cecb_parser"

    def validate_inputs(self, inputs: ThermicInputs) -> list[str]:
        """Pour CecbParser, 'ifc_path' est en fait le chemin du XML CECB."""
        warnings: list[str] = []
        if not inputs.ifc_path.exists():
            raise ConnectorError(f"Fichier CECB introuvable : {inputs.ifc_path}")
        if inputs.ifc_path.suffix.lower() not in {".xml", ".cecb"}:
            warnings.append(f"Extension inhabituelle pour CECB : {inputs.ifc_path.suffix}")
        size = inputs.ifc_path.stat().st_size
        if size < 100:
            raise ConnectorError("Fichier CECB vide ou tronqué")
        if size > 10 * 1024 * 1024:
            warnings.append("Fichier CECB volumineux (>10 MB)")
        return warnings

    def simulate(self, inputs: ThermicInputs) -> SimulationResult:
        """Parse le XML et retourne le résultat."""
        start = time.monotonic()
        warnings = self.validate_inputs(inputs)

        raw = self.parse_file(inputs.ifc_path, warnings)

        # Conversion MJ→kWh si l'IDC semble être en MJ (>1000 suspect)
        if raw.idc_kwh_m2_an is not None and raw.idc_kwh_m2_an > 1000:
            raw.idc_kwh_m2_an = raw.idc_kwh_m2_an / 3.6
            warnings.append("IDC semble être en MJ/m²·an, converti en kWh/m²·an")

        if raw.qh_kwh_m2_an is None:
            raise ConnectorError("Qh introuvable dans le CECB XML")
        if raw.sre_m2 is None or raw.sre_m2 <= 0:
            raise ConnectorError("SRE introuvable ou invalide dans le CECB XML")

        qh_limite = limite_qh_for_affectation(
            raw.affectation or inputs.affectation,
        )
        compliant = None
        if qh_limite is not None and raw.qh_kwh_m2_an is not None:
            compliant = raw.qh_kwh_m2_an <= qh_limite

        energy_class = self._parse_class(raw.class_global or raw.class_envelope)
        elapsed = time.monotonic() - start

        logger.info(
            "CECB parsé : Qh=%.1f, classe=%s, SRE=%.0f m² en %.2fs",
            raw.qh_kwh_m2_an, energy_class, raw.sre_m2, elapsed,
        )

        return SimulationResult(
            qh_kwh_m2_an=raw.qh_kwh_m2_an,
            ep_kwh_m2_an=raw.ep_kwh_m2_an or raw.et_kwh_m2_an or raw.qh_kwh_m2_an * 1.2,
            sre_m2=raw.sre_m2,
            idc_kwh_m2_an=raw.idc_kwh_m2_an,
            qh_limite_kwh_m2_an=qh_limite,
            energy_class=energy_class,
            compliant=compliant,
            engine_used=self.name,
            computation_seconds=elapsed,
            warnings=warnings,
            raw_output={
                "cecb_id": raw.cecb_id,
                "affectation_detected": raw.affectation,
                "canton_detected": raw.canton,
                "class_envelope": raw.class_envelope,
                "class_global": raw.class_global,
            },
        )

    def parse_file(self, xml_path: Path, warnings: list[str]) -> CecbRawData:
        """Parse effectif du fichier - exposé pour réutilisation."""
        try:
            tree = ET.parse(xml_path)
        except ET.ParseError as exc:
            raise ConnectorError(f"CECB XML malformé : {exc}") from exc

        root = tree.getroot()
        raw = CecbRawData()

        # Extraction floats
        raw.qh_kwh_m2_an = self._find_float(root, TAG_CANDIDATES["qh"], warnings)
        raw.ep_kwh_m2_an = self._find_float(root, TAG_CANDIDATES["ep"], warnings)
        raw.et_kwh_m2_an = self._find_float(root, TAG_CANDIDATES["et"], warnings)
        raw.idc_kwh_m2_an = self._find_float(root, TAG_CANDIDATES["idc"], warnings)
        raw.sre_m2 = self._find_float(root, TAG_CANDIDATES["sre"], warnings)

        # Extraction strings
        raw.class_envelope = self._find_text(root, TAG_CANDIDATES["class_envelope"])
        raw.class_global = self._find_text(root, TAG_CANDIDATES["class_global"])
        raw.affectation = self._normalize_affectation(
            self._find_text(root, TAG_CANDIDATES["affectation"])
        )
        raw.canton = self._find_text(root, TAG_CANDIDATES["canton"])
        raw.cecb_id = self._find_text(root, TAG_CANDIDATES["cecb_id"])

        return raw

    @staticmethod
    def _find_text(root: ET.Element, tag_candidates: list[str]) -> str | None:
        """Cherche le premier texte non vide parmi les tags candidats."""
        for tag in tag_candidates:
            # Recherche ignorant le namespace
            for el in root.iter():
                local = el.tag.split("}")[-1] if "}" in el.tag else el.tag
                if local == tag and el.text and el.text.strip():
                    return el.text.strip()
        return None

    @classmethod
    def _find_float(
        cls,
        root: ET.Element,
        tag_candidates: list[str],
        warnings: list[str],
    ) -> float | None:
        txt = cls._find_text(root, tag_candidates)
        if txt is None:
            return None
        # Retire unités incluses (ex: "95.3 kWh/m²a")
        numeric = re.sub(r"[^\d.,\-]", "", txt).replace(",", ".")
        if not numeric:
            return None
        try:
            return float(numeric)
        except ValueError:
            warnings.append(f"Impossible de parser '{txt}' en nombre")
            return None

    @staticmethod
    def _parse_class(class_str: str | None) -> EnergyClass | None:
        if not class_str:
            return None
        letter = class_str.strip().upper()[:1]
        try:
            return EnergyClass(letter)
        except ValueError:
            return None

    @staticmethod
    def _normalize_affectation(raw: str | None) -> str | None:
        if not raw:
            return None
        lower = raw.lower()
        if "habit" in lower or "logement" in lower:
            return "logement_collectif" if "collectif" in lower or "collective" in lower or "multi" in lower \
                else "logement_individuel"
        if "admin" in lower or "bureau" in lower or "office" in lower:
            return "administration"
        if "école" in lower or "ecole" in lower or "school" in lower:
            return "ecole"
        if "commerce" in lower or "retail" in lower:
            return "commerce"
        if "industr" in lower:
            return "industriel"
        return lower.replace(" ", "_")
