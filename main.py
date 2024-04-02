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
        working_dir=DEFAULT_WORKING_DIR,
        save_meta=config.get('SAVE_META', False)
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

    def download_imgs(self, save_meta=False):
        FAIL_DATA_DOWNLOAD_PATH = DEFAULT_WORKING_DIR / 'failed_img_download.json'
        failed_download_list = []
        owned_games = self.steam_downloader.owned_games

        for i in tqdm(range(len(owned_games['response']['games']))):
            game = owned_games['response']['games'][i]
            failed_info = {
                'appid': game['appid'],
                'name': game['name']
            }
            try:
                self.steam_downloader.download_img(game['appid'])
            except Exception as e:
                failed_download_list.append(failed_info)

        if save_meta:
            # write failed img download games to file
            with open(FAIL_DATA_DOWNLOAD_PATH, 'w') as f:
                json.dump(failed_download_list, f)

    def eagle_load(self):
        owned_games = self.steam_downloader.owned_games
        appid_to_tags = self.steam_downloader.appid_to_tags
        self.eagle_loader.load_steam_img_to_eagle(
            tag_info=appid_to_tags,
            owned_games=owned_games
        )


def main(args):
    user_config = json.load(open(DEFAULT_WORKING_DIR / 'config.json'))
    config_validate_result = config_format_is_valid(user_config)
    if config_validate_result['status'] == 'error':
        raise Exception(config_validate_result['message'])

    main_action = MainAction(user_config)
    if args.download_img:
        main_action.download_imgs()
    elif args.eagle_load:
        main_action.eagle_load()
    else:
        print('-------Start download images and tags-------')
        main_action.download_imgs()

        print('-------Start load images to eagle-----------')
        main_action.eagle_load()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        allow_abbrev=False,
        description='Help to download steam game images and load to eagle'
    )
    main_action_group = parser.add_argument_group('Main Action', 'Main Action')
    exclusive_group = main_action_group.add_mutually_exclusive_group(required=False)
    exclusive_group.add_argument('-d', '--download_img', action='store_true', help='download images from owned games')
    exclusive_group.add_argument('-e', '--eagle_load', action='store_true', help='load images to eagle')
    args = parser.parse_args()
    main(args)