"""
TransfermarktSource — market data provider implementation.

.. note::

   The implementation has been refactored into ``fetching.py``,
   ``squad.py``, ``market_data.py``, and ``transfers.py``
   for maintainability.  This module re-exports
   ``TransfermarktSource`` so existing imports continue to
   work unchanged.
"""


__all__ = [
    "TransfermarktSource",
]
