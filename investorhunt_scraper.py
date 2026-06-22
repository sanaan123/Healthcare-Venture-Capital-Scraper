import asyncio
import aiohttp
from bs4 import BeautifulSoup
import pandas as pd
import time
# Scrapes healthcare VC firms from investorhunt.co
# Outputs structured CSV dataset
BASE_URL = "https://investorhunt.co"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
}
OUTPUT_PATH = "/Users/theguy/Desktop/stuff/investorhunt.csv"
TOTAL_PAGES = 42
MAX_CONCURRENT = 10  # max simultaneous requests


async def scrape_detail_page(session, url, semaphore):
    """
    Visits an investor's detail page and extracts
    their investment stages and past investments.
    """
    async with semaphore:
        try:
            async with session.get(url) as response:
                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")

                #Stages
                stages = "N/A"
                cards = soup.find_all("div", class_="styles_card__uoKHy")
                for card in cards:
                    label = card.find("p", class_="styles_label__hYqgu")
                    if label and label.get_text(strip=True) == "Stages":
                        stage_parts = card.find_all("p", class_="styles_location__j0Ib1")
                        stages = ", ".join([
                            p.get_text(strip=True).strip(",")
                            for p in stage_parts
                        ])

                #Past investments
                investments_div = soup.find("div", class_="styles_pastInvestments__YBcSu")
                if investments_div:
                    items = investments_div.find_all("p", class_="styles_label__hYqgu")
                    past_investments = ", ".join([i.get_text(strip=True) for i in items[:5]])
                else:
                    past_investments = "N/A"

                return stages, past_investments

        except Exception as e:
            print(f"    ✗ Detail failed {url}: {e}")
            return "N/A", "N/A"


async def scrape_listing_page(session, page, semaphore):
    """
    Scrapes one listing page and returns a list of investor dicts.
    For each investor found, also visits their detail page.
    """
    url = f"{BASE_URL}/markets/health-care?page={page}"
    investors_on_page = []

    async with semaphore:
        try:
            async with session.get(url) as response:
                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")
                cards = soup.find_all("div", class_="styles_card__XZbp2")

                if not cards:
                    print(f"  ⚠ No cards found on page {page + 1}")
                    return []

                print(f"  Found {len(cards)} investors on page {page + 1}")

                # build detail page tasks for all investors on this page
                detail_tasks = []
                card_data = []

                for card in cards:
                    #Name
                    name_tag = card.find("p", class_="styles_fullName__ooMWO")
                    name = name_tag.get_text(strip=True) if name_tag else "N/A"

                    #Location
                    location_div = card.find("div", class_="styles_locations__Z_Ar4")
                    if location_div:
                        loc_parts = location_div.find_all("p", class_="styles_location__j0Ib1")
                        location = " ".join([
                            p.get_text(strip=True).strip(",")
                            for p in loc_parts
                        ])
                    else:
                        location = "N/A"

                    #Markets (visible only)
                    markets_div = card.find("div", class_="styles_markets__LnVU_")
                    if markets_div:
                        visible = markets_div.find_all(
                            "div",
                            class_="styles_market__DIjfR",
                            attrs={"data-hidden": "false"}
                        )
                        markets = ", ".join([m.get_text(strip=True) for m in visible])
                    else:
                        markets = "N/A"

                    #Investor types
                    all_loc_divs = card.find_all("div", class_="styles_locations__Z_Ar4")
                    investor_types = "N/A"
                    if len(all_loc_divs) > 1:
                        type_parts = all_loc_divs[-1].find_all("p", class_="styles_location__j0Ib1")
                        investor_types = ", ".join([
                            p.get_text(strip=True).strip(",")
                            for p in type_parts
                        ])

                    #Detail link
                    detail_tag = card.find("a", class_="styles_button__ANfa_")
                    detail_link = BASE_URL + detail_tag["href"] if detail_tag else None

                    card_data.append({
                        "name": name,
                        "location": location,
                        "investment_focus": markets,
                        "investor_type": investor_types,
                        "detail_link": detail_link,
                    })

                    # queue up detail page request
                    if detail_link:
                        detail_tasks.append(
                            scrape_detail_page(session, detail_link, semaphore)
                        )
                    else:
                        detail_tasks.append(asyncio.coroutine(lambda: ("N/A", "N/A"))())

                # fire all detail requests concurrently for this page
                detail_results = await asyncio.gather(*detail_tasks)

                # combine listing + detail data
                for i, investor in enumerate(card_data):
                    stages, past_investments = detail_results[i]
                    investors_on_page.append({
                        "name": investor["name"],
                        "location": investor["location"],
                        "investment_focus": investor["investment_focus"],
                        "investor_type": investor["investor_type"],
                        "stage_focus": stages,
                        "portfolio_examples": past_investments,
                        "source_link": investor["detail_link"] or "N/A",
                    })
                    print(f"    ✓ {investor['name']}")

        except Exception as e:
            print(f"  ✗ Failed page {page + 1}: {e}")

    return investors_on_page


async def main():
    semaphore = asyncio.Semaphore(20)
    all_investors = []

    start = time.time()

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        # process pages one at a time so we see output as we go
        for page in range(0, TOTAL_PAGES):
            print(f"\n--- Scraping page {page + 1}/42 ---")
            result = await scrape_listing_page(session, page, semaphore)
            all_investors.extend(result)

    elapsed = round(time.time() - start, 2)
    print(f"\nFinished in {elapsed}s")
    print(f"Total investors scraped: {len(all_investors)}")

    df = pd.DataFrame(all_investors)
    df.drop_duplicates(subset="name", inplace=True)
    df.replace("N/A", pd.NA, inplace=True)

    print("\nNull counts per column:")
    print(df.isnull().sum())

    df.to_csv(OUTPUT_PATH, index=False)
    print(f"\nSaved to {OUTPUT_PATH}")


asyncio.run(main())