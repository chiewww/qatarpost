import os
import re
import sys
import time
import unicodedata

import requests

COUNTRIES_URL = "https://qatarpost.qa/Home/GetCountries"
COST_URL = "https://qatarpost.qa/SendPackage/GetShipmentCost"
OUTPUT_FILE = "output_qatar.txt"

WEIGHT = 20
PRODUCT_ID = 101      # Global Standard - Letter
SOURCE_ID = 100
LETTER_SERVICE_ID = 109
DEFAULT_SERVICE_NAME = "Global standard-Letter"
CURRENCY = "QAR"

REQUEST_DELAY = 0.3   # seconds between requests (be polite to the server)
MAX_RETRIES = 3

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; qatarpost-monitor/1.0)",
    "Accept": "application/json, text/plain, */*",
}

# ---------------------------------------------------------------------------
# Postcrossing master list (248 entries)
# ---------------------------------------------------------------------------
MASTER_RAW = """
1|Afghanistan
2|Åland Islands
3|Albania
4|Algeria
5|American Samoa
6|Andorra
7|Angola
8|Anguilla
9|Antarctica
10|Antigua & Barbuda
11|Argentina
12|Armenia
13|Aruba
14|Australia
15|Austria
16|Azerbaijan
17|Bahamas
18|Bahrain
19|Bangladesh
20|Barbados
21|Belarus
22|Belgium
23|Belize
24|Benin
25|Bermuda
26|Bhutan
27|Bolivia
28|Bonaire, Sint Eustatius and Saba
29|Bosnia-Herzegovina
30|Botswana
31|Brazil
32|British Indian Ocean Territory
33|Brunei
34|Bulgaria
35|Burkina Faso
36|Burundi
37|Cabo Verde
38|Cambodia
39|Cameroon
40|Canada
41|Cayman Islands
42|Central African Republic
43|Chad
44|Chile
45|China
46|Christmas Island
47|Cocos Islands
48|Colombia
49|Comoros
50|Congo
51|Dem. Rep. Of Congo
52|Cook Islands
53|Costa Rica
54|Côte d'Ivoire
55|Croatia
56|Cuba
57|Curaçao
58|Cyprus
59|Czechia
60|Denmark
61|Djibouti
62|Dominica
63|Dominican Republic
64|Ecuador
65|Egypt
66|El Salvador
67|Equatorial Guinea
68|Eritrea
69|Estonia
70|Eswatini /Swaziland
71|Ethiopia
72|Falkland Islands /Malvinas
73|Faroe Islands
74|Fiji
75|Finland
76|France
77|French Guiana
78|French Polynesia
79|French Southern Territories
80|Gabon
81|Gambia
82|Georgia
83|Germany
84|Ghana
85|Gibraltar
86|Greece
87|Greenland
88|Grenada
89|Guadeloupe
90|Guam
91|Guatemala
92|Guernsey
93|Guinea
94|Guinea-Bissau
95|Guyana
96|Haiti
97|Honduras
98|Hong Kong
99|Hungary
100|Iceland
101|India
102|Indonesia
103|Iran
104|Iraq
105|Ireland
106|Isle of Man
107|Israel
108|Italy
109|Jamaica
110|Japan
111|Jersey
112|Jordan
113|Kazakhstan
114|Kenya
115|Kiribati
116|Korea(North)
117|Korea(South)
118|Kosovo
119|Kuwait
120|Kyrgyzstan
121|Laos
122|Latvia
123|Lebanon
124|Lesotho
125|Liberia
126|Libya
127|Liechtenstein
128|Lithuania
129|Luxembourg
130|Macao
131|Madagascar
132|Malawi
133|Malaysia
134|Maldives
135|Mali
136|Malta
137|Marshall Islands
138|Martinique
139|Mauritania
140|Mauritius
141|Mayotte
142|Mexico
143|Micronesia
144|Moldova
145|Monaco
146|Mongolia
147|Montenegro
148|Montserrat
149|Morocco
150|Mozambique
151|Myanmar
152|Namibia
153|Nauru / Naoero
154|Nepal
155|Netherlands
156|New Caledonia
157|New Zealand
158|Nicaragua
159|Niger
160|Nigeria
161|Niue
162|Norfolk Island
163|Northern Mariana Islands
164|North Macedonia
165|Norway
166|Oman
167|Pakistan
168|Palau
169|Palestine
170|Panama
171|Papua New Guinea
172|Paraguay
173|Peru
174|Philippines
175|Pitcairn
176|Poland
177|Portugal
178|Puerto Rico
179|Qatar
180|Réunion
181|Romania
182|Russia
183|Rwanda
184|Saint Barthélemy
185|Saint Helena, Ascension and Tristan da Cunha
186|Saint Kitts and Nevis
187|Saint Lucia
188|Saint Martin
189|Saint Pierre & Miquelon
190|Saint Vincent and the Grenadines
191|Samoa
192|San Marino
193|Sao Tome and Principe
194|Saudi Arabia
195|Senegal
196|Serbia
197|Seychelles
198|Sierra Leone
199|Singapore
200|Sint Maarten
201|Slovakia
202|Slovenia
203|Solomon Islands
204|Somalia
205|South Africa
206|South Georgia and S. Sandwich Islands
207|South Sudan
208|Spain
209|Sri Lanka
210|Sudan
211|Suriname
212|Svalbard and Jan Mayen
213|Sweden
214|Switzerland
215|Syria
216|Taiwan
217|Tajikistan
218|Tanzania
219|Thailand
220|Timor-Leste
221|Togo
222|Tokelau
223|Tonga
224|Trinidad and Tobago
225|Tunisia
226|Turkey
227|Turkmenistan
228|Turks and Caicos Islands
229|Tuvalu
230|Uganda
231|Ukraine
232|United Arab Emirates
233|United Kingdom
234|Uruguay
235|U.S.A.
236|U.S. Minor Outlying Islands
237|Uzbekistan
238|Vanuatu
239|Vatican
240|Venezuela
241|Vietnam
242|Virgin Islands (UK)
243|Virgin Islands of the USA
244|Wallis & Futuna
245|Western Sahara
246|Yemen
247|Zambia
248|Zimbabwe
"""

