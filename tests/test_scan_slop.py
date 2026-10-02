#!/usr/bin/env python3
"""Fixture tests for scan_slop. Each case is a bug that was found in review."""
import importlib.util
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def _find(name, *cands):
    for c in cands:
        p = os.path.join(HERE, c)
        if os.path.exists(p):
            return p
    raise SystemExit(f"cannot locate {name}")


# works flat (scan_slop.py + fixtures/ next to this file) or
# nested (scripts/scan_slop.py + tests/fixtures/ from the repo root)
SCAN = _find("scan_slop.py", "scan_slop.py", "../scripts/scan_slop.py",
             "scripts/scan_slop.py")
FIX = _find("fixtures", "fixtures", "../fixtures", "tests/fixtures")

spec = importlib.util.spec_from_file_location("scan_slop", SCAN)
scan = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scan)

FAILS = []


def case(name, cond, detail=""):
    print(f"{'PASS' if cond else 'FAIL'}  {name}" + (f"  ({detail})" if detail and not cond else ""))
    if not cond:
        FAILS.append(name)


def run(fixture, *flags):
    env = dict(os.environ)
    p = subprocess.run([sys.executable, SCAN, os.path.join(FIX, fixture), *flags],
                       capture_output=True, text=True, env=env)
    try:
        return json.loads(p.stdout), p.returncode
    except json.JSONDecodeError:
        return {"_raw": p.stdout, "_err": p.stderr}, p.returncode


# 1. clean page must NOT report Inter from "pointer-events" / "interface"
clean, code = run("clean")
case("clean: no phantom Inter", clean["default_fonts"] == [], clean["default_fonts"])
case("clean: no numbered steps from table cells", clean["numbered_steps"] == 0,
     clean["numbered_steps"])
case("clean: radius count <=3", clean["distinct_radius_values"] <= 3,
     clean["radius_tokens"])
case("clean: clean verdict", clean["verdict"] == "clean", clean["findings"])
case("clean: exit 0", code == 0, code)
case("clean: fonts detected by declaration", "bitter" not in clean["default_fonts"])

# 2. sloppy page must trip the tells
sloppy, scode = run("sloppy")
case("sloppy: verdict slop", sloppy["verdict"] == "slop", sloppy["tell_count"])
case("sloppy: exit 2", scode == 2, scode)
for key in ["vibecode_purple", "colored_glows", "hero_emphasis", "nested_cards",
            "numbered_steps", "hidden_without_js", "missing_reduced_motion",
            "outline_removed", "stale_copyright", "generic_taglines",
            "generic_title"]:
    v = sloppy.get(key)
    case(f"sloppy: flags {key}", bool(v), v)
found = {f["check"] for f in sloppy["findings"]}
case("sloppy: flags missing_og", "missing_og" in found, sorted(found))
case("sloppy: flags missing_favicon", "missing_favicon" in found, sorted(found))
case("sloppy: radius count >3", sloppy["distinct_radius_values"] > 3, sloppy["radius_tokens"])
case("sloppy: contrast failure found", bool(sloppy["contrast_failures"]),
     sloppy["contrast_failures"])
case("sloppy: uppercase labels counted", sloppy["uppercase_labels"] >= 4)
case("sloppy: off-scale spacing flagged", "off_scale_spacing" in
     [f["check"] for f in sloppy["findings"]])
case("sloppy: gradient count includes tailwind-free source", sloppy["gradient_count"] >= 3)

# 3. node_modules / vendor must not be attributed to the page
vendor, vcode = run("vendorcase")
case("vendor: dependency CSS skipped", vendor["vibecode_purple"] == [],
     vendor["vibecode_purple"])
case("vendor: no vendor gradient", vendor["gradient_count"] == 0, vendor["gradient_count"])
case("vendor: no vendor glow", vendor["colored_glows"] == 0, vendor["colored_glows"])
case("vendor: no vendor hover lift", vendor["hover_lift_effects"] == 0)
case("vendor: vendor dirs listed as skipped", "node_modules" not in " ".join(vendor["files_scanned"]))
case("vendor: clean verdict", vendor["verdict"] == "clean", vendor["findings"])

# 4. radius shorthand and percentages must be visible
sh, _ = run("shorthand")
case("shorthand: 8px 8px 0 0 counted", "8px" in sh["radius_tokens"], sh["radius_tokens"])
case("shorthand: 50% counted", "50%" in sh["radius_tokens"], sh["radius_tokens"])
case("shorthand: border width not read as radius", "1px" not in sh["radius_tokens"],
     sh["radius_tokens"])
case("shorthand: distinct count is 2", sh["distinct_radius_values"] == 2,
     sh["radius_tokens"])

