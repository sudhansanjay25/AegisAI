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
    table.add_column("Risk", justify="right")
    table.add_column("Policy", justify="center")

    for case in cases:
        r = httpx.post(f"{url}/v1/outputs/score", json={"output_text": case["text"]}, timeout=60.0)
        if r.status_code != 200:
            console.print(f"[red]Error {r.status_code}[/red]: {r.text}")
            continue
            
        data = r.json()
        score = data.get("similarity_score", 0.0)
        verdict = data.get("judge_verdict", "N/A")
        risk = data.get("risk_score", 0.0)
        policy = data.get("policy_action", "N/A")
        
        judge_display = verdict
        if verdict == "leak":
            judge_display = "[bold red]LEAK[/bold red]"
        elif verdict == "no_leak":
            judge_display = "[green]CLEAN[/green]"
            
        policy_display = policy
        if policy == "block":
            policy_display = "[bold red]BLOCK[/bold red]"
        elif policy == "human_review":
            policy_display = "[yellow]REVIEW[/yellow]"
        elif policy == "redact":
            policy_display = "[orange3]REDACT[/orange3]"
        elif policy == "allow":
            policy_display = "[green]ALLOW[/green]"
            
        table.add_row(case["id"], case["label"], f"{score:.3f}", judge_display, f"{risk:.1f}", policy_display)

    console.print(table)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000", help="API base URL")
    args = parser.parse_args()
    main(args.url)
