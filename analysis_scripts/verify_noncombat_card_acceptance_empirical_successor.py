"""Independent source-only verifier identity for the empirical successor."""

from __future__ import annotations

from typing import Any


VERIFIER_CONTRACT_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-verifier-contract-v1"
)

# This tuple is intentionally local: the verifier must not import its producer.
_AUTHORITY_NAMES = (
    "causal",
    "communication_mod",
    "environment_construction",
    "evaluation",
    "execution",
    "formal_rl",
    "gameplay",
    "model_fitting",
    "native_loading",
    "ope",
    "production_model_loading",
    "promotion",
    "qualification",
    "seed_access",
    "training",
)


def verifier_contract() -> dict[str, Any]:
    """Return a fresh verifier contract without importing successor modules."""
    return {
        "authority": {name: False for name in _AUTHORITY_NAMES},
        "producer_imported": False,
        "runtime_imported": False,
        "schema_version": VERIFIER_CONTRACT_SCHEMA_VERSION,
        "seed_inventory_imported": False,
        "standard_library_only": True,
    }
