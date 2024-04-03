
from dataclasses import dataclass

@dataclass
class SteamIDComponent:
    universe: int # x
    account_type: int
    account_instance: int
    account_number: int # z
    y: int


def get_steamid_component(steam_id64: int) -> SteamIDComponent:
    b_steam_id = format(steam_id64, '064b')

    return SteamIDComponent(
        universe=int(b_steam_id[0:8], 2),
        account_type=int(b_steam_id[8:12], 2),
        account_instance=int(b_steam_id[12:32], 2),
        account_number=int(b_steam_id[32:63], 2),
        y=int(b_steam_id[-1])
    )


def get_steam_id32(steam_id_component: SteamIDComponent) -> int:
    return steam_id_component.account_number*2 + steam_id_component.y


def get_steam_id64(steam_id_component: SteamIDComponent) -> int:
    steamid64_identifier = {
        1: 0x0110000100000000,
        7: 0x0170000000000000
    }
    return steam_id_component.account_number*2 + steam_id_component.y + int(steamid64_identifier[steam_id_component.account_type])


assert get_steamid_component(76561198092541763) == SteamIDComponent(1, 1, 1, 66138017, 1)
assert get_steam_id64(SteamIDComponent(1, 1, 1, 66138017, 1)) == 76561198092541763
assert get_steam_id32(SteamIDComponent(1, 1, 1, 66138017, 1)) == 132276035