QATAR_NUMBER = 179
SAINT_HELENA_NUMBER = 185

# Destinations to ignore completely (matched on the start of the normalized name)
IGNORED_PREFIXES = (
    "bouvet",
    "heard island",
)

# Extra spellings Qatar Post might use -> Postcrossing number
ALIASES = {
    "cape verde": 37,
    "congo republic of the": 50,
    "republic of the congo": 50,
    "congo brazzaville": 50,
    "congo democratic republic of the": 51,
    "congo the democratic republic of the": 51,
    "democratic republic of the congo": 51,
    "democratic republic of congo": 51,
    "dr congo": 51,
    "drc": 51,
    "congo kinshasa": 51,
    # Côte d'Ivoire
    "ivory coast": 54,
    "cote divoir": 54,
    "cote divoire": 54,
    "cote d ivoire": 54,
    "cote d ivoir": 54,
    # United Kingdom
    "great britain": 233,
    "czech republic": 59,
    "swaziland": 70,
    "eswatini": 70,
    "falkland islands": 72,
    "malvinas": 72,
    "nauru": 153,
    "naoero": 153,
    # Korea
    "north korea": 116,
    "south korea": 117,
    "korea north": 116,
    "korea south": 117,
    "korea democratic peoples republic of": 116,
    "democratic peoples republic of korea": 116,
    "dem peoples rep of korea": 116,
    "dem people s rep of korea": 116,
    "dem peoples republic of korea": 116,
    "korea republic of": 117,
    "korea rep of": 117,
    "korea rep": 117,
    "republic of korea": 117,
    "macau": 130,
    "macao sar china": 130,
    "hong kong sar china": 98,
    "burma": 151,
    "myanmar burma": 151,
    "macedonia": 164,
    "republic of north macedonia": 164,
    "turkiye": 226,
    "united states": 235,
    "united states of america": 235,
    "usa": 235,
    "u s a": 235,
    "us": 235,
    "us minor outlying islands": 236,
    "united states minor outlying islands": 236,
    # Vatican
    "vatican city": 239,
    "vatican city state": 239,
    "holy see": 239,
    "vatican": 239,
    # Virgin Islands
    "virgin islands": 243,   # without (UK) attached -> USA
    "virgin islands british": 242,
    "virgin islands uk": 242,
    "british virgin islands": 242,
    "virgin islands us": 243,
    "virgin islands,u.s.": 243,
    "virgin islands usa": 243,
    "virgin islands of the usa": 243,
    "virgin islands of the united states": 243,
    "us virgin islands": 243,
    "united states virgin islands": 243,
    "wallis and futuna islands": 244,
    "east timor": 220,
    "bosnia and herzegovina": 29,
    "bosnia herzegovina": 29,
    "cocos keeling islands": 47,
    "cocos islands": 47,
    "palestinian territory": 169,
    "palestinian territories": 169,
    "state of palestine": 169,
    "palestine state of": 169,
    "russian federation": 182,
    "syrian arab republic": 215,
    "lao peoples democratic republic": 121,
    "lao pdr": 121,
    "moldova republic of": 144,
    "republic of moldova": 144,
    "tanzania united republic of": 218,
    "united republic of tanzania": 218,
    "iran islamic republic of": 103,
    "islamic republic of iran": 103,
    "venezuela bolivarian republic of": 240,
    "bolivia plurinational state of": 27,
    "brunei darussalam": 33,
    "micronesia federated states of": 143,
    "federated states of micronesia": 143,
    "libyan arab jamahiriya": 126,
    "south georgia and the south sandwich islands": 206,
    "south georgia and south sandwich islands": 206,
    "pitcairn islands": 175,
    "svalbard and jan mayen islands": 212,
    "sao tome and principe": 193,
    "sint maarten dutch part": 200,
    "saint martin french part": 188,
    "bonaire": 28,
    "bonaire saint eustatius and saba": 28,
    # Saint Helena, Ascension and Tristan da Cunha
    "saint helena": 185,
    "saint helena ascension and tristan da cunha": 185,
    "ascension": 185,
    "ascension island": 185,
    "tristan da cunha": 185,
    "saint barthelemy": 184,
    "reunion": 180,
    "curacao": 57,
    "aland islands": 2,
}


