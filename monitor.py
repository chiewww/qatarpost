import requests
import os
COUNTRIES_URL = "https://qatarpost.qa/Home/GetCountries"
COST_URL = "https://qatarpost.qa/SendPackage/GetShipmentCost"

OUTPUT_FILE = "docs/no_option_available.txt"

WEIGHT = 20
PRODUCT_ID = 101   # Global Standard - Letter
SOURCE_ID = 100


def get_countries():
    r = requests.get(COUNTRIES_URL, timeout=30)
    r.raise_for_status()
    return r.json()


def check_country(country):
    payload = {
        "WeightInKg": WEIGHT,
        "Destination": country["value"],
        "CountryId": country["id"],
        "SourceId": SOURCE_ID,
        "ShipmentType": " overseas ",
        "ProductId": PRODUCT_ID
    }

    try:
        r = requests.post(
            COST_URL,
            json=payload,
            timeout=30
        )
        r.raise_for_status()
        data = r.json()

        # Letter service is id 109
        letter = next(
            (item for item in data if item.get("id") == 109),
            None
        )

        if letter is None:
            return True

        price = letter.get("actualPrice")
        message = letter.get("message") or ""

        # Treat these as unavailable
        if price is None:
            return True

        if price == 0:
            return True

        if "Unable to calculate" in message:
            return True

        return False

    except Exception as e:
        print(f"Error checking {country['value']}: {e}")
        return False


def main():
    os.makedirs("docs", exist_ok=True)
    countries = get_countries()

    unavailable = []

    for i, country in enumerate(countries, start=1):
        name = country["value"]
        print(f"{i}/{len(countries)} Checking {name}")

        if check_country(country):
            unavailable.append(name)

    unavailable.sort()

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:
        for country in unavailable:
            f.write(country + "\n")

    print(f"Saved {len(unavailable)} countries")


if __name__ == "__main__":
    main()
