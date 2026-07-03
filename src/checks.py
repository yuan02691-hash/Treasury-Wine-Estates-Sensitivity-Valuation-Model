"""Model validation — the audit page of the model.

Every run executes these checks before outputs are written; a failed hard
check aborts the run. Mirrors how a reviewed corporate model carries a
dedicated checks sheet rather than trusting the build.
"""
import numpy as np


HARD_BOUNDS = {
    "ebit_margin": (0.05, 0.45),      # wine-industry plausible band
    "tax_rate": (0.20, 0.35),
    "terminal_growth": (0.0, 0.04),   # cannot outgrow the economy forever
    "wacc": (0.05, 0.15),
}


def check_inputs(cfg: dict) -> list[str]:
    """Hard checks: raise on violation. Returns list of passed-check notes."""
    notes = []
    base = cfg["base_financials"]

    for scen, s in cfg["scenarios"].items():
        for m in s["ebit_margin_path"]:
            _within("ebit_margin", m, scen)
        if len(s["revenue_growth"]) != cfg["projection"]["years"]:
            raise ValueError(f"{scen}: growth path length != projection years")
        if len(s["ebit_margin_path"]) != cfg["projection"]["years"]:
            raise ValueError(f"{scen}: margin path length != projection years")
    notes.append("scenario paths: lengths consistent, margins within industry band")

    _within("tax_rate", base["tax_rate"])
    _within("terminal_growth", cfg["projection"]["terminal_growth"])
    notes.append("tax rate and terminal growth within policy bounds")

    if base["nwc_pct_revenue"] < 0.15:
        raise ValueError("NWC% looks too low for an inventory-heavy wine business")
    notes.append("working-capital intensity consistent with wine inventory cycle")
    return notes


def check_results(results: list, wacc_values: list[float]) -> list[str]:
    """Post-run checks on DCF outputs."""
    notes = []
    for w in wacc_values:
        _within("wacc", w)
    notes.append("all WACC values within sanity band")

    for r in results:
        recomputed = r.pv_explicit + r.pv_terminal
        if not np.isclose(recomputed, r.enterprise_value, rtol=1e-9):
            raise AssertionError(f"{r.scenario}: EV bridge does not tie")
        if not (0.4 <= r.tv_share_of_ev <= 0.9):
            notes.append(f"WARN {r.scenario}: terminal value is "
                         f"{r.tv_share_of_ev:.0%} of EV — outside typical 40-90%")
    notes.append("EV bridge ties (PV explicit + PV terminal = EV) for all scenarios")
    return notes


def _within(name: str, value: float, context: str = "") -> None:
    lo, hi = HARD_BOUNDS[name]
    if not (lo <= value <= hi):
        raise ValueError(f"{context + ': ' if context else ''}{name}={value} "
                         f"outside hard bounds [{lo}, {hi}]")
