# -*- coding: utf-8 -*-
"""Entry point: load assumptions -> validate -> project -> value -> write outputs/.

Usage:  python run_valuation.py
Outputs: outputs/scenario_summary.csv, sensitivity heatmap, FCFF chart,
         WACC-scenario chart, and a console audit log.
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from valuation import project_fcff, wacc_grid, dcf, sensitivity_table  # noqa: E402
import checks  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "outputs")
os.makedirs(OUT, exist_ok=True)

NAVY, BLUE, RED, GREY = "#1F3A5F", "#2E6DA4", "#C0392B", "#8A8F98"


def main() -> None:
    cfg = yaml.safe_load(open(os.path.join(ROOT, "assumptions", "inputs.yaml"),
                              encoding="utf-8"))
    base, w = cfg["base_financials"], cfg["wacc"]
    company = cfg["company"]
    g_term = cfg["projection"]["terminal_growth"]

    print("== input checks ==")
    for note in checks.check_inputs(cfg):
        print("  PASS:", note)

    # WACC under rate scenarios
    wg = wacc_grid(w, base["tax_rate"])
    base_wacc = float(wg.loc["base", "wacc"])
    print(f"\n== WACC grid (base = {base_wacc:.2%}) ==")
    print(wg.round(4).to_string())

    # Project and value each operating scenario at base WACC
    results, projections = [], {}
    for key, s in cfg["scenarios"].items():
        proj = project_fcff(base, s["revenue_growth"], s["ebit_margin_path"], s["label"])
        projections[key] = proj
        results.append(dcf(proj, base_wacc, g_term,
                           company["net_debt"], company["shares_outstanding_m"]))

    print("\n== result checks ==")
    for note in checks.check_results(results, list(wg["wacc"])):
        print("  " + ("PASS: " if not note.startswith("WARN") else "") + note)

    summary = pd.DataFrame([{
        "scenario": r.scenario, "wacc": r.wacc, "terminal_growth": r.terminal_growth,
        "pv_explicit": r.pv_explicit, "pv_terminal": r.pv_terminal,
        "enterprise_value": r.enterprise_value, "equity_value": r.equity_value,
        "value_per_share_aud": r.value_per_share, "tv_share_of_ev": r.tv_share_of_ev,
    } for r in results]).set_index("scenario")
    summary.to_csv(os.path.join(OUT, "scenario_summary.csv"), encoding="utf-8-sig")
    print("\n== scenario summary (A$m; per-share in A$) ==")
    print(summary.round(2).to_string())

    _plot_scenarios(summary, company)
    _plot_fcff(projections)
    _plot_sensitivity(projections["base"], cfg, company)
    _plot_wacc(wg)
    print(f"\nWROTE outputs -> {OUT}")


def _plot_scenarios(summary: pd.DataFrame, company: dict) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    vals = summary["value_per_share_aud"]
    bars = ax.bar(range(len(vals)), vals, color=[BLUE, NAVY, RED], width=0.55)
    ax.axhline(company["price_snapshot_aud"], color=GREY, ls="--", lw=1.2,
               label=f"price snapshot A${company['price_snapshot_aud']:.2f}")
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.1, f"A${v:.2f}",
                ha="center", fontsize=10, fontweight="bold")
    ax.set_xticks(range(len(vals)))
    ax.set_xticklabels([s.split("—")[0].strip() for s in summary.index], fontsize=10)
    ax.set_ylabel("DCF value per share (A$)")
    ax.set_title("TWE — DCF value per share by operating scenario (base WACC)")
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "scenario_values.png"), dpi=150)


def _plot_fcff(projections: dict) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    colors = {"base": BLUE, "china_reacceleration": NAVY, "domestic_squeeze": RED}
    for key, proj in projections.items():
        ax.plot(proj.table.index, proj.table["fcff"], marker="o",
                color=colors[key], label=proj.scenario)
    ax.set_xlabel("Forecast year")
    ax.set_ylabel("FCFF (A$m)")
    ax.set_title("Free cash flow to the firm — explicit horizon")
    ax.legend(frameon=False, fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fcff_paths.png"), dpi=150)


def _plot_sensitivity(base_proj, cfg: dict, company: dict) -> None:
    tbl = sensitivity_table(base_proj, cfg["sensitivity"]["wacc_range"],
                            cfg["sensitivity"]["terminal_growth_range"],
                            company["net_debt"], company["shares_outstanding_m"])
    tbl.to_csv(os.path.join(OUT, "sensitivity_table.csv"), encoding="utf-8-sig")

    fig, ax = plt.subplots(figsize=(8, 4.8))
    data = tbl.to_numpy(dtype=float)
    im = ax.imshow(data, cmap="RdYlGn", aspect="auto")
    ax.set_xticks(range(len(tbl.columns)), tbl.columns, fontsize=9)
    ax.set_yticks(range(len(tbl.index)), tbl.index, fontsize=9)
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            if not np.isnan(data[i, j]):
                ax.text(j, i, f"{data[i, j]:.2f}", ha="center", va="center",
                        fontsize=8.5)
    ax.set_title("Sensitivity — DCF value per share (A$), base scenario")
    fig.colorbar(im, ax=ax, shrink=0.85, label="A$/share")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "sensitivity_heatmap.png"), dpi=150)


def _plot_wacc(wg: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.bar(wg.index, wg["wacc"] * 100, color=[BLUE, NAVY, RED], width=0.5)
    for b, v in zip(bars, wg["wacc"] * 100):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.05, f"{v:.2f}%",
                ha="center", fontsize=10, fontweight="bold")
    ax.set_ylabel("WACC (%)")
    ax.set_title("WACC under parallel interest-rate scenarios")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "wacc_scenarios.png"), dpi=150)


if __name__ == "__main__":
    main()
