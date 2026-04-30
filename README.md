# Tyler-Young-Comp5700-Project

## Objectives

### Extract and Structure Requirements

`generate_requirements.py` parses `CFR-117.130.md` and generates requirements based on the hazard analysis rules (saved to `requirements.json`).
Script also generates `expected_structure.json`, outlining the format of the parent and children included in the requirements.

### Generate Minimal Test Cases

`10_selected_rules.txt` are used to generate test cases via LLM's used in `generate_test_cases.py`. These selected rules can be changed are are derived from `expected_structure.json`.

### Verification and Validation

Utilizing GitHub actions, `validate.py` and `verify.py` are run on `test_cases.json` each time a new commit is pushed to the repo.

## Reproducibility  

### Generate Requirements
Download `generate_requirements.py` and `CFR-117.130.md` to local environment
Run script with the following command, replacing inputs as necessary : 
- python generate_requirements.py --input "Input (CFR) markdown file" --output "Output file name" --cfr "CFR section to reference" --expected "Output file name"
