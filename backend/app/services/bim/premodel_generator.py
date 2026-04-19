"""Générateur de pré-modèle IFC depuis programme + surfaces.

Périmètre V2 :
- Bâtiments orthogonaux (rectangles emboîtés)
- Jusqu'à R+8
- Géométrie simple, sans décrochements complexes
- Zones thermiques = étages (pas de zonage fin par pièce en auto)

Utilise ifcopenshell.api pour une construction propre (plutôt que create_entity brut).
"""
import logging
import tempfile
import uuid
from pathlib import Path
from typing import Any

import ifcopenshell
import ifcopenshell.api
import ifcopenshell.guid

from app.services.bim.wall_library import COMPOSITIONS_TYPES, compute_u_value, get_composition

logger = logging.getLogger(__name__)


class PreBIMGenerator:
    """Construit un fichier IFC 4 à partir d'une spec simple.

    Spec attendue :
    {
      "project_name": "Résidence Les Acacias",
      "site_name": "Genève", "site_latitude": 46.2, "site_longitude": 6.1,
      "building_name": "Bâtiment A",
      "storeys": [
        {"name": "Rez", "elevation_m": 0, "height_m": 3.0, "area_m2": 250, "usage": "logement_collectif"},
        {"name": "R+1", "elevation_m": 3.0, "height_m": 2.8, "area_m2": 250, "usage": "logement_collectif"},
        ...
      ],
      "envelope": {
        "plan_width_m": 25, "plan_depth_m": 10,   # rectangle de base
        "wall_composition_key": "mur_ext_neuf_standard",
        "roof_composition_key": "toit_neuf_perform",
        "slab_ground_composition_key": "dalle_sur_terrain_neuf",
        "window_ratio_by_orientation": {"N": 0.15, "S": 0.35, "E": 0.25, "W": 0.25},
        "window_u_value": 1.0,
        "window_g_value": 0.55,
      },
    }
    """

    def __init__(self, spec: dict):
        self.spec = spec
        self.warnings: list[str] = []
        self.confidence: float = 1.0
        self.model = self._create_base_model()
        self.owner_history = self._create_owner_history()
        self.context = self._create_geometric_context()

    def _create_base_model(self) -> ifcopenshell.file:
        return ifcopenshell.api.run("project.create_file", version="IFC4")

    def _create_owner_history(self):
        return ifcopenshell.api.run("owner.add_person", self.model)

    def _create_geometric_context(self):
        return ifcopenshell.api.run("context.add_context", self.model, context_type="Model")

    def _new_guid(self) -> str:
        return ifcopenshell.guid.new()

    def build(self) -> dict:
        """Construit le modèle IFC et retourne un dict avec le path + métadonnées."""
        spec = self.spec
        envelope = spec.get("envelope", {})
        storeys_spec = spec.get("storeys", [])

        if not storeys_spec:
            self.warnings.append("Aucun étage défini - modèle minimal généré")
            self.confidence = 0.2

        plan_w = envelope.get("plan_width_m", 20.0)
        plan_d = envelope.get("plan_depth_m", 10.0)

        if plan_w <= 0 or plan_d <= 0:
            self.warnings.append("Dimensions de plan invalides - défauts appliqués (20x10m)")
            plan_w, plan_d = 20.0, 10.0
            self.confidence *= 0.5

        # Projet
        project = ifcopenshell.api.run(
            "root.create_entity",
            self.model,
            ifc_class="IfcProject",
            name=spec.get("project_name", "Projet BET"),
        )
        ifcopenshell.api.run("unit.assign_unit", self.model)

        # Contexte
        ctx = ifcopenshell.api.run(
            "context.add_context", self.model, context_type="Model"
        )
        body = ifcopenshell.api.run(
            "context.add_context",
            self.model,
            context_type="Model",
            context_identifier="Body",
            target_view="MODEL_VIEW",
            parent=ctx,
        )

        # Site
        site = ifcopenshell.api.run(
            "root.create_entity", self.model, ifc_class="IfcSite",
            name=spec.get("site_name", "Site"),
        )
        ifcopenshell.api.run("aggregate.assign_object", self.model, relating_object=project, product=site)

        # Bâtiment
        building = ifcopenshell.api.run(
            "root.create_entity", self.model, ifc_class="IfcBuilding",
            name=spec.get("building_name", "Bâtiment A"),
        )
        ifcopenshell.api.run("aggregate.assign_object", self.model, relating_object=site, product=building)

        # Étages
        storeys_created = []
        for st_spec in storeys_spec:
            storey = ifcopenshell.api.run(
                "root.create_entity", self.model, ifc_class="IfcBuildingStorey",
                name=st_spec.get("name", "Étage"),
            )
            # Élévation
            try:
                ifcopenshell.api.run(
                    "attribute.edit_attributes",
                    self.model,
                    product=storey,
                    attributes={"Elevation": float(st_spec.get("elevation_m", 0))},
                )
            except Exception as e:
                logger.debug(f"Élévation non appliquée : {e}")
            ifcopenshell.api.run(
                "aggregate.assign_object", self.model,
                relating_object=building, product=storey,
            )
            storeys_created.append((storey, st_spec))

        # Pour chaque étage : génération des 4 murs extérieurs + dalle + espace (IfcSpace)
        for storey, st_spec in storeys_created:
            self._build_storey_envelope(
                storey=storey,
                st_spec=st_spec,
                plan_w=plan_w,
                plan_d=plan_d,
                envelope=envelope,
                body_context=body,
            )

        # Toiture (sur dernier étage)
        if storeys_created:
            last_storey, last_spec = storeys_created[-1]
            self._add_roof(
                storey=last_storey,
                plan_w=plan_w, plan_d=plan_d,
                elevation_m=last_spec.get("elevation_m", 0) + last_spec.get("height_m", 3.0),
                envelope=envelope,
                body_context=body,
            )

        # Propriétés thermiques attachées aux parois
        self._attach_thermal_psets(envelope)

        # Écriture du fichier
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".ifc")
        self.model.write(tmp.name)
        tmp.close()

        return {
            "ifc_path": tmp.name,
            "confidence": self.confidence,
            "warnings": self.warnings,
            "report": self._build_report(),
        }

    def _build_storey_envelope(
        self,
        storey,
        st_spec: dict,
        plan_w: float,
        plan_d: float,
        envelope: dict,
        body_context,
    ):
        """Crée 4 murs extérieurs + 1 espace pour un étage."""
        from ifcopenshell.util.element import get_psets  # noqa: F401

        storey_height = st_spec.get("height_m", 3.0)

        # Composition des murs
        comp_key = envelope.get("wall_composition_key", "mur_ext_neuf_standard")
        composition = get_composition(comp_key) or {"u_value": 0.25, "label": "par défaut"}

        # 4 murs - nord, sud, est, ouest
        wall_specs = [
            ("Mur Nord", "N", plan_w, storey_height),
            ("Mur Sud", "S", plan_w, storey_height),
            ("Mur Est", "E", plan_d, storey_height),
            ("Mur Ouest", "W", plan_d, storey_height),
        ]

        window_ratios = envelope.get("window_ratio_by_orientation", {}) or {}

        for wall_name, orientation, length_m, height_m in wall_specs:
            wall = ifcopenshell.api.run(
                "root.create_entity", self.model, ifc_class="IfcWall",
                name=wall_name,
            )
            ifcopenshell.api.run(
                "spatial.assign_container", self.model,
                relating_structure=storey, product=wall,
            )
            wall_area = length_m * height_m

            # Pset thermique
            pset = ifcopenshell.api.run("pset.add_pset", self.model, product=wall, name="Pset_WallCommon")
            ifcopenshell.api.run(
                "pset.edit_pset", self.model, pset=pset,
                properties={
                    "IsExternal": True,
                    "ThermalTransmittance": composition.get("u_value"),
                },
            )
            # Pset custom pour la surface et orientation
            pset2 = ifcopenshell.api.run("pset.add_pset", self.model, product=wall, name="BETAgent_WallData")
            ifcopenshell.api.run(
                "pset.edit_pset", self.model, pset=pset2,
                properties={
                    "NetArea": wall_area,
                    "Orientation": orientation,
                    "CompositionKey": comp_key,
                    "CompositionLabel": composition.get("label", ""),
                },
            )

            # Fenêtre estimée par ratio
            ratio = window_ratios.get(orientation, 0)
            if ratio > 0:
                window_area = wall_area * ratio
                window = ifcopenshell.api.run(
                    "root.create_entity", self.model, ifc_class="IfcWindow",
                    name=f"Fenêtres {wall_name}",
                )
                ifcopenshell.api.run(
                    "spatial.assign_container", self.model,
                    relating_structure=storey, product=window,
                )
                pset_w = ifcopenshell.api.run(
                    "pset.add_pset", self.model, product=window, name="Pset_WindowCommon"
                )
                ifcopenshell.api.run(
                    "pset.edit_pset", self.model, pset=pset_w,
                    properties={
                        "ThermalTransmittance": envelope.get("window_u_value", 1.0),
                        "GlazingAreaFraction": 0.8,
                    },
                )
                pset_w2 = ifcopenshell.api.run(
                    "pset.add_pset", self.model, product=window, name="BETAgent_WindowData"
                )
                ifcopenshell.api.run(
                    "pset.edit_pset", self.model, pset=pset_w2,
                    properties={
                        "GlassArea": window_area,
                        "GValue": envelope.get("window_g_value", 0.55),
                        "Orientation": orientation,
                    },
                )

        # Espace IfcSpace (1 par étage pour simplicité - zonage fin = V3)
        space = ifcopenshell.api.run(
            "root.create_entity", self.model, ifc_class="IfcSpace",
            name=f"Espace {st_spec.get('name', '')}",
        )
        ifcopenshell.api.run(
            "spatial.assign_container", self.model,
            relating_structure=storey, product=space,
        )
        # Pset surface
        pset_s = ifcopenshell.api.run(
            "pset.add_pset", self.model, product=space, name="Qto_SpaceBaseQuantities"
        )
        ifcopenshell.api.run(
            "pset.edit_pset", self.model, pset=pset_s,
            properties={
                "NetFloorArea": st_spec.get("area_m2", plan_w * plan_d),
                "Height": storey_height,
                "NetVolume": st_spec.get("area_m2", plan_w * plan_d) * storey_height,
            },
        )
        pset_s2 = ifcopenshell.api.run(
            "pset.add_pset", self.model, product=space, name="BETAgent_SpaceData"
        )
        ifcopenshell.api.run(
            "pset.edit_pset", self.model, pset=pset_s2,
            properties={
                "Usage": st_spec.get("usage", "logement_collectif"),
                "TempSetpointC": 20,
            },
        )

        # Dalle plancher
        slab_name = "Dalle sur terrain" if st_spec.get("elevation_m", 0) == 0 else "Plancher"
        slab = ifcopenshell.api.run(
            "root.create_entity", self.model, ifc_class="IfcSlab",
            name=slab_name,
        )
        ifcopenshell.api.run(
            "spatial.assign_container", self.model,
            relating_structure=storey, product=slab,
        )
        slab_comp_key = (envelope.get("slab_ground_composition_key", "dalle_sur_terrain_neuf")
                         if st_spec.get("elevation_m", 0) == 0
                         else "plancher_inter_etage")
        slab_comp = get_composition(slab_comp_key) or {"u_value": 0.25}

        pset_sl = ifcopenshell.api.run(
            "pset.add_pset", self.model, product=slab, name="Pset_SlabCommon"
        )
        ifcopenshell.api.run(
            "pset.edit_pset", self.model, pset=pset_sl,
            properties={
                "ThermalTransmittance": slab_comp.get("u_value"),
                "IsExternal": st_spec.get("elevation_m", 0) == 0,
            },
        )

    def _add_roof(self, storey, plan_w, plan_d, elevation_m, envelope, body_context):
        roof = ifcopenshell.api.run(
            "root.create_entity", self.model, ifc_class="IfcRoof",
            name="Toiture",
        )
        ifcopenshell.api.run(
            "spatial.assign_container", self.model,
            relating_structure=storey, product=roof,
        )
        comp_key = envelope.get("roof_composition_key", "toit_neuf_perform")
        comp = get_composition(comp_key) or {"u_value": 0.15}
        pset = ifcopenshell.api.run(
            "pset.add_pset", self.model, product=roof, name="Pset_RoofCommon"
        )
        ifcopenshell.api.run(
            "pset.edit_pset", self.model, pset=pset,
            properties={
                "ThermalTransmittance": comp.get("u_value"),
                "IsExternal": True,
            },
        )
        pset2 = ifcopenshell.api.run(
            "pset.add_pset", self.model, product=roof, name="BETAgent_RoofData"
        )
        ifcopenshell.api.run(
            "pset.edit_pset", self.model, pset=pset2,
            properties={
                "NetArea": plan_w * plan_d,
                "CompositionKey": comp_key,
            },
        )

    def _attach_thermal_psets(self, envelope: dict):
        """Hook pour enrichissements thermiques supplémentaires. No-op en V2."""
        pass

    def _build_report(self) -> dict:
        """Rapport de génération lisible par l'utilisateur."""
        spec = self.spec
        storeys = spec.get("storeys", [])
        envelope = spec.get("envelope", {})
        return {
            "project_name": spec.get("project_name", ""),
            "nb_storeys": len(storeys),
            "total_area_m2": sum(s.get("area_m2", 0) for s in storeys),
            "plan_dimensions_m": [envelope.get("plan_width_m"), envelope.get("plan_depth_m")],
            "envelope_choices": {
                "walls": envelope.get("wall_composition_key"),
                "roof": envelope.get("roof_composition_key"),
                "slab_ground": envelope.get("slab_ground_composition_key"),
            },
            "confidence": self.confidence,
            "warnings": self.warnings,
            "scope_limits": [
                "Géométrie orthogonale simple (rectangle de base)",
                "Zones thermiques = 1 par étage (pas de zonage pièce à pièce)",
                "Pas de décrochements, balcons, attiques automatiques",
                "Compositions issues de bibliothèque standard BET Agent",
                "Fenêtres distribuées par ratio orientation (pas de positionnement réel)",
            ],
            "next_steps": [
                "Valider la géométrie dans le viewer IFC intégré",
                "Préciser les compositions réelles si différentes",
                "Définir le zonage thermique fin si besoin (logements, communs...)",
                "Compléter avec l'architecte si géométrie non orthogonale",
            ],
        }


def generate_premodel(spec: dict) -> dict:
    """Point d'entrée principal : génère un pré-modèle IFC depuis la spec."""
    gen = PreBIMGenerator(spec)
    return gen.build()
