# -*- coding: utf-8 -*-
"""
Created on Sun Aug 30 13:17:33 2026

@author: mohak
"""

# -*- coding: utf-8 -*-

"""
Research Feature Registry

The registry must contain only features supported by
research.engine.feature_engine.calculate_features().
"""

FEATURE_REGISTRY = [
    {"id":"open","name":"Open","category":"price","type":"numeric","parameters":[]},
    {"id":"high","name":"High","category":"price","type":"numeric","parameters":[]},
    {"id":"low","name":"Low","category":"price","type":"numeric","parameters":[]},
    {"id":"close","name":"Close","category":"price","type":"numeric","parameters":[]},

    {
        "id": "volume",
        "name": "Volume",
        "category": "volume",
        "type": "numeric",
        "parameters": []
    },

    {
        "id": "delivery_percentage",
        "name": "Delivery %",
        "category": "delivery",
        "type": "numeric",
        "parameters": []
    },

    {
        "id": "rsi",
        "name": "RSI",
        "category": "technical",
        "type": "numeric",
        "parameters": [
            {
                "id": "period",
                "name": "Period",
                "type": "integer",
                "default": 14,
                "minimum": 1,
                "maximum": 200
            }
        ]
    },

    {
        "id": "ema",
        "name": "EMA",
        "category": "technical",
        "type": "numeric",
        "parameters": [
            {
                "id": "period",
                "name": "Period",
                "type": "integer",
                "default": 20,
                "minimum": 1,
                "maximum": 500
            }
        ]
    },

    {
        "id": "sma",
        "name": "SMA",
        "category": "technical",
        "type": "numeric",
        "parameters": [
            {
                "id": "period",
                "name": "Period",
                "type": "integer",
                "default": 20,
                "minimum": 1,
                "maximum": 500
            }
        ]
    },

    {
        "id": "return",
        "name": "Return",
        "category": "returns",
        "type": "numeric",
        "parameters": [
            {
                "id": "period",
                "name": "Period",
                "type": "integer",
                "default": 1,
                "minimum": 1,
                "maximum": 500
            }
        ]
    },

    {
        "id": "average_volume",
        "name": "Average Volume",
        "category": "volume",
        "type": "numeric",
        "parameters": [
            {
                "id": "period",
                "name": "Period",
                "type": "integer",
                "default": 20,
                "minimum": 1,
                "maximum": 500
            }
        ]
    },

    {
        "id": "average_delivery_percentage",
        "name": "Average Delivery %",
        "category": "delivery",
        "type": "numeric",
        "parameters": [
            {
                "id": "period",
                "name": "Period",
                "type": "integer",
                "default": 20,
                "minimum": 1,
                "maximum": 500
            }
        ]
    },
    
    {
    "id": "upper_wick",
    "name": "Upper Wick",
    "category": "price_action",
    "type": "numeric",
    "parameters": []
},

{
    "id": "lower_wick",
    "name": "Lower Wick",
    "category": "price_action",
    "type": "numeric",
    "parameters": []
},

{
    "id": "candle_range",
    "name": "Candle Range",
    "category": "price_action",
    "type": "numeric",
    "parameters": []
},

{
    "id": "body",
    "name": "Candle Body",
    "category": "price_action",
    "type": "numeric",
    "parameters": []
},

{
    "id": "upper_wick_pct",
    "name": "Upper Wick %",
    "category": "price_action",
    "type": "numeric",
    "parameters": []
},

{
    "id": "lower_wick_pct",
    "name": "Lower Wick %",
    "category": "price_action",
    "type": "numeric",
    "parameters": []
},

{
    "id": "body_pct",
    "name": "Body %",
    "category": "price_action",
    "type": "numeric",
    "parameters": []
},

{
    "id": "close_position",
    "name": "Close Position %",
    "category": "price_action",
    "type": "numeric",
    "parameters": []
},
]



