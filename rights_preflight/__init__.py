"""rights-preflight: rights gate for creative assets (fonts, images, audio, video, 3D)."""
import fnmatch
import hashlib
import json
import os
import re
import struct
import xml.etree.ElementTree as ET
import zlib

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


MEDIA_TYPES = {
    "image": "png jpg jpeg gif webp svg tif tiff bmp psd heic avif exr ico",
    "audio": "wav mp3 ogg oga flac aac m4a aif aiff opus",
    "video": "mp4 mov webm mkv avi m4v",
    "font": "ttf otf ttc woff",
    "3d": "glb gltf obj fbx blend stl usdz dae 3ds ply",
}
EXT_TYPE = {"." + e: t for t, exts in MEDIA_TYPES.items() for e in exts.split()}
SKIP_DIRS = {"node_modules", "__pycache__"}
SIDECAR = ".rights.json"
FIELDS = ("license", "author", "source")


def read_font_names(data):
    """Return {nameID: text} from a TTF/OTF/TTC/WOFF 'name' table; {} if unreadable."""
    try:
        if data[:4] == b"wOFF":
            n = struct.unpack(">H", data[12:14])[0]
            for i in range(n):
                tag, off, clen, olen, _ = struct.unpack(">4sIIII", data[44 + 20 * i: 64 + 20 * i])
                if tag == b"name":
                    t = data[off:off + clen]
                    return _name_table(zlib.decompress(t) if clen < olen else t)
            return {}
        base = struct.unpack(">I", data[12:16])[0] if data[:4] == b"ttcf" else 0  # first font in a collection
        n = struct.unpack(">H", data[base + 4:base + 6])[0]
        for i in range(n):
            tag, _, off, length = struct.unpack(">4sIII", data[base + 12 + 16 * i: base + 28 + 16 * i])
            if tag == b"name":
                return _name_table(data[off:off + length])
    except (struct.error, zlib.error, IndexError):
        pass
    return {}


def _name_table(t):
    _, count, str_off = struct.unpack(">3H", t[:6])
    names = {}
    for i in range(count):
        plat, enc, lang, nid, length, off = struct.unpack(">6H", t[6 + 12 * i: 18 + 12 * i])
        raw = t[str_off + off: str_off + off + length]
        if plat in (0, 3):
            text = raw.decode("utf-16-be", "replace")
        elif plat == 1 and enc == 0:
            text = raw.decode("mac_roman", "replace")
        else:
            continue
        # Prefer English Windows records, else keep the first one seen.
        if nid not in names or (plat == 3 and lang == 0x409):
            names[nid] = text.strip()
    return names


_NS = {
    "{http://purl.org/dc/elements/1.1/}rights": "rights",
    "{http://purl.org/dc/elements/1.1/}creator": "creator",
    "{http://ns.adobe.com/xap/1.0/rights/}WebStatement": "web_statement",
    "{http://ns.adobe.com/xap/1.0/rights/}UsageTerms": "usage_terms",
    "{http://creativecommons.org/ns#}license": "cc_license",
    "{http://creativecommons.org/ns#}attributionURL": "cc_attribution_url",
}
_RDF_RES = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource"


def read_xmp(data):
    """Return rights fields from the first uncompressed XMP packet in the bytes; {} if none."""
    m = re.search(rb"<x:xmpmeta.*?</x:xmpmeta>", data, re.S)
    if not m or b"<!DOCTYPE" in m.group(0) or b"<!ENTITY" in m.group(0):
        return {}
    try:
        tree = ET.fromstring(m.group(0))
    except ET.ParseError:
        return {}
    out = {}
    for el in tree.iter():
        for attr, val in el.attrib.items():  # short form: <rdf:Description xmpRights:WebStatement="...">
            if attr in _NS and val.strip():
                out.setdefault(_NS[attr], val.strip())
        if el.tag in _NS:
            texts = [t.strip() for t in el.itertext() if t.strip()]
            val = "; ".join(texts) if texts else el.get(_RDF_RES, "").strip()
            if val:
                out.setdefault(_NS[el.tag], val)
    return out


