"""Price result snapshot persistence for execution.

PRODUCT-INTEL.4C-B corrections:
* Snapshot creation is now done in orchestration.py inside the atomic block
* This module handles encoding only
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from product_intelligence.research.price_result_codec import encode_price_aggregation_result

if TYPE_CHECKING:
    from product_intelligence.research.aggregation import PriceAggregationResult

logger = logging.getLogger(__name__)


def encode_price_result(result: PriceAggregationResult) -> dict:
    """Encode aggregation result to JSON-serializable dict.

    Parameters
    ----------
    result : PriceAggregationResult
        The aggregation result to encode.

    Returns
    -------
    dict
        JSON-serializable dict suitable for storage.
    """
    return encode_price_aggregation_result(result)