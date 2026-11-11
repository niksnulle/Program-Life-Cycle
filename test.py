
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
from urllib.parse import urljoin, urlparse

BASE_URL = "https://www.rdveikals.lv"
headers = {"User-Agent": "Mozilla/5.0"}

products = []
seen = set()


def save():
    if products:
        pd.DataFrame(products).drop_duplicates(
            subset="URL"
        ).to_csv(
            "rd_electronics.csv",
            index=False,
            encoding="utf-8-sig"
        )
        print("Saved:", len(products), "products")


try:
    # Open homepage
    response = requests.get(BASE_URL, headers=headers, timeout=25)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    # Find website links
    links = set()

    for a in soup.select("a[href]"):
        url = urljoin(BASE_URL, a["href"])

        if urlparse(url).netloc == urlparse(BASE_URL).netloc:
            links.add(url)

    # Choose number of pages
    print("1 - Specific number of pages")
    print("2 - All pages")

    choice = input("Choose: ")

    max_pages = None

    if choice == "1":
        max_pages = int(input("Number of pages: "))
        if max_pages < 1:
            raise ValueError("Enter a positive number")
    elif choice != "2":
        raise ValueError("Invalid choice")

    # Visit each link
    for link in links:

        print("\nChecking:", link)

        try:
            response = requests.get(link, headers=headers, timeout=25)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            # Find total pages
            page_numbers = [1]

            for a in soup.select("a[href]"):
                match = re.search(r"/page/(\d+)/", a.get("href", ""))
                if match:
                    page_numbers.append(int(match.group(1)))

            total_pages = max(page_numbers)

            if max_pages:
                total_pages = min(total_pages, max_pages)

            # Scrape pages
            for page in range(1, total_pages + 1):

                if page > 1:
                    page_url = re.sub(
                        r"/page/\d+/",
                        f"/page/{page}/",
                        link
                    )

                    response = requests.get(
                        page_url,
                        headers=headers,
                        timeout=25
                    )
                    response.raise_for_status()
                    soup = BeautifulSoup(response.text, "html.parser")

                count = 0

                for a in soup.select("h3 a"):

                    name = a.get_text(" ", strip=True)
                    url = urljoin(BASE_URL, a.get("href", ""))

                    if not name or url in seen:
                        continue

                    # Find price
                    container = a
                    prices = []

                    for _ in range(8):
                        if container.parent:
                            container = container.parent

                        prices = re.findall(
                            r"(\d[\d\s\u00a0]*[.,]\d{2})\s*€",
                            container.get_text(" ", strip=True)
                        )

                        if prices:
                            break

                    if not prices:
                        continue

                    price = float(
                        prices[0].replace(" ", "")
                        .replace("\u00a0", "")
                        .replace(",", ".")
                    )

                    products.append({
                        "Product": name,
                        "Price (€)": price,
                        "URL": url
                    })

                    seen.add(url)
                    count += 1

                print(f"Page {page}/{total_pages}: {count} new products")

                # Save after every page
                save()

                time.sleep(1)

        except requests.RequestException as error:
            print("Could not load:", error)

except KeyboardInterrupt:
    print("\nScraping stopped!")

except Exception as error:
    print("Error:", error)

finally:
    save()
    print("\nFinished! Total unique products:", len(seen))
    print("Saved to rd_electronics.csv")