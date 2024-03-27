import argparse
import json
import os
import pathlib

from tqdm import tqdm

from eagle import EagleLoader, EagleloaderConfig
from steam_download import SteamDownloader, SteamDownloaderConfig

CURR_DIR = pathlib.Path(__file__).parent.absolute()
DEFAULT_WORKING_DIR = CURR_DIR

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



def get_steam_downloader_config(config) -> SteamDownloaderConfig:
    img_dir_path = CURR_DIR / 'img'
    if config.get('IMG_DIR_PATH') != 'DEFAULT':
        if not os.path.isdir(config.get('IMG_DIR_PATH')):
            raise Exception(f'{config.get("IMG_DIR_PATH")} is not a valid directory')
        img_dir_path = pathlib.Path(config.get('IMG_DIR_PATH'))

    return SteamDownloaderConfig(
        img_dir_path=img_dir_path,
        api_key=config.get('API_KEY'),
        steam_id=config.get('STEAM_ID'),
        tag_language=config.get('TAG_LANGUAGE'),
        working_dir=DEFAULT_WORKING_DIR
    )


def get_eagle_loader_config(config) -> EagleloaderConfig:
    img_dir_path = CURR_DIR / 'img'
    if config.get('IMG_DIR_PATH') != 'DEFAULT':
        if not os.path.isdir(config.get('IMG_DIR_PATH')):
            raise Exception(f'{config.get("IMG_DIR_PATH")} is not a valid directory')
        img_dir_path = pathlib.Path(config.get('IMG_DIR_PATH'))
    
    return EagleloaderConfig(
        eagle_library_name=config.get('EAGLE_LIBRARY_NAME'),
        eagle_folder_name=config.get('EAGLE_FOLDER_NAME'),
        img_dir_path=img_dir_path,
        working_dir=DEFAULT_WORKING_DIR
    )


class MainAction:
    def __init__(self, user_config):
        self.steam_downloader = SteamDownloader(get_steam_downloader_config(user_config))
        self.eagle_loader = EagleLoader(get_eagle_loader_config(user_config))

    def write_owned_games_file(self):
        self.steam_downloader.download_owned_games()

    def download_img_and_tags(self):
        FAIL_DATA_DOWNLOAD_PATH = DEFAULT_WORKING_DIR / 'failed_data_download.json'
        APPID_TO_TAGS_PATH = DEFAULT_WORKING_DIR / 'appid_to_tags.json'
        failed_download_appid = []
        appid_to_tags = {}
        with open(DEFAULT_WORKING_DIR / 'owned_games.json', 'r') as f:
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
    user_config = json.load(open(DEFAULT_WORKING_DIR / 'config.json'))
    config_validate_result = config_format_is_valid(user_config)
    if config_validate_result['status'] == 'error':
        raise Exception(config_validate_result['message'])

    main_action = MainAction(user_config)
    if args.init:
        main_action.write_owned_games_file()
    elif args.download_img_and_tag:
        main_action.download_img_and_tags()
    elif args.eagle_load:
        main_action.eagle_load()
    else:
        print('-------Start write owned games file---------')
        main_action.write_owned_games_file()

        print('-------Start download images and tags-------')
        main_action.download_img_and_tags()

        print('-------Start load images to eagle-----------')
        main_action.eagle_load()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        allow_abbrev=False,
        description='Help to download steam game images and load to eagle'
    )
    main_action_group = parser.add_argument_group('Main Action', 'Main Action')
    exclusive_group = main_action_group.add_mutually_exclusive_group(required=False)
    exclusive_group.add_argument('-i', '--init', action='store_true', help='init to get owned games json file')
    exclusive_group.add_argument('-d', '--download_img_and_tag', action='store_true', help='download images and tags from owned games')
    exclusive_group.add_argument('-e', '--eagle_load', action='store_true', help='load images to eagle')
    args = parser.parse_args()
    main(args)