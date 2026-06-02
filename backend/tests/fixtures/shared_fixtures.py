"""Fixtures partagées pour tous les tests V3.

Génère dynamiquement :
- Un IFC 4 minimal mais valide (3 zones + enveloppe orthogonale)
- Un XML CECB v5 réaliste (classe C, logement collectif)
- Un PDF de facture mazout avec texte extractible
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


# ============================================================
# IFC MINIMAL
# ============================================================

@pytest.fixture(scope="session")
def sample_ifc_bytes() -> bytes:
    """Génère un IFC 4 minimal in-memory avec 3 IfcSpace + murs/toit/dalle."""
    import ifcopenshell
    import ifcopenshell.api
    import ifcopenshell.guid

    model = ifcopenshell.api.run("project.create_file", version="IFC4")

    project = ifcopenshell.api.run(
        "root.create_entity", model, ifc_class="IfcProject", name="TEST_PROJECT",
    )
    ifcopenshell.api.run("unit.assign_unit", model)
    ctx = ifcopenshell.api.run("context.add_context", model, context_type="Model")
    ifcopenshell.api.run(
        "context.add_context", model,
        context_type="Model", context_identifier="Body",
        target_view="MODEL_VIEW", parent=ctx,
    )

    site = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcSite", name="TestSite")
    ifcopenshell.api.run(
        "aggregate.assign_object", model, relating_object=project, products=[site],
    )

    building = ifcopenshell.api.run(
        "root.create_entity", model, ifc_class="IfcBuilding", name="TestBldg",
    )
    ifcopenshell.api.run(
        "aggregate.assign_object", model, relating_object=site, products=[building],
    )

    # Un étage
    storey = ifcopenshell.api.run(
        "root.create_entity", model, ifc_class="IfcBuildingStorey", name="RDC",
    )
    ifcopenshell.api.run(
        "aggregate.assign_object", model, relating_object=building, products=[storey],
    )

    # 3 espaces de 100 m² chacun, H=3m, V=300 m³
    for idx in range(1, 4):
        space = ifcopenshell.api.run(
            "root.create_entity", model, ifc_class="IfcSpace", name=f"Space_{idx}",
        )
        ifcopenshell.api.run(
            "aggregate.assign_object", model, relating_object=storey, products=[space],
        )
        pset = ifcopenshell.api.run(
            "pset.add_pset", model, product=space, name="Qto_SpaceBaseQuantities",
        )
        ifcopenshell.api.run("pset.edit_pset", model, pset=pset, properties={
            "NetFloorArea": 100.0,
            "GrossFloorArea": 105.0,
            "NetVolume": 300.0,
            "GrossVolume": 315.0,
            "Height": 3.0,
        })

    # 4 murs extérieurs (N/S/E/W)
    orientations = [("MurN", 30.0, 0.25), ("MurS", 30.0, 0.25),
                    ("MurE", 10.0, 0.25), ("MurW", 10.0, 0.25)]
    for name, length, u_val in orientations:
        wall = ifcopenshell.api.run(
            "root.create_entity", model, ifc_class="IfcWall", name=name,
        )
        ifcopenshell.api.run("spatial.assign_container", model,
                             relating_structure=storey, products=[wall])
        pset = ifcopenshell.api.run("pset.add_pset", model,
                                    product=wall, name="Pset_WallCommon")
        ifcopenshell.api.run("pset.edit_pset", model, pset=pset, properties={
            "IsExternal": True,
            "ThermalTransmittance": u_val,
        })
        qto = ifcopenshell.api.run("pset.add_qto", model,
                                   product=wall, name="Qto_WallBaseQuantities")
        ifcopenshell.api.run("pset.edit_qto", model, qto=qto, properties={
            "NetArea": length * 3.0,
            "GrossArea": length * 3.0 * 1.05,
        })

    # Toit et dalle
    for roof_name, ifc_class, area, u_val, pset_name in [
        ("Toit", "IfcRoof", 300.0, 0.18, "Pset_RoofCommon"),
        ("Dalle", "IfcSlab", 300.0, 0.25, "Pset_SlabCommon"),
    ]:
        elem = ifcopenshell.api.run(
            "root.create_entity", model, ifc_class=ifc_class, name=roof_name,
        )
        ifcopenshell.api.run("spatial.assign_container", model,
                             relating_structure=storey, products=[elem])
        pset = ifcopenshell.api.run("pset.add_pset", model, product=elem, name=pset_name)
        ifcopenshell.api.run("pset.edit_pset", model, pset=pset, properties={
            "IsExternal": True,
            "ThermalTransmittance": u_val,
        })
        qto = ifcopenshell.api.run("pset.add_qto", model, product=elem,
                                   name=f"Qto_{ifc_class[3:]}BaseQuantities")
        ifcopenshell.api.run("pset.edit_qto", model, qto=qto, properties={
            "NetArea": area,
            "GrossArea": area,
        })

    # Fenêtre avec U=1.0
    window = ifcopenshell.api.run(
        "root.create_entity", model, ifc_class="IfcWindow", name="FenetreSud",
    )
    ifcopenshell.api.run("spatial.assign_container", model,
                         relating_structure=storey, products=[window])
    pset_w = ifcopenshell.api.run("pset.add_pset", model,
                                  product=window, name="Pset_WindowCommon")
    ifcopenshell.api.run("pset.edit_pset", model, pset=pset_w, properties={
        "ThermalTransmittance": 1.0,
    })
    qto_w = ifcopenshell.api.run("pset.add_qto", model, product=window,
                                 name="Qto_WindowBaseQuantities")
    ifcopenshell.api.run("pset.edit_qto", model, qto=qto_w, properties={
        "Area": 15.0,
    })

    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".ifc", delete=False) as f:
        tmp_path = f.name
    model.write(tmp_path)
    data = Path(tmp_path).read_bytes()
    Path(tmp_path).unlink(missing_ok=True)
    return data


@pytest.fixture
def temp_ifc_file(tmp_path: Path, sample_ifc_bytes: bytes) -> Path:
    """Un IFC écrit sur disque, disponible pour chaque test."""
    target = tmp_path / "sample.ifc"
    target.write_bytes(sample_ifc_bytes)
    return target


# ============================================================
# CECB XML v5 (classe C, logement collectif)
# ============================================================

SAMPLE_CECB_XML: str = """<?xml version="1.0" encoding="UTF-8"?>
<CECB xmlns="http://www.cecb.ch/schema/v5" version="5.0">
    <Metadata>
        <CertificateId>CECB-2024-GE-001234</CertificateId>
        <NumeroCECB>GE-2024-001234</NumeroCECB>
        <IssuedDate>2024-03-15</IssuedDate>
        <Canton>GE</Canton>
        <Validity>2034-03-15</Validity>
    </Metadata>

    <Building>
        <Address>Rue du Test 42, 1207 Genève</Address>
        <EGID>1234567</EGID>
        <Affectation>Habitation collective</Affectation>
        <YearOfConstruction>1985</YearOfConstruction>
        <SRE>1250.0</SRE>
        <Volume>4375.0</Volume>
        <NbLogements>18</NbLogements>
    </Building>

    <Results>
        <ThermalDemand>
            <Qh unit="kWh/m2a">75.3</Qh>
            <Qww unit="kWh/m2a">22.1</Qww>
        </ThermalDemand>
        <PrimaryEnergy>
            <Ep unit="kWh/m2a">112.8</Ep>
            <Et unit="kWh/m2a">125.5</Et>
        </PrimaryEnergy>
        <IDC unit="kWh/m2a">97.4</IDC>
        <ClasseEnveloppe>C</ClasseEnveloppe>
        <ClasseGlobale>C</ClasseGlobale>
    </Results>

    <Systems>
        <Heating vector="gas" efficiency="0.88"/>
        <Ventilation type="natural"/>
    </Systems>
