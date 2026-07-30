"""
Seed script — uploads all files in seed_data/ to the vault endpoint.

Usage:
    python scripts/seed_vault.py [--url http://localhost:8000]
"""

import argparse
import os
import sys

import requests


def seed_vault(base_url: str, seed_dir: str = "seed_data"):
    """Upload all files in seed_dir to the vault endpoint."""
    endpoint = f"{base_url}/v1/vault/documents"
    files = sorted(os.listdir(seed_dir))

    if not files:
        print(f"No files found in {seed_dir}/")
        sys.exit(1)

    print(f"Seeding vault at {endpoint} with {len(files)} files...\n")

    sensitivity_map = {
        "employee_record.txt": "pii",
        "medical_record.txt": "hipaa",
        "board_strategy_memo.txt": "confidential",
        "financial_report.csv": "financial",
        "customer_database.txt": "pii",
        "security_incident_report.txt": "internal",
    }

    for filename in files:
        filepath = os.path.join(seed_dir, filename)
        if not os.path.isfile(filepath):
            continue

        tag = sensitivity_map.get(filename, "restricted")
        print(f"  Uploading: {filename} (tag={tag})...", end=" ")

        with open(filepath, "rb") as f:
            response = requests.post(
                endpoint,
                files={"file": (filename, f)},
                params={"sensitivity_tag": tag},
            )

        if response.status_code == 200:
            data = response.json()
            print(f"✅ doc_id={data['document_id']}, chunks={data['chunks_created']}")
        else:
            print(f"❌ {response.status_code}: {response.text}")

    print("\nDone!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed the AegisAI vault")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of the API")
    args = parser.parse_args()
    seed_vault(args.url)
