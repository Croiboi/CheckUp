import json
import sys
from pathlib import Path

from api import TEAMS, app

folder = Path(__file__).with_name("roster_snapshots")
folder.mkdir(exist_ok=True)

with app.test_client() as client:
    for team in sys.argv[1:] or TEAMS:
        response = client.get(f"/api/team/{team}/roster")
        data = response.get_json()
        if (
            response.status_code == 200 and data
            and data["players"] and not data["averagesUnavailable"]
        ):
            (folder / f"{team}.json").write_text(json.dumps(data), encoding="utf-8")
            print(f"Saved {team}")
        else:
            print(f"Skipped {team}. Kept any existing snapshot.")
