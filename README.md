# World Cup 2026 — Round-of-32 Opponent Predictions

An exact, Opta-grounded model and standalone visualisation of every team's likely
Round-of-32 opponent at the 2026 FIFA World Cup (built around England, Group L).

**Live page:** [`wc26_r32_predictions.html`](wc26_r32_predictions.html)
(a frozen snapshot is preserved in [`wc26_r32_predictions_frozen.html`](wc26_r32_predictions_frozen.html)).

## How it works

- **Inputs (Opta only):** each team's finish-position probabilities (1st/2nd/3rd/4th)
  and qualification (reach-R32) chance, taken from the publicly available
  [Opta Analyst](https://theanalyst.com/) Supercomputer. No additional forecasting
  is applied to those numbers.
- **Method:** FIFA's published Round-of-32 bracket rules (including the official
  495-combination table for which group winner hosts which third-placed team) are
  applied to Opta's figures — bracket arithmetic, not a new forecast. Every value is
  computed **exactly** (no Monte Carlo).
- **One assumption:** the joint distribution of which eight third-placed teams qualify
  together (Opta publishes only per-group marginals). This is modelled as independent
  Bernoulli draws conditioned on exactly eight advancing, restricted to combinations
  consistent with the fixed order of already-decided thirds.

## Pipeline

| Script | Output |
|---|---|
| `opponent_matrix_exact.py` | `opponent_matrix_exact.csv` — every team × position × opponent |
| `kickoff_probabilities.py` | `kickoff_probabilities.csv` — P(team plays each dated fixture) |
| `build_webpage.py` | `wc26_r32_predictions.html` — the standalone visualisation |

To refresh with new Opta data: update `opta_positions.csv` (finish positions),
the `QUAL` dict (reach-R32 figures), and `LOCKED_THIRDS_ORDER` (decided thirds),
then rerun the three scripts.

## Disclaimer

Independent, non-commercial, illustrative project. Not affiliated with or endorsed
by Stats Perform, Opta, or FIFA. Finish-position and qualification data
© Stats Perform / Opta, used for personal reference only. Tournament rules text
adapted from Wikipedia (CC BY-SA 4.0); flags from flagcdn.com.
