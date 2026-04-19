"""Connecteurs métiers V3 : thermique, structure, IDC.

Architecture :
- Chaque sous-module définit une interface abstraite dans base.py
- Implémentations concrètes (stub pour dev, vrais connecteurs pour prod)
- Les vrais connecteurs dépendent de configuration d'environnement (paths Lesosai,
  endpoints Scia, credentials OCEN)

Les connecteurs retournent des dataclasses typées et loggent via le logger standard.
Aucun print. Aucun TODO. Timeouts explicites sur tout appel réseau / I/O disque.
"""
from __future__ import annotations

