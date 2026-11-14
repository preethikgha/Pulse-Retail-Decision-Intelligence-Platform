import json
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

DATA = Path(__file__).resolve().parent / "data"
st.set_page_config(page_title="Pulse | Retail Decision Dashboard", layout="wide")

NAVY, AMBER, TEAL, RED, GREEN, GREY = "#16202D", "#E8820C", "#0F8B8D", "#C8372D", "#1E8E5A", "#6B7686"
LATE_MAX, CANCEL_MAX, DAYS_MAX = 0.10, 0.02, 2.0

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, .stApp, [class*="css"] { font-family: 'Inter', sans-serif; }
#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; height: 0; }
.block-container { padding-top: 1.4rem; padding-bottom: 3rem; max-width: 1280px; }
.hero { background: linear-gradient(135deg, #16202D 0%, #26384F 100%); border-radius: 16px;
        padding: 30px 36px; margin-bottom: 22px; color: #FFFFFF; }
.hero .eyebrow { color: #E8820C; font-weight: 700; letter-spacing: .16em; font-size: .78rem; }
.hero h1 { color: #FFFFFF; font-size: 2.1rem; font-weight: 800; margin: 6px 0 6px 0; padding: 0; }
.hero p { color: #B9C4D2; font-size: .95rem; margin: 0 0 14px 0; }
.chip { display: inline-block; background: rgba(255,255,255,.10); color: #E6ECF3; border-radius: 999px;
        padding: 4px 12px; margin-right: 8px; font-size: .78rem; font-weight: 500; }
div[data-testid="stMetric"] { background: #FFFFFF; border: 1px solid #E3E7ED; border-radius: 14px;
        padding: 16px 18px; box-shadow: 0 1px 3px rgba(22,32,45,.06); }
div[data-testid="stMetricLabel"] p { font-size: .72rem; text-transform: uppercase; letter-spacing: .06em;
        color: #6B7686; font-weight: 600; white-space: normal !important; line-height: 1.25; }
div[data-testid="stMetricValue"] { font-weight: 700; color: #16202D; font-size: clamp(1.25rem, 2vw, 2rem); }
div[data-testid="stMetricValue"] > div { overflow: visible !important; text-overflow: clip !important; white-space: nowrap !important; }
div[data-testid="stMetricLabel"], div[data-testid="stMetricLabel"] * { white-space: normal !important; overflow: visible !important; text-overflow: clip !important; }
.stTabs [data-baseweb="tab-list"] { gap: 4px; border-bottom: 1px solid #DDE2E9; }
.stTabs [data-baseweb="tab"] { padding: 10px 18px; font-weight: 600; color: #6B7686; }
.stTabs [aria-selected="true"] { color: #16202D; }
.alert { border-left: 5px solid; border-radius: 10px; padding: 12px 18px; margin: 8px 0;
         font-size: .92rem; font-weight: 500; background: #FFFFFF; }
.alert.red { border-color: #C8372D; background: #FDF1F0; color: #7A1F18; }
.alert.green { border-color: #1E8E5A; background: #EDF8F2; color: #14583A; }
.section { font-size: 1.05rem; font-weight: 700; color: #16202D; margin: 22px 0 2px 0; }
.note { color: #6B7686; font-size: .82rem; margin-bottom: 8px; }
</style>
""", unsafe_allow_html=True)


def style(c):
    return (c.configure_view(strokeWidth=0)
            .configure_axis(labelFont="Inter", titleFont="Inter", labelColor=GREY, titleColor=GREY,
                            gridColor="#EDF0F4", domainColor="#D5DBE3", tickColor="#D5DBE3",
                            titleFontWeight=600, labelFontSize=11, titleFontSize=11)
            .configure_legend(labelFont="Inter", titleFont="Inter", orient="top", labelColor=GREY)
            .configure(background="transparent"))


def show(chart):
    chart = style(chart)
    with st.container(border=True):
        try:
            st.altair_chart(chart, width="stretch")
        except Exception:
            st.altair_chart(chart, use_container_width=True)


def section(title, sub=""):
    html = f'<div class="section">{title}</div>'
    if sub:
        html += f'<div class="note">{sub}</div>'
    st.markdown(html, unsafe_allow_html=True)


def alert(kind, text):
    st.markdown(f'<div class="alert {kind}">{text}</div>', unsafe_allow_html=True)


@st.cache_data
def load():
    m = pd.read_csv(DATA / "monthly_metrics.csv")
    m["month_dt"] = pd.to_datetime(m["purchase_month"])
    m["month"] = m["month_dt"].dt.strftime("%Y-%m")
    m = m[m.orders >= 100].reset_index(drop=True)
    m["trailing6_days"] = m["avg_delivery_days"].shift(1).rolling(6, min_periods=3).mean()
    m["days_vs_trailing"] = m["avg_delivery_days"] - m["trailing6_days"]
    stages = pd.read_csv(DATA / "stages_by_month.csv")
    stages["month_dt"] = pd.to_datetime(stages["month"] + "-01")
    return (m, stages,
            pd.read_csv(DATA / "dose_response.csv"),
            pd.read_csv(DATA / "regression_results.csv"),
            pd.read_csv(DATA / "segment_lifts.csv"),
            pd.read_csv(DATA / "ab_topline.csv").iloc[0],
            pd.read_csv(DATA / "backtest_results.csv"),
            json.loads((DATA / "model_info.json").read_text()))


m, stages, dose, reg, seg, ab, bt, info = load()
m["alert_late"] = m.late_rate > LATE_MAX
m["alert_cancel"] = m.cancel_rate > CANCEL_MAX
m["alert_days"] = m.days_vs_trailing > DAYS_MAX
m["alerts"] = m[["alert_late", "alert_cancel", "alert_days"]].sum(axis=1)

st.markdown(f"""
<div class="hero">
  <div class="eyebrow">PULSE</div>
  <h1>Retail Decision Dashboard</h1>
  <p>Delivery performance, root causes, customer impact, experiment results and a late-order model on real marketplace data.</p>
  <span class="chip">Real data, not simulated</span>
  <span class="chip">{int(m.orders.sum()):,} orders (months with 100+)</span>
  <span class="chip">{m.month.min()} to {m.month.max()}</span>
  <span class="chip">Source: Olist and Marketing A/B (Kaggle)</span>
</div>
""", unsafe_allow_html=True)

t1, t2, t3, t4, t5 = st.tabs(["Overview", "Delivery stages", "Late vs reviews", "A/B test", "Model"])

# ---------------- Overview ----------------
with t1:
    months = m.month.tolist()
    sel = st.selectbox("Month", months, index=len(months) - 1)
    i = months.index(sel)
    cur = m.iloc[i]
    prev = m.iloc[i - 1] if i > 0 else None

    def delta(col, fmt):
        return None if prev is None else fmt.format(cur[col] - prev[col])

    c = st.columns(5)
    c[0].metric("Orders", f"{int(cur.orders):,}", None if prev is None else f"{int(cur.orders - prev.orders):+,}")
    c[1].metric("Good delivery", f"{cur.good_delivery_rate:.1%}", delta("good_delivery_rate", "{:+.1%}"))
    c[2].metric("Late rate", f"{cur.late_rate:.1%}", delta("late_rate", "{:+.1%}"), delta_color="inverse")
    c[3].metric("Avg days", f"{cur.avg_delivery_days:.1f}", delta("avg_delivery_days", "{:+.1f}"),
                delta_color="inverse")
    c[4].metric("Cancel rate", f"{cur.cancel_rate:.2%}", delta("cancel_rate", "{:+.2%}"), delta_color="inverse")

    section("Guardrail status")
    flags = []
    if cur.alert_late:
        flags.append(f"Late rate {cur.late_rate:.1%} is above the {LATE_MAX:.0%} threshold")
    if cur.alert_cancel:
        flags.append(f"Cancellation rate {cur.cancel_rate:.2%} is above the {CANCEL_MAX:.0%} threshold")
    if cur.alert_days:
        flags.append(f"Average delivery days are {cur.days_vs_trailing:.1f} above the trailing 6-month average")
    if flags:
        for f in flags:
            alert("red", f)
    else:
        alert("green", "No guardrail alerts this month.")

    section("Late-delivery rate by month",
            "Red dots breach the 10% guardrail (dashed line). The amber band marks the selected month.")
    x = alt.X("month_dt:T", title=None, axis=alt.Axis(format="%b %y", labelAngle=0, tickCount=8))
    tip = [alt.Tooltip("month:N", title="Month"), alt.Tooltip("orders:Q", format=","),
           alt.Tooltip("late_rate:Q", format=".1%", title="Late rate"),
           alt.Tooltip("avg_delivery_days:Q", format=".1f", title="Avg days")]
    line = alt.Chart(m).mark_line(color=NAVY, strokeWidth=2.5).encode(
        x=x, y=alt.Y("late_rate:Q", axis=alt.Axis(format="%"), title="Late-delivery rate"))
    pts = alt.Chart(m).mark_circle(size=90).encode(
        x=x, y=alt.Y("late_rate:Q", title="Late-delivery rate"),
        color=alt.condition("datum.alert_late", alt.value(RED), alt.value(NAVY)), tooltip=tip)
    thr = alt.Chart(pd.DataFrame({"y": [LATE_MAX]})).mark_rule(
        color=AMBER, strokeDash=[6, 4], strokeWidth=2).encode(y=alt.Y("y:Q", title="Late-delivery rate"))
    band = alt.Chart(m[m.month == sel]).mark_rule(color=AMBER, opacity=0.30, strokeWidth=14).encode(
        x=alt.X("month_dt:T", title=None))
    show((band + line + thr + pts).properties(height=300))

    left, right = st.columns(2)
    with left:
        section("Order volume")
        bars = alt.Chart(m).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
            x=alt.X("month_dt:T", title=None, axis=alt.Axis(format="%b %y", labelAngle=0, tickCount=6)),
            y=alt.Y("orders:Q", title="Orders"),
            color=alt.condition(f"datum.month == '{sel}'", alt.value(AMBER), alt.value("#A9B8C9")),
            tooltip=tip)
        show(bars.properties(height=240))
    with right:
        section("Good-delivery rate", "On time AND review of 4 or 5 stars (north-star metric)")
        area = alt.Chart(m).mark_area(color=TEAL, opacity=0.18, line={"color": TEAL, "strokeWidth": 2.5}).encode(
            x=alt.X("month_dt:T", title=None, axis=alt.Axis(format="%b %y", labelAngle=0, tickCount=6)),
            y=alt.Y("good_delivery_rate:Q", axis=alt.Axis(format="%"), scale=alt.Scale(domain=[0.5, 0.9]),
                    title="Good-delivery rate"),
            tooltip=[alt.Tooltip("month:N"), alt.Tooltip("good_delivery_rate:Q", format=".1%")])
        show(area.properties(height=240))

    section("Months with guardrail alerts")
    bad = m[m.alerts > 0][["month", "orders", "late_rate", "cancel_rate", "avg_delivery_days", "days_vs_trailing"]]
    bad = bad.rename(columns={"month": "Month", "orders": "Orders", "late_rate": "Late rate",
                              "cancel_rate": "Cancel rate", "avg_delivery_days": "Avg days",
                              "days_vs_trailing": "Days vs trailing 6-mo"}).round(3)
    st.dataframe(bad, hide_index=True)
    st.caption("Thresholds from analysis/metric_spec.md. Months with fewer than 100 orders are excluded. "
               "Read late rate together with delivery days: a tighter promised window raises late rate "
               "even when delivery gets faster.")

# ---------------- Delivery stages ----------------
with t2:
    section("Where the delivery time goes", "Average days per stage, delivered orders only")
    long = stages.melt(id_vars=["month_dt"],
                       value_vars=["approval_days", "seller_handling_days", "carrier_days"],
                       var_name="stage", value_name="days")
    names = {"approval_days": "Payment approval", "seller_handling_days": "Seller handling",
             "carrier_days": "Carrier transit"}
    long["stage"] = long.stage.map(names)
    area = alt.Chart(long).mark_area(opacity=0.92).encode(
        x=alt.X("month_dt:T", title=None, axis=alt.Axis(format="%b %y", labelAngle=0, tickCount=8)),
        y=alt.Y("days:Q", stack="zero", title="Average days"),
        color=alt.Color("stage:N", legend=alt.Legend(title=None),
                        scale=alt.Scale(domain=list(names.values()), range=["#9AA7B8", TEAL, AMBER])),
        tooltip=[alt.Tooltip("month_dt:T", format="%b %Y"), alt.Tooltip("stage:N"),
                 alt.Tooltip("days:Q", format=".1f")])
    show(area.properties(height=320))

    section("Promised window vs actual delivery time",
            "When the promise shrinks faster than delivery improves, late rate rises even though service got faster.")
    stages["actual_days"] = stages.approval_days + stages.seller_handling_days + stages.carrier_days
    pv = stages.melt(id_vars=["month_dt"], value_vars=["promised_days", "actual_days"],
                     var_name="series", value_name="days")
    pv["series"] = pv.series.map({"promised_days": "Promised (estimated) days", "actual_days": "Actual days"})
    lines = alt.Chart(pv).mark_line(strokeWidth=2.8, point=True).encode(
        x=alt.X("month_dt:T", title=None, axis=alt.Axis(format="%b %y", labelAngle=0, tickCount=8)),
        y=alt.Y("days:Q", title="Days"),
        color=alt.Color("series:N", legend=alt.Legend(title=None),
                        scale=alt.Scale(domain=["Promised (estimated) days", "Actual days"], range=[AMBER, NAVY])),
        tooltip=[alt.Tooltip("month_dt:T", format="%b %Y"), alt.Tooltip("series:N"),
                 alt.Tooltip("days:Q", format=".1f")])
    show(lines.properties(height=300))
    st.caption("From analysis/rca.md. The carrier leg is about 8-9 days in normal months and about 13 days in "
               "Feb-Mar 2018. The dataset has no carrier field, so this shows where time was lost, not why. "
               "Actual days is the sum of the three stages.")

# ---------------- Late vs reviews ----------------
with t3:
    naive = reg[reg.model.str.startswith("M1")].late_effect.iloc[0]
    prob = reg[reg.model.str.startswith("M5")].late_effect.iloc[0]
    k = st.columns(3)
    k[0].metric("Naive review gap (late vs on time)", f"{naive:.2f} stars")
    k[1].metric("More likely to get 1-2 stars", f"+{prob * 100:.0f} pp")
    k[2].metric("Models tested", f"{(~reg.model.str.startswith('M5')).sum()} specifications")

    section("Average review score by delivery timing")
    order = dose["lateness_bucket"].tolist()
    xenc = alt.X("lateness_bucket:N", sort=order, title="Delivered vs promised date", axis=alt.Axis(labelAngle=0))
    bars = alt.Chart(dose).mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5).encode(
        x=xenc, y=alt.Y("avg_review:Q", scale=alt.Scale(domain=[0, 5]), title="Average review score"),
        color=alt.Color("avg_review:Q", legend=None, scale=alt.Scale(domain=[1.7, 4.3], range=[RED, GREEN])),
        tooltip=[alt.Tooltip("lateness_bucket:N", title="Timing"), alt.Tooltip("orders:Q", format=","),
                 alt.Tooltip("avg_review:Q", format=".2f"), alt.Tooltip("low_review_share:Q", format=".0%")])
    txt = alt.Chart(dose).mark_text(dy=-9, fontWeight=700, color=NAVY).encode(
        x=xenc, y=alt.Y("avg_review:Q"), text=alt.Text("avg_review:Q", format=".2f"))
    show((bars + txt).properties(height=300))

    section("Effect of late delivery on review score, by model",
            "Point = estimate, line = 95% confidence interval. Stable across controls.")
    f = reg[~reg.model.str.startswith("M5")].copy()
    yenc = alt.Y("model:N", sort=None, title=None, axis=alt.Axis(labelLimit=420))
    xaxis = alt.X("late_effect:Q", title="Effect of late delivery on review score (stars)",
                  scale=alt.Scale(domain=[-2.0, -1.4]))
    rules = alt.Chart(f).mark_rule(color=NAVY, strokeWidth=2.5).encode(
        y=yenc, x=alt.X("ci_low:Q", scale=alt.Scale(domain=[-2.0, -1.4]), title="Effect of late delivery on review score (stars)"),
        x2="ci_high:Q")
    dots = alt.Chart(f).mark_point(filled=True, size=120, color=AMBER, opacity=1).encode(
        y=yenc, x=xaxis, tooltip=[alt.Tooltip("model:N"), alt.Tooltip("late_effect:Q", format=".3f"),
                                  alt.Tooltip("ci_low:Q", format=".3f"), alt.Tooltip("ci_high:Q", format=".3f")])
    show((rules + dots).properties(height=240))
    st.caption("From analysis/causal.md. This is an adjusted association from observational data, not proven causation. "
               "Seller quality, damaged items and wrong items are not observed.")

# ---------------- A/B test ----------------
with t4:
    a = st.columns(4)
    a[0].metric("Ad conversion", f"{ab.rate_ad:.2%}", f"{int(ab.n_ad):,} users")
    a[1].metric("PSA (control) conversion", f"{ab.rate_psa:.2%}", f"{int(ab.n_psa):,} users")
    a[2].metric("Absolute lift", f"+{ab.lift_pp:.2f} pp")
    a[3].metric("95% CI", f"{ab.ci_low_pp:.2f} to {ab.ci_high_pp:.2f} pp")

    section("Conversion rate by group")
    g = pd.DataFrame({"group": ["Ad", "PSA (control)"], "rate": [ab.rate_ad, ab.rate_psa]})
    gx = alt.X("group:N", title=None, axis=alt.Axis(labelAngle=0))
    gb = alt.Chart(g).mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5, size=90).encode(
        x=gx, y=alt.Y("rate:Q", axis=alt.Axis(format=".1%"), title="Conversion rate"),
        color=alt.Color("group:N", legend=None, scale=alt.Scale(domain=["Ad", "PSA (control)"], range=[AMBER, "#9AA7B8"])))
    gt = alt.Chart(g).mark_text(dy=-9, fontWeight=700, color=NAVY).encode(
        x=gx, y="rate:Q", text=alt.Text("rate:Q", format=".2%"))
    show((gb + gt).properties(height=260))

    section("Lift by day of week", "Green = significant after Holm correction across all 27 segment tests")
    days = seg[seg.dimension == "most_ads_day"].copy()
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    db = alt.Chart(days).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
        x=alt.X("segment:N", sort=day_order, title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("lift_pp:Q", title="Lift (percentage points)"),
        color=alt.condition("datum.significant_after_holm", alt.value(GREEN), alt.value("#B8C2CF")),
        tooltip=[alt.Tooltip("segment:N"), alt.Tooltip("lift_pp:Q", format=".2f"),
                 alt.Tooltip("rate_ad:Q", format=".2%"), alt.Tooltip("rate_psa:Q", format=".2%"),
                 alt.Tooltip("n_psa:Q", format=",")])
    show(db.properties(height=260))

    section("Lift by hour of day")
    hrs = seg[seg.dimension == "most_ads_hour"].copy()
    hrs["hour"] = hrs.segment.astype(int)
    hb = alt.Chart(hrs).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
        x=alt.X("hour:O", title="Hour of day", axis=alt.Axis(labelAngle=0)),
        y=alt.Y("lift_pp:Q", title="Lift (percentage points)"),
        color=alt.condition("datum.significant_after_holm", alt.value(GREEN), alt.value("#B8C2CF")),
        tooltip=[alt.Tooltip("hour:O"), alt.Tooltip("lift_pp:Q", format=".2f"), alt.Tooltip("n_psa:Q", format=",")])
    show(hb.properties(height=260))
    st.caption("From experiments/memo.md. The assignment method and intended split are not documented, and the day and "
               "hour mix differs between groups, so this is strong but unconfirmed evidence. Do not use these "
               "segment results to target days or hours.")

# ---------------- Model ----------------
with t5:
    t = info["test"]
    s = st.columns(4)
    s[0].metric("Selected model", info["model"])
    s[1].metric("Held-out PR-AUC (May-Aug 2018)", f"{t['pr_auc']:.3f}", f"{t['lift']:.1f}x base rate")
    s[2].metric("ROC-AUC", f"{t['roc_auc']:.3f}")
    s[3].metric("Late orders caught in top 10%", f"{t['recall_top10']:.1%}")

    section("Mean backtest lift by model", "Lift = PR-AUC divided by that month's late rate. 1.0 means no skill.")
    mean = bt.groupby("run")["lift"].mean().reset_index().rename(columns={"lift": "mean_lift"})
    mb = alt.Chart(mean).mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4).encode(
        y=alt.Y("run:N", sort="-x", title=None, axis=alt.Axis(labelLimit=260)),
        x=alt.X("mean_lift:Q", title="Mean lift over base rate", scale=alt.Scale(domain=[0, 3])),
        color=alt.condition(f"datum.run == '{info['model']}'", alt.value(AMBER), alt.value("#A9B8C9")),
        tooltip=[alt.Tooltip("run:N"), alt.Tooltip("mean_lift:Q", format=".2f")])
    base = alt.Chart(pd.DataFrame({"x": [1.0]})).mark_rule(color=NAVY, strokeDash=[5, 4], strokeWidth=2).encode(x="x:Q")
    show((mb + base).properties(height=240))

    section("Lift by validation month")
    hm = bt[["run", "fold", "lift"]].copy()
    rect = alt.Chart(hm).mark_rect(cornerRadius=4).encode(
        x=alt.X("fold:O", title="Month scored", axis=alt.Axis(labelAngle=0)),
        y=alt.Y("run:N", title=None, axis=alt.Axis(labelLimit=260)),
        color=alt.Color("lift:Q", legend=None, scale=alt.Scale(range=["#F4F6F9", AMBER])))
    lab = alt.Chart(hm).mark_text(fontWeight=600, color=NAVY).encode(
        x="fold:O", y="run:N", text=alt.Text("lift:Q", format=".2f"))
    show((rect + lab).properties(height=240))
    st.caption("Modest model using only purchase-time features, so use it to rank orders by risk and not as a certain "
               "prediction. Models were selected by rolling-origin backtest and scored once on the held-out window.")