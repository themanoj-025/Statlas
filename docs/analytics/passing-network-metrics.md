# Passing Network Metrics — Interpretation Guide

## Network Construction

Each match produces a **directed graph** per team where:
- **Nodes** = individual players (by jersey number/team)
- **Edges** = completed passes between players (direction matters: A→B ≠ B→A)
- **Edge weight** = number of completed passes between that pair

## Centrality Metrics

### Degree Centrality
**Definition:** How many different teammates does this player pass to?

- **High degree** → connector/playmaker, involved in buildup across the team
- **Low degree** → specialist, plays in a focused area or role
- **Range:** 0 to (N-1) where N is the number of players in the network

### Betweenness Centrality
**Definition:** How often does this player sit on the shortest path between other player pairs?

- **High betweenness** → central hub, critical to team structure (e.g., Busquets, Pirlo)
- **Low betweenness** → player is peripheral to the passing structure
- **Range:** 0 to 1 (normalized)

### Clustering Coefficient
**Definition:** What fraction of this player's teammates also pass to each other?

- **High clustering** → tight, interconnected passing triangle (possession-heavy teams)
- **Low clustering** → dispersed, direct play style
- **Range:** 0 to 1

## Passing Pattern Metrics

### Pass Success Rate
**Definition:** Percentage of attempted passes that are completed.

- Interpreted per-player within network context
- Combined with passing volume for tactical assessment

### Average Pass Distance
**Definition:** Mean length of completed passes (in StatsBomb coordinate units, ~yards).

- **Short (< 12 units)** → possession/sideways style
- **Medium (12–20 units)** → balanced play
- **Long (> 20 units)** → direct/long-ball style

### Pass Volume
**Definition:** Total completed passes by the team (or per-player).

- Combined with average distance to determine tactical style:
  - High volume + short distance = **possession/sideways**
  - Low volume + long distance = **direct play**
  - Medium volume + medium distance = **balanced**

## Tactical Style Classification

| Style | Pass Volume | Avg Distance | Width | Description |
|---|---|---|---|---|
| Possession | > median | < 12 | Variable | Patient buildup, short passes |
| Direct | < median | > 20 | Central | Long balls, quick transitions |
| Progressive | Median | Increasing | Variable | Building through thirds |
| Wide Play | Variable | Variable | High wing concentration | Flank-focused attacks |
| Central Play | Variable | Variable | High central concentration | Through the middle |

## Outlier Detection

Flags unusual patterns:
- **Dominant playmaker:** Player with unusually high betweenness centrality
- **Asymmetric flow:** One player sending many more passes than receiving
- **Disconnected node:** Player with zero passes to/from them (data error or benching)

## Formation Correlation

Passing networks correlate with formations:
- **4-3-3:** Typically shows central midfield hub with wing distribution
- **5-2-3:** Strong wing-back nodes with central defensive concentration
- **4-4-2:** Balanced two-bank structure with wing play
