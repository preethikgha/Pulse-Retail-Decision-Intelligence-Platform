# Root-Cause Analysis: Late-Delivery Spikes

**Data:** real Olist orders (Kaggle), Sep 2016 to Aug 2018. Months with fewer than 100 orders are excluded.
**Late** = delivered after the estimated delivery date. **Baseline** = May-Oct 2017 and Apr-Jul 2018 (late rate 4.6%).

## Question
Why did the late-delivery rate jump in Nov 2017 (14.3%) and Feb-Mar 2018 (16.0%, 21.4%)?

## Method
- For each segment: excess late orders = actual late - (rows x that segment's baseline late rate). The share of total excess shows how much of the spike a segment explains.
- Cuts: customer state, product category, seller state, seller, same-state vs cross-state shipping.
- Split delivery time into approval, seller handling and carrier legs, and checked the promised delivery window.
- Code: `analysis/rca.py`. Raw outputs: `analysis/rca_outputs/`.
- Seller and category cuts are item-level (an order with 2 items counts twice). Segments with fewer than 30 baseline rows are excluded, so shares are among segments with enough history.

## Finding 1: Nov 2017, demand surge plus stretched logistics
- Orders rose 63% vs Oct 2017 (4,631 to 7,544). Late rate went from 5.3% to 14.3%.
- Carrier leg rose from 8.4 to 11.1 days and seller handling from 3.1 to 3.6 days. The promised window did not change (about 23 days), so deliveries really slowed.
- Customers in RJ: 28.1% late (baseline 4.9%), about 33% of the excess from about 14% of orders.
- Cross-state shipments: 66% of items but 83% of the excess (16.5% late vs 8.6% same-state).
- bed_bath_table: 21.0% late, about 21% of the excess from about 11% of items.
- Six of the eight largest seller contributors ran 27-53% late, against seller baselines under 5%. The top 8 sellers explain about 40% of the excess among sellers with enough history, so part of the spike is seller-specific.

## Finding 2: Feb-Mar 2018, a broad transit-leg slowdown
- Late rate 16.0% (Feb) and 21.4% (Mar). Carrier leg 13.4 and 13.0 days vs about 8.5 in normal months.
- Seller handling stayed flat (about 3 days) and the promised window was normal.
- Volume was not unusual (6.7k-7.2k orders per month). April had similar volume and a late rate of 5.3%, so this is not a volume story.
- Broad-based: RJ 36.4% late, MG 17.2%, CE 48.6%, BA 28.9%. Many categories rose to 17-24%. No single seller explains more than about 4% of the excess.
- Cross-state shipments: 87% of the excess (23.1% late vs 9.1% same-state).
- Conclusion: a systemic slowdown in the carrier/transit leg of about 4-5 days that ended in April.

## Finding 3 (side note): Jun-Aug 2018, late rate rose while delivery got faster
- Aug 2018: 10.4% late, but average delivery was 7.7 days and the carrier leg only 5.2 days.
- The promised window shrank from about 24 days to 15.8 days, so more orders were flagged late against a tighter promise.
- Takeaway: late rate alone can mislead. Track it next to delivery days.

## What this analysis cannot claim
- This is segmentation, so it shows where the lateness was, not why. The dataset has no carrier, weather, warehouse capacity or holiday fields.
- Candidate causes (peak-season demand, carrier capacity) need outside evidence.
- The excess method assumes baseline rates are stable, and the baseline months have their own noise.

## Recommended actions
1. Monitor the carrier-leg days by customer state weekly, and alert when it is more than 2 days above baseline.
2. In peak season, add a buffer to promised dates for cross-state orders to RJ.
3. Add a seller scorecard that flags any seller above 25% late in a month.
4. Report delivery days next to late rate so tighter promises are not mistaken for slower delivery.