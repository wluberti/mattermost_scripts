import csv
import argparse
import re
import sys
from typing import List, Dict

def parse_args():
    parser = argparse.ArgumentParser(description="Transform members export CSV to users.csv format.")
    parser.add_argument("input_file", nargs="?", default="clubcollect.csv", help="Path to input CSV (semicolon separated, default: clubcollect.csv)")
    parser.add_argument("--output", default="users.csv", help="Path to output CSV (default: users.csv)")
    return parser.parse_args()

def parse_labels(labels_str: str) -> (str, List[str]):
    """
    Parses 'Labels' field.
    Team: Single letter, or Letter+Digit (e.g., H1, D, A2).
    Tags: All other labels (filtered by allow list).
    """
    if not labels_str:
        return "", []

    parts = [p.strip() for p in labels_str.split("^") if p.strip()]

    team = ""
    tags = []

    team_regex = re.compile(r"^[A-Za-z]\d?$") # Single letter or Letter+Digit

    # Allowed tags (case-insensitive for checking)
    ALLOWED_TAGS = {'trainer', 'tientjeslid', 'trainingmember', 'captain', 'tc', 'bestuur'}

    # Check for 'recreant' priority
    recreant_match = next((p for p in parts if "recreant" in p.lower()), None)
    if recreant_match:
        team = "recreant"

    for part in parts:
        # If this part was the one containing recreant, skip adding it to tags
        if recreant_match and part == recreant_match:
            continue

        # If we haven't found a team yet (recreant wasn't there), and this looks like a team, take it.
        if not team and team_regex.match(part):
            team = part
        else:
            # Check allow list
            if part.lower() in ALLOWED_TAGS:
                tags.append(part)

    return team, tags

def main():
    args = parse_args()

    output_rows = []

    try:
        with open(args.input_file, mode='r', encoding='utf-8-sig') as infile:
            # Semicolon separated
            reader = csv.DictReader(infile, delimiter=';')

            for row in reader:
                # Extract fields
                firstname = row.get("Voornaam", "").strip()

                tussenvoegsel = row.get("Tussenvoegsel", "").strip()
                achternaam = row.get("Achternaam", "").strip()
                lastname = f"{tussenvoegsel} {achternaam}".strip()

                email = row.get("E-mailadres voor contact", "").strip()

                labels = row.get("Labels", "")
                team, tags_list = parse_labels(labels)

                # Add "Extern lidnummer" if present
                extern_lidnummer = row.get("Extern lidnummer", "").strip()
                if extern_lidnummer:
                    tags_list.append(extern_lidnummer)

                if email:
                    output_rows.append({
                        "firstname": firstname,
                        "lastname": lastname,
                        "email": email,
                        "team": team,
                        "tags": ",".join(tags_list)
                    })

    except FileNotFoundError:
        print(f"Error: Input file '{args.input_file}' not found.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error processing file: {e}", file=sys.stderr)
        sys.exit(1)

    # Write output
    fieldnames = ["firstname", "lastname", "email", "team", "tags"]

    outfile = sys.stdout
    if args.output and args.output != "stdout":
        try:
            outfile = open(args.output, "w", encoding='utf-8', newline='')
        except OSError as e:
            print(f"Error opening output file: {e}", file=sys.stderr)
            sys.exit(1)

    try:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)
    finally:
        if outfile is not sys.stdout:
            outfile.close()

if __name__ == "__main__":
    main()
