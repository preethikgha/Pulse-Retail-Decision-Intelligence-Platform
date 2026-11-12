# Ship / No-Ship Memo: Marketing Ad Campaign vs PSA Control

**Data note:** public Kaggle dataset (Marketing A/B Testing). I did not run this experiment. The intended allocation and the assignment method are not documented.
**Code:** `experiments/ab_test.py`. **Outputs:** `experiments/outputs/`.

## Recommendation
**Ship (continue the ad campaign), conditional on a short confirmation test and a cost check.** The lift is large and well outside noise, but the dataset cannot rule out an assignment problem, and it has no cost data, so profitability cannot be confirmed here.

## Setup
- Hypothesis: users shown the ad convert more often than users shown a public service announcement (PSA).
- Groups: ad 564,577 users (96.0%), PSA 23,524 users (4.0%). Outcome: converted (yes/no).
- Test: two-proportion z-test with a Newcombe confidence interval for the absolute difference, alpha 0.05, two-sided.

## Results
| | Ad | PSA |
|---|---|---|
| Users | 564,577 | 23,524 |
| Conversions | 14,423 | 420 |
| Conversion rate | 2.555% | 1.785% |

- Absolute lift: **+0.769 pp** (95% CI 0.587 to 0.936). Relative lift: **+43.1%** (95% CI 30.0% to 57.5%).
- z = 7.37, p = 1.7e-13. A chi-square test agrees.
- In plain terms: about 7.7 extra conversions per 1,000 users reached (range 5.9 to 9.4).

## Power
With 80% power at alpha 0.05, this sample can detect a lift of about 0.25 pp (13.8% relative). The observed lift is about 3.1 times that, so the result is not a borderline detection. The small PSA group is what limits precision.

## Segments (27 tests: 7 days of week and 20 hours of day)
- Holm correction applied across all 27 tests together.
- Significant after correction: Monday (+1.07 pp), Tuesday (+1.60 pp), Wednesday (+0.96 pp) and 14:00 (+1.25 pp).
- All 27 segments show a positive lift. The weakest is Thursday (+0.14 pp, not significant).
- Differences between segments were not formally tested (no interaction test), and the PSA group is small in each segment. Do not use this to target specific days or hours.

## Data integrity concerns
- **Group balance:** the distributions of most-ads-day and most-ads-hour differ between the groups (chi-square p about 5e-48 and 1e-28). These fields are measured after users enter the experiment, so a difference could come from the treatment or from non-random assignment, and this dataset cannot separate the two. Average ads seen is nearly identical (24.8 vs 24.8).
- **SRM:** a sample ratio mismatch test needs a documented target split. It is not documented here, so the 96/4 split could not be checked.
- **CUPED:** not applicable. Every available covariate is measured after assignment, so adjusting on it could bias the estimate.

## Exposure pattern (descriptive only)
- At 2-20 ads seen, ad and PSA conversion rates are about the same. The gap appears at 21 or more ads (21-50 ads: 2.9% vs 2.2%; 51-100: 11.6% vs 5.8%).
- This conditions on a post-assignment variable and heavy-exposure users are more engaged anyway, so it is a hypothesis to test, not a finding.

## Risks
- No cost, margin or revenue data, so profitability cannot be computed. Rule: ship only if the lower bound of the lift (0.587 pp) beats break-even, where break-even lift = cost per reached user / margin per conversion.
- Conversion is the only outcome. Long-term effects, unsubscribes and brand effects are not measured.

## Next steps
1. Run a confirmation test with a documented split, random assignment logged at user level, and a pre-experiment covariate (so SRM and CUPED apply).
2. Compute break-even from real cost and margin before scaling spend.
3. Test whether the effect depends on exposure count in that follow-up.