import re
from typing import Any, Dict, List, NamedTuple, TypedDict

from erepublik.constants import COUNTRIES

__all__ = ["events", "COUNTRIES", "UTF_FLAG", "DivisionData"]

region = r"[\w\(\)\-& ']+"
country = r"(Resistance force of )?[\w\(\)\- ]+"
citizen = r"[\w\(\)\-\. \d]+"


class EventKind(NamedTuple):
    slug: str
    name: str
    regex: re.Pattern
    format: str


events = [
    EventKind(
        "region_attacked",
        "Region attacked",
        re.compile(rf"(?P<invader>{country}) attacked (?P<region>{region}), (?P<defender>{country})"),
        "{invader} attacked {defender} ({region})",
    ),
    EventKind(
        "region_secured",
        "Region secured",
        re.compile(rf"(?P<region>{region}) was secured by (?P<defender>{country}) in the war versus (?P<invader>{country})?"),
        "{defender} defended {invader}'s attack ({region})",
    ),
    EventKind(
        "region_conquered",
        "Region conquered",
        re.compile(rf"(?P<region>{region}) was conquered by (?P<invader>{country}) in the war versus (?P<defender>{country})"),
        "{invader} conquered {region} from {defender}",
    ),
    EventKind(
        "war_declared",
        "War declared",
        re.compile(rf"(?P<invader>{country}) declared war on (?P<defender>{country})"),
        "{invader} declared war against {defender}",
    ),
    EventKind(
        "war_declaration",
        "War declaration",
        re.compile(rf"President of (?P<invader>{country}) proposed a war declaration against (?P<defender>{country})"),
        "{invader} proposed a war declaration on {defender}",
    ),
    EventKind(
        "war_rejected",
        "War rejected",
        re.compile(rf"The proposal for declaring war against (?P<defender>{country}) was rejected."),
        "{current_country} rejected war declaration on {defender}",
    ),
    EventKind(
        "mpp_proposed",
        "MPP proposed",
        re.compile(rf"President of (?P<country>{country}) proposed an alliance with (?P<partner>{country})"),
        "{country} proposed MPP with {partner}",
    ),
    EventKind(
        "mpp_approved",
        "MPP approved",
        re.compile(rf"(?P<country>{country}) signed an alliance with (?P<partner>{country})"),
        "{country} signed a MPP with {partner}",
    ),
    EventKind(
        "mpp_rejected",
        "MPP rejected",
        re.compile(rf"The alliance between (?P<country>{country}) and (?P<partner>{country}) was rejected"),
        "MPP between {country} and {partner} was rejected",
    ),
    EventKind(
        "airstrike_proposed",
        "Airstrike proposed",
        re.compile(rf"President of (?P<invader>{country}) proposed an airstrike against (?P<defender>{country})"),
        "{invader} proposed an airstrike against {defender}",
    ),
    EventKind(
        "airstrike_approved",
        "Airstrike approved",
        re.compile(rf"(?P<invader>{country}) prepares an airstrike on (?P<defender>{country})"),
        "{invader} approved an airstrike against {defender}",
    ),
    EventKind(
        "airstrike_rejected",
        "Airstrike rejected",
        re.compile(rf"The airstrike on (?P<defender>{country}) was rejected"),
        "{current_country} rejected the airstrike against {defender}",
    ),
    EventKind(
        "ne_proposed",
        "NE proposed",
        re.compile(rf"(?P<invader>{country}) has declared (?P<defender>{country}) as a Natural Enemy"),
        "{invader} proposed Natural Enemy declaration against {defender}",
    ),
    EventKind(
        "ne_approved",
        "NE approved",
        re.compile(rf"(?P<defender>{country}) has been proposed as Natural Enemy"),
        "{current_country} declared {defender} as Natural Enemy",
    ),
    EventKind(
        "ne_rejected",
        "NE rejected",
        re.compile(rf"(?P<defender>{country}) as new Natural Enemy proposal has been rejected"),
        "{current_country} rejected {defender} as Natural Enemy",
    ),
    EventKind(
        "ne_stopped",
        "NE stopped",
        re.compile(rf"(?P<defender>{country}) is no longer a Natural Enemy for (?P<invader>{country})"),
        "{invader} removed Natural Enemy from {defender}",
    ),
    EventKind(
        "ne_cleared",
        "NE cleared",
        re.compile(rf"(?P<country>{country}) no longer has a Natural Enemy"),
        "{country} no longer has a Natural Enemy",
    ),
    EventKind(
        "ne_reset",
        "NE reset",
        re.compile("No Natural Enemy law has been proposed."),
        "{current_country} has proposed to clear Natural Enemy",
    ),
    EventKind(
        "peace_proposal",
        "Peace proposal",
        re.compile(rf"President of (?P<defender>{country}) proposed a peace in the war against (?P<invader>{country})"),
        "{defender} proposed peace against {invader}",
    ),
    EventKind(
        "peace_proposal",
        "Peace proposal",
        re.compile(rf"(?P<defender>{country}) proposed peace in the war against (?P<invader>{country})"),
        "{defender} proposed peace against {invader}",
    ),
    EventKind(
        "peace_approved",
        "Peace approved",
        re.compile(rf"(?P<invader>{country}) signed a peace treaty with (?P<defender>{country})"),
        "{invader} and {defender} is not in peace",
    ),
    EventKind(
        "peace_rejected",
        "Peace rejected",
        re.compile(rf"The proposed peace treaty between (?P<defender>{country}) and (?P<invader>{country}) was rejected"),
        "{defender} and {invader} did not sign a peace treaty",
    ),
    EventKind(
        "embargo_proposed",
        "Embargo proposed",
        re.compile(rf"President of (?P<major>{country}) proposed to stop the trade with (?P<minor>{country})"),
        "{major} proposed trade embargo against {minor}",
    ),
    EventKind(
        "embargo_approved",
        "Embargo approved",
        re.compile(rf"(?P<major>{country}) stopped trading with (?P<minor>{country})"),
        "{major} declared trade ambargo against {minor}",
    ),
    EventKind(
        "donation_proposed",
        "Donation proposed",
        re.compile(rf"A congress donation to (?P<org>{citizen}) was proposed"),
        "{current_country} proposed a donation to {org}",
    ),
    EventKind(
        "donation_approved",
        "Donation approved",
        re.compile(rf"(?P<country>{country}) made a donation to (?P<org>{citizen})"),
        "{current_country} approved a donation to {org}",
    ),
    EventKind(
        "donation_rejected",
        "Donation rejected",
        re.compile(rf"The proposal for a congress donation to (?P<org>{citizen}) was rejected"),
        "{current_country} rejected a donation to {org}",
    ),
    EventKind(
        "rw_started",
        "RW started",
        re.compile(rf"A resistance has started in (?P<region>{region})"),
        "Resistance war was opened in {region} ({current_country})",
    ),
    EventKind(
        "res_concession",
        "Res Concession",
        re.compile(
            rf"A Resource Concession law to //www.erepublik.com<b>(?P<target>{country})</b> "
            rf'<a href="(?P<link>((https?:)?//www\.erepublik\.com)?/en/main/law/(?P<source>{country})/\d+)">has been (?P<result>.*?)</a>'
        ),
        "Resource Concession law between {source} and {target} has been {result}",
    ),
    EventKind(
        "cp_impeachment",
        "CP impeachment",
        re.compile(rf"A president impeachment against (?P<cp>{citizen}) was proposed"),
        "Impeachment against {cp} president of {current_country} was proposed",
    ),
    EventKind(
        "cp_impeachment",
        "CP impeachment",
        re.compile("The president impeachment proposal has been rejected"),
        "Impeachment against president of {current_country} was rejected",
    ),
    EventKind(
        "min_wage_proposed",
        "Minimum Wage proposed",
        re.compile("A new minimum wage was proposed"),
        "A new minimum wage in {current_country} was proposed",
    ),
    EventKind(
        "min_wage_rejected",
        "Minimum Wage rejected",
        re.compile("The proposal for a minimum wage change was rejected"),
        "The new minimum wage proposal in {current_country} was rejected",
    ),
    EventKind(
        "worktax_approved",
        "WorkTax approved",
        re.compile(rf"(?P<country>{country}) now has a new Work Tax"),
        "{country} has new Work Tax",
    ),
    EventKind(
        "worktax_proposed",
        "WorkTax proposed",
        re.compile("A new Work Tax was proposed"),
        "{country} proposed a new Work Tax",
    ),
    EventKind(
        "worktax_rejected",
        "WorkTax rejected",
        re.compile("The proposal for a new Work Tax was rejected"),
        "{country} rejected new Work Tax",
    ),
    EventKind(
        "product_tax_approved",
        "Product Tax approved",
        re.compile(r"Taxes for (?P<product>[\w ]+) changed"),
        "{current_country} changed taxes for {product}",
    ),
    EventKind(
        "product_tax_rejected",
        "Product Tax rejected",
        re.compile(r"Tax proposal of tax changes for (?P<product>[\w ]+) were rejected"),
        "{current_country} rejected new taxes for {product}",
    ),
    EventKind(
        "product_tax_proposed",
        "Product Tax proposed",
        re.compile(r"New taxes for (?P<product>[\w ]+) were proposed"),
        "{current_country} proposed new taxes for {product}",
    ),
    EventKind(
        "new_welcome_message_proposed",
        "New Welcome message has been proposed",
        re.compile(rf"President of (?P<country>{country}) proposed a new welcome message for new citizens"),
        "{country} proposed new welcome message!",
    ),
    EventKind(
        "new_welcome_message_approved",
        "New Welcome message has been approved",
        re.compile(rf"(?P<country>{country}) now has a new welcoming message for new citizens"),
        "{country} approved new welcome message!",
    ),
]

