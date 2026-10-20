"""Regenerate the tiny binary fixtures in tests/fixtures. Run: python3 tests/make_fixtures.py"""
import json
import os
import struct
import zlib

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")

XMP = (
    '<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>'
    '<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
    '<rdf:Description rdf:about="" xmlns:dc="http://purl.org/dc/elements/1.1/" '
    'xmlns:xmpRights="http://ns.adobe.com/xap/1.0/rights/"{attrs}>'
    '<dc:rights><rdf:Alt><rdf:li xml:lang="x-default">{rights}</rdf:li></rdf:Alt></dc:rights>'
    '<dc:creator><rdf:Seq><rdf:li>{creator}</rdf:li></rdf:Seq></dc:creator>'
    '</rdf:Description></rdf:RDF></x:xmpmeta><?xpacket end="w"?>'
)


def png(xmp=None):
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    out = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 0, 0, 0, 0))
    if xmp:
        out += chunk(b"iTXt", b"XML:com.adobe.xmp\x00\x00\x00\x00\x00" + xmp.encode())
    return out + chunk(b"IDAT", zlib.compress(b"\x00\x00")) + chunk(b"IEND", b"")


def ttf(names):
    """Minimal sfnt with only a 'name' table (Windows/Unicode records)."""
    records, strings = b"", b""
    for name_id, text in sorted(names.items()):
        s = text.encode("utf-16-be")
        records += struct.pack(">6H", 3, 1, 0x409, name_id, len(s), len(strings))
        strings += s
    table = struct.pack(">3H", 0, len(names), 6 + len(records)) + records + strings
    header = struct.pack(">IHHHH", 0x00010000, 1, 16, 0, 0)
    return header + struct.pack(">4sIII", b"name", 0, 12 + 16, len(table)) + table


def wav():
    data = b"\x00\x00" * 8
    fmt = struct.pack("<HHIIHH", 1, 1, 8000, 16000, 2, 16)
    return (b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt " + struct.pack("<I", 16) + fmt
            + b"data" + struct.pack("<I", len(data)) + data)


def write(rel, data):
    path = os.path.join(HERE, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if isinstance(data, (dict, list)):
        data = json.dumps(data, indent=2) + "\n"
    open(path, "wb").write(data.encode() if isinstance(data, str) else data)


def main():
    # project/: passes `check`; fails `check --commercial` only on images/nc.png.
    write("project/rights.json", {"rules": [
        {"glob": "audio/*", "license": "CC0", "author": "Freesound user", "source": "https://freesound.org/s/1/"},
    ]})
    write("project/fonts/Demo.ttf", ttf({
        0: "Copyright 2026 Demo Foundry", 1: "Demo Sans", 9: "Ada Demo",
        11: "https://example.com/foundry",
        13: "This Font Software is licensed under the SIL Open Font License, Version 1.1.",
        14: "https://openfontlicense.org",
    }))
    write("project/images/photo.png", png(XMP.format(
        attrs=' xmpRights:WebStatement="https://creativecommons.org/licenses/by/4.0/"',
        rights="CC BY 4.0", creator="Jane Photo")))
    write("project/images/photo.png.rights.json", {"source": "https://example.com/photo"})
    write("project/images/nc.png", png())
    write("project/images/nc.png.rights.json", {"license": "CC-BY-NC", "author": "Nina", "source": "https://example.com/nc"})
    write("project/audio/beep.wav", wav())
    write("project/models/cube.obj", "v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n")
    write("project/models/cube.obj.rights.json", {"license": "ai-generated", "author": "Team", "source": "Prompted in-house"})
    write("project/README.txt", "not a media file\n")

    # broken/: one problem per file.
    write("broken/a.png", png())                                   # missing-license
    write("broken/b.png", png())
    write("broken/b.png.rights.json", {"license": "CC-BY"})         # missing-author, missing-source
    write("broken/c.mp3", b"ID3\x03\x00\x00\x00\x00\x00\x00")
    write("broken/c.mp3.rights.json", {"license": "WTFPL"})         # unknown-license
    write("broken/d.jpg", b"\xff\xd8\xff\xd9")
    write("broken/d.jpg.rights.json", "{not json")                  # bad-sidecar
    write("broken/e.png", png(XMP.format(attrs="", rights="All rights reserved", creator="Someone")))  # unknown-license


if __name__ == "__main__":
    main()
