from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class EncodedStateV2:
    continuous: np.ndarray
    card_ids: np.ndarray
    potion_ids: np.ndarray
    relic_ids: np.ndarray
