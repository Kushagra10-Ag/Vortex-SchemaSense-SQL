"""Loads prompt files. Format: '### SYSTEM' section then '### USER' section. Variables look like {question}."""
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
# temperature per prompt version (None = provider default). Record these in the prompt sheet.
SETTINGS = {"v1": None, "v2": None, "v3": 0, "final": 0}


def load(version: str, name: str):
    text = (PROMPTS_DIR / version / f"{name}.txt").read_text(encoding="utf-8")
    system = text.split("### SYSTEM", 1)[1].split("### USER", 1)[0].strip()
    user = text.split("### USER", 1)[1].strip()
    return system, user


def render(template: str, **variables) -> str:
    for k, v in variables.items():
        template = template.replace("{" + k + "}", str(v))
    return template
