from math import floor
from time import time
from io import BytesIO
from os import environ

from dotenv import load_dotenv
from requests import get, post
from PIL import Image

language_id = 1  # Japanese
generation_id = 4  # Ultra Sun / Ultra Moon
battle_type = 2  # Double battle
rank_count = 10
image_size = 300


def get_timestamp():
    return floor(time() * 1000)


def get_cookies():
    url = 'https://3ds.pokemon-gl.com/frontendApi/getLoginStatus'
    response = post(url, data={
        'languageId': language_id,
        'timezone': 'UTC',
        'timeStamp': get_timestamp(),
    }, headers={
        'Referer': 'https://3ds-sp.pokemon-gl.com/',
    })
    response.raise_for_status()

    data = response.json()
    assert data['status_code'] == '0000'

    return response.cookies


def get_latest_season(cookies):
    url = 'https://3ds-sp.pokemon-gl.com/frontendApi/gbu/getSeason'
    response = post(url, data={
        'languageId': language_id,
        'generationId': generation_id,
        'timeStamp': get_timestamp(),
    }, headers={
        'Referer': 'https://3ds-sp.pokemon-gl.com/',
    }, cookies=cookies)
    response.raise_for_status()

    data = response.json()
    assert data['status_code'] == '0000'

    latest_season = data['seasonInfo'][0]
    return latest_season


def get_pokemons(season, cookies):
    url = 'https://3ds-sp.pokemon-gl.com/frontendApi/gbu/getSeasonPokemon'
    response = post(url, data={
        'languageId': language_id,
        'seasonId': season['seasonId'],
        'battleType': battle_type,
        'timeStamp': get_timestamp(),
    }, headers={
        'Referer': 'https://3ds-sp.pokemon-gl.com/',
    }, cookies=cookies)
    response.raise_for_status()

    data = response.json()
    assert data['status_code'] == '0000'

    pokemons = data['rankingPokemonInfo']
    return pokemons


def get_pokemon_image(pokemon):
    n = pokemon['monsno']
    id = int(pokemon['formNo'])
    '''
    r = (0x1000000 | ((0x159a55e5 * (n + id * 0x10000)) & 0xffffff))
      .toString(16)
      .substr(1);
    '''
    code = hex(0x1000000 | ((0x159a55e5 * (n + id * 0x10000)) & 0xffffff))[3:]
    url = ('https://n-3ds-pgl-contents.pokemon-gl.com'
           '/share/images/pokemon/{}/{}.png').format(image_size, code)

    response = get(url)
    response.raise_for_status()

    content = response.content
    image = Image.open(BytesIO(content))

    size = image_size
    half_size = image_size >> 1

    top_left = image.crop((0, 0, half_size, half_size))
    top_right = image.crop((half_size, 0, size, half_size))
    bottom_left = image.crop((0, half_size, half_size, size))
    bottom_right = image.crop((half_size, half_size, size, size))
    image.paste(top_left, (half_size, half_size))
    image.paste(top_right, (0, half_size))
    image.paste(bottom_left, (half_size, 0))
    image.paste(bottom_right, (0, 0))

    return image


def send_to_weibo(access_token, image):
    url = 'https://api.weibo.com/2/statuses/share.json'

    imageIO = BytesIO()
    image.save(imageIO, 'PNG')
    imageIO.seek(0)

    response = post(url, params={
        'access_token': access_token,
    }, files={
        'status': 'Pokemon Global Link ranking today',
        'pic': ('ranks.png', imageIO, 'image/png'),
    })
    response.raise_for_status()

    data = response.json()
    assert 'error' not in data, data['error']


def main():
    cookies = get_cookies()
    season = get_latest_season(cookies=cookies)
    pokemons = get_pokemons(season, cookies=cookies)

    image = Image.new('RGBA', (image_size, image_size * rank_count))
    for (index, pokemon) in enumerate(pokemons[0:rank_count]):
        pokemon_image = get_pokemon_image(pokemon)
        image.paste(pokemon_image, (0, index * image_size))

    send_to_weibo(environ['WEIBO_ACCESS_TOKEN'], image)


if __name__ == "__main__":
    load_dotenv()
    main()
