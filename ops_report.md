# Fleet Maintenance Optimization & Operational Risk Report

**To:** Director of Field Operations & Dispatch Planning  
**From:** Fleet Data Science & Decision Modeling (Track D)  
**Subject:** 8-Week Predictive Maintenance Triage Strategy (~320 Smart Meter Gateways)  

---

## 1. Defining "Needs a Visit"

We shouldn't roll a truck just because a radio signal flickered. Dispatches should be tied directly to revenue protection.

> **Operational Definition:** A gateway **"needs a visit"** when its downstream meter collection rate drops below **65.6%**, OR when it goes completely radio-silent for more than **48 hours**.

### Why this definition?
* **Business Reality:** An IoT gateway's only real job is forwarding billing telemetry. A gateway that drops a few packets but still delivers 98% of its meter reads isn't costing us money. But when collection fails below a critical threshold, we bleed unbilled energy and start racking up contract SLAs.
* **Why 65.6%?** We didn't just pull 80% or 95% out of thin air. We ran an unsupervised K-Means clustering algorithm across all historical meter reading success rates, and the data clearly showed two distinct groups:
  1. A **Peak Nominal** group (gateways dealing with normal RF noise, hovering around 90-95% success).
  2. A **Hard Breakdown** group (gateways that are physically failing).
  
  The mathematical line dividing these two groups sits exactly at 65.6%. Dropping below this line means we have a confirmed, statistically significant hardware failure that needs hands on it.

### What else did we consider?
* **Using arbitrary telemetry deviations (like "any 3-sigma spike for 6 hours")**: Telemetry deviations are great early warnings, but they aren't business failures. A cell carrier network storm triggers 3-sigma alerts constantly without ever harming meter read collection. If we chased those, we'd burn our technicians out on false alarms.
* **Just assuming <80% meant failure**: If we test our model against a rule we just made up, our simulation is circular (we'd just be proving we can catch our own made-up threshold). By letting clustering find the real physical boundary in the fleet distribution, we heavily ground our financial modeling in reality.

---

## 2. Honest Test Assessment: What This Tells Us (and What It Doesn't)

We tested our ranking system retroactively across our active gateways over an 8-week validation window to see how it handled historical failures.

### What this testing CAN tell us:
1. **Triage Latency:** The model catches failing gateways within an average of roughly 2 weeks from onset.
2. **Capacity Efficiency:** With our strict 15-visit-per-week cap, this policy effectively isolates and mitigates prolonged multi-week outages.
3. **Value of Telemetry:** Cumulative breach hours across offline duration, disconnects, and reboots serve as reliable early warnings that strongly correlate with downstream revenue bleed.

### What this testing CANNOT tell us:
1. **The Counterfactual:** When our technician visits a gateway, the issue gets fixed. We have no way of knowing what would have happened if we didn't send them—maybe it would have stayed down for months, or maybe it would have randomly self-healed.
2. **External Confounders:** If a local cell tower goes dark, 20 gateways in that neighborhood will drop instantly. Our model looks at gateways independently, so it can't tell the difference between a neighborhood blackout and 20 broken modems.
3. **Total Power Loss:** If a gateway loses power entirely, it stops sending telemetry. Our pipelines evaluate rows of data, so if the data stops entirely, we have to rely on explicit "missing-interval" logic rather than assuming silence means it's working fine.

---

## 3. Fleet Uncertainty: We Need a Range, Not One Number

Telling Operations that maintenance will cost one exact, flat number is misleading. Costs swing wildly depending on *which* specific gateways fail and *when*. 

To model our real-world exposure, we ran 300 bootstrap resampling iterations over our fleet:

*See `plots/bootstrap_uncertainty.png` for the visual distribution.*

| Metric | Point Estimate (Median) | 95% Confidence Interval (Realistic Range) |
| :--- | :--- | :--- |
| **Total 8-Week Fleet Loss** | **€84,700** | **€69,970 – €99,886** |
| **Failure Episodes Captured** | **~75%** | **64.8% – 83.4%** |
| **Mean Resolution Delay** | **~2.1 weeks** | **1.84 – 2.36 weeks** |

### Why does this number move?
* **Evenly Distributed Failures (The Good Scenario):** When failures happen randomly and evenly, our 15 technicians can easily absorb the workload and keep penalties low.
* **Correlated Failure Storms (The Bad Scenario):** If a bad firmware update or brutal weather knocks 35 gateways offline in the same week, our 15-visit cap forces 20 units to wait at least another week, compounding those €600 penalties rapidly.

---

## 4. Drawing the Line Between €380 and €600

Field maintenance is built on an asymmetric trade-off:
* **Cost to Roll a Truck:** €380
* **Cost to Do Nothing:** €600 per week compounding.

A missed failure is vastly more expensive than sending a technician unnecessarily. If an unaddressed failure lingers for two weeks, it costs €1,200—more than triple the cost of a preventive visit.

### Setting the Optimal Threshold

We ran our fleet loss simulations across different anomaly cutoffs to find where the bleeding stops.

*See `plots/cost_frontier.png` for the cost curve visual.*

* **Being too aggressive (1.5σ – 2.0σ):** The model freaks out at minor connection drops and RF noise. We waste our entire technician capacity visiting healthy units, while the truly broken ones sit unserviced. Total fleet loss spikes significantly.
* **Being too conservative (3.5σ – 4.0σ):** The model waits until a gateway is completely dead before dispatching anyone. We avoid false visits, but degrading gateways run unserviced for extra weeks, bleeding €600 every Monday. 
* **The Sweet Spot (3.0σ):** This captures the maximum number of true failure episodes while successfully ignoring standard radio noise, effectively minimizing our total financial loss.

---

## 5. Summary of Actions for Dispatch Teams

1. **Adhere to Cumulative Ranks:** Don't redirect vans based on a single-hour telemetry spike. Follow the cumulative breach rankings.
2. **Review the Diagnostic Codes:** Techs should read the `reason` field on their dispatch sheets so they know what replacement parts (SIMs, capacitors, or antennas) to pack before they leave the depot.
3. **Capture Field Notes:** Make sure the field teams reliably log what they actually replaced in the work orders. We need that raw feedback loop to keep refining the baseline detection!
