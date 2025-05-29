# jackpot.py
from typing import List

from fastapi import APIRouter, Depends, HTTPException

# sqlalchemy
from sqlalchemy.orm import Session

import requests
from starlette.responses import JSONResponse

from app.api.endpoints.jackpot.functions import save_to_csv, save_to_database, save_to_json, save_matches_to_csv
from app.api.endpoints.jackpot.scraplinks import scrape_all_links
# import
from app.schemas.jackpot import JackpotDetails, EventModel
from app.core.dependencies import get_db
from bs4 import BeautifulSoup

jackpot_module = APIRouter()

BASE_URL = "https://footballplatform.com/category/mozzart-bet-jackpot/page/"


@jackpot_module.get("/fetch-jackpot-details", response_model=List[JackpotDetails])
async def fetch_jackpot_details(db: Session = Depends(get_db)):
    initial_jackpot_id = "528371ab-d123-4978-a136-383eb6c99da0"
    all_jackpot_details = []

    def fetch_and_process_jackpot(jackpot_id):
        url = f"https://jackpot-betslip.ke.sportpesa.com/api/jackpots/history/{jackpot_id}/details"
        response = requests.get(url)
        data = response.json()
        print(jackpot_id)

        finished_date = data.get("finished", "")
        jackpot_human_id = data.get("jackpotHumanId", "")
        next_jackpot = data.get("nextJackpot")
        next_jackpot_id = next_jackpot.get("jackpotId") if next_jackpot else None

        events = []
        for event in data.get("events", []):
            home = event.get("competitorHome", "")
            away = event.get("competitorAway", "")
            score = event.get("score", "")
            result = event.get("resultPick", "")
            events.append(EventModel(Home=home, Away=away, Score=score, Result=result))

        jackpot_details = JackpotDetails(
            Date=finished_date,
            JackpotId=jackpot_human_id,
            Events=events,
            NextJackpotId=next_jackpot_id
        )

        all_jackpot_details.append(jackpot_details)

        if next_jackpot_id:
            fetch_and_process_jackpot(next_jackpot_id)

    fetch_and_process_jackpot(initial_jackpot_id)

    # Save to CSV
    save_to_csv(all_jackpot_details)

    # Save to JSON
    save_to_json(all_jackpot_details)

    # Save to database
    # save_to_database(all_jackpot_details)

    # return all_jackpot_details[0]  # Return the first jackpot details as the response
    return all_jackpot_details  # Return the first jackpot details as the response


@jackpot_module.get("/scrape-links/")
async def scrape_links(start_page: int = 1, end_page: int = 38):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        all_links = []
        print("Processing Links ...")
        for page in range(start_page, end_page + 1):
            url = f"{BASE_URL}{page}/"
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, "html.parser")
                titles = soup.select(".entry-title a")
                links = [title['href'] for title in titles if title.has_attr('href')]
                all_links.extend(links)
            else:
                return JSONResponse(
                    content={"error": f"Failed to retrieve page {page}"},
                    status_code=500
                )

        print(all_links)
        # Scrape all links
        all_match_data = scrape_all_links(all_links)

        save_matches_to_csv(all_match_data, "mozzart-bet-jackpot5.csv")
        # Output the scraped data
        # for match in all_match_data:
        #     print(match)
        return {"links": all_links}
    except Exception as e:
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )
