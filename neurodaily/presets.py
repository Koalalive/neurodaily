"""Built-in research settings offered by the setup page."""

import json
from importlib.resources import files

from .config import DEFAULT_CONFIG

_RESEARCH_FIELDS = ("profile", "disciplines", "global_keywords", "journals", "sources",
                    "policy_feeds")


def research_presets() -> list[dict]:
    directory = files("neurodaily").joinpath("data").joinpath("presets")
    oncology = json.loads(directory.joinpath("oncology.json").read_text(encoding="utf-8"))
    presets = (("神经科学", DEFAULT_CONFIG().to_dict()), ("肿瘤学", oncology))
    return [{"label": label, "config": {key: config[key] for key in _RESEARCH_FIELDS}}
            for label, config in presets]
