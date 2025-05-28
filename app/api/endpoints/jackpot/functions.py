import csv
import json
from typing import List

from sqlalchemy.orm import Session

from app.models.jackpot import Jackpot, Event
from app.schemas.jackpot import JackpotDetails
import pandas as pd


def save_to_csv(all_jackpot_details: List[JackpotDetails]):
    data = {
        "Date": [],
        "JackpotId": [],
        "Home": [],
        "Away": [],
        "Score": [],
        "Result": []
    }

    for jackpot_details in all_jackpot_details:
        data["Date"].extend([jackpot_details.Date] * len(jackpot_details.Events))
        data["JackpotId"].extend([jackpot_details.JackpotId] * len(jackpot_details.Events))
        data["Home"].extend([event.Home for event in jackpot_details.Events])
        data["Away"].extend([event.Away for event in jackpot_details.Events])
        data["Score"].extend([event.Score for event in jackpot_details.Events])
        data["Result"].extend([event.Result for event in jackpot_details.Events])

    df = pd.DataFrame(data)
    df.to_csv("jackpot_details.csv", index=False)


def save_to_json(all_jackpot_details: List[JackpotDetails]):
    with open("jackpot_details.json", "w") as json_file:
        json.dump([jackpot_details.dict() for jackpot_details in all_jackpot_details], json_file, indent=4)


def save_to_database(db: Session, jackpot_details: JackpotDetails, next_jackpot_details: JackpotDetails):
    try:
        # Save initial jackpot details
        jackpot = Jackpot(date=jackpot_details.Date, jackpot_id=jackpot_details.JackpotId,
                          next_jackpot_id=jackpot_details.NextJackpotId)
        db.add(jackpot)
        db.commit()
        db.refresh(jackpot)

        for event in jackpot_details.Events:
            event_db = Event(jackpot_id=jackpot.id, home=event.Home, away=event.Away, score=event.Score,
                             result=event.Result)
            db.add(event_db)

        # Save next jackpot details
        next_jackpot = Jackpot(date=next_jackpot_details.Date, jackpot_id=next_jackpot_details.JackpotId,
                               next_jackpot_id=next_jackpot_details.NextJackpotId)
        db.add(next_jackpot)
        db.commit()
        db.refresh(next_jackpot)

        for event in next_jackpot_details.Events:
            event_db = Event(jackpot_id=next_jackpot.id, home=event.Home, away=event.Away, score=event.Score,
                             result=event.Result)
            db.add(event_db)

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error saving to database: {e}")
    finally:
        db.close()


def parse_match_data(match):
    # Extract id, teams, and score
    match_id, teams = match['teams'].split(" ", 1)
    home_team, away_team = teams.split(" vs ")
    score = match['score']

    # Calculate result
    if score == "Postp":
        result = "postponed"
    elif "-" in score:
        home_score, away_score = map(int, score.split("-"))
        if home_score > away_score:
            result = "home"
        elif away_score > home_score:
            result = "away"
        else:
            result = "draw"
    else:
        result = "unknown"

    # Return structured data
    return {
        "id": int(match_id),
        "home": home_team.strip(),
        "away": away_team.strip(),
        "score": score,
        "result": result
    }


def save_matches_to_csv(matches, filename):
    # Specify the CSV file headers
    headers = ["date", "home_team", "away_team", "score", "result"]

    # Write the data to a CSV file
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=headers)
        writer.writeheader()  # Write the header row
        writer.writerows(matches)  # Write the match data rows

    print(f"Matches successfully saved to {filename}")

