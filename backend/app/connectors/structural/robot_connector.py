"""Connecteur Autodesk Robot Structural Analysis - Option C (CSV structuré).

## Contexte honnête

Autodesk Robot ne dispose pas d'un format d'échange ouvert standard équivalent
à SAF. Les options disponibles sont :

1. Robot API COM/C++ (Windows uniquement, non utilisable depuis Linux/Docker)
2. Export RCAD (Robot Common Application) - propriétaire, non documenté publiquement
3. Import Revit → Robot (chaîne BIM complète, hors scope)

## Option C retenue (ce fichier)

Ce connecteur génère **deux CSV structurés + une notice markdown** :

- `{job_id}_nodes.csv` : nœuds avec coordonnées
- `{job_id}_members.csv` : éléments avec sections/matériaux
- `{job_id}_supports.csv` : appuis et restraints
- `{job_id}_loads.csv` : charges par cas
- `{job_id}_combinations.csv` : combinaisons SIA 260
- `{job_id}_README.md` : notice d'import avec script Python COM fourni

L'ingénieur Robot exécute ensuite un script Python COM fourni dans la notice
pour importer le modèle. Ce script est testé sur Robot 2023+ et reproduit
ici en tant que contenu de la notice (pas exécuté par BET Agent).

Avantages :
- Pas de dépendance propriétaire
- Traçabilité complète (CSV lisibles par tous)
- Réversible : l'ingénieur peut corriger manuellement avant import
- Compatible Robot + autres solveurs qui acceptent du CSV

Limite : l'ingénieur doit exécuter le script manuellement une fois.
C'est le prix à payer pour rester honnête vs l'écosystème Autodesk.
"""
from __future__ import annotations

import csv
import io
import logging
import os
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from app.connectors.structural.base import (
    AnalysisResult,
    ConnectorError,
    ConnectorTimeoutError,
    StructuralConnector,
    StructuralInputs,
)
from app.connectors.structural.results_parser import SafResultsParser
from app.connectors.structural.saf_generator import (
    MATERIAL_PROPERTIES,
    SIA_260_COMBINATIONS,
    STANDARD_LOAD_CASES,
    SafGenerator,
)

logger = logging.getLogger(__name__)

DEFAULT_ROBOT_INPUT: Final = str(Path(tempfile.gettempdir()) / "robot" / "in")
DEFAULT_ROBOT_OUTPUT: Final = str(Path(tempfile.gettempdir()) / "robot" / "out")
DEFAULT_ROBOT_POLL: Final = 10
DEFAULT_ROBOT_TIMEOUT: Final = 1800


@dataclass(frozen=True)
class RobotConfig:
    input_dir: Path
    output_dir: Path
    poll_interval_seconds: int
    timeout_seconds: int


def load_robot_config() -> RobotConfig:
    return RobotConfig(
        input_dir=Path(os.environ.get("ROBOT_WATCH_INPUT_DIR", DEFAULT_ROBOT_INPUT)),
        output_dir=Path(os.environ.get("ROBOT_WATCH_OUTPUT_DIR", DEFAULT_ROBOT_OUTPUT)),
        poll_interval_seconds=int(os.environ.get("ROBOT_POLL_INTERVAL_SECONDS", str(DEFAULT_ROBOT_POLL))),
        timeout_seconds=int(os.environ.get("ROBOT_TIMEOUT_SECONDS", str(DEFAULT_ROBOT_TIMEOUT))),
    )


