# Treasury Wine Estates (ASX: TWE) — Scenario & Sensitivity Valuation Model

A layered, auditable **DCF valuation model** for Treasury Wine Estates, built the way a
reviewed corporate model should be: assumptions in one sourced input file, pure-function
calculations, hard validation checks that run before any output is written, and
scenario / sensitivity analysis around the two levers that actually move the answer —
**WACC and terminal growth**.

> Built as a public rebuild of client-style work I do as a financial analyst
> (scenario planning and WACC modelling for an Australian wine exporter across
> domestic and China markets) — reconstructed on public data so it can be shared.

---

## Business question

TWE's earnings mix is shifting toward China-led luxury exports while domestic margins
face labour-cost and demand pressure. What is a share worth under coherent
**operating scenarios** (China re-acceleration vs domestic squeeze), and how sensitive
is that value to **funding-cost assumptions** in a moving rate environment?

## Method

```
assumptions/inputs.yaml   ->   src/valuation.py   ->   src/checks.py   ->   outputs/
(single sourced input          FCFF projection         hard bounds +        charts,
 sheet, FY25-based)            CAPM/WACC, DCF,          EV-bridge tie        tables,
                               sensitivity grid         checks               audit log
```

1. **FCFF projection (5 years)** — revenue → EBIT → NOPAT → FCFF walk per scenario,
   with D&A / capex / working capital tied to revenue (documented simplification;
   wine is inventory-heavy, so NWC intensity is a first-class input).
2. **WACC** — CAPM cost of equity + after-tax cost of debt at a target D/V of 25%,
   evaluated under parallel **interest-rate scenarios** (easing / base / tightening).
3. **DCF** — explicit-horizon PV + Gordon terminal value, EV → equity → per share.
4. **Checks before outputs** — margin/tax/growth hard bounds, path-length consistency,
   `g < WACC` guard, EV-bridge tie-out, terminal-value share flagged outside 40–90%.

## Results (FY2025 actuals as operating base; market inputs as at early Jul 2026)

| Scenario | WACC | Value / share |
|---|---|---|
| Bull — China luxury re-acceleration | 7.66% | **A$12.96** |
| Base — steady premiumisation | 7.66% | **A$11.01** |
| Bear — margin squeeze (US/domestic) | 7.66% | **A$9.12** |

WACC grid: **6.73% (easing) / 7.66% (base) / 8.58% (tightening)** — built off the
4.80% AU 10Y yield (3 Jul 2026); a ±100bp parallel rate shift moves the discount
rate by roughly ±90bp at the target capital structure.

**What the gap to the market price says.** At the early-July 2026 quote of ~A$4.81,
the market price sits below the *most conservative cell of the entire sensitivity
grid* (A$5.61 at WACC 10.5% × g 1.5%). No plausible discount-rate assumption
reconciles FY25-anchored cash flows with today's price — the market is pricing
**structurally weaker operating assumptions** than even this model's bear case.
The context supports that read: FY25 EBITS was a record A$770m, yet H1 FY26 brought
a large non-cash US asset impairment and a statutory loss, so the market is
discounting margin durability (US portfolio, China concentration, tariff risk)
rather than the rate environment. That is exactly what scenario modelling is for:
the grid shows the disagreement is about cash flows, not the discount rate, and
directs the next round of work to the operating inputs — a harsher impairment-case
scenario would be the natural next build.

WACC grid: **6.27% (easing) / 7.20% (base) / 8.12% (tightening)** — a ±100bp parallel
rate shift moves the discount rate by roughly ±90bp at the target capital structure.

![Scenario values](outputs/scenario_values.png)

![Sensitivity heatmap](outputs/sensitivity_heatmap.png)

![FCFF paths](outputs/fcff_paths.png)

![WACC scenarios](outputs/wacc_scenarios.png)

**Reading the sensitivity table:** at base-scenario cash flows, the per-share value
spans **A$5.61 – A$14.26** across WACC 7.5–10.5% × terminal growth 1.5–3.5% — the
discount-rate assumption moves the answer more than any single operating lever, which
is why the model treats WACC as a scenario variable rather than a constant. Terminal
value is ~77–80% of EV, typical for a 5-year explicit window and flagged by the
checks layer. Note the market price (~A$4.81) sits below the grid's floor — see the
gap discussion above.

## Data provenance (refreshed 2026-07-04)

| Input | Value | Vintage / source |
|---|---|---|
| Net sales revenue | A$2,900m | FY2025 actuals (+7.2% yoy), TWE FY25 results, Aug 2025 |
| EBITS margin | 26.6% | EBITS A$770.3m / NSR, same source |
| Net debt | A$1,770m | FY2025 balance sheet (incl. leases), same source |
| Shares outstanding | ~810m | Approximation — verify against latest ASX Appendix 2A |
| Price snapshot | A$4.81 | ASX quote, 2026-07-03 (context only, not a model input) |
| Risk-free rate | 4.80% | AU 10Y government bond yield, 2026-07-03 |
| Cost of debt | 6.70% | rf + ~190bp credit spread (calibration held constant) |
| Beta / ERP / D-to-V | 0.70 / 5.5% / 25% | Practitioner-range assumptions, unchanged |
| D&A, capex, NWC ratios | 6.2% / 6.0% / 32% | FY2024-derived structural ratios, carried forward pending FY26 report |

Update policy: operating base refreshes on each annual result; market inputs
(price, 10Y yield) are dated snapshots; anything not directly sourced is labelled
an approximation in `assumptions/inputs.yaml`.

## Run it

```bash
pip install -r requirements.txt
python run_valuation.py        # writes outputs/ and prints the audit log
```

Every run prints the audit log first (input checks → WACC grid → result checks
→ scenario summary) before writing `outputs/`.

## Repo structure

```
assumptions/inputs.yaml    # ALL inputs, sourced & dated — edit here, nowhere else
src/valuation.py           # projection, WACC, DCF, sensitivity (pure functions)
src/checks.py              # hard-bound validation + EV bridge tie-out
run_valuation.py           # entry point: validate -> value -> plot
outputs/                   # generated charts + CSV tables (committed for the README)
```

## Known simplifications

- D&A, capex and working capital scale with revenue; in perpetuity capex (6.0% of
  revenue) sits slightly below D&A (6.2%), which marginally favours terminal FCFF —
  the checks layer flags this on every run so a reviewer can't miss it.
- Single-segment model: TWE's Penfolds / Premium / Commercial divisions are not
  modelled separately; the scenario margin paths proxy for mix shift.
- Net debt is held constant across the horizon (no explicit debt schedule).

## Disclaimer

The operating base uses TWE's published FY2025 results with FY2024-derived structural
ratios; market inputs are dated snapshots (see Data provenance). Everything is
**deliberately simplified for methodology demonstration**. This is a modelling
portfolio piece, not investment research or advice.
