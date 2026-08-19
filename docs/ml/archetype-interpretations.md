# Phase 14 — Archetype Interpretations

## Overview

This document defines the naming rationale and descriptions for discovered player
archetypes. Archetypes are named based on their cluster center's statistical
characteristics, not arbitrary labels.

**Constitution Addendum §1.3:** Every archetype must be explainable. If a user
asks "why is this player in this archetype?" the answer must reference specific
statistical characteristics, not "the model assigned them."

## Naming Methodology

For each cluster:
1. Compute the cluster center (mean feature values for all players in cluster)
2. Compute the difference between cluster center and global mean for each feature
3. Identify the top 3-5 features that differ most from the global mean
4. Name the archetype based on those distinguishing features
5. Write a description grounded in the actual statistics

## Archetype Naming Conventions

- Names must be descriptive and grounded in statistics
- Names must be understandable by football analysts
- Names must not be arbitrary labels (no "Type A", "Group 1")
- Examples of good names: "Progressive Ball-Winners", "Possession Controllers"
- Examples of bad names: "The Energizer", "Type B", "Cluster 3"

## Typical Archetype Descriptions

The following are example archetype descriptions (actual names will be determined
by the clustering results). Each archetype has:
- A descriptive name
- A one-paragraph plain-language description
- The top 3 distinguishing features with actual stat values vs. global average
- Example players closest to the cluster center

### Example Archetypes (for reference)

#### "Progressive Ball-Winners"
High pressing activity, high tackle rates, above-average progressive passes.
These players win the ball and immediately look to advance it. Typical of
modern pressing midfielders who combine defensive work with ball progression.

Distinguishing features:
- Pressures p90: 45.2 (global avg: 32.1)
- Tackles p90: 3.8 (global avg: 2.4)
- Progressive passes p90: 8.1 (global avg: 5.6)

#### "Possession Controllers"
High pass completion, high progressive passes, low pressure activity. These
players dictate tempo through passing rather than pressing. Typical of
deep-lying playmakers and metronome midfielders.

Distinguishing features:
- Pass completion %: 89.2% (global avg: 82.1%)
- Progressive passes p90: 10.3 (global avg: 5.6)
- Pressures p90: 18.7 (global avg: 32.1)

#### "Box-to-Box Athletes"
Balanced profile across all dimensions — moderate-to-high in pressing, passing,
carrying, and creation. These players contribute in all phases. Typical of
complete midfielders who cover the full pitch.

Distinguishing features:
- Pressures p90: 35.8 (global avg: 32.1)
- Progressive carries p90: 3.2 (global avg: 2.1)
- Key passes p90: 1.8 (global avg: 1.2)

## Bias Audit Notes

When interpreting archetypes, the following biases must be documented:

1. **League bias:** If a cluster is dominated by players from one league, the
   archetype may reflect league-specific tactical patterns rather than universal
   playing styles.

2. **Position bias within groups:** Even within a position group (e.g., CM),
   there may be sub-position differences (defensive CM vs. attacking CM) that
   affect archetype assignment.

3. **Data sparsity:** Players with fewer minutes may have noisier feature values,
   making their archetype assignment less reliable.

4. **Seasonal variation:** A player's archetype may change across seasons as their
   role evolves. This is expected and documented, not a bug.
