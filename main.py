import argparse
import json
import os
import sys

import cssselect
import lxml.html
import requests
from tqdm import tqdm

config = json.load(open('config.json'))

class SteamDownloader:
    @staticmethod
    def download_owned_games():
        REQUEST_URL = 'http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/'
        WRITE_PATH = 'owned_games.json'
        params = {
            'key': config.get('API_KEY'),
            'steamid': config.get('STEAM_ID'),
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
        if not os.path.exists('img'):
            os.makedirs('img')
        if not overwrite and os.path.exists(f'img/{appid}.jpg'):
            return

        url = SteamDownloader.get_img_url(appid)
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception(f'Failed to download image for appid {appid}')

        with open(f'img/{appid}.jpg', 'wb') as f:
            f.write(response.content)

    @staticmethod
    def get_tags(appid):
        game_page_response = requests.get(f'https://store.steampowered.com/app/{appid}')
        if game_page_response.status_code != 200:
            raise Exception(f'Failed to get game page for appid {appid}')
        root = lxml.html.fromstring(game_page_response.text)
        return [elem.text_content().strip() for elem in root.cssselect('a.app_tag')]
    

class MainAction:
    def __init__(self):
        self.steam_downloader = SteamDownloader()
    
    def write_owned_games_file(self):
        self.steam_downloader.download_owned_games()

    def download_img_and_tags(self):
        FAIL_DATA_DOWNLOAD_PATH = 'failed_data_download.json'
        APPID_TO_TAGS_PATH = 'appid_to_tags.json'
        failed_download_appid = []
        appid_to_tags = {}
        with open('owned_games.json', 'r') as f:
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
        pass


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
        description='Help to download steam game images and load to eagle'
    )
    main_action_group = parser.add_argument_group('Main Action', 'Main Action')
    exclusive_group = main_action_group.add_mutually_exclusive_group(required=True)
    exclusive_group.add_argument('--init', action='store_true', help='init to get owned games json file')
    exclusive_group.add_argument('--download_img', action='store_true', help='download images from owned games')
    exclusive_group.add_argument('--eagle_load', action='store_true', help='load images to eagle')
    args = parser.parse_args()
    main(args)