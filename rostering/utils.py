"""
Utility functions for roster scheduling.
"""
import pandas as pd
from datetime import datetime, time


def to_hour(v):
    """Convert various time formats to decimal hours."""
    if pd.isna(v):
        return None
    if isinstance(v, time):
        return v.hour + v.minute/60 + v.second/3600
    if isinstance(v, datetime):
        return v.hour + v.minute/60 + v.second/3600
    if isinstance(v, (int, float)):
        return v * 24 if 0 <= v <= 1 else float(v)
    if isinstance(v, str):
        try:
            parts = [float(p) for p in v.split(":")]
            if len(parts) >= 2:
                return parts[0] + parts[1]/60 + (parts[2]/3600 if len(parts) > 2 else 0)
            return float(v)
        except:
            return None
    return None


def hour_to_time(h):
    """Convert decimal hours to HH:MM format."""
    if h is None:
        return "N/A"
    hours = int(h)
    mins = int((h - hours) * 60)
    return f"{hours:02d}:{mins:02d}"
