"""Generate frontend vision DTOs from the backend Pydantic schema.

Run from backend: python scripts/generate_frontend_types.py
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.schemas.vision import MealEstimateResponse


def ts_type(field):
    if "anyOf" in field:
        return " | ".join(ts_type(option) for option in field["anyOf"])
    if field.get("type") == "null":
        return "null"
    if "$ref" in field:
        return field["$ref"].rsplit("/", 1)[-1]
    if field.get("type") == "array":
        return f"Array<{ts_type(field['items'])}>"
    return {"string": "string", "number": "number", "integer": "number", "boolean": "boolean"}[field["type"]]


def interface(name, schema):
    required = set(schema.get("required", []))
    fields = [f"  {key}{'' if key in required else '?'}: {ts_type(value)};" for key, value in schema["properties"].items()]
    return f"export interface {name} {{\n" + "\n".join(fields) + "\n}"


schema = MealEstimateResponse.model_json_schema()
blocks = ["// Generated from backend/src/schemas/vision.py. Do not edit manually."]
blocks.extend(interface(name, definition) for name, definition in schema.get("$defs", {}).items())
blocks.append(interface("MealEstimateResponse", schema))
target = Path(__file__).resolve().parents[2] / "frontend/src/types/vision.ts"
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text("\n\n".join(blocks) + "\n")