</CECB>
"""


@pytest.fixture
def sample_cecb_xml() -> str:
    return SAMPLE_CECB_XML


@pytest.fixture
def temp_cecb_file(tmp_path: Path) -> Path:
    target = tmp_path / "sample_cecb.xml"
    target.write_text(SAMPLE_CECB_XML, encoding="utf-8")
    return target


# ============================================================
# PDF facture mazout
# ============================================================

@pytest.fixture(scope="session")
def sample_facture_mazout_bytes() -> bytes:
    """Facture PDF texte réaliste pour tests d'extraction."""
    try:
        from pypdf import PdfWriter  # pypdf v3+
    except ImportError:
        # Fallback : génération via reportlab
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
            import io

            buf = io.BytesIO()
            c = canvas.Canvas(buf, pagesize=A4)
            c.setFont("Helvetica", 11)
            y = 780
            lines = [
                "FACTURE MAZOUT - Carburants SA Genève",
                "",
                "Client : M. Dupont, Rue du Chêne 5, 1207 Genève",
                "No client : 123456",
                "Date facture : 15.03.2024",
                "",
                "Période de livraison du 01.10.2023 au 31.03.2024",
                "",
                "Livraison mazout EL (Eurofuel)",
                "Quantité livrée : 5'250 litres",
                "Prix unitaire : 1.15 CHF / litre",
                "",
                "Total HT : 6'037.50 CHF",
                "TVA 8.1% : 489.04 CHF",
                "Total TTC : 6'526.54 CHF",
            ]
            for line in lines:
                c.drawString(50, y, line)
                y -= 20
            c.save()
            return buf.getvalue()
        except ImportError:
            pytest.skip("Ni pypdf ni reportlab disponible pour générer facture PDF")

    # Avec pypdf : on crée un PDF minimal via fpdf2 si dispo
    try:
        from fpdf import FPDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", size=11)

        lines = [
            "FACTURE MAZOUT - Carburants SA Geneve",
            "",
            "Client : M. Dupont, Rue du Chene 5, 1207 Geneve",
            "No client : 123456",
            "Date facture : 15.03.2024",
            "",
            "Periode de livraison du 01.10.2023 au 31.03.2024",
            "",
            "Livraison mazout EL (Eurofuel)",
            "Quantite livree : 5'250 litres",
            "Prix unitaire : 1.15 CHF / litre",
            "",
            "Total HT : 6'037.50 CHF",
            "TVA 8.1% : 489.04 CHF",
            "Total TTC : 6'526.54 CHF",
        ]
        for line in lines:
            pdf.cell(0, 7, txt=line, ln=True)

        return bytes(pdf.output(dest="S"))
    except ImportError:
        pytest.skip("fpdf non disponible")


