import json
import joblib
import duckdb
import numpy as np
import pandas as pd
import mlflow
import mlflow.sklearn
from pathlib import Path
from mlflow.tracking import MlflowClient
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, average_precision_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier

ROOT = Path(__file__).resolve().parent.parent
pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 30)

con = duckdb.connect(str(ROOT / "warehouse" / "retail.duckdb"), read_only=True)
df = con.execute("SELECT * FROM marts.ml_features").df()
con.close()

NUM = ["estimated_days", "n_items", "n_sellers", "items_value", "freight_value", "freight_ratio",
       "weight_g", "volume_cm3", "distance_km", "same_state",
       "purchase_hour", "purchase_dow", "purchase_month_num"]
CAT = ["customer_state", "seller_state", "category"]
for c in CAT:
    df[c] = df[c].fillna("unknown").astype(str)


def make_pre():
    return ColumnTransformer([
        ("num", Pipeline([("imp", SimpleImputer(strategy="median")), ("sc", StandardScaler())]), NUM),
        ("cat", OneHotEncoder(handle_unknown="ignore", min_frequency=30), CAT),
    ])


def build(kind, params):
    if kind == "logreg":
        clf = LogisticRegression(max_iter=2000, **params)
    else:
        clf = XGBClassifier(subsample=0.8, colsample_bytree=0.8, eval_metric="logloss",
                            tree_method="hist", n_jobs=-1, random_state=42, **params)
    return Pipeline([("pre", make_pre()), ("clf", clf)])


def metrics(y, p):
    base = float(y.mean())
    k = int(len(y) * 0.10)
    top = np.argsort(-p)[:k]
    pr = float(average_precision_score(y, p))
    return {"base_rate": base, "pr_auc": pr, "lift": pr / base,
            "roc_auc": float(roc_auc_score(y, p)), "recall_top10": float(y[top].sum() / y.sum())}


RUNS = [
    ("logreg_C0.1", "logreg", {"C": 0.1}),
    ("logreg_C1", "logreg", {"C": 1.0}),
    ("xgb_depth4_lr0.05", "xgboost", {"max_depth": 4, "learning_rate": 0.05, "n_estimators": 300}),
    ("xgb_depth6_lr0.05", "xgboost", {"max_depth": 6, "learning_rate": 0.05, "n_estimators": 300}),
    ("xgb_depth6_lr0.02", "xgboost", {"max_depth": 6, "learning_rate": 0.02, "n_estimators": 600}),
]
FOLDS = ["2018-01", "2018-02", "2018-03", "2018-04"]

mlflow.set_tracking_uri(f"sqlite:///{(ROOT / 'mlflow.db').as_posix()}")
mlflow.set_experiment("pulse-late-delivery-backtest")

rows = []
for name, kind, params in RUNS:
    with mlflow.start_run(run_name=f"backtest_{name}"):
        mlflow.log_params({"model": kind, **params,
                           "folds": ",".join(FOLDS), "scheme": "expanding window, train on all months before the fold"})
        fold_lifts = []
        for m in FOLDS:
            tr, va = df[df.month < m], df[df.month == m]
            pipe = build(kind, params)
            pipe.fit(tr[NUM + CAT], tr.is_late.values)
            mm = metrics(va.is_late.values, pipe.predict_proba(va[NUM + CAT])[:, 1])
            mlflow.log_metrics({f"{m}_{k}": v for k, v in mm.items()})
            rows.append({"run": name, "fold": m, **mm})
            fold_lifts.append(mm["lift"])
        mlflow.log_metric("mean_lift", float(np.mean(fold_lifts)))
        print(f"done: {name}  mean lift {np.mean(fold_lifts):.2f}")

bt = pd.DataFrame(rows)
bt.to_csv(ROOT / "ml" / "backtest_results.csv", index=False)
lift = bt.pivot(index="run", columns="fold", values="lift")
lift["mean_lift"] = lift.mean(axis=1)
lift["worst_fold"] = lift[FOLDS].min(axis=1)
lift["mean_pr_auc"] = bt.groupby("run")["pr_auc"].mean()
print("\n--- Backtest: lift = PR-AUC / base rate in that month (1.0 = no skill) ---")
print(bt.groupby("fold")["base_rate"].first().round(3).to_frame("base_rate").T.to_string())
print(lift.sort_values("mean_lift", ascending=False).round(2).to_string())

best = lift["mean_lift"].idxmax()
kind, params = next((k, p) for n, k, p in RUNS if n == best)
print(f"\nSelected by mean backtest lift: {best}")

train = df[df.month <= "2018-04"]
test = df[df.month >= "2018-05"]
pipe = build(kind, params)
pipe.fit(train[NUM + CAT], train.is_late.values)
tm = metrics(test.is_late.values, pipe.predict_proba(test[NUM + CAT])[:, 1])
print(f"Final model trained on Jan 2017 - Apr 2018 ({len(train):,} orders), scored once on May-Aug 2018 ({len(test):,} orders):")
print(f"  test base late rate {tm['base_rate']:.3f} | PR-AUC {tm['pr_auc']:.3f} ({tm['lift']:.1f}x base) | "
      f"ROC-AUC {tm['roc_auc']:.3f} | late orders caught in top 10% of scores: {tm['recall_top10']:.1%}")
print("Note: test results from the first training run were seen before this selection method was chosen.")

with mlflow.start_run(run_name=f"final_{best}"):
    mlflow.log_params({"model": kind, **params, "trained_on": "2017-01..2018-04", "selected_by": "mean backtest lift"})
    mlflow.log_metrics({f"test_{k}": v for k, v in tm.items()})
    mlflow.log_metric("backtest_mean_lift", float(lift.loc[best, "mean_lift"]))
    info = mlflow.sklearn.log_model(pipe, artifact_path="model", serialization_format="cloudpickle")
    try:
        mv = mlflow.register_model(info.model_uri, "pulse-late-delivery")
        MlflowClient().set_registered_model_alias("pulse-late-delivery", "champion", mv.version)
        print(f"Registered pulse-late-delivery v{mv.version} with alias 'champion'")
    except Exception as e:
        print("Model registry step failed (the rest still worked):", e)

out = ROOT / "api" / "model"
out.mkdir(parents=True, exist_ok=True)
joblib.dump(pipe, out / "model.joblib")
(out / "model_info.json").write_text(json.dumps({
    "model": best, "num_features": NUM, "cat_features": CAT,
    "backtest_mean_lift": round(float(lift.loc[best, "mean_lift"]), 3),
    "test": {k: round(v, 4) for k, v in tm.items()},
}, indent=2))
print("Saved api/model/model.joblib and ml/backtest_results.csv")