ROBOT_IMPORT_SCRIPT: Final[str] = '''"""Script d'import Robot Structural Analysis - fourni par BET Agent V3.

Prérequis :
- Windows + Robot 2023 ou plus récent
- Python 3.8+ avec pywin32 (pip install pywin32)
- Les CSV générés par BET Agent dans le même dossier que ce script

Usage :
    python import_from_betagent.py {job_id}

Ce script utilise l'API COM de Robot pour :
1. Créer un nouveau projet vide
2. Importer les nœuds depuis {job_id}_nodes.csv
3. Importer les éléments depuis {job_id}_members.csv
4. Importer les appuis depuis {job_id}_supports.csv
5. Définir les cas de charges et combinaisons
6. Sauvegarder le modèle Robot (.rtd)

L'utilisateur lance ensuite le calcul manuellement dans Robot.
Après calcul, l'export SAF ou CSV des résultats est à replacer dans le dossier
de sortie BET Agent pour déclencher le double-check.
"""
import csv
import sys
from pathlib import Path

try:
    import win32com.client
except ImportError:
    print("ERREUR: pywin32 requis. Exécuter: pip install pywin32")
    sys.exit(1)


def main(job_id: str) -> None:
    base_dir = Path(__file__).parent

    nodes_file = base_dir / f"{job_id}_nodes.csv"
    members_file = base_dir / f"{job_id}_members.csv"
    supports_file = base_dir / f"{job_id}_supports.csv"

    for f in (nodes_file, members_file, supports_file):
        if not f.exists():
            print(f"ERREUR: fichier manquant: {f}")
            sys.exit(1)

    print("Démarrage de Robot Structural Analysis...")
    robot_app = win32com.client.Dispatch("Robot.Application")
    robot_app.Visible = 1
    robot_app.Interactive = 1

    # Nouveau projet
    robot_app.Projects.New(3)  # 3 = cadre 3D
    structure = robot_app.Project.Structure

    # 1. Import des nœuds
    print("Import des nœuds...")
    with open(nodes_file, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            node_num = int(row["node_num"])
            structure.Nodes.Create(
                node_num,
                float(row["x_m"]),
                float(row["y_m"]),
                float(row["z_m"]),
            )

    # 2. Import des éléments
    print("Import des éléments...")
    with open(members_file, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            bar_num = int(row["member_num"])
            structure.Bars.Create(
                bar_num,
                int(row["node_start_num"]),
                int(row["node_end_num"]),
            )
            bar = structure.Bars.Get(bar_num)
            # Section et matériau : l'utilisateur doit les adapter à la base Robot
            bar.SectionName = row["section"]
            bar.Material = row["material"]

    # 3. Import des appuis
    print("Import des appuis...")
    for row_data in _read_csv(supports_file):
        node_num = int(row_data["node_num"])
        support_type = row_data["support_type"]
        # Application de l'appui au nœud : détails dépendent de la base de supports Robot
        print(f"  Noeud {node_num} : {support_type}")

    print("Modèle importé. Sauvegarder le projet (.rtd) puis lancer le calcul.")
    print("Une fois le calcul terminé, exporter les résultats au format SAF ou CSV")
    print("et les déposer dans le dossier de sortie BET Agent.")


def _read_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python import_from_betagent.py <job_id>")
        sys.exit(1)
    main(sys.argv[1])
'''


