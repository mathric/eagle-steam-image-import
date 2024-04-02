# eagle-steam-image-import

Download your own steam game library image and help import to eagle

## Usage

1. Setup value in config.json

    ```json
    {
        "API_KEY": "Your API key",
        "STEAM_ID": "Steam user ID",
        "IMG_DIR_PATH": "DEFAULT",
        "EAGLE_LIBRARY_NAME": "Your current library name",
        "EAGLE_FOLDER_NAME": "Folder name in which you want to store the images",
        "TAG_LANGUAGE": "en"
    }
    ```

    - `IMG_DIR_PATH`: DEFAULT path will generate an img folder in this project root directory
    - `TAG_LANGUAGE`: Current support en and zh-TW

2. Install `requirements.txt` in your environment

3. Run `main.py [Option]`

## Description

If no option is given, it just run in the following order

(1) --download_img\
(2) --eagle_load

### Options

- -d, --download_img

    Download all games image file

- -e, --eagle_load

    Load all images and the tags into Eagle
