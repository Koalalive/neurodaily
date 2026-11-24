"""Built-in research settings offered by the setup page."""

import json
from importlib.resources import files

from .config import DEFAULT_CONFIG

_RESEARCH_FIELDS = ("profile", "disciplines", "global_keywords", "journals", "sources",
                    "policy_feeds", "search")


def _neuroscience() -> dict:
    preset = DEFAULT_CONFIG().to_dict()
    preset["disciplines"].extend([
        {"name": "Neuroengineering", "mesh_terms": ["Brain-Computer Interfaces", "Neuroprostheses"],
         "arxiv_cats": ["q-bio.NC", "eess.SP"], "bio_cats": ["neuroscience"],
         "keywords": ["brain-computer interface", "neuroprosthesis", "electrocorticography",
                      "neuromodulation", "deep brain stimulation"]},
        {"name": "Neurodegeneration", "mesh_terms": ["Neurodegenerative Diseases", "Alzheimer Disease",
                                                    "Parkinson Disease"],
         "bio_cats": ["neuroscience"], "keywords": ["neurodegeneration", "Alzheimer disease",
                                                    "Parkinson disease", "alpha-synuclein",
                                                    "amyotrophic lateral sclerosis"]},
    ])
    preset["sources"].update({
        "europe_pmc": {"enabled": True, "max_results": 40, "lookback_days": 2},
        "nih_brain": {"enabled": True, "max_results": 25, "lookback_days": 7},
    })
    preset["sources"]["conferences"]["query"] = "neuro"
    for url, kind in preset["sources"]["policy"]["feed_kinds"].items():
        if kind == "funding" and "fda.gov" in url:
            preset["sources"]["policy"]["feed_kinds"][url] = "policy"
    preset["search"] = {"rules": {"trial": 'TS="brain-computer interface" OR TS=neuroprosthesis OR '
                                           'TS=neuroscience OR TS=epilepsy OR TS=neuromodulation OR '
                                           'TS=depression OR TS=schizophrenia OR TS=dementia OR '
                                           'TS=parkinson OR TS=alzheimer OR TS="brain injury" '
                                           'OR TS=stroke OR TS=addiction'}}
    return preset


def research_presets() -> list[dict]:
    directory = files("neurodaily").joinpath("data").joinpath("presets")
    presets = [("神经科学", _neuroscience())]
    for label, filename in (("肿瘤学", "oncology.json"), ("重症医学", "critical-care.json")):
        data = directory.joinpath(filename).read_text(encoding="utf-8")
        presets.append((label, json.loads(data)))
    return [{"label": label, "config": {key: config[key] for key in _RESEARCH_FIELDS}}
            for label, config in presets]
