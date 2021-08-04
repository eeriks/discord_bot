import feedparser
from constants import COUNTRIES, events


def main(country):
    page = 1
    has_unknown = False
    while True:
        for entry in feedparser.parse(f"https://www.erepublik.com/en/main/news/military/all/{country}/{page}/rss").entries:
            msg = entry["summary"]
            for kind in events:
                match = kind.regex.search(msg)
                if match:
                    values = match.groupdict()
                    if "invader" in values and not values["invader"]:
                        values["invader"] = values["defender"]
                    has_latvia = any("Latvia" in v for v in values.values())
                    if has_latvia:
                        text = kind.format.format(**dict(match.groupdict(), **{"current_country": country}))
                        print(f"{kind.name:<20} -||- {text:<80} -||- {entry['link']:<64} -||- {entry['published']}")
                    break
            else:
                has_unknown = True
                break
        else:
            page += 1
            if page > 5:
                break
            continue
        break
    if has_unknown:
        print(page, entry)
        raise ValueError(msg)


if __name__ == "__main__":
    for c in sorted(COUNTRIES.values(), key=lambda _c: _c.id):
        if c.id > 35:
            main(c.link)
            print("Finished", c)
