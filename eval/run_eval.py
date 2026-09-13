"""Evaluation harness for DiagnoZ.

Measures two things against the real running system (not unit tests with mocks):

1. Triage extraction accuracy - runs every scenario in scenarios.json's
   triage_scenarios through the actual app.services.llm_triage.analyze_appliance_issue()
   and checks appliance_type/urgency against the expected labels.

2. Dispatch KNN precision - for each dispatch_scenarios entry, creates real technician
   rows at the given coordinates (via direct DB writes, since there's no bulk-seed API),
   calls the real find_nearest_available_technician() PostGIS query, and checks it
   returned the expected technician (or None where none should be within radius).

Run inside the backend container so it can import app.* and reach the DB directly:
    docker cp eval/run_eval.py <backend-container>:/app/run_eval.py
    docker exec <backend-container> python run_eval.py
"""
import asyncio
import json
import uuid
from pathlib import Path

from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy import text

from app.core.database import SessionLocal
from app.models.technician import TechnicianProfile
from app.models.user import User
from app.services.llm_triage import analyze_appliance_issue
from app.services.spatial_matcher import find_nearest_available_technician

SCENARIOS_PATH = Path(__file__).parent / "scenarios.json"


def run_triage_eval(scenarios: list[dict]) -> dict:
    correct_appliance = 0
    correct_urgency = 0
    correct_both = 0
    failures = []

    for scenario in scenarios:
        result = asyncio.run(analyze_appliance_issue(scenario["transcript"]))
        appliance_ok = result["appliance_type"] == scenario["expected"]["appliance_type"]
        urgency_ok = result["urgency"] == scenario["expected"]["urgency"]

        if appliance_ok:
            correct_appliance += 1
        if urgency_ok:
            correct_urgency += 1
        if appliance_ok and urgency_ok:
            correct_both += 1
        else:
            failures.append(
                {
                    "id": scenario["id"],
                    "transcript": scenario["transcript"],
                    "expected": scenario["expected"],
                    "got": {"appliance_type": result["appliance_type"], "urgency": result["urgency"]},
                }
            )

    total = len(scenarios)
    return {
        "total": total,
        "appliance_type_accuracy": round(correct_appliance / total, 3),
        "urgency_accuracy": round(correct_urgency / total, 3),
        "both_correct_accuracy": round(correct_both / total, 3),
        "failures": failures,
    }


def run_dispatch_eval(scenarios: list[dict]) -> dict:
    """Runs against the live technician_profiles table. Any pre-existing technician rows
    (e.g. from manual/demo testing) are temporarily marked unavailable for the duration of
    the eval so they can't contaminate the KNN match, then restored - this eval must be
    correct regardless of what demo data already exists in the DB.
    """
    db = SessionLocal()
    correct = 0
    failures = []
    created_user_ids = []
    created_profile_ids = []

    pre_existing_available_ids = [
        row[0]
        for row in db.execute(
            text("SELECT id FROM technician_profiles WHERE is_available = TRUE")
        ).fetchall()
    ]
    if pre_existing_available_ids:
        db.execute(
            text("UPDATE technician_profiles SET is_available = FALSE WHERE id = ANY(:ids)"),
            {"ids": pre_existing_available_ids},
        )
        db.commit()

    try:
        for scenario in scenarios:
            name_to_user_id = {}
            scenario_profile_ids = []
            for tech in scenario["technicians"]:
                user = User(
                    full_name=f"Eval Technician {tech['name']}",
                    email=f"eval_{scenario['id']}_{tech['name']}@example.com",
                    phone_number=f"9{uuid.uuid4().int % 10**9:09d}",
                    role="TECHNICIAN",
                    hashed_password="not-used-in-eval",
                )
                db.add(user)
                db.flush()
                created_user_ids.append(user.id)
                name_to_user_id[tech["name"]] = user.id

                profile = TechnicianProfile(
                    user_id=user.id,
                    skills=[],
                    is_available=tech["is_available"],
                    current_location=from_shape(Point(tech["longitude"], tech["latitude"]), srid=4326),
                )
                db.add(profile)
                db.flush()
                created_profile_ids.append(profile.id)
                scenario_profile_ids.append(profile.id)

            db.commit()

            matched_user_id = find_nearest_available_technician(
                db, scenario["customer"]["longitude"], scenario["customer"]["latitude"]
            )

            expected_name = scenario["expected_match"]
            expected_user_id = name_to_user_id.get(expected_name) if expected_name else None

            if matched_user_id == expected_user_id:
                correct += 1
            else:
                matched_name = next(
                    (n for n, uid in name_to_user_id.items() if uid == matched_user_id), None
                )
                failures.append(
                    {
                        "id": scenario["id"],
                        "description": scenario["description"],
                        "expected_match": expected_name,
                        "got_match": matched_name,
                    }
                )

            # Isolate scenarios from each other: this scenario's fixtures must not be
            # visible to the KNN query in the NEXT scenario's assertion.
            db.execute(
                text("UPDATE technician_profiles SET is_available = FALSE WHERE id = ANY(:ids)"),
                {"ids": scenario_profile_ids},
            )
            db.commit()

        total = len(scenarios)
        return {
            "total": total,
            "precision": round(correct / total, 3) if total else 0,
            "failures": failures,
        }
    finally:
        # Clean up eval fixtures so re-runs stay idempotent and don't pollute demo data.
        for profile_id in created_profile_ids:
            db.execute(text("DELETE FROM technician_profiles WHERE id = :id"), {"id": profile_id})
        for user_id in created_user_ids:
            db.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
        # Restore whatever was available before this eval run touched it.
        if pre_existing_available_ids:
            db.execute(
                text("UPDATE technician_profiles SET is_available = TRUE WHERE id = ANY(:ids)"),
                {"ids": pre_existing_available_ids},
            )
        db.commit()
        db.close()


def main():
    scenarios = json.loads(SCENARIOS_PATH.read_text())

    print("=== Triage Extraction Accuracy ===")
    triage_results = run_triage_eval(scenarios["triage_scenarios"])
    print(json.dumps(triage_results, indent=2))

    print("\n=== Dispatch KNN Precision ===")
    dispatch_results = run_dispatch_eval(scenarios["dispatch_scenarios"])
    print(json.dumps(dispatch_results, indent=2))


if __name__ == "__main__":
    main()
