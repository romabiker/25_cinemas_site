from collections import deque, Counter, namedtuple
from datetime import datetime
from queue import Queue
from threading import Thread
import logging
import random
import re
import time


from bs4 import BeautifulSoup
import requests
from flask.helpers import get_debug_flag


from affiche.extensions import cache


FilmInfo = namedtuple('FilmInfo', [
        'title',
        'afisha_link',
        'kinopoisk_id',
        'film_year',
        'kinopoisk_link',
        'kinopoisk_rating',
        'film_genre',
        'creation',
        'description',
    ])


if get_debug_flag():
    logging.basicConfig(level=logging.INFO,
                          format='(%(threadName)-9s) %(message)s',)


@cache.cached(timeout=60*60*24, key_prefix='proxy_ip_list')
def fetch_proxy_ip_list(provider='http://www.freeproxy-list.ru/api/proxy'):
    response = requests.get(
                provider, params={'anonymity': 'false', 'token': 'demo'})
    if response.ok:
        return response.text.splitlines()


@cache.cached(timeout=60*60*24, key_prefix='useragents_list')
def make_useragents_list(from_file='affiche/user_agents.txt'):
    with open(from_file, 'r') as file_handler:
        return file_handler.read().splitlines()


def compose_proxy_url(from_ip):
    if from_ip:
        return {'http': 'http://{}'.format(from_ip),}


@cache.memoize(60*60*24)
def download_afisha_film_html(link, proxy_ips, user_agents,):
    return requests.get(
        link,
        headers=produce_headers(get_random(user_agents)),
        proxies=compose_proxy_url(get_random(proxy_ips)),
    )



def get_random(from_iterable):
    if from_iterable:
        return random.choice(from_iterable)


def produce_headers(user_agent):
    return {'User-Agent': user_agent}


def find_year_in(div_elem, default_year=0, first_el=0):
    year_tag = div_elem.find('span', class_='year')
    if year_tag:
        year = re.findall(r'\d{4}', year_tag.text)[first_el]
        if year:
            return int(year)
    return default_year


def extract_kinopoisk_rating(soup, default_rating='0'):
    rating_tag = soup.find('div', class_='rating')
    if rating_tag:
        return rating_tag.text
    return default_rating


def parse_id_and_rating_from(kinopoisk_search, film, top_count_res=2, first_el=0):
    soup = BeautifulSoup(kinopoisk_search, 'html.parser')
    top_search_results = soup.find_all('div', class_='element')[:top_count_res]
    best_match_variants = Counter(dict(((result, find_year_in(result))
                                         for result in top_search_results)))
    best_match_div, film_year = best_match_variants.most_common()[first_el]
    link_with_film_id = best_match_div.find('div', class_='info').p.a['href']
    film_kinopisk_id = re.findall(r'\d{5,7}', link_with_film_id)[first_el]
    film_kinopisk_rating = extract_kinopoisk_rating(best_match_div)
    return tuple(
        FilmInfo(title=film['title'],
                 afisha_link=film['afisha_link'],
                 kinopoisk_id=film_kinopisk_id,
                 film_year=film_year,
                 kinopoisk_link=link_with_film_id,
                 kinopoisk_rating=film_kinopisk_rating,
                 film_genre='',
                 creation='',
                 description='',),
        film_kinopisk_rating,
    )


def parse_afisha_film_page(film_html, film_info):
    soup = BeautifulSoup(film_html, 'html.parser')
    film_tag = soup.find('div', id='content')
    return film_info._replace(
        film_genre = film_tag.find('div', class_='b-tags').text,
        creation =  film_tag.find('span', class_='creation').text,
        description = film_tag.find('p',
        id='ctl00_CenterPlaceHolder_ucMainPageContent_pEditorComments').text,
    )


def download_and_parse_film_info_from_afisha(
        film,
        proxy_ips,
        user_agents,
        min_delay=0,
        max_delay=1,
        ):
    film_info, kinopoisk_rating = film
    delay = random.choice(range(min_delay, max_delay))
    time.sleep(delay)
    response = download_afisha_film_html(
        film_info.afisha_link, proxy_ips, user_agents)
    logging.info('{} : {}'.format(film_info.afisha_link, response.status_code))
    if response.ok:
        film_info = parse_afisha_film_page(response.text, film_info)
        logging.info(film_info)
        return film_info


