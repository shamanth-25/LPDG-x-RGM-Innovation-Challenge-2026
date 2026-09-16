# ⚡ IoT Gateway Predictive Maintenance
### Track D: Decision Modeling & Asymmetric Cost Optimization

This repo contains my submission for the IoT Predictive Maintenance challenge. It’s an automated triage pipeline that figures out exactly which 15 gateways we need to send field technicians to each week. 

At its core, this is an economic balancing act: we pay a flat €380 to roll a truck, but if we ignore a broken gateway, it bleeds €600 every week in missed meter readings.

---

## 📌 Executive Summary

Field dispatch operations face a tricky problem:
* **Cost of Action:** It costs €380 to send a technician.
* **Cost of Inaction:** If a gateway stays broken, we lose €600 per week.
* **The Catch:** We only have the budget to deploy 15 technicians a week.

To solve this, I built a rolling 28-day statistical anomaly model covering the three main telemetry metrics (`offline_duration_sec`, `disconnection_cnt`, `reboot_cnt`). Instead of just guessing, it uses an asymmetric cost frontier to rank our weakest gateways without accidentally leaking future data into the model.

---

## 📊 Key Results

Here is a quick look at how the model actually performs:

| Metric | What We Got | What It Means |
| :--- | :--- | :--- |
| **Optimal Cutoff** | **3.0σ** | Minimizes total fleet loss (€182,400 across 8 weeks) compared to being too aggressive (1.5σ costs €194,400). |
| **Total 8-Week Loss Range** | **€69,970 – €99,886** | 300-iteration bootstrap resampling over 299 gateways (95% CI). Operations shouldn't rely on a single static number. |
| **Median Expected Loss** | **€84,700** | Our baseline financial baseline across standard failure variance. |
| **Failure Capture Rate** | **64.8% – 83.4%** | How well we catch real failure episodes within the strict 15-visit cap. |
| **Mean Resolution Delay** | **~2 weeks** | The average time a fault sits unresolved before a technician gets to it. |

---

## 🖼️ Visuals & Data

* **Threshold Sensitivity:** Check out `plots/cost_frontier.png`. It shows how fleet loss behaves as we adjust our anomaly cutoffs from 1.5σ to 4.0σ.
* **Fleet Uncertainty:** Check out `plots/bootstrap_uncertainty.png`. It maps out the 95% confidence intervals for our expected costs.

---

## 🚀 Quick Start

Ensure your telemetry dataset is mounted inside the `./data` folder, then just spin up Docker:

```bash
docker compose up --build
```

It will process the data and output the required 120-row `predictions.csv`. Easy as that.