UTF_FLAG = {
    1: "🇷🇴",
    9: "🇧🇷",
    10: "🇮🇹",
    11: "🇫🇷",
    12: "🇩🇪",
    13: "🇭🇺",
    14: "🇨🇳",
    15: "🇪🇸",
    23: "🇨🇦",
    24: "🇺🇸",
    26: "🇲🇽",
    27: "🇦🇷",
    28: "🇻🇪",
    29: "🇬🇧",
    30: "🇨🇭",
    31: "🇳🇱",
    32: "🇧🇪",
    33: "🇦🇹",
    34: "🇨🇿",
    35: "🇵🇱",
    36: "🇸🇰",
    37: "🇳🇴",
    38: "🇸🇪",
    39: "🇫🇮",
    40: "🇺🇦",
    41: "🇷🇺",
    42: "🇧🇬",
    43: "🇹🇷",
    44: "🇬🇷",
    45: "🇯🇵",
    47: "🇰🇷",
    48: "🇮🇳",
    49: "🇮🇩",
    50: "🇦🇺",
    51: "🇿🇦",
    52: "🇲🇩",
    53: "🇵🇹",
    54: "🇮🇪",
    55: "🇩🇰",
    56: "🇮🇷",
    57: "🇵🇰",
    58: "🇮🇱",
    59: "🇹🇭",
    61: "🇸🇮",
    63: "🇭🇷",
    64: "🇨🇱",
    65: "🇷🇸",
    66: "🇲🇾",
    67: "🇵🇭",
    68: "🇸🇬",
    69: "🇧🇦",
    70: "🇪🇪",
    71: "🇱🇻",
    72: "🇱🇹",
    73: "🇰🇵",
    74: "🇺🇾",
    75: "🇵🇾",
    76: "🇧🇴",
    77: "🇵🇪",
    78: "🇨🇴",
    79: "🇲🇰",
    80: "🇲🇪",
    81: "🇹🇼",
    82: "🇨🇾",
    83: "🇧🇾",
    84: "🇳🇿",
    164: "🇸🇦",
    165: "🇪🇬",
    166: "🇦🇪",
    167: "🇦🇱",
    168: "🇬🇪",
    169: "🇦🇲",
    170: "🇳🇬",
    171: "🇨🇺",
}


class DivisionData(TypedDict):
    region: str
    round_time: str
    round_time_s: int
    sides: List[str]
    url: str
    zone_id: int
    div_id: int
    extra: Dict[str, Any]