@cache.memoize(60*60*24)
def download_kinopoisk_search_html(
        film_title,
        proxy_ips,
        user_agents,
        from_url='https://www.kinopoisk.ru/index.php',
    ):
    return requests.get(
        from_url,
        params={'kp_query': film_title.encode('cp1251'),
                'first': 'no',
                'what': '',},
        headers=produce_headers(get_random(user_agents)),
        proxies=compose_proxy_url(get_random(proxy_ips)),
    )


def download_and_parse_ids_and_ratings(
        film,
        proxy_ips,
        user_agents,
        min_delay=1,
        max_delay=5,
    ):
    delay = random.choice(range(min_delay, max_delay))
    time.sleep(delay)
    response = download_kinopoisk_search_html(film['title'],
                                              proxy_ips, user_agents)
    if response.ok:
        return parse_id_and_rating_from(response.text, film,)


def grab_with_threads(popular_movies, proxy_ips, user_agents,
                      graber_func, workers_number=4):
    def run(tasks, results, proxy_ips, user_agents):
        while True:
            film = tasks.get()
            logging.info('{film} was taken'.format(film=film))
            results.append(graber_func(film, proxy_ips, user_agents))
            logging.info('{film} was done'.format(film=film))
            tasks.task_done()
    tasks = Queue()
    for film in popular_movies:
        tasks.put(film)
    results = deque()
    for number in range(workers_number):
        graber = Thread(
            target=run,
            daemon=True,
            args=(tasks,
                  results,
                  proxy_ips,
                  user_agents,))
        graber.start()
    tasks.join()
    return list(results)


def fetch_ids_and_ratings_from_kinopoisk(popular_movies,
                                         proxy_ips, user_agents, top_count):
    popular_movies = grab_with_threads(popular_movies, proxy_ips, user_agents,
                                    graber_func=download_and_parse_ids_and_ratings)
    logging.info(popular_movies)
    return Counter(dict(popular_movies)).most_common(top_count)


def download_afisha_schedule_cinema_page(proxy_ips, user_agents,
        afisha_cinema_url='https://www.afisha.ru/msk/schedule_cinema/'):
    response = requests.get(
        afisha_cinema_url,
        headers=produce_headers(get_random(user_agents)),
        proxies=compose_proxy_url(get_random(proxy_ips)),
    )
    if not response.ok:
        response.raise_for_status()
    return response.text


def is_popular_by(cinemas_num, pop_level):
    return cinemas_num > pop_level


@cache.memoize(60*60*24)
def find_afisha_popular_movies(pop_level, proxy_ips, user_agents):
    afisha_page = download_afisha_schedule_cinema_page(proxy_ips, user_agents)
    logging.info('Fetched afisha page')
    afisha_soup = BeautifulSoup(afisha_page, 'html.parser')
    popular_movies = []
    film_tags = afisha_soup.find_all('div', class_='m-disp-table')
    for film_div in film_tags:
        cinemas_quantity = len(film_div.find_next('table').find_all('tr'))
        if is_popular_by(cinemas_quantity, pop_level):
            title = film_div.a.text
            afisha_link = film_div.a['href']
            popular_movies.append(
                dict(title=title,
                     afisha_link=afisha_link))
    logging.info(popular_movies)
    return popular_movies


@cache.memoize(60*60*24)
def fetch_top_movies_with_data(top_count=10, pop_level=30):
    start = datetime.now()
    logging.info('Starting fetch_top_movies_with_data...')
    proxy_ips = fetch_proxy_ip_list()
    user_agents = make_useragents_list()
    popular_movies = find_afisha_popular_movies(pop_level, proxy_ips,
                                                user_agents,)
    popular_movies = fetch_ids_and_ratings_from_kinopoisk(
                            popular_movies, proxy_ips, user_agents, top_count,)
    movies_full_info = grab_with_threads(popular_movies, proxy_ips, user_agents,
                        graber_func=download_and_parse_film_info_from_afisha,)
    logging.info('Total time: {}'.format(datetime.now() - start))
    return movies_full_info