def _first_license(*candidates):
    """First candidate that resolves to a known license, else the first non-empty one (reported as unknown)."""
    cands = [c for c in candidates if c]
    for c in cands:
        if resolve_license(c):
            return c
    return cands[0] if cands else None


def embedded_rights(kind, data):
    if kind == "font":
        n = read_font_names(data)
        return {"license": _first_license(n.get(14), n.get(13)),
                "author": n.get(9) or n.get(8) or n.get(0),
                "source": n.get(11) or n.get(12)}
    if kind == "image":
        x = read_xmp(data)
        return {"license": _first_license(x.get("cc_license"), x.get("web_statement"), x.get("rights"), x.get("usage_terms")),
                "author": x.get("creator"),
                "source": x.get("cc_attribution_url")}
    return {}


def load_rules(root):
    path = os.path.join(root, "rights.json")
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as f:
            cfg = json.load(f)
        rules = cfg["rules"] if isinstance(cfg, dict) else cfg
        if not all(isinstance(r, dict) and isinstance(r.get("glob"), str) for r in rules):
            raise TypeError
        return rules
    except (ValueError, KeyError, TypeError):
        raise ValueError(path + ": expected an object with a rules list of glob/license/author/source entries")


def _rule_for(rel, rules):
    for r in rules:
        g = r["glob"]
        if fnmatch.fnmatchcase(rel, g) or ("/" not in g and fnmatch.fnmatchcase(os.path.basename(rel), g)):
            return r
    return {}


def _read_sidecar(path):
    with open(path, encoding="utf-8") as f:
        side = json.load(f)
    if not isinstance(side, dict):
        raise ValueError("not a JSON object")
    return side


def scan(root):
    """List media files under root with type, size, sha256 and resolved rights."""
    rules = load_rules(root)
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith(".") and d not in SKIP_DIRS)
        for name in sorted(filenames):
            kind = EXT_TYPE.get(os.path.splitext(name)[1].lower())
            if not kind:
                continue
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            # ponytail: reads each file fully (hash + metadata); stream if multi-GB videos hurt.
            with open(full, "rb") as f:
                data = f.read()
            entry = {"path": rel, "type": kind, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
            emb = embedded_rights(kind, data)
            side, errors = {}, []
            if os.path.exists(full + SIDECAR):
                try:
                    side = _read_sidecar(full + SIDECAR)
                except (ValueError, UnicodeDecodeError) as e:
                    errors.append("cannot read " + name + SIDECAR + ": " + str(e))
            rule = _rule_for(rel, rules)
            rights, origin = {}, {}
            for field in FIELDS:
                rights[field] = None
                for label, src in (("sidecar", side), ("rules", rule), ("embedded", emb)):
                    val = src.get(field)
                    if isinstance(val, str) and val.strip():
                        rights[field], origin[field] = val.strip(), label
                        break
            rights["license_id"] = resolve_license(rights["license"])
            entry["rights"], entry["rights_from"] = rights, origin
            if errors:
                entry["errors"] = errors
            out.append(entry)
    return out


def write_manifest(files, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"tool": "rights-preflight", "version": __version__, "files": files}, f, indent=2, ensure_ascii=False)
        f.write("\n")


def check(files, commercial=False):
    """Return a list of problems: dicts with path, code and message. Empty list means ship it."""
    problems = []

    def add(f, code, msg):
        problems.append({"path": f["path"], "code": code, "message": msg})

    for f in files:
        for err in f.get("errors", []):
            add(f, "bad-sidecar", err)
        r = f["rights"]
        lid = r["license_id"]
        if not r["license"]:
            add(f, "missing-license", "no license in sidecar, rights.json or embedded metadata")
            continue
        if not lid:
            add(f, "unknown-license", "unknown license: " + r["license"])
            continue
        lic = LICENSES[lid]
        if lic["attribution"]:
            for field in ("author", "source"):
                if not r[field]:
                    add(f, "missing-" + field, lid + " requires attribution: add " + field)
        if commercial and not lic["commercial"]:
            add(f, "non-commercial", lid + " does not allow commercial use")
    return problems
