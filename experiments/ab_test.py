import duckdb
import numpy as np
import pandas as pd
from pathlib import Path
from scipy import stats
from statsmodels.stats.proportion import proportions_ztest, confint_proportions_2indep
from statsmodels.stats.multitest import multipletests

ROOT = Path(__file__).resolve().parent.parent
con = duckdb.connect(str(ROOT / "warehouse" / "retail.duckdb"), read_only=True)
OUT = ROOT / "experiments" / "outputs"
OUT.mkdir(exist_ok=True)
pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 30)

df = con.execute("""
    SELECT user_id, test_group, converted::INT AS converted,
           total_ads, most_ads_day, most_ads_hour
    FROM staging.stg_marketing_ab
""").df()

ad = df[df.test_group == "ad"]
psa = df[df.test_group == "psa"]
n1, x1 = len(ad), int(ad.converted.sum())
n0, x0 = len(psa), int(psa.converted.sum())
p1, p0 = x1 / n1, x0 / n0

print("--- 1. Topline ---")
print(f"ad : n={n1:,}  converted={x1:,}  rate={p1:.4%}")
print(f"psa: n={n0:,}  converted={x0:,}  rate={p0:.4%}")
print(f"ad share of users: {n1 / (n1 + n0):.1%}")

z, p = proportions_ztest([x1, x0], [n1, n0])
d_lo, d_hi = confint_proportions_2indep(x1, n1, x0, n0, method="newcomb", compare="diff")
r_lo, r_hi = confint_proportions_2indep(x1, n1, x0, n0, method="log", compare="ratio")
print(f"\nAbsolute lift: {(p1 - p0) * 100:.3f} pp   95% CI [{d_lo * 100:.3f}, {d_hi * 100:.3f}] pp")
print(f"Relative lift: {(p1 / p0 - 1):.1%}   95% CI [{r_lo - 1:.1%}, {r_hi - 1:.1%}]")
print(f"Two-proportion z-test: z={z:.2f}, p={p:.2e}")
chi2, p_chi, _, _ = stats.chi2_contingency([[x1, n1 - x1], [x0, n0 - x0]])
print(f"Chi-square check:      chi2={chi2:.1f}, p={p_chi:.2e}")

print("\n--- 2. Power analysis (alpha=0.05 two-sided, power=0.80) ---")
se = np.sqrt(p0 * (1 - p0) * (1 / n1 + 1 / n0))
mde = (stats.norm.ppf(0.975) + stats.norm.ppf(0.80)) * se
print(f"Control rate {p0:.3%}. Minimum detectable absolute lift with this sample: {mde * 100:.3f} pp "
      f"({mde / p0:.1%} relative)")
print(f"Observed lift is {(p1 - p0) / mde:.1f}x the minimum detectable lift")
for target in [0.002, 0.004]:
    pbar = p0 + target / 2
    n_each = 2 * (stats.norm.ppf(0.975) + stats.norm.ppf(0.80)) ** 2 * pbar * (1 - pbar) / target ** 2
    print(f"To detect a {target * 100:.1f} pp lift in a 50/50 test you would need about {n_each:,.0f} users per group")

print("\n--- 3. Group balance ---")
print(f"Observed split: ad {n1 / (n1 + n0):.2%} / psa {n0 / (n1 + n0):.2%}")
print("The dataset does not document the intended allocation, so an SRM test against a stated ratio is not possible.")
print("total_ads, most_ads_day and most_ads_hour are measured after assignment, so they are not pre-experiment covariates.")
print("CUPED and covariate adjustment are not applicable.")
print("\nMean total_ads by group (post-treatment exposure, for context):")
print(df.groupby("test_group")["total_ads"].agg(["mean", "median"]).round(2))
for col in ["most_ads_day", "most_ads_hour"]:
    ct = pd.crosstab(df[col], df.test_group)
    chi, pv, _, _ = stats.chi2_contingency(ct)
    print(f"Distribution of {col} differs between groups? chi2 p = {pv:.3g}")

print("\n--- 4. Segment lifts with multiple-testing correction ---")
rows = []
for col in ["most_ads_day", "most_ads_hour"]:
    for seg, g in df.groupby(col):
        a, b = g[g.test_group == "ad"], g[g.test_group == "psa"]
        if len(b) < 100:
            continue
        xa, na, xb, nb = int(a.converted.sum()), len(a), int(b.converted.sum()), len(b)
        zz, pp = proportions_ztest([xa, xb], [na, nb])
        rows.append({"dimension": col, "segment": seg, "n_ad": na, "n_psa": nb,
                     "rate_ad": xa / na, "rate_psa": xb / nb,
                     "lift_pp": (xa / na - xb / nb) * 100, "p_value": pp})
seg = pd.DataFrame(rows)
seg["p_holm"] = multipletests(seg.p_value, method="holm")[1]
seg["p_bonferroni"] = multipletests(seg.p_value, method="bonferroni")[1]
seg["significant_after_holm"] = seg.p_holm < 0.05
seg = seg.round({"rate_ad": 4, "rate_psa": 4, "lift_pp": 3})
seg["p_value"] = seg.p_value.map("{:.2e}".format)
seg["p_holm"] = seg.p_holm.map("{:.2e}".format)
seg["p_bonferroni"] = seg.p_bonferroni.map("{:.2e}".format)
print(f"{len(seg)} segment tests run. Corrected across all of them together.")
print(seg.to_string(index=False))
seg.to_csv(OUT / "segment_lifts.csv", index=False)

print("\n--- 5. Conversion by ad exposure (descriptive, NOT causal) ---")
bins = [0, 1, 5, 20, 50, 100, 1e9]
labels = ["1", "2-5", "6-20", "21-50", "51-100", "100+"]
df["exposure"] = pd.cut(df.total_ads, bins=bins, labels=labels)
dose = df.pivot_table(index="exposure", columns="test_group", values="converted",
                      aggfunc=["count", "mean"], observed=True).round(4)
print(dose)
print("Users who see more ads are also the more engaged users, so this gradient can reflect engagement, not ad effect.")
dose.to_csv(OUT / "exposure_conversion.csv")