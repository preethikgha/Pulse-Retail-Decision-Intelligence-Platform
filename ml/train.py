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

# 1. Build features in the warehouse, then load them
con = duckdb.connect(str(ROOT / "warehouse" / "retail.duckdb"))
con.execute((ROOT / "ml" / "features.sql").read_text(encoding="utf-8"))
df = con.execute("SELECT * FROM marts.ml_features").df()
con.close()
print(f"Feature rows: {len(df):,}")

NUM = ["estimated_days", "n_items", "n_sellers", "items_value", "freight_value", "freight_ratio",
       "weight_g", "volume_cm3", "distance_km", "same_state",
       "purchase_hour", "purchase_dow", "purchase_month_num"]
CAT = ["customer_state", "seller_state", "category"]
for c in CAT:
    df[c] = df[c].fillna("unknown").astype(str)

# 2. Time-based split (no leakage from the future)
train = df[df.month <= "2018-02"]
valid = df[(df.month >= "2018-03") & (df.month <= "2018-04")]
test = df[df.month >= "2018-05"]
for name, d in [("train", train), ("valid", valid), ("test", test)]:
    print(f"{name}: {len(d):,} orders, late rate {d.is_late.mean():.3f}")

Xtr, ytr = train[NUM + CAT], train.is_late.values
Xva, yva = valid[NUM + CAT], valid.is_late.values
Xte, yte = test[NUM + CAT], test.is_late.values


def make_pre():
    return ColumnTransformer([
        ("num", Pipeline([("imp", SimpleImputer(strategy="median")), ("sc", StandardScaler())]), NUM),
        ("cat", OneHotEncoder(handle_unknown="ignore", min_frequency=30), CAT),
    ])


def metrics(y, p, prefix):
    k = int(len(y) * 0.10)
    top = np.argsort(-p)[:k]
    return {
        f"{prefix}_roc_auc": float(roc_auc_score(y, p)),
        f"{prefix}_pr_auc": float(average_precision_score(y, p)),
        f"{prefix}_recall_top10": float(y[top].sum() / y.sum()),
    }


RUNS = [
    ("logreg_C0.1", "logreg", {"C": 0.1}),
    ("logreg_C1", "logreg", {"C": 1.0}),
    ("xgb_depth4_lr0.05", "xgboost", {"max_depth": 4, "learning_rate": 0.05, "n_estimators": 300}),
    ("xgb_depth6_lr0.05", "xgboost", {"max_depth": 6, "learning_rate": 0.05, "n_estimators": 300}),
    ("xgb_depth6_lr0.02", "xgboost", {"max_depth": 6, "learning_rate": 0.02, "n_estimators": 600}),
]


def build(kind, params):
    if kind == "logreg":
        clf = LogisticRegression(max_iter=2000, **params)
    else:
        clf = XGBClassifier(subsample=0.8, colsample_bytree=0.8, eval_metric="logloss",
                            tree_method="hist", n_jobs=-1, random_state=42, **params)
    return Pipeline([("pre", make_pre()), ("clf", clf)])


# 3. Train and track every run in MLflow
mlflow.set_tracking_uri(f"sqlite:///{(ROOT / 'mlflow.db').as_posix()}")
mlflow.set_experiment("pulse-late-delivery")

results, pipes = [], {}
for name, kind, params in RUNS:
    with mlflow.start_run(run_name=name) as run:
        mlflow.log_params({"model": kind, **params, "n_features": len(NUM) + len(CAT),
                           "split": "train<=2018-02, valid 2018-03..04, test>=2018-05"})
        mlflow.log_metrics({"base_rate_val": float(yva.mean()), "base_rate_test": float(yte.mean())})
        pipe = build(kind, params)
        pipe.fit(Xtr, ytr)
        m = {}
        m.update(metrics(yva, pipe.predict_proba(Xva)[:, 1], "val"))
        m.update(metrics(yte, pipe.predict_proba(Xte)[:, 1], "test"))
        mlflow.log_metrics(m)
        mlflow.sklearn.log_model(pipe, artifact_path="model")
        results.append({"run": name, "run_id": run.info.run_id, **m})
        pipes[name] = pipe
        print(f"done: {name}  val PR-AUC {m['val_pr_auc']:.3f}  test PR-AUC {m['test_pr_auc']:.3f}")

res = pd.DataFrame(results)
cols = ["run", "val_pr_auc", "val_roc_auc", "val_recall_top10", "test_pr_auc", "test_roc_auc", "test_recall_top10"]
print("\n--- All runs (higher is better; the winner is chosen on VALIDATION PR-AUC) ---")
print(res[cols].round(3).to_string(index=False))
print(f"\nBase late rate: validation {yva.mean():.3f}, test {yte.mean():.3f} "
      f"(PR-AUC of a no-skill model equals the base rate)")

# 4. Pick the winner on validation, register it, save it for the API
best = res.sort_values("val_pr_auc", ascending=False).iloc[0]
print(f"\nBest on validation: {best['run']}  (val PR-AUC {best['val_pr_auc']:.3f}, "
      f"test PR-AUC {best['test_pr_auc']:.3f})")
try:
    mv = mlflow.register_model(f"runs:/{best['run_id']}/model", "pulse-late-delivery")
    MlflowClient().set_registered_model_alias("pulse-late-delivery", "champion", mv.version)
    print(f"Registered pulse-late-delivery v{mv.version} with alias 'champion'")
except Exception as e:
    print("Model registry step failed (the rest still worked):", e)

out = ROOT / "api" / "model"
out.mkdir(parents=True, exist_ok=True)
joblib.dump(pipes[best["run"]], out / "model.joblib")
(out / "model_info.json").write_text(json.dumps({
    "model": best["run"], "num_features": NUM, "cat_features": CAT,
    "metrics": {k: round(float(best[k]), 4) for k in best.index if k.startswith(("val_", "test_"))},
}, indent=2))
res[cols].round(4).to_csv(ROOT / "ml" / "results.csv", index=False)
print("Saved api/model/model.joblib and ml/results.csv")