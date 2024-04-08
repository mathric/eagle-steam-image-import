import dataclasses
import os
import pathlib
from dataclasses import dataclass
from pathlib import Path

import requests


@dataclass
class EagleloaderConfig:
    eagle_library_name: str
    eagle_folder_name: str
    img_dir_path: Path
    working_dir: Path


class EagleLoader:
    def __init__(self, config: EagleloaderConfig):
        self.config = dataclasses.replace(config)

    @property
    def lib_info(self):
        return requests.get('http://localhost:41595/api/library/info').json()
    
    @property
    def folder_info(self):
        return requests.get('http://localhost:41595/api/folder/list').json()

    def get_or_create_steam_folder(self):
        if self.config.eagle_library_name != (curr_lib_name:=self.lib_info['data']['library']['name']):
            raise Exception(f'Library name not match {self.config.eagle_library_name} != {curr_lib_name}')
        
        for folder_info in self.folder_info['data']:
            if folder_info['name'] == self.config.eagle_folder_name:
                return folder_info['id']
        
        payload = {
            'folderName': self.config.eagle_folder_name,
        }
        response = requests.post('http://localhost:41595/api/folder/create', json=payload)
        if response.status_code != 200:
            raise Exception(f'Failed to create folder "{self.config.eagle_folder_name}" : {response.text}')
        else:
            return response.json().get('data', {}).get('id')
    

    def load_steam_img_to_eagle(self, app_id_to_details):
        if not os.path.exists(self.config.img_dir_path):
            raise Exception('Img folder not exists')

        steam_folder_id = self.get_or_create_steam_folder()
        
        items = []
        for img_file_name in os.listdir(self.config.img_dir_path):
            appid = pathlib.Path(img_file_name).stem
            details = app_id_to_details.get(appid)
            if not details:
                raise Exception(f'Appid {appid} details not found')
            
            item = {
                'path': str(self.config.img_dir_path / f'{img_file_name}'),
                'name': details.get('name'),
                'tags': details.get('tags'),
                'website': details.get('website'),
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