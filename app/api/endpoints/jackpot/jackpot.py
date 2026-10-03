# jackpot.py
from typing import List
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup
from fastapi import APIRouter, Depends, HTTPException

# sqlalchemy
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

from app.api.endpoints.jackpot.functions import (
    save_matches_to_csv,
    save_to_csv,
    save_to_database,
    save_to_json,
)
from app.api.endpoints.jackpot.scraplinks import scrape_all_links
from app.core.dependencies import get_db

# import
from app.schemas.jackpot import EventModel, JackpotDetails

jackpot_module = APIRouter()

ARCHIVE_URL = "https://footballplatform.com/archive/"

# The Sportpesa API is behind Akamai Bot Manager: plain requests get 403 and a
# browser User-Agent alone gets a JS-challenge page instead of JSON. Refresh these
# values from a logged browser session (DevTools > copy as cURL) when they expire.
SPORTPESA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) QoderApp/0.3.4 Chrome/150.0.7871.114 Electron/43.1.1 Safari/537.36",
    "Accept": "application/json",
}
SPORTPESA_COOKIES = {
    "bm_so": "3AC865D4857DC06A379E2CB623DD214EE7BEEDEF18E7691322F10B31FE30C213~YAAQZqERAj19GfSgAQAA1lFIAQkbi/ojlLO+rs/2Jp21V/WnqJYEc6If61WMsUzkh7IQPVcwqXc8Nr1oIzoeyWUkr0kWg8eiRmEeWmG4M/r3ZcRgN7Fk8piReHqe9ThtjU/uEJCvk56RmRPxU7aYBS+G0MJhFVWqdmkpiMlC3+4XqCRF8J4u88zV6bhKdYbIi4yNj0OzOqQCRoqikOaqEntL11n9Hs4/zjSaCqt8n2FYOxk1cXapRqYzX+IIkVAQkzYcg3EaDqpeqUKwAc6cuGrBB4yp7wXb7r92pS8ED1OixCH8woZgUdItbTSqS0Hw5e3nyJgmME9s8BE7g2+uhNE9V0ho4UiSYYT4xgAEpUYPC4bO2+fIrmppwEUcGm6uFO4XZKX9eLnxduhwQJFfr3QDsxn0FM/17eP19oShn9ntuPbq4fHbw9yPOTflLWeaRMYwNf0EVlprisrEzEtF/6zo4Pd5bzCAtOxDkd3IJc0QDwoYhypi~2",
    "bm_sv": "1D9DA4DEFF9FABC3427C312CD0ACEECB~YAAQZqERAj59GfSgAQAA1lFIAQGEbKyHE+vPcw2b/g9gRpSJy+s0AdZqyeVw4KKTRaGp6t55JFhhM1815iz0730uKgVkFmIxJYy0BhEe4eFBP30wwEzpP1V0st4CNGm8RttSrqJAEqrO6+md3CACJajft/6bvO4vYWrU5K1Jyo0/+Qah3lun9pywVNoEVMTH3UPfvngiGhay73eDEXJS715gEotArWDPcQ59Vsmn40SuiEriJveuZU2T1HOGJCpt8ej9V/UrxSpAf3H5PYv14A==~1",
}


@jackpot_module.get("/fetch-jackpot-details", response_model=List[JackpotDetails])
async def fetch_jackpot_details(db: Session = Depends(get_db)):
    # jackpotHumanId 1 (oldest finished jackpot); the chain is crawled forward via nextJackpot.
    initial_jackpot_id = "6ab8a2c7-f7a3-419d-8303-d7898ebbe6a5"
    all_jackpot_details = []

    def fetch_and_process_jackpot(jackpot_id):
        url = f"https://jackpot-betslip.ke.sportpesa.com/api/jackpots/history/{jackpot_id}/details"
        response = requests.get(url, headers=SPORTPESA_HEADERS, cookies=SPORTPESA_COOKIES, timeout=30)
        if "json" not in response.headers.get("content-type", ""):
            raise HTTPException(
                status_code=503,
                detail="Sportpesa returned an anti-bot challenge page; refresh SPORTPESA_COOKIES/HEADERS in jackpot.py",
            )
        response.raise_for_status()
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
async def scrape_links(
    start_page: int = 1,
    end_page: int = 1,
    source: str = "betika mega",
    filename: str = "betika-mega-jackpot.csv",
):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        all_links = []
        seen = set()
        print("Processing Links ...")
        for page in range(start_page, end_page + 1):
            url = f"{ARCHIVE_URL}?paged={page}&tp_s={quote_plus(source)}&tp_pp=100&tp_date&tp_cat"
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, "html.parser")
                titles = soup.select(".tp-tips-archive-list a[href]")
                links = [title['href'] for title in titles]
                for link in links:
                    if link not in seen:
                        seen.add(link)
                        all_links.append(link)
            else:
                return JSONResponse(
                    content={"error": f"Failed to retrieve page {page}"},
                    status_code=500
                )

        # Scrape all links
        all_match_data = scrape_all_links(all_links)

        save_matches_to_csv(all_match_data, filename)
        return {
            "source": source,
            "pages": end_page - start_page + 1,
            "links": len(all_links),
            "matches": len(all_match_data),
            "file": filename,
        }
    except Exception as e:
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )
