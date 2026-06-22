from bs4 import BeautifulSoup
import requests
import pandas as pd
import time
# Scrapes healthcare VC firms from vcsheet.com
# Outputs structured CSV dataset
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
}

base_url = "https://www.vcsheet.com"
all_firms = []

# Extract portfolio companies from investments section
def get_portfolio(soup):
    investments_section = soup.find("div", id="investments")

    if not investments_section:
        return "N/A"

    names = investments_section.select("div.profile-row-name")

    cleaned = [
        n.get_text(strip=True)
        for n in names
        if n.get_text(strip=True)
    ]

    cleaned = list(dict.fromkeys(cleaned))

    return ", ".join(cleaned[:5]) if cleaned else "N/A"
def get_stat(soup, label_text):
    label = soup.find("div", class_="filters-label", string=label_text)
    if not label:
        return "N/A"
    parent = label.find_parent("div", class_="fund-stat-block")
    if not parent:
        return "N/A"
    pills = parent.select("div.w-dyn-item div")
    if pills:
        return ", ".join([p.get_text(strip=True) for p in pills])
    text = parent.find("div", class_="fund-stat-text")
    return text.get_text(strip=True) if text else "N/A"
start = time.time()
response = requests.get('https://www.vcsheet.com/sheet/healthcare-funds', headers=headers)
print(f"Status: {response.status_code}")

soup = BeautifulSoup(response.text, "html.parser")
investors = soup.find_all("a", class_="data-item-block")

count = 0

for investor in investors:
    
    link = investor.get("href")
    if not link or "/fund/" not in link:
        continue

    name_div = investor.select_one('div[data-search-field="name"]')
    firm_name = name_div.get_text(strip=True) if name_div else "N/A"
    full_link = base_url + link
    count += 1

    try:
        detail_response = requests.get(full_link, headers=headers)
        detail_soup = BeautifulSoup(detail_response.text, "html.parser")
        website = detail_soup.find("a", class_="website")

        firm_data = {
            "firm_name": firm_name,
            "website": website['href'] if website else "N/A",
            "stage_focus": get_stat(detail_soup, "Stages they invest in"),
            "investment_focus": get_stat(detail_soup, "Sectors they invest in"),
            "avg_check_size": get_stat(detail_soup, "Avg Check size"),
            "location": get_stat(detail_soup, "Location"),
            "geographies": get_stat(detail_soup, "Geographies They Invest in"),
            "can_lead": get_stat(detail_soup, "Can They Lead?"),
            "source_link": full_link,
            "portfolio_examples": get_portfolio(detail_soup),
        }

        all_firms.append(firm_data)
        print(f"✓ {firm_name}")

    except Exception as e:
        print(f"✗ Failed {firm_name}: {e}")

    time.sleep(0.5)

print(f"\nTotal investors: {count}")


    
df = pd.DataFrame(all_firms)
df.drop_duplicates(subset="firm_name", inplace=True)
df.replace(
    ["N/A", "", " ", "-", "N/A "],
    pd.NA,
    inplace=True
)
print(df.isnull().sum())

elapsed = round(time.time() - start, 2)
print(f"\nFinished in {elapsed}s")

df.to_csv("/Users/theguy/Desktop/stuff/vcsheet.csv", index=False)
print("Saved to vcsheet.csv")