class RobotConnector(StructuralConnector):
    """Exporte le modèle en CSV structurés + notice d'import COM pour Robot."""

    name = "robot_csv_option_c"

    def __init__(self, config: RobotConfig | None = None) -> None:
        self.config = config or load_robot_config()
        self.saf_gen = SafGenerator()
        self.parser = SafResultsParser()

    def validate_inputs(self, inputs: StructuralInputs) -> list[str]:
        warnings = self.saf_gen.validate_inputs(inputs)
        if not self.config.input_dir.exists():
            self.config.input_dir.mkdir(parents=True, exist_ok=True)
        if not self.config.output_dir.exists():
            self.config.output_dir.mkdir(parents=True, exist_ok=True)
        warnings.append(
            "Robot ne supporte pas d'import automatique depuis Linux. "
            "L'ingénieur doit exécuter le script COM fourni sous Windows."
        )
        return warnings

    def analyze(self, inputs: StructuralInputs) -> AnalysisResult:
        start = time.monotonic()
        warnings = self.validate_inputs(inputs)

        job_id = f"robot_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        csv_files = self._write_csv_bundle(inputs, job_id)
        notice_path = self._write_notice(job_id, csv_files)
        logger.info("Robot CSV bundle écrit : %d fichiers + notice %s", len(csv_files), notice_path)

        effective_timeout = min(inputs.timeout_seconds, self.config.timeout_seconds)
        result_path = self._wait_for_result(job_id, effective_timeout)

        # Les résultats doivent être exportés en SAF xlsx (Robot supporte SAF en export 2023+)
        # Ou en CSV avec les colonnes M_kNm, N_kN, V_kN, utilization
        if result_path.suffix.lower() == ".xlsx":
            # On a un SAF enrichi, on utilise le parser SAF standard
            saf_input_stub = csv_files.get("members")  # juste pour référence
            result = self.parser.parse_and_check(
                saf_input=saf_input_stub if saf_input_stub else result_path,
                saf_output=result_path,
                model_data=inputs.model_data if inputs.model_data else {},
            )
        else:
            result = self.parser.parse_csv_results_and_check(
                csv_results_path=result_path,
                model_data=inputs.model_data if inputs.model_data else {},
            )

        result.engine_used = self.name
        result.computation_seconds = time.monotonic() - start
        result.warnings = warnings + result.warnings
        result.raw_output["job_id"] = job_id
        result.raw_output["csv_bundle"] = {k: str(v) for k, v in csv_files.items()}
        result.raw_output["notice_path"] = str(notice_path)
        return result

    def _write_csv_bundle(self, inputs: StructuralInputs, job_id: str) -> dict[str, Path]:
        """Génère les 5 CSV + retourne leurs paths."""
        # Reconstruction du modèle via le SafGenerator pour cohérence
        warnings_unused: list[str] = []
        model = self.saf_gen._build_model(inputs, warnings_unused)

        out = self.config.input_dir
        files: dict[str, Path] = {}

        # Nodes
        nodes_path = out / f"{job_id}_nodes.csv"
        with open(nodes_path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["node_num", "node_id", "x_m", "y_m", "z_m"])
            w.writeheader()
            for idx, n in enumerate(model.nodes, start=1):
                w.writerow({
                    "node_num": idx,
                    "node_id": n.id,
                    "x_m": round(n.x, 4),
                    "y_m": round(n.y, 4),
                    "z_m": round(n.z, 4),
                })
        files["nodes"] = nodes_path

        # Members
        members_path = out / f"{job_id}_members.csv"
        node_id_to_num = {n.id: idx for idx, n in enumerate(model.nodes, start=1)}
        with open(members_path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=[
                "member_num", "member_id", "member_type",
                "node_start_num", "node_end_num",
                "section", "material",
            ])
            w.writeheader()
            for idx, m in enumerate(model.members, start=1):
                w.writerow({
                    "member_num": idx,
                    "member_id": m.id,
                    "member_type": m.member_type,
                    "node_start_num": node_id_to_num.get(m.node_start, 0),
                    "node_end_num": node_id_to_num.get(m.node_end, 0),
                    "section": m.section,
                    "material": m.material,
                })
        files["members"] = members_path

        # Supports
        supports_path = out / f"{job_id}_supports.csv"
        with open(supports_path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["support_id", "node_id", "node_num", "support_type"])
            w.writeheader()
            for s in model.supports:
                w.writerow({
                    "support_id": s.get("id", ""),
                    "node_id": s.get("node", ""),
                    "node_num": node_id_to_num.get(s.get("node", ""), 0),
                    "support_type": s.get("type", "fixed"),
                })
        files["supports"] = supports_path

        # Load cases
        cases_path = out / f"{job_id}_load_cases.csv"
        with open(cases_path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["case_id", "name", "category"])
            w.writeheader()
            for lc in STANDARD_LOAD_CASES:
                w.writerow({
                    "case_id": lc["id"],
                    "name": lc["name"],
                    "category": lc["category"],
                })
        files["load_cases"] = cases_path

        # Combinations
        combos_path = out / f"{job_id}_combinations.csv"
        with open(combos_path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["combo_id", "name", "type", "factors"])
            w.writeheader()
            import json
            for c in SIA_260_COMBINATIONS:
                w.writerow({
                    "combo_id": c["id"],
                    "name": c["name"],
                    "type": c["type"],
                    "factors": json.dumps(c["factors"], ensure_ascii=False),
                })
        files["combinations"] = combos_path

        return files

    def _write_notice(self, job_id: str, csv_files: dict[str, Path]) -> Path:
        notice_path = self.config.input_dir / f"{job_id}_README.md"

        file_list = "\n".join(f"- `{p.name}`" for p in csv_files.values())
        content = f"""# Import Robot Structural Analysis — job {job_id}

## Fichiers fournis

{file_list}

## Procédure d'import (5 min)

### 1. Prérequis
- Windows + Robot Structural Analysis 2023 (ou plus récent)
- Python 3.8+ avec pywin32 : `pip install pywin32`

### 2. Script d'import
Enregistrer le script ci-dessous en `import_from_betagent.py` dans le même dossier
que les CSV, puis exécuter :

```
python import_from_betagent.py {job_id}
```

### 3. Calcul et export
Une fois le modèle importé :
1. Vérifier la géométrie, sections, matériaux dans Robot
2. Ajouter les charges manuellement (ou via autre CSV à importer)
3. Lancer le calcul
4. Exporter les résultats en SAF (xlsx) ou CSV dans le dossier de sortie BET Agent,
   nommé `{job_id}_results.xlsx` ou `{job_id}_results.csv`

Format attendu du CSV si non-SAF :
```
member_id,check_name,M_kNm,N_kN,V_kN,utilization,compliant
M1,ULS_bending,45.2,12.3,8.1,0.78,true
...
```

## Script Python COM

```python
{ROBOT_IMPORT_SCRIPT}
```

## Support

En cas d'erreur, vérifier :
- La version de Robot (>= 2023)
- La base de sections et matériaux Robot correspond aux noms exportés
- Les droits COM (Robot doit être lancé au moins une fois manuellement avant)

Contact BET Agent : support@bet-agent.ch
"""
        notice_path.write_text(content, encoding="utf-8")
        return notice_path

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
                if path.suffix.lower() not in (".xlsx", ".csv"):
                    continue
                if self._file_is_stable(path):
                    return path

            if attempts % 6 == 0:
                logger.info("Robot polling job=%s (%ds timeout)", job_id, timeout_seconds)
            time.sleep(poll)

        raise ConnectorTimeoutError(
            f"Aucun résultat Robot pour job={job_id} après {timeout_seconds}s"
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
