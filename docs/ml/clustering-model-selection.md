# Phase 14 — Clustering Model Selection

## Algorithm Choice: K-Means Clustering

### Why K-Means

1. **Simplicity and interpretability:** K-means produces hard cluster assignments
   and cluster centers that are directly interpretable as "average player profiles."
   This satisfies the Constitution's burden of explainability (§1.3).

2. **Speed:** K-means runs in O(n·k·d·i) time (n = players, k = clusters,
   d = features, i = iterations). For ~2000 players × 17 features × 8 clusters,
   training completes in under 1 second.

3. **Well-understood:** The algorithm's behavior is predictable and its failure
   modes are well-documented. There are no "black box" surprises.

4. **Deterministic given seed:** With a fixed random seed, the results are
   reproducible. This satisfies the reproducibility requirement (§2.1).

### Why Not Other Algorithms

| Algorithm | Reason for rejection |
|-----------|---------------------|
| DBSCAN | Produces noise labels; hard to define a fixed number of interpretable archetypes |
| Gaussian Mixture Models | Soft assignments harder to explain; "this player is 60% archetype A" is less useful than "this player IS archetype A" |
| Hierarchical clustering | O(n²) memory; doesn't scale well; harder to assign new players at inference |
| Spectral clustering | Less interpretable; requires eigendecomposition; overkill for this use case |

## Hyperparameter Selection

### Number of Clusters (k)

The optimal k is determined by:

1. **Silhouette analysis:** Compute silhouette score for k ∈ {4, 5, 6, 7, 8, 9, 10}.
   The silhouette score measures how similar a player is to their own cluster vs.
   the nearest other cluster. Higher is better.

2. **Elbow method:** Plot within-cluster sum of squares (WCSS) vs. k. Look for the
   "elbow" where adding more clusters provides diminishing returns.

3. **Interpretability check:** For each candidate k, manually interpret the resulting
   clusters. If any cluster cannot be given a coherent name and description, k is
   too high (clusters are splitting meaningful groups into artificial subgroups).

**Decision threshold:** Silhouette score must exceed 0.30 to be considered for
production. Scores below this indicate the clusters are not well-separated.

**Expected outcome:** k = 6-8 is likely optimal for each position group, balancing
cluster coherence with interpretability.

### Random Seed

A fixed random seed (42) is used for reproducibility. Stability tests verify that
training with different seeds (42, 123, 456) produces similar cluster centers
(centroid cosine similarity > 0.95).

### Initialization

K-means++ initialization (the sklearn default) is used for better convergence
and reduced sensitivity to initial centroid placement.

### Max Iterations

300 iterations (sklearn default). In practice, convergence is reached in <50
iterations for this dataset size.

## Evaluation Metrics

### Primary: Silhouette Score

Range: [-1, 1]. Higher is better.
- > 0.5: strong structure (good)
- 0.25-0.5: moderate structure (acceptable)
- < 0.25: weak structure (investigate)

### Secondary: Davies-Bouldin Index

Range: [0, ∞). Lower is better. Measures average similarity between clusters.
Lower values indicate more distinct clusters.

### Per-Subgroup Metrics

Silhouette score computed separately for:
- Each position group (CB, FB, DM, CM, AM, W, ST)
- Each league (Premier League, La Liga, Bundesliga, Serie A, Ligue 1)

**Bias audit:** If any subgroup shows silhouette score < 0.20 while the overall
score is > 0.30, this is flagged as a potential bias issue and documented in
the bias audit.

## Stability Testing

Train the model 3 times with different random seeds (42, 123, 456). For each
pair of runs, compute:
- Centroid cosine similarity per cluster (must be > 0.95)
- Assignment agreement (% of players assigned to the same cluster; must be > 85%)

If stability criteria are not met, increase k or investigate data quality.
