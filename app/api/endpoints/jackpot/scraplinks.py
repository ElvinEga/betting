#scraplinks.py
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup


def scrape_table_from_link(link):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        # Send a GET request to the link
        response = requests.get(link, headers=headers)
        response.raise_for_status()

        # Parse the HTML content
        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract all rows with match data
        # rows = soup.find_all('tr', role="row")
        tbody = soup.find('tbody')
        matches = []
        date = extract_date(link)
        print(date)
        style_pattern = re.compile(r'text-align:\s*left\s*!important')
        # Loop through each row and extract relevant data
        for row in tbody.find_all('tr'):
            try:
                if "group" in row.get("class", []) or not row.find_all("td"):
                    continue

                # team_cell = row.find('td', style='text-align:left!important')
                team_cell = row.find('td', style=style_pattern)
                score_info = row.find_all('td')[2].text.strip()  # The score is in the second <td> after the team names
                # score_cell = row.find_all('td')[3]  # Betika
                fallback_info = row.find_all('td')[3].text.strip()

                # print(score_cell)
                # Extract the team names and score
                team_names = team_cell.find('b').get_text(strip=True).split(' vs ')
                # score = score_cell.get_text(strip=True)

                if re.match(r"^\d+-\d+$", score_info):  # Check if score is in "1-2" format
                    score = score_info
                else:
                    score = fallback_info

                # Determine the result
                if score.lower() == "postp":
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

                # Append the data to the list
                matches.append({
                    "date": date,
                    "home_team": clean_team_name(team_names[0]),
                    "away_team": clean_team_name(team_names[1]),
                    "score": score,
                    "result": result,
                })
            except Exception as e:
                print(f"Error processing row: {e}")
        # print(matches)
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


# Example: List of links
# all_links = [
#     "https://example.com/page1",
#     "https://example.com/page2",
#     # Add more links here
# ]


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
