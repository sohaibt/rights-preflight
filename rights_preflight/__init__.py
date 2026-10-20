"""rights-preflight: rights gate for creative assets (fonts, images, audio, video, 3D)."""
import re

__version__ = "0.1.0"

# attribution: credits must name author and source. commercial: allowed in paid work.
LICENSES = {
    "CC0": {"name": "Creative Commons Zero 1.0", "url": "https://creativecommons.org/publicdomain/zero/1.0/", "attribution": False, "commercial": True},
    "CC-BY": {"name": "Creative Commons Attribution 4.0", "url": "https://creativecommons.org/licenses/by/4.0/", "attribution": True, "commercial": True},
    "CC-BY-SA": {"name": "Creative Commons Attribution-ShareAlike 4.0", "url": "https://creativecommons.org/licenses/by-sa/4.0/", "attribution": True, "commercial": True},
    "CC-BY-NC": {"name": "Creative Commons Attribution-NonCommercial 4.0", "url": "https://creativecommons.org/licenses/by-nc/4.0/", "attribution": True, "commercial": False},
    "OFL": {"name": "SIL Open Font License 1.1", "url": "https://openfontlicense.org/", "attribution": False, "commercial": True},
    "Apache-2.0": {"name": "Apache License 2.0", "url": "https://www.apache.org/licenses/LICENSE-2.0", "attribution": True, "commercial": True},
    "MIT": {"name": "MIT License", "url": "https://opensource.org/license/mit", "attribution": True, "commercial": True},
    "public-domain": {"name": "Public domain", "url": "https://creativecommons.org/publicdomain/mark/1.0/", "attribution": False, "commercial": True},
    "licensed-proprietary": {"name": "Licensed (proprietary)", "url": "", "attribution": False, "commercial": True},
    "ai-generated": {"name": "AI-generated", "url": "", "attribution": False, "commercial": True},
}


def _key(s):
    k = re.sub(r"[\s_]+", "-", s.strip()).upper()
    return re.sub(r"-V?\d+(\.\d+)*$", "", k)


_IDS = {_key(i): i for i in LICENSES}
_IDS.update({"PD": "public-domain", "PROPRIETARY": "licensed-proprietary", "AI": "ai-generated",
             "SIL-OFL": "OFL", "OFL-1.1": "OFL", "AI-GENERATED-CONTENT": "ai-generated"})

# Free-text / URL detection for embedded metadata. Order matters: NC and SA before plain BY.
_PATTERNS = [
    (r"publicdomain/zero|\bCC0\b|\bCC[ -]ZERO\b", "CC0"),
    (r"licenses/by-nc|\bCC[ -]BY[ -]NC\b|non-?commercial", "CC-BY-NC"),
    (r"licenses/by-sa/|\bCC[ -]BY[ -]SA\b", "CC-BY-SA"),
    (r"licenses/by/|\bCC[ -]BY\b(?![ -](SA|NC|ND))", "CC-BY"),
    (r"open font license|openfontlicense\.org|scripts\.sil\.org/ofl|\bOFL\b", "OFL"),
    (r"apache\.org/licenses|apache license", "Apache-2.0"),
    (r"\bMIT license\b|opensource\.org/licenses?/mit", "MIT"),
    (r"publicdomain/mark|\bpublic domain\b", "public-domain"),
]


def resolve_license(raw):
    """Map a license ID, alias, name or URL to a LICENSES key, or None if unknown."""
    if not raw or not raw.strip():
        return None
    hit = _IDS.get(_key(raw))
    if hit:
        return hit
    for pat, lid in _PATTERNS:
        if re.search(pat, raw, re.I):
            return lid
    return None
