#scraplinks.py
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

LEFT_CELL_PATTERN = re.compile(r'text-align:\s*left\s*!important')


def classify_result(score):
    if score.lower() in ("postp", "postponed", "ppd"):
        return "postponed"
    elif re.match(r"^\d+\s*-\s*\d+$", score):
        home_score, away_score = map(int, re.split(r"\s*-\s*", score))
        if home_score > away_score:
            return "home"
        elif away_score > home_score:
            return "away"
        else:
            return "draw"
    else:
        return "unknown"


def scrape_table_from_link(link):
    try:
        response = requests.get(link, headers=HEADERS)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        date = extract_date(link)
        matches = []
        for row in soup.find_all('tr'):
            try:
                # New template: classed cells. Legacy template: style-based team cell with <b>.
                team_cell = row.find('td', class_='ha-cell')
                league = ""
                if team_cell:
                    main = team_cell.find('span', class_='ha-main')
                    if main is None:
                        continue
                    teams_text = main.get_text(strip=True)
                    sub = team_cell.find('span', class_='ha-sub')
                    if sub:
                        flag = sub.find('span', class_='flag-emoji')
                        if flag:
                            flag.extract()
                        league = sub.get_text(' ', strip=True)
                else:
                    legacy = row.find('td', style=LEFT_CELL_PATTERN)
                    if legacy is None or legacy.find('b') is None:
                        continue
                    teams_text = legacy.find('b').get_text(strip=True)

                team_names = teams_text.split(' vs ')
                if len(team_names) != 2:
                    continue

                tds = row.find_all('td')

                def cell_text(index):
                    return tds[index].get_text(' ', strip=True) if len(tds) > index else ""

                score_cell = row.find('td', class_='score-cell')
                score = score_cell.get_text(' ', strip=True) if score_cell else cell_text(2)
                if not re.match(r"^\d+\s*-\s*\d+$", score) and score.lower() not in ("postp", "postponed", "ppd"):
                    score = cell_text(3) or score

                matches.append({
                    "date": date,
                    "home_team": clean_team_name(team_names[0]),
                    "away_team": clean_team_name(team_names[1]),
                    "league": league,
                    "score": score,
                    "odds": cell_text(3),
                    "bet_type": cell_text(4),
                    "pick": cell_text(5),
                    "result": classify_result(score),
                })
            except Exception as e:
                print(f"Error processing row: {e}")
        return matches
    except Exception as e:
        print(f"Error fetching link {link}: {e}")
        return []


def scrape_all_links(links):
    all_data = []
    for link in links:
        print(f"Scraping link: {link}")
        data = scrape_table_from_link(link)
        all_data.extend(data)
    return all_data


def extract_date(url):
    # Regular expression to match the date pattern
    date_pattern = r"(\d{1,2}-[a-zA-Z]+-\d{4})"
    match = re.search(date_pattern, url)

    if match:
        date_str = match.group(1)  # Extract the matched date string
        # Convert the date string to a proper date format (optional)
        try:
            date_obj = datetime.strptime(date_str, "%d-%B-%Y")
            return date_obj.strftime("%d-%m-%Y")  # Return formatted date
        except ValueError as e:
            return f"Invalid date format: {e}"
    else:
        return "No date found"


def clean_team_name(team_name):
    # Remove numbers and any non-breaking spaces
    cleaned_name = re.sub(r"^\d+\s+|(\u00A0|\s)+", " ", team_name)
    # Strip leading and trailing spaces
    return cleaned_name.strip()
