"""
Serialization engine for remote execution.

Handles serialization/deserialization of Python objects, numpy arrays,
tensors, images, and other data types for cloud RPC transport.
"""

from __future__ import annotations

import base64
import json
import pickle
from typing import Any


# Types safe to pickle for remote execution
_PICKLE_ALLOWLIST = frozenset({
    "builtins", "collections", "datetime", "decimal",
    "fractions", "numbers", "re", "uuid",
})


def serialize_args(args: Any) -> Any:
    """Serialize function arguments for RPC transport."""
    if args is None:
        return None
    if isinstance(args, (str, int, float, bool)):
        return args
    if isinstance(args, (list, tuple)):
        return [serialize_value(a) for a in args]
    if isinstance(args, dict):
        return {k: serialize_value(v) for k, v in args.items()}
    return serialize_value(args)


def serialize_value(value: Any) -> Any:
    """Serialize a single value."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, (list, tuple)):
        return {"__type__": "list", "values": [serialize_value(v) for v in value]}

    if isinstance(value, dict):
        return {"__type__": "dict", "items": {k: serialize_value(v) for k, v in value.items()}}

    if isinstance(value, bytes):
        return {"__type__": "bytes", "data": base64.b64encode(value).decode("ascii")}

    if isinstance(value, complex):
        return {"__type__": "complex", "real": value.real, "imag": value.imag}

    if isinstance(value, set):
        return {"__type__": "set", "values": [serialize_value(v) for v in value]}

    # numpy array
    if _is_numpy_array(value):
        return _serialize_numpy(value)

    # Try pickle as fallback for known-safe types
    module = type(value).__module__
    if module.split(".")[0] in _PICKLE_ALLOWLIST:
        return _serialize_pickle(value)

    # Generic: convert to string representation
    return {"__type__": "repr", "value": repr(value), "class": type(value).__name__}


def deserialize_result(data: Any) -> Any:
    """Deserialize an RPC result."""
    if data is None or isinstance(data, (str, int, float, bool)):
        return data

    if isinstance(data, list):
        return [deserialize_result(item) for item in data]

    if isinstance(data, dict):
        type_tag = data.get("__type__")
        if type_tag:
            return _deserialize_typed(type_tag, data)
        return {k: deserialize_result(v) for k, v in data.items()}

    return data


def _deserialize_typed(type_tag: str, data: dict) -> Any:
    """Deserialize a typed value."""
    if type_tag == "list":
        return [deserialize_result(v) for v in data.get("values", [])]

    if type_tag == "dict":
        return {k: deserialize_result(v) for k, v in data.get("items", {}).items()}

    if type_tag == "bytes":
        return base64.b64decode(data["data"])

    if type_tag == "complex":
        return complex(data["real"], data["imag"])

    if type_tag == "set":
        return {deserialize_result(v) for v in data.get("values", [])}

    if type_tag == "ndarray":
        return _deserialize_numpy(data)

    if type_tag == "tensor":
        return _deserialize_tensor(data)

    if type_tag == "pickle":
        return _deserialize_pickle(data)

    if type_tag == "repr":
        return data.get("value", "")

    return data


# ── NumPy Serialization ─────────────────────────────────────────────

def _is_numpy_array(value: Any) -> bool:
    try:
        import numpy as np
        return isinstance(value, np.ndarray)
    except ImportError:
        return False


def _serialize_numpy(arr: Any) -> dict:
    import numpy as np
    return {
        "__type__": "ndarray",
        "dtype": str(arr.dtype),
        "shape": list(arr.shape),
        "data": base64.b64encode(arr.tobytes()).decode("ascii"),
    }


def _deserialize_numpy(data: dict) -> Any:
    try:
        import numpy as np
        arr = np.frombuffer(
            base64.b64decode(data["data"]),
            dtype=np.dtype(data["dtype"]),
        )
        return arr.reshape(data["shape"])
    except ImportError:
        return data


# ── Tensor Serialization ────────────────────────────────────────────

def _deserialize_tensor(data: dict) -> Any:
    try:
        import torch
        import numpy as np
        arr = np.frombuffer(
            base64.b64decode(data["data"]),
            dtype=np.dtype(data.get("numpy_dtype", "float32")),
        ).reshape(data["shape"])
        return torch.from_numpy(arr)
    except ImportError:
        return _deserialize_numpy(data)


# ── Pickle Serialization (restricted) ────────────────────────────────

def _serialize_pickle(value: Any) -> dict:
    return {
        "__type__": "pickle",
        "data": base64.b64encode(pickle.dumps(value)).decode("ascii"),
        "class": f"{type(value).__module__}.{type(value).__name__}",
    }


def _deserialize_pickle(data: dict) -> Any:
    class_path = data.get("class", "")
    module = class_path.split(".")[0]
    if module not in _PICKLE_ALLOWLIST:
        return data
    return pickle.loads(base64.b64decode(data["data"]))
