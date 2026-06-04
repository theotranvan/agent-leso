"""Génère une géométrie structurelle orthogonale déterministe depuis des
paramètres simples (trame de poteaux + niveaux).

Ce module ne fait AUCUN calcul de résistance : il produit la topologie
(nœuds, poteaux, poutres, appuis) d'un portique régulier en béton armé,
prête à être sérialisée en SAF puis enrichie/calculée dans Scia/RFEM.

Hypothèses (volontairement simples et explicites) :
  - Trame régulière : `n_bays_x` travées de `bay_x_m`, `n_bays_y` de `bay_y_m`.
  - `n_levels` étages de hauteur `story_height_m` au-dessus du niveau 0.
  - Un poteau à chaque intersection de la trame, continu sur toute la hauteur.
  - Des poutres reliant les têtes de poteaux à chaque plancher (z > 0), dans
    les deux directions de la trame.
  - Appuis encastrés à la base (nœuds de niveau le plus bas).

La géométrie est 100 % déterministe : mêmes paramètres ⇒ mêmes nœuds/membres.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FrameParams:
    n_levels: int = 3
    n_bays_x: int = 3
    bay_x_m: float = 5.4
    n_bays_y: int = 2
    bay_y_m: float = 6.0
    story_height_m: float = 2.8
    column_section: str = "POT_30x30"
    beam_section: str = "POU_30x50"
    material: str = "C30/37"

    def validate(self) -> None:
        if self.n_levels < 1:
            raise ValueError("n_levels doit être ≥ 1")
        if self.n_bays_x < 1 or self.n_bays_y < 1:
            raise ValueError("n_bays_x et n_bays_y doivent être ≥ 1")
        for v, name in (
            (self.bay_x_m, "bay_x_m"),
            (self.bay_y_m, "bay_y_m"),
            (self.story_height_m, "story_height_m"),
        ):
            if v <= 0:
                raise ValueError(f"{name} doit être > 0")


def build_frame_geometry(params: FrameParams) -> dict:
    """Construit la géométrie d'un portique régulier.

    Retourne {nodes, members, supports} au format attendu par le générateur SAF
    (et par le stockage `structural_models`).
    """
    params.validate()

    nx = params.n_bays_x + 1   # lignes de poteaux en X
    ny = params.n_bays_y + 1   # lignes de poteaux en Y
    n_node_levels = params.n_levels + 1  # niveaux de nœuds (base incluse)

    nodes: list[dict] = []
    node_id_at: dict[tuple[int, int, int], str] = {}

    def nid(k: int, i: int, j: int) -> str:
        return f"N{k}_{i}_{j}"

    for k in range(n_node_levels):
        z = round(k * params.story_height_m, 3)
        for i in range(nx):
            x = round(i * params.bay_x_m, 3)
            for j in range(ny):
                y = round(j * params.bay_y_m, 3)
                node_id = nid(k, i, j)
                node_id_at[(k, i, j)] = node_id
                nodes.append({"id": node_id, "x": x, "y": y, "z": z})

    members: list[dict] = []

    # Poteaux : segment vertical entre deux niveaux consécutifs, à chaque grille.
    for k in range(params.n_levels):
        for i in range(nx):
            for j in range(ny):
                members.append({
                    "id": f"C_{k}_{i}_{j}",
                    "type": "column",
                    "node_start": nid(k, i, j),
                    "node_end": nid(k + 1, i, j),
                    "section": params.column_section,
                    "material": params.material,
                })

    # Poutres : à chaque plancher (k ≥ 1), dans les deux directions.
    for k in range(1, n_node_levels):
        # Poutres en X (le long de chaque ligne Y)
        for j in range(ny):
            for i in range(params.n_bays_x):
                members.append({
                    "id": f"BX_{k}_{i}_{j}",
                    "type": "beam",
                    "node_start": nid(k, i, j),
                    "node_end": nid(k, i + 1, j),
                    "section": params.beam_section,
                    "material": params.material,
                })
        # Poutres en Y (le long de chaque ligne X)
        for i in range(nx):
            for j in range(params.n_bays_y):
                members.append({
                    "id": f"BY_{k}_{i}_{j}",
                    "type": "beam",
                    "node_start": nid(k, i, j),
                    "node_end": nid(k, i, j + 1),
                    "section": params.beam_section,
                    "material": params.material,
                })

    # Appuis encastrés à la base (niveau 0).
    supports: list[dict] = []
    for i in range(nx):
        for j in range(ny):
            supports.append({
                "id": f"S_{i}_{j}",
                "node": nid(0, i, j),
                "type": "fixed",
            })

    return {"nodes": nodes, "members": members, "supports": supports}


def geometry_summary(geometry: dict) -> dict:
    """Comptes rapides pour affichage UI / vérifications."""
    members = geometry.get("members", [])
    return {
        "nb_nodes": len(geometry.get("nodes", [])),
        "nb_members": len(members),
        "nb_columns": sum(1 for m in members if m.get("type") == "column"),
        "nb_beams": sum(1 for m in members if m.get("type") == "beam"),
        "nb_supports": len(geometry.get("supports", [])),
    }
