"""Agent for analyzing calendar availability patterns."""

import numpy as np
import joblib
from app.config import settings
from app.services.availability_service import get_calendar_data

def extract_pattern_availability(listing_id: int) -> dict:
    rows = get_calendar_data(listing_id)
    if not rows:
        return {"error": f"No calendar data for listing {listing_id}"}

    total_days = len(rows)
    available_days = sum(1 for r in rows if r[1] == "t")
    blocked_days = total_days - available_days

    prices = []
    for r in rows:
        if r[2]:
            try:
                p = float(str(r[2]).replace("$", "").replace(",", ""))
                prices.append(p)
            except (ValueError, TypeError):
                pass

    avg_price = round(np.mean(prices), 2) if prices else 0
    min_price = round(min(prices), 2) if prices else 0
    max_price = round(max(prices), 2) if prices else 0

    streaks = []
    current_status = None
    streak_len = 0
    for r in rows:
        status = "available" if r[1] == "t" else "blocked"
        if status == current_status:
            streak_len += 1
        else:
            if current_status is not None:
                streaks.append({"type": current_status, "length": streak_len})
            current_status = status
            streak_len = 1
    if current_status:
        streaks.append({"type": current_status, "length": streak_len})

    cluster_label = None
    try:
        kmeans = joblib.load(settings.KMEANS_MODEL_PATH)
        scaler = joblib.load(settings.SCALER_PATH)
        avail_rate = available_days / max(total_days, 1)
        avg_streak = np.mean([s["length"] for s in streaks]) if streaks else 0
        features = np.array([[avail_rate, avg_price, avg_streak]])
        scaled = scaler.transform(features)
        cluster_label = int(kmeans.predict(scaled)[0])
    except Exception as e:
        print(f"KMeans prediction failed: {e}")

    return {
        "listing_id": listing_id,
        "total_days": total_days,
        "available_days": available_days,
        "blocked_days": blocked_days,
        "availability_rate": round(available_days / max(total_days, 1), 3),
        "avg_price": avg_price,
        "min_price": min_price,
        "max_price": max_price,
        "streaks_summary": {
            "total_streaks": len(streaks),
            "avg_streak_length": round(np.mean([s["length"] for s in streaks]), 1) if streaks else 0,
        },
        "cluster": cluster_label,
    }
