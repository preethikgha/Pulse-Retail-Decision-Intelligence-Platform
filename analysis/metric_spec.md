# Metric Spec

Source tables: `marts.fct_orders`, `marts.fct_order_items`. Monthly values: `analysis/monthly_metrics.sql`.

| Type | Metric | Definition |
|---|---|---|
| North-star | Good-delivery orders (monthly) | Delivered orders that arrived on time AND have review score >= 4 |
| North-star rate | Good-delivery rate | Good-delivery orders / delivered orders |
| Guardrail | Late-delivery rate | Late delivered orders / delivered orders |
| Guardrail | Cancellation rate | Canceled orders / all orders |
| Guardrail | Avg delivery days | Mean days from purchase to delivery (delivered orders) |
| Supporting | Avg review score | Mean review score |

## Definitions and exclusions
- **Late:** `delivered_at > estimated_delivery_at` (timestamp comparison).
- **Undelivered orders** (about 2,965) are excluded from late rate and delivery days.
- **Orders with no review** (768) count as NOT good-delivery in the north-star.
- **Months with fewer than 100 orders** (Sep 2016, Dec 2016, Sep-Oct 2018) are excluded from reporting.
- **One review per order:** if an order has several reviews, the latest one is used.

## Known limits
- Late is measured against the promised date, so tighter promises raise the late rate even when delivery speeds up (seen in Aug 2018). Always read it with avg delivery days.
- Orders from the final months that are not yet delivered are missing from late-rate calculations.

## Alert thresholds (used in the dashboard)
- Late rate above 10% for a month
- Avg delivery days more than 2 days above the trailing 6-month average
- Cancellation rate above 2%