def normalize(name):
    """Lowercase, strip accents, '&' -> 'and', drop punctuation, tidy spaces."""
    s = unicodedata.normalize("NFKD", str(name))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"^(st|ste) ", "saint ", s)
    return s


def is_ignored(norm_name):
    return any(norm_name.startswith(p) for p in IGNORED_PREFIXES)


def saint_helena_part(norm_name):
    """Returns 'Ascension' / 'Tristan da Cunha' if the entry is that sub-territory."""
    if norm_name in ("ascension", "ascension island"):
        return "Ascension"
    if norm_name.startswith("tristan"):
        return "Tristan da Cunha"
    return None


def load_master():
    """Returns (names_by_number, lookup_by_normalized_name)."""
    names = {}
    lookup = {}
    for line in MASTER_RAW.strip().splitlines():
        num_str, name = line.split("|", 1)
        num = int(num_str)
        name = name.strip()
        names[num] = name
        lookup[normalize(name)] = num
        # Names like "Eswatini /Swaziland" -> also index each half
        if "/" in name:
            for part in name.split("/"):
                lookup[normalize(part)] = num
    for key, num in ALIASES.items():
        lookup.setdefault(normalize(key), num)
    return names, lookup


# ---------------------------------------------------------------------------
# Qatar Post requests
# ---------------------------------------------------------------------------
def with_retries(func, *args, **kwargs):
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:  # noqa: BLE001
            last_error = e
            print(f"  attempt {attempt}/{MAX_RETRIES} failed: {e}")
            time.sleep(2 * attempt)
    raise RuntimeError(f"Giving up after {MAX_RETRIES} attempts: {last_error}")


def get_countries(session):
    def _do():
        r = session.get(COUNTRIES_URL, timeout=30)
        r.raise_for_status()
        return r.json()

    data = with_retries(_do)
    if isinstance(data, dict):
        for v in data.values():
            if isinstance(v, list):
                data = v
                break
    if not isinstance(data, list) or not data:
        raise RuntimeError("Country list came back empty or in an unexpected format.")
    return data


def get_cost(session, country):
    payload = {
        "WeightInKg": WEIGHT,
        "Destination": country["value"],
        "CountryId": country["id"],
        "SourceId": SOURCE_ID,
        "ShipmentType": " overseas ",
        "ProductId": PRODUCT_ID,
    }

    def _do():
        r = session.post(COST_URL, json=payload, timeout=30)
        r.raise_for_status()
        return r.json()

    data = with_retries(_do)
    if isinstance(data, dict):
        for v in data.values():
            if isinstance(v, list):
                return v
        return []
    if not isinstance(data, list):
        return []
    return data


NAME_KEYS = ("serviceName", "name", "productName", "title", "serviceType")


def item_name(item, default=None):
    for key in NAME_KEYS:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return default


def find_letter(items):
    for item in items:
        if isinstance(item, dict) and item.get("id") == LETTER_SERVICE_ID:
            return item
    return None


def to_price(value):
    try:
        price = float(value)
    except (TypeError, ValueError):
        return None
    return price if price > 0 else None


