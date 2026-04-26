from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, r"D:\DEV\ComfyUI\.codex_deps")

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap


ROOT = Path(__file__).resolve().parent
CATALOG_PATH = ROOT / "sd_catalog_civitai.yml"
DETAIL_ROOT = ROOT / "sd_catalog_civitai" / "detail"
DETAIL_ROOT_DISPLAY = "sd_catalog_civitai/detail"


def cmap(items=()):
    result = CommentedMap()
    for key, value in items:
        result[key] = value
    return result


def pick(mapping, keys):
    result = CommentedMap()
    if not isinstance(mapping, dict):
        return result
    for key in keys:
        if key in mapping:
            result[key] = mapping[key]
    return result


def sample_summary(model):
    samples = model.get("samples") if isinstance(model, dict) else None
    if not isinstance(samples, dict):
        return cmap([("status", "not_structured"), ("count", 0)])
    return pick(
        samples,
        [
            "status",
            "source",
            "fetched_at",
            "model_id",
            "version_id",
            "count",
            "fetch_error",
        ],
    )


def review_summary(model):
    review = model.get("review") if isinstance(model, dict) else None
    if not isinstance(review, dict):
        return CommentedMap()
    return pick(
        review,
        [
            "status",
            "missing",
            "sample_status",
            "sample_count",
            "nsfw_samples_present",
        ],
    )


def index_entry(model_key, model):
    civitai = model.get("civitai") if isinstance(model.get("civitai"), dict) else {}
    entry = cmap(
        [
            ("detail_file", f"{DETAIL_ROOT_DISPLAY}/{model_key}.yml"),
            ("local_file", model.get("local_file")),
            ("catalog_type", model.get("catalog_type")),
            ("base_model", model.get("base_model")),
            ("base_model_raw", model.get("base_model_raw")),
            (
                "civitai",
                pick(
                    civitai,
                    [
                        "model_id",
                        "version_id",
                        "model_url",
                        "air",
                        "model_name",
                        "version_name",
                        "creator",
                        "nsfw",
                        "tags",
                        "trained_words",
                        "download_url",
                    ],
                ),
            ),
            ("samples", sample_summary(model)),
        ]
    )
    review = review_summary(model)
    if review:
        entry["review"] = review
    return entry


def main():
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.width = 120
    yaml.indent(mapping=2, sequence=4, offset=2)

    catalog = yaml.load(CATALOG_PATH.read_text(encoding="utf-8"))
    if not isinstance(catalog, dict) or not isinstance(catalog.get("models"), dict):
        raise RuntimeError(f"Expected models mapping in {CATALOG_PATH}")

    DETAIL_ROOT.mkdir(parents=True, exist_ok=True)

    index_models = CommentedMap()
    for model_key, model in catalog["models"].items():
        detail = cmap(
            [
                ("schema_version", catalog.get("schema_version")),
                ("kind", "civitai_model_detail"),
                ("model_key", model_key),
                ("sources", catalog.get("sources")),
                ("model", model),
            ]
        )
        detail_path = DETAIL_ROOT / f"{model_key}.yml"
        with detail_path.open("w", encoding="utf-8", newline="\n") as handle:
            yaml.dump(detail, handle)
        index_models[model_key] = index_entry(model_key, model)

    index = cmap(
        [
            ("schema_version", catalog.get("schema_version")),
            ("kind", "civitai_catalog_index"),
            ("sources", catalog.get("sources")),
            (
                "split",
                cmap(
                    [
                        ("detail_root", DETAIL_ROOT_DISPLAY),
                        ("detail_file_pattern", "{model_key}.yml"),
                        ("detail_schema", "civitai_model_detail"),
                        ("model_count", len(index_models)),
                    ]
                ),
            ),
            ("models", index_models),
        ]
    )

    with CATALOG_PATH.open("w", encoding="utf-8", newline="\n") as handle:
        yaml.dump(index, handle)

    print(f"split {len(index_models)} models")
    print(f"index: {CATALOG_PATH}")
    print(f"details: {DETAIL_ROOT}")


if __name__ == "__main__":
    main()
