import pytest
from src.steam_screenshot import SteamIDComponent, get_steamid_component, get_steam_id32, get_steam_id64

def test_steam_component_parse():
    assert get_steamid_component(76561198092541763) == SteamIDComponent(1, 1, 1, 66138017, 1)

def test_steam_id64():
    assert get_steam_id64(SteamIDComponent(1, 1, 1, 66138017, 1)) == 76561198092541763

def test_steam_id32():
    assert get_steam_id32(SteamIDComponent(1, 1, 1, 66138017, 1)) == 132276035
