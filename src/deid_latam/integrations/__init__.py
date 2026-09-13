"""Adapters that plug deid-latam into the pipelines people already run.

Neither Presidio nor OpenMed is a dependency of this package, so neither submodule is
imported here. Import the one you need and install its extra:

    pip install "deid-latam[presidio]"
    from deid_latam.integrations.presidio import register

    pip install "deid-latam[openmed]"
    from deid_latam.integrations.openmed import redact

Both adapters call ``find_identifiers`` rather than re-implementing the patterns, so
what an integration detects is what the library detects and what the benchmark measures.
"""
from __future__ import annotations

__all__ = ["presidio", "openmed"]
