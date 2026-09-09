"""Deprecated split stub.

The package split created partial duplicate class definitions here, which
broke imports. The intact implementation lives in source.py; this stub
keeps the module path importable for backward compatibility.
"""

from app.sources.transfermarkt_pkg.source import TransfermarktSource

__all__ = ["TransfermarktSource"]
