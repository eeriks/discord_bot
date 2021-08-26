import datetime
from json import JSONDecodeError
from operator import itemgetter
from typing import Any, Dict, Generator, Tuple, Union

import requests as requests

from dbot.base import logger
from dbot.constants import UTF_FLAG, DivisionData

LAST_BATTLE_RESPONSE = None
LAST_BATTLE_UPDATE_TIMESTAMP = 0


def timestamp_to_datetime(ts: int) -> datetime.datetime:
    return datetime.datetime.fromtimestamp(ts)


def timestamp() -> int:
    return int(datetime.datetime.now().timestamp())


def s_to_human(seconds: Union[int, float]) -> str:
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds - (h * 3600)) // 60
    s = seconds % 60
    return f"{h:01d}:{m:02d}:{s:02d}"


def check_battles(battle_json: Dict[str, Dict[str, Any]]) -> Generator[Tuple[str, int, DivisionData], None, None]:
    for battle in sorted(battle_json.values(), key=itemgetter("start")):
        if battle["start"] > timestamp():
            continue
        region_name = battle["region"]["name"]
        invader_flag = UTF_FLAG[battle["inv"]["id"]]
        defender_flag = UTF_FLAG[battle["def"]["id"]]
        for div in battle["div"].values():
            if div["end"]:
                continue
            division = div["div"]
            dom = div["wall"]["dom"]
            epic = div["epic"]
            division_meta_data = DivisionData(
                region=region_name,
                round_time=s_to_human(timestamp() - battle["start"]),
                round_time_s=int(timestamp() - battle["start"]),
                sides=[],
                url=f"https://www.erepublik.com/en/military/battlefield/{battle['id']}",
                zone_id=battle["zone_id"],
                div_id=div["id"],
                extra={},
            )
            if dom == 50:
                division_meta_data.update(sides=[invader_flag, defender_flag])
                yield "empty", division, division_meta_data
                division_meta_data["sides"].clear()
            if dom == 100:
                division_meta_data.update(sides=[invader_flag if battle["def"]["id"] == div["wall"]["for"] else defender_flag])
                yield "empty", division, division_meta_data
                division_meta_data["sides"].clear()
            if epic > 1:
                division_meta_data.update(sides=[invader_flag, defender_flag])
                division_meta_data["extra"].update(intensity_scale=div["intensity_scale"], epic_type=epic)
                yield "epic", division, division_meta_data
                division_meta_data["sides"].clear()
                division_meta_data["extra"].clear()
            if dom >= 66.8:
                division_meta_data.update(sides=[invader_flag if battle["def"]["id"] == div["wall"]["for"] else defender_flag])
                yield "steal", division, division_meta_data
                division_meta_data["sides"].clear()
    return


def get_battle_page():
    global LAST_BATTLE_UPDATE_TIMESTAMP, LAST_BATTLE_RESPONSE
    if int(datetime.datetime.now().timestamp()) >= LAST_BATTLE_UPDATE_TIMESTAMP + 60:
        dt = datetime.datetime.now()
        r = requests.get("https://www.erepublik.com/en/military/campaignsJson/list")
        try:
            LAST_BATTLE_RESPONSE = r.json()
        except JSONDecodeError:
            logger.warning("Received non json response from erep.lv/battles.json!")
            return get_battle_page()
        LAST_BATTLE_UPDATE_TIMESTAMP = LAST_BATTLE_RESPONSE.get("last_updated", int(dt.timestamp()))
    return LAST_BATTLE_RESPONSE
