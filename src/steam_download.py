import dataclasses
import json
import os
from dataclasses import dataclass
from pathlib import Path

import cssselect
import lxml.html
import requests
from tqdm import tqdm


@dataclass
class SteamDownloaderConfig:
    api_key: str
    steam_id64: str
    tag_language: str
    img_dir_path: Path
    working_dir: Path
    save_meta: bool = False


class SteamDownloader:
    def __init__(self, config:SteamDownloaderConfig):
        self.config = dataclasses.replace(config)
        self._owned_games = None
        self._appid_to_tags = None

    @property
    def owned_games(self):
        if self._owned_games is None:
            self._owned_games = self.download_owned_games()
        return self._owned_games
    
    @property
    def appid_to_tags(self):
        if not self._appid_to_tags:
            self._appid_to_tags = self.download_tags()
        return self._appid_to_tags

    @staticmethod
    def get_img_url(appid):
        return f'https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/library_600x900.jpg'
    
    def download_owned_games(self):
        REQUEST_URL = 'http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/'
        WRITE_PATH = self.config.working_dir / 'owned_games.json'
        params = {
            'key': self.config.api_key,
            'steamid': self.config.steam_id64,
            'format': 'json',
            'include_appinfo': 1,
        }
        response = requests.get(REQUEST_URL, params=params)
        if response.status_code != 200:
            raise Exception(f'Failed to get owned games {response.text}')
        
        json_data = response.json()
        if self.config.save_meta:
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
    
    def download_tags(self):
        failed_download = []
        appid_to_tags = {}
        owned_games = self.owned_games

        for i in tqdm(range(len(owned_games['response']['games'])), desc='Downloading tags'):
            game = owned_games['response']['games'][i]
            failed_info = {
                'appid': game['appid'],
                'name': game['name']
            }
                
            try:
                appid_to_tags[game['appid']] = self.get_tags(game['appid'])
            except Exception as e:
                failed_download.append(failed_info)
        
        if self.config.save_meta:
            with open(self.config.working_dir / 'failed_tag_download.json', 'w') as f:
                json.dump(failed_download, f)
            
            with open(self.config.working_dir / 'appid_to_tags.json', 'w') as f:
                json.dump(appid_to_tags, f)
        
        return appid_to_tags