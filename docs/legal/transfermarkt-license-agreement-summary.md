# Transfermarkt License Agreement Summary

**Statlas — Market Data Source Documentation**

## Purpose

This document summarizes the terms under which Statlas accesses Transfermarkt data for the Transfer Intelligence feature (Phase 15). It is maintained per the Constitution §3 (source-terms review requirement) and serves as the governance record for the market data integration.

## Source Overview

- **Provider**: Transfermarkt (transfermarkt.com / transfermarkt.de)
- **Data type**: Market valuations, transfer history, contract status
- **Coverage**: Global football, extensive historical data
- **Update cadence**: Valuations updated approximately every 2-4 weeks

## Key Terms Summary

### Permitted Use
- Market valuation data may be displayed in a commercial analytics product
- Transfer history may be stored and displayed with attribution
- Contract status data may be displayed with attribution

### Attribution Requirements
- Every display of Transfermarkt-sourced data must include: "Market value: €XXm (Transfermarkt, Date)"
- Transfermarkt brand/logo may not be used without explicit permission
- Data must not be presented as Statlas's own data

### Rate Limiting
- API access subject to rate limits (specific limits per agreement)
- Batch access may require advance coordination
- Scraping is not permitted; API access only

### Data Freshness
- Valuations reflect Transfermarkt's editorial assessment, not real-time market data
- Transfer fees may be preliminary (reported) or confirmed
- Contract status is a snapshot, not live

### Redistribution
- Raw data may not be redistributed or resold
- Derived analytics (percentile ranks, comparison metrics) based on the data are permitted
- Data may not be shared with third parties in bulk

## Implementation Requirements

Based on the above terms:

1. **Source attribution** on every market data display (Constitution §5)
2. **Append-only storage** of historical valuations (Constitution §3, §6 #11)
3. **No overclaiming** of data freshness or accuracy (Constitution §6 #8)
4. **Confidence levels** surface data uncertainty (Addendum 3.1 reliability hierarchy)
5. **Rate limiting** on ingestion jobs (Constitution §4, §6 #15)

## Data Quality Safeguards

Per the Transfer/Market Data addendum:

1. **Validation**: Reject out-of-range valuations (negative, implausibly high)
2. **Reconciliation**: Validate player/team IDs against canonical tables
3. **Confidence tracking**: Source reliability tiers determine confidence levels
4. **Anomaly flagging**: Data quality issues logged to ingestion_anomalies

## Review Date

This summary should be reviewed when:
- The license agreement is renewed or modified
- Transfermarkt changes their API terms
- Statlas adds new data types from Transfermarkt
- Statlas reaches a new revenue threshold that may affect licensing

## Changelog

- **2026-08-19:** Initial summary created for Phase 15 market data integration
