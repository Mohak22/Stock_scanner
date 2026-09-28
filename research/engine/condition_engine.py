
from __future__ import annotations
from typing import Any
import pandas as pd
from api.research.features import get_feature_column_candidates, normalize_feature_parameters

def _normalize_expression(expression: Any) -> dict:
    if isinstance(expression,dict):
        p=dict(expression); params=dict(p.get("parameters") or {})
        if "period" in p and "period" not in params: params["period"]=p["period"]
        p["parameters"]=params; p.pop("period",None); return p
    if isinstance(expression,str): return {"feature":expression,"parameters":{},"multiplier":1}
    return {"value":expression,"multiplier":1}

def _resolve_feature_column(dataframe,feature,parameters=None):
    candidates=get_feature_column_candidates(feature,parameters)
    lookup={str(c).upper():c for c in dataframe.columns}
    for c in candidates:
        if c in dataframe.columns: return c
        if str(c).upper() in lookup: return lookup[str(c).upper()]
    raise ValueError(f"Feature '{feature}' with parameters {parameters or {}} not found in dataframe.")

def _resolve_expression(dataframe,expression):
    p=_normalize_expression(expression)
    has_feature=bool(p.get("feature")); has_value=p.get("value") is not None
    if has_feature == has_value: raise ValueError("An expression must contain exactly one of 'feature' or 'value'.")
    multiplier=float(p.get("multiplier",1))
    if multiplier<0: raise ValueError("Arithmetic multiplier must be non-negative.")
    if has_feature:
        col=_resolve_feature_column(dataframe,str(p["feature"]).strip(),p.get("parameters"))
        base=dataframe[col]
    else: base=p["value"]
    return base*multiplier

def _legacy_condition_to_canonical(condition):
    if "left" in condition and "right" in condition: return condition
    lp={}
    if condition.get("period") not in (None,""): lp["period"]=condition["period"]
    rv=condition.get("value")
    right=dict(rv) if isinstance(rv,dict) else ({"feature":rv} if isinstance(rv,str) else {"value":rv})
    if "period" in right and "parameters" not in right: right["parameters"]={"period":right.pop("period")}
    return {"left":{"feature":condition.get("feature"),"parameters":lp,"multiplier":1},"operator":condition.get("operator"),"right":right}

def apply_conditions(dataframe,conditions):
    signal=pd.Series(True,index=dataframe.index)
    for raw in conditions:
        c=_legacy_condition_to_canonical(raw)
        left=_resolve_expression(dataframe,c["left"]); right=_resolve_expression(dataframe,c["right"])
        op=c["operator"]
        if op=="<": current=left<right
        elif op=="<=": current=left<=right
        elif op==">": current=left>right
        elif op==">=": current=left>=right
        elif op=="==": current=left==right
        elif op=="!=": current=left!=right
        else: raise ValueError(f"Unsupported operator: {op}")
        signal &= current.fillna(False)
    return signal
