"""
Run eval cases through the local scoring endpoint to inspect the similarity distribution.
"""

import json
import httpx
import argparse
from rich.console import Console
from rich.table import Table

def main(url: str):
    console = Console()
    with open("tests/eval_cases.json") as f:
        cases = json.load(f)

    from app.config import settings
    
    table = Table(title=f"Similarity Evaluation ({url}) | Threshold: {settings.SIMILARITY_THRESHOLD}")
    table.add_column("ID", style="cyan")
    table.add_column("Label", style="magenta")
    table.add_column("Score", justify="right", style="green")
    table.add_column("Judge", justify="center")
    table.add_column("Reason", style="dim")

    for case in cases:
        r = httpx.post(f"{url}/v1/outputs/score", json={"output_text": case["text"]}, timeout=60.0)
        if r.status_code != 200:
            console.print(f"[red]Error {r.status_code}[/red]: {r.text}")
            continue
            
        data = r.json()
        score = data.get("similarity_score", 0.0)
        verdict = data.get("judge_verdict", "N/A")
        reason = data.get("judge_reason", "")
        
        judge_display = verdict
        if verdict == "leak":
            judge_display = "[bold red]LEAK[/bold red]"
        elif verdict == "no_leak":
            judge_display = "[green]CLEAN[/green]"
            
        table.add_row(case["id"], case["label"], f"{score:.3f}", judge_display, reason)

    console.print(table)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000", help="API base URL")
    args = parser.parse_args()
    main(args.url)
