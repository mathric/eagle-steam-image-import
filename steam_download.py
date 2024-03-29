import dataclasses
import json
import os
from dataclasses import dataclass
from pathlib import Path

import cssselect
import lxml.html
import requests


@dataclass
class SteamDownloaderConfig:
    api_key: str
    steam_id: str
    tag_language: str
    img_dir_path: Path
    working_dir: Path


class SteamDownloader:
    def __init__(self, config:SteamDownloaderConfig):
        self.config = dataclasses.replace(config)

    @staticmethod
    def get_img_url(appid):
        return f'https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/library_600x900.jpg'
    
    def download_owned_games(self):
        REQUEST_URL = 'http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/'
        WRITE_PATH = self.config.working_dir / 'owned_games.json'
        params = {
            'key': self.config.api_key,
            'steamid': self.config.steam_id,
            'format': 'json',
            'include_appinfo': 1,
        }
        response = requests.get(REQUEST_URL, params=params)
        if response.status_code != 200:
            raise Exception(f'Failed to get owned games {response.text}')
        
        json_data = response.json()
        with open(WRITE_PATH, 'w') as f:
            json.dump(json_data, f)
        return json_data

    def download_img(self, appid, overwrite=False):
        if not os.path.exists(self.config.img_dir_path):
            os.makedirs(self.config.img_dir_path)

        if not overwrite and os.path.exists(self.config.img_dir_path / f'{appid}.jpg'):
            return
        url = SteamDownloader.get_img_url(appid)
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception(f'Failed to download image for appid {appid}')

        with open(self.config.img_dir_path / f'{appid}.jpg', 'wb') as f:
            f.write(response.content)

    def get_tags(self, appid):
        language_param_map = {
            'en': 'english',
            'zh-TW': 'tchinese'
        }
        params = {
            'l': language_param_map[self.config.tag_language]
        }
        game_page_response = requests.get(f'https://store.steampowered.com/app/{appid}', params)
        if game_page_response.status_code != 200:
            raise Exception(f'Failed to get game page for appid {appid}')
        root = lxml.html.fromstring(game_page_response.text)
        return [elem.text_content().strip() for elem in root.cssselect('a.app_tag')]