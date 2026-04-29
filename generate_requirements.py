import json
import re
import argparse

# ---------- Arguments ----------
parser = argparse.ArgumentParser(description="Generate requirement JSON from CFR Markdown")
parser.add_argument("--input", "-i", required=True, help="Input Markdown file (.md)")
parser.add_argument("--output", "-o", required=True, help="Output JSON file for requirements")
parser.add_argument("--cfr", "-c", required=True, help="CFR section (e.g., 21 CFR 117.130)")
parser.add_argument("--expected", "-e", default="expected_structure.json", help="Output JSON file for expected structure")
args = parser.parse_args()

INPUT_MD = args.input
OUTPUT_JSON = args.output
CFR_SECTION = args.cfr
EXPECTED_JSON = args.expected

# ---------- Read File ----------
with open(INPUT_MD, "r", encoding="utf-8") as f:
    lines = [line.strip() for line in f if line.strip()]

requirements = []
current_req = None

# Dictionary for expected structure: parent -> list of child letters
expected_structure = {}

# ---------- Parse ----------
for line in lines:
    # Capture REQ ID
    req_match = re.search(r"→\s*(REQ-[\d\.]+-\d+)", line)
    if req_match:
        current_req = req_match.group(1)
        # Initialize empty list for this parent in expected_structure
        if current_req not in expected_structure:
            expected_structure[current_req] = []
        continue

    # Capture atomic rules
    atomic_match = re.match(r"^(.*?)\s*→\s*([A-Z]\d*)$", line)
    if atomic_match and current_req:
        description = atomic_match.group(1).strip()
        suffix = atomic_match.group(2)

        requirement_id = f"{current_req}{suffix}"

        # Parent logic
        if len(suffix) == 1:
            parent = current_req
            # Add to expected_structure (only single letters at top level)
            if suffix not in expected_structure[current_req]:
                expected_structure[current_req].append(suffix)
        else:
            parent = f"{current_req}{suffix[0]}"
            # For nested rules (A1, B2), add to their immediate parent
            parent_key = parent
            child_letter = suffix
            if parent_key not in expected_structure:
                expected_structure[parent_key] = []
            if child_letter not in expected_structure[parent_key]:
                expected_structure[parent_key].append(child_letter)

        requirements.append({
            "requirement_id": requirement_id,
            "description": description,
            "source": CFR_SECTION,
            "parent": parent
        })

# Sort the child letters for each parent in expected_structure
for parent in expected_structure:
    expected_structure[parent].sort()

# ---------- Save Requirements ----------
with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
    json.dump(requirements, f, indent=2)

print(f"Saved {len(requirements)} requirements → {OUTPUT_JSON}")

# ---------- Save Expected Structure ----------
with open(EXPECTED_JSON, "w", encoding="utf-8") as f:
    json.dump(expected_structure, f, indent=2)

print(f"Saved expected structure with {len(expected_structure)} parents → {EXPECTED_JSON}")
