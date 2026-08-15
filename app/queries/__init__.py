"""Internal query layer (Phase 2+ consumes these; the public REST API is Phase 4).

Only PUBLISHED percentile rows are ever returned — the anomaly gate is
enforced at the query layer, not just the pipeline.
"""
