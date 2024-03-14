import json
import os
import sys

import requests
from tqdm import tqdm

config = json.load(open('config.json'))

def get_owned_games():
    REQUEST_URL = 'http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/'
    params = {
        'key': config.get('API_KEY'),
        'steamid': config.get('STEAM_ID'),
        'format': 'json',
        'include_appinfo': 1,
    }
    response = requests.get(REQUEST_URL, params=params)
    if response.status_code != 200:
        raise Exception(f'Failed to get owned games {response.text}')
    return response.json()


def get_img_url(appid):
    return f'https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/library_600x900.jpg'


def download_img(appid, overwrite=False):
    if not overwrite and os.path.exists(f'img/{appid}.jpg'):
        return

    url = get_img_url(appid)
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f'Failed to download image for appid {appid}')

    with open(f'img/{appid}.jpg', 'wb') as f:
        f.write(response.content)


if __name__ == '__main__':
    # write to json file
    if len(sys.argv) > 1 and sys.argv[1] == 'init':
        with open('owned_games.json', 'w') as f:
            json.dump(get_owned_games(), f)

    if not os.path.exists('img'):
        os.makedirs('img')

    # load from json file
    failed_download_appid = []
    with open('owned_games.json', 'r') as f:
        data = json.load(f)
        for i in tqdm(range(len(data['response']['games']))):
            game = data['response']['games'][i]
            try:
                download_img(game['appid'])
            except Exception as e:
                failed_download_appid.append(
                    {
                        'appid': game['appid'],
                        'name': game['name']
                    }
                )
    
    # write failed img download games to file
    with open('failed_img_download.json', 'w') as f:
        json.dump(failed_download_appid, f)
