import re
from typing import NamedTuple
import feedparser
from erepublik.constants import COUNTRIES

region = "[\w\(\)\- ']+"
country = "(Resistance force of )?[\w\(\)\- ]+"
citizen = "[\w\(\)\-\. \d]+"


class EventKind(NamedTuple):
    name: str
    regex: re.Pattern
    format: str


events = [
    EventKind(
        "Region attacked",
        re.compile(rf"(?P<invader>{country}) attacked (?P<region>{region}), (?P<defender>{country})"),
        "{invader} attacked {defender} ({region})",
    ),
    EventKind(
        "Region secured",
        re.compile(rf"(?P<region>{region}) was secured by (?P<defender>{country}) in the war versus ?(?P<invader>{country})?"),
        "{defender} defended {invader}'s attack ({region})",
    ),
    EventKind(
        "Region conquered",
        re.compile(rf"(?P<region>{region}) was conquered by (?P<invader>{country}) in the war versus ?(?P<defender>{country})?"),
        "{invader} conquered {region} from {defender}",
    ),
    EventKind(
        "War approved",
        re.compile(rf"(?P<invader>{country}) declared war on (?P<defender>{country})"),
        "{invader} declared war against {defender}",
    ),
    EventKind(
        "War declared",
        re.compile(rf"President of (?P<invader>{country}) proposed a war declaration against (?P<defender>{country})"),
        "{invader} proposed a war declaration on {defender}",
    ),
    EventKind(
        "War rejected",
        re.compile(rf"The proposal for declaring war against (?P<defender>{country}) was rejected."),
        "{current_country} rejected war declaration on {defender}",
    ),
    EventKind(
        "MPP proposed",
        re.compile(rf"President of (?P<country>{country}) proposed an alliance with (?P<partner>{country})"),
        "{country} proposed MPP with {partner}",
    ),
    EventKind(
        "MPP approved",
        re.compile(rf"(?P<country>{country}) signed an alliance with (?P<partner>{country})"),
        "{country} signed a MPP with {partner}",
    ),
    EventKind(
        "MPP rejected",
        re.compile(rf"The alliance between (?P<country>{country}) and (?P<partner>{country}) was rejected"),
        "MPP between {country} and {partner} was rejected",
    ),
    EventKind(
        "Airstrike proposed",
        re.compile(rf"President of (?P<invader>{country}) proposed an airstrike against (?P<defender>{country})"),
        "{invader} proposed an airstrike against {defender}",
    ),
    EventKind(
        "Airstrike approved",
        re.compile(rf"(?P<invader>{country}) prepares an airstrike on (?P<defender>{country})"),
        "{invader} approved an airstrike against {defender}",
    ),
    EventKind(
        "Airstrike rejected",
        re.compile(rf"The airstrike on (?P<defender>{country}) was rejected"),
        "{current_country} rejected the airstrike against {defender}",
    ),
    EventKind(
        "NE proposed",
        re.compile(rf"(?P<invader>{country}) has declared (?P<defender>{country}) as a Natural Enemy"),
        "{invader} proposed Natural Enemy declaration against {defender}",
    ),
    EventKind(
        "NE approved",
        re.compile(rf"(?P<defender>{country}) has been proposed as Natural Enemy"),
        "{current_country} declared {defender} as Natural Enemy",
    ),
    EventKind(
        "NE rejected",
        re.compile(rf"(?P<defender>{country}) as new Natural Enemy proposal has been rejected"),
        "{current_country} rejected {defender} as Natural Enemy",
    ),
    EventKind(
        "NE stopped",
        re.compile(rf"(?P<defender>{country}) is no longer a Natural Enemy for (?P<invader>{country})"),
        "{invader} removed Natural Enemy from {defender}",
    ),
    EventKind(
        "NE cleared", re.compile(rf"(?P<country>{country}) no longer has a Natural Enemy"), "{country} no longer has a Natural Enemy"
    ),
    EventKind("NE reset", re.compile("No Natural Enemy law has been proposed."), "{current_country} has proposed to clear Natural Enemy"),
    EventKind(
        "Peace proposal",
        re.compile(rf"President of (?P<defender>{country}) proposed a peace in the war against (?P<invader>{country})"),
        "{defender} proposed peace against {invader}",
    ),
    EventKind(
        "Peace proposal",
        re.compile(rf"(?P<defender>{country}) proposed peace in the war against (?P<invader>{country})"),
        "{defender} proposed peace against {invader}",
    ),
    EventKind(
        "Peace approved",
        re.compile(rf"(?P<invader>{country}) signed a peace treaty with (?P<defender>{country})"),
        "{invader} and {defender} is not in peace",
    ),
    EventKind(
        "Peace rejected",
        re.compile(rf"The proposed peace treaty between (?P<defender>{country}) and (?P<invader>{country}) was rejected"),
        "{defender} and {invader} did not sign a peace treaty",
    ),
    EventKind(
        "Embargo proposed",
        re.compile(rf"President of (?P<major>{country}) proposed to stop the trade with (?P<minor>{country})"),
        "{major} proposed trade embargo against {minor}",
    ),
    EventKind(
        "Embargo approved",
        re.compile(rf"(?P<major>{country}) stopped trading with (?P<minor>{country})"),
        "{major} declared trade ambargo against {minor}",
    ),
    EventKind(
        "Donation proposed",
        re.compile(rf"A congress donation to (?P<org>{citizen}) was proposed"),
        "{current_country} proposed a donation to {org}",
    ),
    EventKind(
        "Donation approved",
        re.compile(rf"(?P<country>{country}) made a donation to (?P<org>{citizen})"),
        "{current_country} approved a donation to {org}",
    ),
    EventKind(
        "Donation rejected",
        re.compile(rf"The proposal for a congress donation to (?P<org>{citizen}) was rejected"),
        "{current_country} rejected a donation to {org}",
    ),
    EventKind(
        "RW started",
        re.compile(rf"A resistance has started in (?P<region>{region})"),
        "Resistance war was opened in {region} ({current_country})",
    ),
    EventKind(
        "Res Concession",
        re.compile(
            rf'A Resource Concession law to //www.erepublik.com<b>(?P<target>{country})</b> <a href="https://www.erepublik.com/en/main/law/(?P<source>{country})/\d+">has been proposed</a>'
        ),
        "{source} proposed resource concession to {target}",
    ),
    EventKind(
        "Res Concession",
        re.compile(
            rf'A Resource Concession law to //www.erepublik.com<b>(?P<target>{country})</b> <a href="https://www.erepublik.com/en/main/law/(?P<source>{country})/\d+">has been approved'
        ),
        "{source} approved resource concession to {target}",
    ),
    EventKind(
        "CP impeachment",
        re.compile(rf"A president impeachment against (?P<cp>{citizen}) was proposed"),
        "Impeachment against {cp} president of {current_country} was proposed",
    ),
    EventKind(
        "CP impeachment",
        re.compile("The president impeachment proposal has been rejected"),
        "Impeachment against president of {current_country} was rejected",
    ),
    EventKind("Minimum Wage", re.compile("A new minimum wage was proposed"), "A new minimum wage in {current_country} was proposed"),
    EventKind(
        "Minimum Wage",
        re.compile("The proposal for a minimum wage change was rejected"),
        "The new minimum wage proposal in {current_country} was rejected",
    ),
    EventKind("WorkTax", re.compile(rf"(?P<country>{country}) now has a new Work Tax"), "{country} has new Work Tax"),
    EventKind("Product Tax", re.compile(rf"Taxes for (?P<product>[\w ]+) changed"), "{current_country} changed taxes for {product}"),
    EventKind(
        "Product Tax",
        re.compile(rf"Tax proposal of tax changes for (?P<product>[\w ]+) were rejected"),
        "{current_country} rejected new taxes for {product}",
    ),
    EventKind(
        "Product Tax", re.compile(rf"New taxes for (?P<product>[\w ]+) were proposed"), "{current_country} proposed new taxes for {product}"
    ),
]


def main(country):
    page = 1
    has_unknown = False
    while True:
        for entry in feedparser.parse(f"https://www.erepublik.com/en/main/news/military/all/{country}/{page}/rss").entries:
            msg = entry["summary"]
            for kind in events:
                match = kind.regex.search(msg)
                if match:
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
        if c.id == 71:
            main(c.link)
            print("Finished", c)