def classify(items):
    """Returns ('available', service_name, price_text) or ('suspended', reason)."""
    items = [i for i in items if isinstance(i, dict)]
    letter = find_letter(items)

    if letter is not None:
        price = to_price(letter.get("actualPrice"))
        message = (letter.get("message") or "").strip()
        if price is not None and "Unable to calculate" not in message:
            service = item_name(letter, DEFAULT_SERVICE_NAME)
            return ("available", service, f"{CURRENCY} {price:.2f}")
        return ("suspended", "No price")

    # Letter service not present at all
    others = []
    for item in items:
        name = item_name(item)
        if name:
            others.append(name)

    if others:
        listed = ", ".join(f"“{n}”" for n in others)
        return (
            "suspended",
            f"It has {listed} but “{DEFAULT_SERVICE_NAME}” is missing",
        )
    return ("suspended", "“No option available”")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    master_names, lookup = load_master()
    session = requests.Session()
    session.headers.update(HEADERS)

    countries = get_countries(session)

    # Build groups in dropdown order. Each group = one destination
    # (one Postcrossing number). Repeated destinations are not counted twice.
    groups = {}          # key -> {"number": int|None, "entries": [country, ...]}
    group_order = []
    unmatched_names = []

    for c in countries:
        name = str(c.get("value", "")).strip()
        norm = normalize(name)
        if not name or norm == "qatar" or is_ignored(norm):
            continue

        number = lookup.get(norm)
        if number == QATAR_NUMBER:
            continue

        key = number if number is not None else ("x", norm)
        if key not in groups:
            groups[key] = {"number": number, "entries": [], "norms": set()}
            group_order.append(key)
            if number is None:
                unmatched_names.append(name)

        group = groups[key]
        if norm in group["norms"]:
            continue  # exact repeat of an entry we already have
        group["norms"].add(norm)
        group["entries"].append(c)

    available = []        # display lines
    suspended_a = []      # display lines
    matched_numbers = set()

    total = len(group_order)
    first_printed = False

    for i, key in enumerate(group_order, start=1):
        group = groups[key]
        number = group["number"]
        entries = group["entries"]

        if number is not None:
            matched_numbers.add(number)
            display_name = master_names[number]
            num_text = str(number)
        else:
            display_name = str(entries[0]["value"]).strip()
            num_text = "??"

        # Normally only the first entry counts; Saint Helena group needs all.
        to_check = entries if number == SAINT_HELENA_NUMBER else entries[:1]

        results = []
        for country in to_check:
            qp_name = str(country["value"]).strip()
            print(f"{i}/{total} Checking {qp_name}")
            items = get_cost(session, country)
            if not first_printed:
                print(f"  (sample raw response for first country: {items})")
                first_printed = True
            results.append((country, classify(items)))
            time.sleep(REQUEST_DELAY)

        # Special rule: Ascension / Tristan da Cunha suspended -> suspend 185
        if number == SAINT_HELENA_NUMBER:
            bad = []
            for country, res in results:
                part = saint_helena_part(normalize(country["value"]))
                if part and res[0] == "suspended" and part not in bad:
                    bad.append(part)
            if bad:
                order = ["Ascension", "Tristan da Cunha"]
                bad.sort(key=order.index)
                verb = "is" if len(bad) == 1 else "are"
                suspended_a.append(
                    f"{num_text}. {display_name} ({' and '.join(bad)} {verb} suspended)"
                )
                continue

        result = results[0][1]
        if result[0] == "available":
            _, service, price_text = result
            available.append(f"{num_text}. {display_name} {service} {price_text}")
        else:
            suspended_a.append(f"{num_text}. {display_name} ({result[1]})")

    # Suspended B: in Postcrossing list but not in Qatar Post's dropdown
    suspended_b = []
    for number in sorted(master_names):
        if number == QATAR_NUMBER:
            continue
        if number not in matched_numbers:
            suspended_b.append(f"{number}. {master_names[number]}")

    if unmatched_names:
        print("\nWARNING: these Qatar Post destinations are not in the Postcrossing "
              "list (shown as '??' in the output). Add them to ALIASES:")
        for n in unmatched_names:
            print(f"  - {n}")

    lines = []
    lines.append(f"AVAILABLE DESTINATIONS ({len(available)})")
    lines.extend(available)
    lines.append("")
    lines.append(
        f"SUSPENDED DESTINATIONS - Global standard-Letter unavailable ({len(suspended_a)})"
    )
    lines.extend(suspended_a)
    lines.append("")
    lines.append(
        f"SUSPENDED DESTINATIONS - Missing from Qatar Post's list ({len(suspended_b)})"
    )
    lines.extend(suspended_b)
    lines.append("")

    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))

    print(
        f"\nSaved {OUTPUT_FILE}: {len(available)} available, "
        f"{len(suspended_a)} suspended (A), {len(suspended_b)} suspended (B)"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        # Exit without touching the output file, so a temporary website
        # problem never gets committed as a fake "change".
        print(f"FAILED: {e}")
        sys.exit(1)
