"""Core valuation engine: FCFF projection -> WACC -> DCF -> per-share equity value.

Layered like a reviewed financial model: inputs come only from the assumptions
file, every calculation is a pure function, and outputs carry enough detail
(PV split, terminal-value share) for an auditor to retrace the numbers.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd


# ---------------------------------------------------------------- WACC

def cost_of_equity(rf: float, beta: float, erp: float) -> float:
    """CAPM: Re = rf + beta * ERP."""
    return rf + beta * erp


def wacc(rf: float, beta: float, erp: float, rd_pretax: float,
         tax_rate: float, debt_to_value: float) -> float:
    re = cost_of_equity(rf, beta, erp)
    rd_after_tax = rd_pretax * (1.0 - tax_rate)
    return (1.0 - debt_to_value) * re + debt_to_value * rd_after_tax


def wacc_grid(w: dict, tax_rate: float) -> pd.DataFrame:
    """WACC under parallel interest-rate shifts (applied to rf and cost of debt)."""
    rows = []
    for name, shift in w["rate_scenarios"].items():
        rows.append({
            "rate_scenario": name,
            "risk_free": w["risk_free"] + shift,
            "cost_of_debt_pretax": w["cost_of_debt_pretax"] + shift,
            "cost_of_equity": cost_of_equity(w["risk_free"] + shift, w["beta"], w["erp"]),
            "wacc": wacc(w["risk_free"] + shift, w["beta"], w["erp"],
                         w["cost_of_debt_pretax"] + shift, tax_rate,
                         w["target_debt_to_value"]),
        })
    return pd.DataFrame(rows).set_index("rate_scenario")


# ---------------------------------------------------------------- FCFF projection

@dataclass
class Projection:
    """Explicit-horizon FCFF forecast for one operating scenario."""
    scenario: str
    table: pd.DataFrame          # year-by-year P&L-to-FCFF walk

    @property
    def fcff(self) -> np.ndarray:
        return self.table["fcff"].to_numpy()


def project_fcff(base: dict, growth: list[float], margin_path: list[float],
                 scenario: str) -> Projection:
    """Walk revenue -> EBIT -> NOPAT -> FCFF year by year.

    FCFF = NOPAT + D&A - capex - change in NWC, with D&A / capex / NWC
    held proportional to revenue (documented simplification).
    """
    years = len(growth)
    revenue = np.empty(years)
    rev_prev = base["revenue"]
    nwc_prev = base["nwc_pct_revenue"] * rev_prev

    rows = []
    for t in range(years):
        revenue[t] = rev_prev * (1.0 + growth[t])
        ebit = revenue[t] * margin_path[t]
        nopat = ebit * (1.0 - base["tax_rate"])
        dna = revenue[t] * base["dna_pct_revenue"]
        capex = revenue[t] * base["capex_pct_revenue"]
        nwc = revenue[t] * base["nwc_pct_revenue"]
        delta_nwc = nwc - nwc_prev
        fcff = nopat + dna - capex - delta_nwc
        rows.append({"year": t + 1, "revenue": revenue[t], "growth": growth[t],
                     "ebit": ebit, "ebit_margin": margin_path[t], "nopat": nopat,
                     "dna": dna, "capex": capex, "delta_nwc": delta_nwc, "fcff": fcff})
        rev_prev, nwc_prev = revenue[t], nwc

    return Projection(scenario=scenario, table=pd.DataFrame(rows).set_index("year"))


# ---------------------------------------------------------------- DCF

@dataclass
class DCFResult:
    scenario: str
    wacc: float
    terminal_growth: float
    pv_explicit: float
    pv_terminal: float
    enterprise_value: float
    equity_value: float
    value_per_share: float
    tv_share_of_ev: float


def dcf(proj: Projection, discount_rate: float, terminal_growth: float,
        net_debt: float, shares_m: float) -> DCFResult:
    """Discount explicit FCFF + Gordon terminal value; bridge EV -> per share."""
    if terminal_growth >= discount_rate:
        raise ValueError(
            f"terminal growth {terminal_growth:.3f} >= discount rate {discount_rate:.3f}")

    fcff = proj.fcff
    t = np.arange(1, len(fcff) + 1)
    disc = (1.0 + discount_rate) ** t
    pv_explicit = float(np.sum(fcff / disc))

    tv = fcff[-1] * (1.0 + terminal_growth) / (discount_rate - terminal_growth)
    pv_terminal = float(tv / disc[-1])

    ev = pv_explicit + pv_terminal
    equity = ev - net_debt
    return DCFResult(
        scenario=proj.scenario, wacc=discount_rate, terminal_growth=terminal_growth,
        pv_explicit=pv_explicit, pv_terminal=pv_terminal, enterprise_value=ev,
        equity_value=equity, value_per_share=equity / shares_m,
        tv_share_of_ev=pv_terminal / ev,
    )


def sensitivity_table(proj: Projection, wacc_range: list[float],
                      g_range: list[float], net_debt: float,
                      shares_m: float) -> pd.DataFrame:
    """Per-share value across the WACC x terminal-growth grid (NaN where g >= WACC)."""
    grid = {}
    for g in g_range:
        col = []
        for w in wacc_range:
            if g >= w:
                col.append(np.nan)
            else:
                col.append(dcf(proj, w, g, net_debt, shares_m).value_per_share)
        grid[f"g={g:.1%}"] = col
    return pd.DataFrame(grid, index=[f"WACC={w:.1%}" for w in wacc_range])
