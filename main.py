import argparse
import json
import os
import sys
import pathlib

import cssselect
import lxml.html
import requests
from tqdm import tqdm

CURR_DIR = pathlib.Path(__file__).parent.absolute()

global_config = json.load(open('config.json'))

def config_format_is_valid(config):
    required_config = ['API_KEY', 'STEAM_ID', 'EAGLE_LIBRARY_NAME', 'EAGLE_FOLDER_NAME']
    for key in required_config:
        if key not in config or not config[key]:
            return {
                'status': 'error',
                'message': f'Config {key} is missing or empty'
            }
    return {
        'status': 'success',
        'message': 'Config is valid'
    }


class SteamDownloader:
    @staticmethod
    def download_owned_games():
        REQUEST_URL = 'http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/'
        WRITE_PATH = CURR_DIR / 'owned_games.json'
        params = {
            'key': global_config.get('API_KEY'),
            'steamid': global_config.get('STEAM_ID'),
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

    @staticmethod
    def get_img_url(appid):
        return f'https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/library_600x900.jpg'

    @staticmethod
    def download_img(appid, overwrite=False):
        if not os.path.exists(CURR_DIR / 'img'):
            os.makedirs(CURR_DIR / 'img')
        if not overwrite and os.path.exists(CURR_DIR / f'img/{appid}.jpg'):
            return

        url = SteamDownloader.get_img_url(appid)
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception(f'Failed to download image for appid {appid}')

        with open(CURR_DIR / f'img/{appid}.jpg', 'wb') as f:
            f.write(response.content)

    @staticmethod
    def get_tags(appid):
        game_page_response = requests.get(f'https://store.steampowered.com/app/{appid}')
        if game_page_response.status_code != 200:
            raise Exception(f'Failed to get game page for appid {appid}')
        root = lxml.html.fromstring(game_page_response.text)
        return [elem.text_content().strip() for elem in root.cssselect('a.app_tag')]


class EagleLoader:
    def __init__(self):
        self._tag_info = None
        self._owned_games = None

    @property
    def lib_info(self):
        return requests.get('http://localhost:41595/api/library/info').json()
    
    @property
    def folder_info(self):
        return requests.get('http://localhost:41595/api/folder/list').json()
    
    @property
    def tag_info(self):
        if self._tag_info is None:
            with open(CURR_DIR / 'appid_to_tags.json', 'r') as f:
                self._tag_info = json.load(f)
        return self._tag_info
    
    @property
    def owned_games(self):
        if self._owned_games is None:
            with open(CURR_DIR / 'owned_games.json', 'r') as f:
                self._owned_games = json.load(f)
        return self._owned_games

    def get_or_create_steam_folder(self):
        if global_config.get('EAGLE_LIBRARY_NAME') != (curr_lib_name:=self.lib_info['data']['library']['name']):
            raise Exception(f'Library name not match {global_config.get("EAGLE_LIBRARY_NAME")} != {curr_lib_name}')
        
        for folder_info in self.folder_info['data']:
            if folder_info['name'] == global_config.get('EAGLE_FOLDER_NAME'):
                return folder_info['id']
        
        payload = {
            'folderName': global_config.get('EAGLE_FOLDER_NAME'),
        }
        response = requests.post('http://localhost:41595/api/folder/create', json=payload)
        if response.status_code != 200:
            raise Exception(f'Failed to create folder "{global_config.get("EAGLE_FOLDER_NAME")}" : {response.text}')
        else:
            return response.json().get('data', {}).get('id')
    

    def load_steam_img_to_eagle(self):
        if not os.path.exists('img'):
            raise Exception('Img folder not exists')
        
        steam_folder_id = self.get_or_create_steam_folder()
        appid_to_game_name = {game['appid']: game['name'] for game in self.owned_games['response']['games']}
        
        items = []
        for img_file_name in os.listdir(pathlib.Path(__file__).parent.absolute() / 'img'):
            appid = pathlib.Path(img_file_name).stem
            tags = self.tag_info.get(appid, [])
            item = {
                'path': str(CURR_DIR / f'img/{img_file_name}'),
                'name': appid_to_game_name.get(int(appid), ''),
                'tags': tags,
                'website': SteamDownloader.get_img_url(appid),
            }
            items.append(item)
        
        payload = {
            'items': items,
            'folderId': steam_folder_id
        }
        response = requests.post('http://localhost:41595/api/item/addFromPaths', json=payload)
        if response.status_code != 200:
            raise Exception(f'Failed to load images to eagle: {response.text}')
        else:
            print('Load images to eagle task send successfully')


class MainAction:
    def __init__(self):
        config_validate_result = config_format_is_valid(global_config)
        if config_validate_result['status'] == 'error':
            raise Exception(config_validate_result['message'])
        self.steam_downloader = SteamDownloader()
        self.eagle_loader = EagleLoader()
    
    def write_owned_games_file(self):
        self.steam_downloader.download_owned_games()

    def download_img_and_tags(self):
        FAIL_DATA_DOWNLOAD_PATH = CURR_DIR / 'failed_data_download.json'
        APPID_TO_TAGS_PATH = CURR_DIR / 'appid_to_tags.json'
        failed_download_appid = []
        appid_to_tags = {}
        with open(CURR_DIR / 'owned_games.json', 'r') as f:
            data = json.load(f)
            for i in tqdm(range(len(data['response']['games']))):
                game = data['response']['games'][i]
                failed_info = {
                    'appid': game['appid'],
                    'name': game['name'],
                    'img_download_failed': False,
                    'tag_download_failed': False
                }
                try:
                    self.steam_downloader.download_img(game['appid'])
                except Exception as e:
                    failed_info['img_download_failed'] = True
                    
                try:
                    appid_to_tags[game['appid']] = self.steam_downloader.get_tags(game['appid'])
                except Exception as e:
                    failed_info['tag_download_failed'] = True

                if failed_info['img_download_failed'] or failed_info['tag_download_failed']:
                    failed_download_appid.append(failed_info)

        # write failed img download games to file
        with open(FAIL_DATA_DOWNLOAD_PATH, 'w') as f:
            json.dump(failed_download_appid, f)

        # write tag info to file
        with open(APPID_TO_TAGS_PATH, 'w') as f:
            json.dump(appid_to_tags, f)
    
    def eagle_load(self):
        self.eagle_loader.load_steam_img_to_eagle()


def main(args):
    main_action = MainAction()
    if args.init:
        main_action.write_owned_games_file()
    elif args.download_img:
        main_action.download_img_and_tags()
    elif args.eagle_load:
        main_action.eagle_load()
    else:
        parser.print_help()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        allow_abbrev=False,
        description='Help to download steam game images and load to eagle'
    )
    main_action_group = parser.add_argument_group('Main Action', 'Main Action')
    exclusive_group = main_action_group.add_mutually_exclusive_group(required=True)
    exclusive_group.add_argument('--init', action='store_true', help='init to get owned games json file')
    exclusive_group.add_argument('--download_img', action='store_true', help='download images from owned games')
    exclusive_group.add_argument('--eagle_load', action='store_true', help='load images to eagle')
    args = parser.parse_args()
    main(args)