# Generic metadata contract shared by UI, API and future research agents.
_FEATURE_METADATA = {
    "open": {"description":"Opening traded price.","data_dependencies":["OPEN"],"column_template":"OPEN"},
    "high": {"description":"Highest traded price.","data_dependencies":["HIGH"],"column_template":"HIGH"},
    "low": {"description":"Lowest traded price.","data_dependencies":["LOW"],"column_template":"LOW"},
    "close": {"description":"Closing traded price.","data_dependencies":["CLOSE"],"column_template":"CLOSE"},
    "volume": {"description":"Total traded quantity.","data_dependencies":["TOTTRDQTY"],"column_template":"VOLUME"},
    "delivery_percentage": {"description":"Delivered quantity as a percentage of traded quantity.","data_dependencies":["DELIV_PER"],"column_template":"DELIVERY_PERCENTAGE"},
    "rsi": {"description":"Relative Strength Index from closing prices.","data_dependencies":["CLOSE"],"column_template":"RSI_{period}"},
    "ema": {"description":"Exponential moving average of closing prices.","data_dependencies":["CLOSE"],"column_template":"EMA_{period}"},
    "sma": {"description":"Simple moving average of closing prices.","data_dependencies":["CLOSE"],"column_template":"SMA_{period}"},
    "return": {"description":"Closing-price percentage return over a lookback.","data_dependencies":["CLOSE"],"column_template":"RETURN_{period}"},
    "average_volume": {"description":"Rolling mean of traded quantity.","data_dependencies":["TOTTRDQTY"],"column_template":"AVG_VOLUME_{period}"},
    "average_delivery_percentage": {"description":"Rolling mean of delivery percentage.","data_dependencies":["DELIV_PER"],"column_template":"AVG_DELIVERY_PERCENTAGE_{period}"},
}
for _feature in FEATURE_REGISTRY:
    _metadata = _FEATURE_METADATA.get(_feature["id"], {})
    _feature.setdefault("data_type", _feature.get("type", "numeric"))
    _feature.setdefault("description", _metadata.get("description", _feature["name"]))
    _feature.setdefault("data_dependencies", _metadata.get("data_dependencies", []))
    if "column_template" in _metadata:
        _feature.setdefault("column_template", _metadata["column_template"])
    for _parameter in _feature.get("parameters", []):
        _parameter.setdefault("required", True)

def get_feature_definition(feature_id: str) -> dict:
    for feature in FEATURE_REGISTRY:
        if feature["id"] == str(feature_id).strip():
            return feature
    raise ValueError(f"Unknown research feature: {feature_id}")

def normalize_feature_parameters(feature_id: str, parameters: dict | None = None) -> dict:
    definition = get_feature_definition(feature_id)
    supplied = dict(parameters or {})
    definitions = {p["id"]: p for p in definition.get("parameters", [])}
    unknown = set(supplied) - set(definitions)
    if unknown:
        raise ValueError(f"Unsupported parameter(s) for feature '{feature_id}': {sorted(unknown)}")
    normalized = {}
    for p in definition.get("parameters", []):
        pid = p["id"]
        if pid in supplied:
            value = supplied[pid]
        elif "default" in p:
            value = p["default"]
        elif p.get("required", True):
            raise ValueError(f"Feature '{feature_id}' requires parameter '{pid}'.")
        else:
            continue
        ptype = str(p.get("type","")).lower()
        if ptype == "integer":
            if isinstance(value, bool):
                raise ValueError(f"Parameter '{pid}' must be an integer.")
            value = float(value)
            if not value.is_integer():
                raise ValueError(f"Parameter '{pid}' must be an integer.")
            value = int(value)
        elif ptype in {"number","float"}:
            value = float(value)
        if p.get("minimum") is not None and value < p["minimum"]:
            raise ValueError(f"Parameter '{pid}' must be at least {p['minimum']}.")
        if p.get("maximum") is not None and value > p["maximum"]:
            raise ValueError(f"Parameter '{pid}' must be at most {p['maximum']}.")
        if p.get("options") and value not in p["options"]:
            raise ValueError(f"Parameter '{pid}' must be one of {p['options']}.")
        normalized[pid] = value
    return normalized

def get_feature_column_candidates(feature_id: str, parameters: dict | None = None) -> list[str]:
    definition = get_feature_definition(feature_id)
    normalized = normalize_feature_parameters(feature_id, parameters)
    candidates = []
    template = definition.get("column_template")
    if template:
        try:
            candidates.append(template.format(**normalized))
        except KeyError:
            pass
    candidates += [feature_id, feature_id.upper(), feature_id.lower()]
    return list(dict.fromkeys(candidates))

def get_feature_registry() -> list:
    return FEATURE_REGISTRY
