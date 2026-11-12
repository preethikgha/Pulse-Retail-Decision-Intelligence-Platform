# Causal Analysis: Does Late Delivery Lower Review Scores?

**Data:** 95,561 delivered orders with a review, purchased Jan 2017 to Aug 2018 (real Olist data, Kaggle). 8.0% of these were late (delivered after the estimated date).
**Code:** `analysis/causal.py`. **Outputs:** `analysis/causal_outputs/`.

## Question
Late orders get worse reviews (4.30 vs 2.57 average stars). Is that because of lateness, or because late orders are different kinds of orders (distance, price, category, season)?

## Approach
This is an observational study with no randomization. I fitted OLS regressions with robust (HC1) standard errors and added controls step by step, watching whether the estimated effect moves.

| Model | Controls | Effect of late delivery on review score | 95% CI |
|---|---|---|---|
| M1 | none (naive) | -1.730 | [-1.767, -1.692] |
| M2 | price, freight, items, sellers, promised days | -1.765 | [-1.802, -1.727] |
| M3 | M2 + customer state and purchase month fixed effects | -1.713 | [-1.751, -1.675] |
| M4 | single-item orders, + category and seller state | -1.749 | [-1.789, -1.709] |
| M5 | M3 controls, outcome = review of 1-2 stars | +0.446 probability | [0.435, 0.457] |

## Results
- The late-delivery effect is stable at about -1.7 to -1.8 stars across all four specifications. Adding controls for order size, price, route, season and category does not shrink it.
- Late orders are about 45 percentage points more likely to receive a 1-2 star review.
- **Dose-response:**

| Delivery vs promised date | Orders | Avg review | Share of 1-2 stars |
|---|---|---|---|
| more than 7 days early | 70,831 | 4.32 | 9.0% |
| 0-7 days early | 17,124 | 4.20 | 10.2% |
| 0-3 days late | 2,596 | 3.75 | 19.7% |
| 3-7 days late | 1,786 | 2.31 | 61.6% |
| more than 7 days late | 3,224 | 1.73 | 78.4% |

  Reviews fall steadily with lateness, with the sharpest drop between 0-3 and 3-7 days late.
- **Balance check:** late orders are about 4.3% higher in price after controlling for state and month. This is statistically significant at this sample size but small in practice.

## Interpretation
Late delivery is strongly and robustly associated with worse reviews, and the association survives adjustment for the observable differences between orders. The dose-response pattern is what we would expect if lateness itself drives dissatisfaction.

## What this analysis cannot claim
- It does not prove causation. Unobserved factors can still bias the estimate: a seller that ships late may also send damaged or wrong items, and reviews may reflect product quality, not delivery.
- It covers only delivered orders with a review. Canceled and undelivered orders, and customers who did not review, are excluded.
- Late is defined against the promised date, so it mixes slow delivery with tight promises.
- The step between 0-3 and 3-7 days late is a description of this data, not a tested threshold.

## Next steps that would strengthen it
- Compare orders within the same seller (seller fixed effects) so seller quality is held constant.
- Add a sensitivity analysis for how strong an unobserved confounder would need to be to remove the effect.