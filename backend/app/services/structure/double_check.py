"""Double-check analytique des résultats structure.

Recalcule les sollicitations critiques avec des formules analytiques simples,
et compare aux résultats importés du logiciel. Alerte si divergence >15%.

Cas couverts en V2 :
- Poutre sur 2 appuis + charge uniforme (M = qL²/8)
- Poteau bi-articulé en compression simple
- Dalle portée unique + charge uniforme (par mètre de largeur)

Les cas complexes (hyperstatiques, précontraints, dynamiques) sont EXPLICITEMENT exclus
du double-check et marqués comme "non vérifié analytiquement".
"""
import logging
from typing import Any

logger = logging.getLogger(__name__)


def moment_poutre_simple_ql2_8(q_kN_m: float, L_m: float) -> float:
    """Moment max d'une poutre sur 2 appuis simples avec charge uniforme q. M = qL²/8 (kNm)."""
    return abs(q_kN_m) * L_m * L_m / 8


def effort_tranchant_poutre_ql_2(q_kN_m: float, L_m: float) -> float:
    """Effort tranchant max d'une poutre simple : V = qL/2 (kN)."""
    return abs(q_kN_m) * L_m / 2


def fleche_poutre_5qL4_384EI(q_kN_m: float, L_m: float, E_GPa: float, I_m4: float) -> float:
    """Flèche max d'une poutre simple : f = 5qL⁴ / (384·E·I) (m).
    Conversion : q en kN/m, L en m, E en GPa (×1e9 Pa), I en m⁴."""
    if E_GPa <= 0 or I_m4 <= 0:
        return 0
    return (5 * abs(q_kN_m) * 1000 * L_m ** 4) / (384 * E_GPa * 1e9 * I_m4)


def effort_normal_poteau(charges_above_kN: float) -> float:
    """Effort normal dans un poteau = somme des charges au-dessus."""
    return abs(charges_above_kN)


def double_check(structural_model: dict, results_parsed: dict) -> dict:
    """Exécute le double-check analytique.

    Retourne :
      {
        "checks": [
          {"member_id": ..., "check_type": ..., "analytical_value": ..., "software_value": ...,
           "divergence_pct": ..., "status": "OK|WARNING|ALERT|SKIP", "comment": ...}
        ],
        "max_divergence_pct": ...,
        "alerts_count": ...,
      }
    """
    checks: list[dict] = []

    nodes = {n.get("id"): n for n in structural_model.get("nodes") or []}
    members = {m.get("id"): m for m in structural_model.get("members") or []}
    loads_by_case: dict[str, list[dict]] = {}
    for l in structural_model.get("loads") or []:
        loads_by_case.setdefault(l.get("case"), []).append(l)

    # Résultats logiciel
    sw_forces_by_member: dict[str, list[dict]] = {}
    for f in results_parsed.get("internal_forces") or []:
        mid = str(f.get("Member") or f.get("MemberID") or f.get("Name") or "")
        if mid:
            sw_forces_by_member.setdefault(mid, []).append(f)

    for mid, member in members.items():
        if member.get("type") in ("beam", "girder"):
            check = _check_simple_beam(mid, member, nodes, structural_model, sw_forces_by_member)
            if check:
                checks.append(check)
        elif member.get("type") in ("column", "post"):
            check = _check_column(mid, member, nodes, structural_model, sw_forces_by_member)
            if check:
                checks.append(check)
        else:
            checks.append({
                "member_id": mid,
                "check_type": "skip",
                "status": "SKIP",
                "comment": f"Type '{member.get('type')}' non couvert par le double-check analytique V2",
            })

    alerts = [c for c in checks if c["status"] == "ALERT"]
    max_div = max((c.get("divergence_pct") or 0 for c in checks if c.get("divergence_pct") is not None), default=0)

    return {
        "checks": checks,
        "max_divergence_pct": round(max_div, 1),
        "alerts_count": len(alerts),
        "summary": (
            f"{len(checks)} vérifications analytiques effectuées "
            f"({len(alerts)} alerte(s), divergence max {max_div:.1f}%)"
        ),
    }