@pytest.fixture
def temp_facture_mazout_pdf(tmp_path: Path, sample_facture_mazout_bytes: bytes) -> Path:
    target = tmp_path / "facture_mazout.pdf"
    target.write_bytes(sample_facture_mazout_bytes)
    return target


# ============================================================
# Mocks environnement
# ============================================================

@pytest.fixture
def mock_anthropic(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Mock client Anthropic qui renvoie une réponse JSON pour l'extraction."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_content = MagicMock()
    mock_content.text = (
        '{"value": 5250.0, "unit": "litre", '
        '"period_start": "2023-10-01", "period_end": "2024-03-31", '
        '"confidence": 0.95}'
    )
    mock_response.content = [mock_content]
    mock_client.messages.create = MagicMock(return_value=mock_response)

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-fixture")
    monkeypatch.setattr(
        "app.connectors.idc.facture_extractor.Anthropic",
        lambda *args, **kwargs: mock_client,
        raising=False,
    )
    return mock_client


@pytest.fixture
def mock_resend(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    mock_send = MagicMock(return_value={"id": "email-test-id"})
    try:
        monkeypatch.setattr("resend.Emails.send", mock_send, raising=False)
    except (ImportError, AttributeError):
        pass
    return mock_send


@pytest.fixture
def mock_redis(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    mock = MagicMock()
    mock.get = MagicMock(return_value=None)
    mock.set = MagicMock(return_value=True)
    mock.delete = MagicMock(return_value=1)
    mock.exists = MagicMock(return_value=False)
    return mock


@pytest.fixture
def supabase_test(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Supabase mocké pour les tests qui n'ont pas besoin d'une vraie DB."""
    mock_client = MagicMock()

    def _chain_returns(value: Any) -> MagicMock:
        chain = MagicMock()
        chain.execute = MagicMock(return_value=MagicMock(data=value))
        chain.select = MagicMock(return_value=chain)
        chain.insert = MagicMock(return_value=chain)
        chain.update = MagicMock(return_value=chain)
        chain.delete = MagicMock(return_value=chain)
        chain.eq = MagicMock(return_value=chain)
        chain.limit = MagicMock(return_value=chain)
        chain.order = MagicMock(return_value=chain)
        chain.maybe_single = MagicMock(return_value=chain)
        return chain

    mock_client.table = MagicMock(side_effect=lambda _name: _chain_returns([]))
    return mock_client
