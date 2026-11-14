import json
from pathlib import Path
from typing import Optional

import joblib
import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel, Field

MODEL_DIR = Path(__file__).resolve().parent / "model"
pipe = joblib.load(MODEL_DIR / "model.joblib")
info = json.loads((MODEL_DIR / "model_info.json").read_text())
NUM, CAT = info["num_features"], info["cat_features"]

app = FastAPI(
    title="Pulse late-delivery API",
    version="1.0",
    description="Predicts the probability that an order is delivered after its promised date, "
                "using only information known at purchase time. Trained on real Olist data.",
)


class Order(BaseModel):
    estimated_days: float = Field(..., ge=0, le=200, description="Promised delivery window in days")
    n_items: int = Field(1, ge=1, le=50)
    n_sellers: int = Field(1, ge=1, le=20)
    items_value: float = Field(..., ge=0, description="Total item price (BRL)")
    freight_value: float = Field(..., ge=0, description="Total freight (BRL)")
    weight_g: Optional[float] = Field(None, ge=0)
    volume_cm3: Optional[float] = Field(None, ge=0)
    distance_km: Optional[float] = Field(None, ge=0, description="Seller-to-customer distance")
    purchase_hour: int = Field(..., ge=0, le=23)
    purchase_dow: int = Field(..., ge=0, le=6, description="0 = Sunday ... 6 = Saturday")
    purchase_month_num: int = Field(..., ge=1, le=12)
    customer_state: str = Field(..., min_length=2, max_length=2, description="e.g. RJ")
    seller_state: str = Field(..., min_length=2, max_length=2, description="e.g. SP")
    category: str = Field("unknown", description="English category name, e.g. bed_bath_table")


@app.get("/health")
def health():
    return {"status": "ok", "model": info["model"]}


@app.get("/model-info")
def model_info():
    return info


@app.post("/predict")
def predict(order: Order):
    row = order.model_dump()
    row["customer_state"] = row["customer_state"].upper()
    row["seller_state"] = row["seller_state"].upper()
    row["freight_ratio"] = row["freight_value"] / row["items_value"] if row["items_value"] > 0 else None
    row["same_state"] = int(row["customer_state"] == row["seller_state"])
    x = pd.DataFrame([row])[NUM + CAT]
    x[NUM] = x[NUM].astype(float)
    p = float(pipe.predict_proba(x)[0, 1])
    return {
        "late_probability": round(p, 4),
        "reference_base_late_rate": info["test"]["base_rate"],
        "model": info["model"],
        "note": "Modest-skill model (about 2x lift over the base rate). Use for ranking orders by risk, not as a certain prediction.",
    }