# 5. hero emphasis must be scoped to h1
plain, _ = run("italic")
case("italic: blockquote emphasis does not trip hero check",
     plain["hero_emphasis"] == [], plain["hero_emphasis"])
hero, _ = run("italic-hero")
case("italic: em inside h1 is caught", len(hero["hero_emphasis"]) == 1,
     hero["hero_emphasis"])

# 6. copyright year must be computed, not hardcoded
case("copyright: computed against current year",
     scan.check_copyright("<p>&copy; 2019 Vibe</p>") == 2019)
case("copyright: current year passes",
     scan.check_copyright("<p>&copy; 2026 Vibe</p>") is None)

# 7. CLI hygiene
p = subprocess.run([sys.executable, SCAN], capture_output=True, text=True)
case("cli: usage instead of traceback", p.returncode == 64 and "usage" in
     (p.stdout + p.stderr).lower() or "scan_slop.py" in p.stdout, p.returncode)
p = subprocess.run([sys.executable, SCAN, "/nope"], capture_output=True, text=True)
case("cli: bad path exits 64", p.returncode == 64, p.returncode)

per, _ = run("sloppy", "--per-file")
case("cli: per-file emits one report per page", isinstance(per, list) and
     per[0]["path"].endswith("index.html"), type(per).__name__)

# 8. mono is only a tell as body copy, and sibling cards are not nested cards
mono, mcode = run("monocode")
case("mono: code/pre mono does not flag body mono", mono["mono_body"] == [],
     mono["mono_body"])
case("mono: sibling cards are not nested", mono["nested_cards"] == 0, mono["nested_cards"])
case("mono: clean verdict", mono["verdict"] == "clean", mono["findings"])
tint, tcode = run("tintcards")
case("tint: low-alpha purple is a review item, not a tell",
     bool(tint["purple_tint"]) and tint["vibecode_purple"] == [], tint["purple_tint"])
case("tint: verdict review not slop", tint["verdict"] == "review" and tcode == 1,
     (tint["verdict"], tcode))
case("tint: no nested card false positive", tint["nested_cards"] == 0, tint["nested_cards"])

# 9. loud purple still a tell (regression guard on the tint split)
loud, lcode = run("sloppy")
case("sloppy: loud purple still a tell", bool(loud["vibecode_purple"]),
     loud["vibecode_purple"])

# 10. the threshold counts distinct patterns, not repeated instances
sloppy2, _ = run("sloppy")
case("counting: tell_count is distinct patterns", sloppy2["tell_count"] <
     sloppy2["tell_instances"], (sloppy2["tell_count"], sloppy2["tell_instances"]))
case("counting: threshold is 4", scan.TELL_THRESHOLD == 4)
case("counting: clean has zero distinct tells", clean["tell_count"] == 0)

# 11. container-reflex tells: status pill with a dot, icon locked in a box
pb, pcode = run("pillbox")
case("pillbox: status pill with dot flagged", pb["status_pill"] == 1, pb.get("status_pill"))
case("pillbox: icon boxes flagged", pb["icon_box"] >= 2, pb.get("icon_box"))
pb_found = {f["check"] for f in pb["findings"]}
case("pillbox: both surface as findings",
     {"status_pill", "icon_box"} <= pb_found, sorted(pb_found))
case("clean: no status pill false positive", clean["status_pill"] == 0, clean.get("status_pill"))
case("clean: no icon box false positive", clean["icon_box"] == 0, clean.get("icon_box"))
case("sloppy: a plain pill with no dot is not a status pill",
     sloppy["status_pill"] == 0, sloppy.get("status_pill"))
case("sloppy: an icon-free page has no icon boxes", sloppy["icon_box"] == 0,
     sloppy.get("icon_box"))

# 12. general box sprawl: nested surfaces + uniform feature grid
bx, _ = run("boxgrid")
case("boxgrid: nested surface flagged", bx["nested_surfaces"] >= 1, bx.get("nested_surfaces"))
case("boxgrid: uniform feature grid flagged", bx["uniform_feature_grid"] >= 1,
     bx.get("uniform_feature_grid"))
case("clean: no nested surface false positive", clean["nested_surfaces"] == 0,
     clean.get("nested_surfaces"))
case("clean: no uniform grid false positive", clean["uniform_feature_grid"] == 0,
     clean.get("uniform_feature_grid"))
case("sloppy: plain nested card is not a nested surface box",
     sloppy["nested_surfaces"] == 0, sloppy.get("nested_surfaces"))

print()
if FAILS:
    print(f"{len(FAILS)} failing: {FAILS}")
    sys.exit(1)
print("all fixtures pass")
