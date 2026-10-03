#scraplinks.py
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

LEFT_CELL_PATTERN = re.compile(r'text-align:\s*left\s*!important')


POSTPONED_VALUES = ("postp", "postponed", "ppd")
ABANDONED_VALUES = ("abn", "abandoned")


def is_score_like(value):
    return bool(re.match(r"^\d+\s*-\s*\d+$", value)) or value.lower() in POSTPONED_VALUES + ABANDONED_VALUES


def classify_result(score):
    if score.lower() in POSTPONED_VALUES:
        return "postponed"
    elif score.lower() in ABANDONED_VALUES:
        return "abandoned"
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


def normalize_score(value):
    # Site uses en-dashes ("2–1"), trailing dots ("Postp."), and occasional
    # decimal typos ("2.2" meaning 2-2).
    value = value.strip().rstrip('.').replace('\u2013', '-').replace('\u2014', '-')
    value = re.sub(r"^(\d+)\.(\d+)$", r"\1-\2", value)
    return value or "Abn"


def split_teams(text):
    # Site typos: missing spaces ("Masjedvs Zob", "K.S.vs"), nbsp separators,
    # capital "Vs". Prefer the spaced separator so clubs whose name embeds "VS"
    # ("AVS vs Nacional") are not split inside the word. Returns [home, away] or None.
    text = text.replace('\u00A0', ' ').strip()
    parts = re.split(r"(?i)\s+vs\.?\s+", text, maxsplit=1)
    if len(parts) != 2:
        parts = re.split(r"(?i)\s*vs\.?\s*", text, maxsplit=1)
    return [p.strip() for p in parts] if len(parts) == 2 else None


def scrape_table_from_link(link):
    try:
        response = requests.get(link, headers=HEADERS)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        date = extract_date(link)
        matches = []
        seen_rows = set()
        for row in soup.find_all('tr'):
            try:
                # Templates differ: new pages use classed cells; older pages use a
                # style-based team cell with <b>, sometimes with extra leading cells.
                # score/odds/bet/pick are always the 4 cells after the team cell.
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
                    team_cell = legacy

                team_names = split_teams(teams_text)
                if team_names is None:
                    continue

                tds = row.find_all('td')
                rest = tds[tds.index(team_cell) + 1:]

                def cell_text(index):
                    return rest[index].get_text(' ', strip=True) if len(rest) > index else ""

                score = normalize_score(cell_text(0))
                if not is_score_like(score):
                    alt = normalize_score(cell_text(1))
                    score = alt if is_score_like(alt) else score

                match = {
                    "date": date,
                    "home_team": clean_team_name(team_names[0]),
                    "away_team": clean_team_name(team_names[1]),
                    "league": league,
                    "score": score,
                    "odds": cell_text(1),
                    "bet_type": cell_text(2),
                    "pick": cell_text(3),
                    "result": classify_result(score),
                }
                # Some 2023 pages repeat the same block twice; skip exact duplicates.
                key = tuple(match.values())
                if key in seen_rows:
                    continue
                seen_rows.add(key)
                matches.append(match)
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
        # Slugs use full ("august") or abbreviated ("aug", "sep") month names.
        for fmt in ("%d-%B-%Y", "%d-%b-%Y"):
            try:
                return datetime.strptime(date_str, fmt).strftime("%d-%m-%Y")
            except ValueError:
                continue
        return f"Invalid date format: {date_str}"
    else:
        return "No date found"


def clean_team_name(team_name):
    # Drop the row-number prefix ("3 – Guanacasteca" -> "Guanacasteca")
    team_name = re.sub(r"^\d+\s*[–-]\s*", "", team_name)
    # Remove numbers and any non-breaking spaces
    cleaned_name = re.sub(r"^\d+\s+|(\u00A0|\s)+", " ", team_name)
    # Strip leading and trailing spaces
    return cleaned_name.strip()
