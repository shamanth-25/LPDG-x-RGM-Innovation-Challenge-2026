=====================================================
NEXORA 2026 - FINAL SUBMISSION
LPDG INNOVATION HUB - SELECTION CHALLENGE 2026
===========================================================

PROJECT OVERVIEW

This submission addresses Track D (Decision Modeling) for the
NEXORA 2026 challenge.

The core problem is field dispatch optimization under an asymmetric 
economic constraint: 
  - ACTION: €380 fixed cost per technician visit.
  - INACTION: €600 weekly recurring penalty for unread meters.
  - CONSTRAINT: Strict capacity of 15 visits per week across the fleet.

To solve this, we cannot rely on arbitrary assumptions. We engineered 
a complete pipeline that empirically defines what a failure is, assesses 
gateway health objectively, and optimizes the financial threshold.

------------------------------------------------------------
THE FULL PROCESS (HOW IT WORKS)
------------------------------------------------------------

PHASE 1: DEFINING FAILURE (UNSUPERVISED LEARNING)
Instead of guessing that severely degraded meter readings imply a broken
gateway, we applied 1-D K-Means Clustering to the entire historical
distribution of meter collection rates. 
The algorithm algebraically isolates two populations:
1. Normal RF interference / self-healing packet drops (usually 90%+ success).
2. Hard physical breakdown.
The boundary naturally emerges at ~65.6%. This gives us a statistically
justified GROUND TRUTH definition for "needs a visit."

PHASE 2: ANOMALY SCORING (NO LOOKAHEAD LEAKAGE)
Because we lack verified failure labels ahead of time, supervised ML 
suffers from severe target leakage here. Instead, we use a rolling
3-Sigma Statistical Deviation model:
1. Extract a strict 28-day baseline from telemetry history.
2. Flag any hours in the final 7 days where variables exceed 3 standard
   deviations of that gateway's own localized baseline.
3. Compute cumulative flagged hours to rank the worst offenders, ignoring
   single-hour network spikes.

PHASE 3: ECONOMIC SIMULATION & OPTIMIZATION
We map our 3-sigma predictive rankings back against the K-Means derived
ground truth across the entire fleet to build a simulated Cost Frontier.
Simulating cutoffs from 1.5σ to 4.0σ proves that a 3.0σ boundary represents 
the exact point of inflection, minimizing total portfolio loss down to 
~€84,700 over the 8-week period.

PHASE 4: QUANTIFYING UNCERTAINTY (BOOTSTRAPPING)
In operations, single-number point estimates are misleading. 
To prove robustness, the pipeline runs 300 non-parametric bootstrap 
resamples to establish 95% Confidence Intervals. This proves our economic
optimization holds true regardless of the random clustering of failures in time.

------------------------------------------------------------
QUICK START
------------------------------------------------------------

1. Ensure your telemetry dataset is mounted in:

    data/

2. Run the complete pipeline via Docker:

    docker compose up --build

Alternatively, to run it natively without Docker:

    pip install -r requirements.txt
    python3 run_solution.py

The pipeline automatically:

    1. Infers empirical ground-truth failure thresholds via K-Means.
    2. Builds the historical baseline anomaly statistics over 28-day windows.
    3. Simulates the cost frontier and generates Uncertainty Plots.
    4. Generates exactly 120 lines in predictions.csv targeting the 
       official benchmark weeks.