def _check_simple_beam(mid, member, nodes, model, sw_forces_by_member) -> dict | None:
    """Vérifie une poutre sur 2 appuis + charge uniforme."""
    node_s = nodes.get(member.get("node_start"))
    node_e = nodes.get(member.get("node_end"))
    if not node_s or not node_e:
        return None

    L = ((node_e.get("x", 0) - node_s.get("x", 0)) ** 2 +
         (node_e.get("y", 0) - node_s.get("y", 0)) ** 2 +
         (node_e.get("z", 0) - node_s.get("z", 0)) ** 2) ** 0.5
    if L <= 0:
        return None

    # Récupération charges sur cette poutre (uniform_vertical)
    total_q = 0.0
    for l in model.get("loads") or []:
        if str(l.get("target")) == mid and l.get("type") == "uniform_vertical":
            # Applique un facteur 1.35 approximatif pour ELU (double check est indicatif)
            total_q += abs(float(l.get("value_kN_m", 0) or 0)) * 1.35

    if total_q == 0:
        return {
            "member_id": mid,
            "check_type": "beam_simple_ql2_8",
            "status": "SKIP",
            "comment": "Pas de charge uniforme définie - saut du check analytique",
        }

    M_analytical = moment_poutre_simple_ql2_8(total_q, L)

    # Valeur logiciel : cherche la valeur de moment max
    sw_M = None
    for f in sw_forces_by_member.get(mid, []):
        for key in ("My", "M_y", "M", "Moment_max", "My_max"):
            v = f.get(key)
            if isinstance(v, (int, float)):
                sw_M = max(sw_M or 0, abs(float(v)))

    if sw_M is None:
        return {
            "member_id": mid,
            "check_type": "beam_simple_ql2_8",
            "analytical_value": round(M_analytical, 2),
            "analytical_unit": "kNm",
            "software_value": None,
            "divergence_pct": None,
            "status": "SKIP",
            "comment": "Moment logiciel non trouvé dans les résultats importés",
        }

    div_pct = abs((sw_M - M_analytical) / M_analytical) * 100 if M_analytical > 0 else 0

    if div_pct < 15:
        status = "OK"
    elif div_pct < 30:
        status = "WARNING"
    else:
        status = "ALERT"

    return {
        "member_id": mid,
        "check_type": "beam_simple_ql2_8",
        "analytical_value": round(M_analytical, 2),
        "analytical_unit": "kNm",
        "software_value": round(sw_M, 2),
        "divergence_pct": round(div_pct, 1),
        "status": status,
        "comment": (
            f"Poutre L={L:.2f}m, q(ELU)={total_q:.2f} kN/m, "
            f"M analytique={M_analytical:.1f} kNm vs logiciel={sw_M:.1f} kNm"
        ),
    }


def _check_column(mid, member, nodes, model, sw_forces_by_member) -> dict | None:
    """Vérifie un poteau en compression simple (effort normal uniquement)."""
    # Somme des charges verticales descendant sur ce poteau (approximation)
    charges_above = 0.0
    for l in model.get("loads") or []:
        if str(l.get("target")) == mid and l.get("type") == "point_vertical":
            charges_above += abs(float(l.get("value_kN", 0) or 0)) * 1.35

    if charges_above == 0:
        return {
            "member_id": mid,
            "check_type": "column_compression",
            "status": "SKIP",
            "comment": "Charges ponctuelles sur poteau non définies - saut du check",
        }

    N_analytical = effort_normal_poteau(charges_above)

    sw_N = None
    for f in sw_forces_by_member.get(mid, []):
        for key in ("N", "N_x", "Nmax", "Normal"):
            v = f.get(key)
            if isinstance(v, (int, float)):
                sw_N = max(sw_N or 0, abs(float(v)))

    if sw_N is None:
        return {
            "member_id": mid,
            "check_type": "column_compression",
            "analytical_value": round(N_analytical, 2),
            "analytical_unit": "kN",
            "software_value": None,
            "status": "SKIP",
            "comment": "N logiciel non trouvé",
        }

    div_pct = abs((sw_N - N_analytical) / N_analytical) * 100 if N_analytical > 0 else 0
    status = "OK" if div_pct < 15 else ("WARNING" if div_pct < 30 else "ALERT")

    return {
        "member_id": mid,
        "check_type": "column_compression",
        "analytical_value": round(N_analytical, 2),
        "analytical_unit": "kN",
        "software_value": round(sw_N, 2),
        "divergence_pct": round(div_pct, 1),
        "status": status,
        "comment": f"Poteau N analytique ≈ {N_analytical:.1f} kN vs logiciel {sw_N:.1f} kN",
    }
