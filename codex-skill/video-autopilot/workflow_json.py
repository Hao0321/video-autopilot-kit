"""Finite JSON wire encoding shared by plan hashing and public audit checksums.

No workflow imports: request/receipt sha256_json retains its historical contract.
"""
import hashlib, json, math
from decimal import Decimal

def json_stringify(value, *, canonical=False):
    def string(item):
        text = json.dumps(item, ensure_ascii=False, separators=(",", ":"))
        return "".join("\\u%04x" % ord(char) if 0xd800 <= ord(char) <= 0xdfff else char for char in text)
    def key_bytes(item):
        return "".join("\ufffd" if 0xd800 <= ord(char) <= 0xdfff else char for char in item).encode("utf-8")
    def keys(item):
        if any(not isinstance(key, str) for key in item): raise ValueError("JSON object keys must be strings")
        if canonical: return sorted(item, key=key_bytes)
        # ECMAScript enumerates array-index keys numerically before other keys.
        indexed = [key for key in item if key.isascii() and key.isdigit() and str(int(key)) == key and int(key) < 4294967295]
        return sorted(indexed, key=int) + [key for key in item if key not in indexed]
    def encode(item):
        if isinstance(item, dict): return "{" + ",".join(string(key) + ":" + encode(item[key]) for key in keys(item)) + "}"
        if isinstance(item, list): return "[" + ",".join(encode(child) for child in item) + "]"
        if type(item) in (int, float):
            if type(item) is int and abs(item) > 9007199254740991:
                try: item = float(item)
                except OverflowError: raise ValueError("Non-finite JSON number")
            if not math.isfinite(item): raise ValueError("Non-finite JSON number")
            if item == 0: return "0"
            if 1e-6 <= abs(item) < 1e21:
                fixed = format(Decimal(str(item)), "f")
                return fixed.rstrip("0").rstrip(".") if "." in fixed else fixed
            mantissa, exponent = format(float(item), ".15e").split("e") if "e" not in repr(item).lower() else repr(item).lower().split("e")
            exponent = int(exponent)
            return mantissa.rstrip("0").rstrip(".") + "e" + ("+" if exponent >= 0 else "-") + str(abs(exponent))
        if item is None or type(item) in (str, bool): return string(item)
        raise ValueError("Unsupported JSON value: " + type(item).__name__)
    return encode(value)

def json_sha256(value, *, canonical=False):
    return hashlib.sha256(json_stringify(value, canonical=canonical).encode("utf-8")).hexdigest()
