from collections import deque, Counter
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


def download_afisha_film_html(
        link,
        proxy_ips,
        user_agents,
        min_delay=0,
        max_delay=1,
    ):
    rnd_proxy = compose_proxy_url(get_random(proxy_ips))
    rnd_header = produce_headers(get_random(user_agents))
    delay = random.choice(range(min_delay, max_delay))
    logging.info('got delay {}'.format(delay))
    time.sleep(delay)
    return requests.get(link, headers=rnd_header, proxies=rnd_proxy,)



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

    return ((film, film_kinopisk_id, film_year, link_with_film_id),
            film_kinopisk_rating)


def parse_afisha_film_page(film_html):
    soup = BeautifulSoup(film_html, 'html.parser')
    film_tag = soup.find('div', id='content')
    return {
        'film_genre': film_tag.find('div', class_='b-tags').text,
        'creation':  film_tag.find('span', class_='creation').text,
        'description': film_tag.find('p',
        id='ctl00_CenterPlaceHolder_ucMainPageContent_pEditorComments').text,
     }


def download_and_parse_film_info_from_afisha(film, proxy_ips, user_agents):
    afisha_link = film[0][0][1]
    response = download_afisha_film_html(afisha_link, proxy_ips, user_agents)
    logging.info('{} : {}'.format(afisha_link, response.status_code))
    if response.ok:
        film_info = parse_afisha_film_page(response.text)
        full_movie_info = {
            'title': film[0][0][0],
            'kinopoisk_id': film[0][1],
            'year': film[0][2],
            'kinopoisk_link': film[0][3],
            'kinopoisk_rating': film[1],
            'afisha_link': afisha_link,
        }
        full_movie_info.update(film_info)
        logging.info(full_movie_info)
        return full_movie_info


def download_kinopoisk_search_html(
        film,
        proxy_ips,
        user_agents,
        title=0,
        from_url='https://www.kinopoisk.ru/index.php',
    ):
    rnd_proxy = compose_proxy_url(get_random(proxy_ips))
    rnd_header = produce_headers(get_random(user_agents))
    return requests.get(
        from_url,
        params={'first': 'no',
                'what': '',
                'kp_query': film[title]},
        headers=rnd_header,
        proxies=rnd_proxy,
    )


def download_and_parse_ids_and_ratings(film, proxy_ips, user_agents):
    response = download_kinopoisk_search_html(film, proxy_ips, user_agents)
    if response.ok:
        return parse_id_and_rating_from(response.text, film,)


def grab_with_threads(popular_movies, proxy_ips, user_agents,
                      grab, workers_number=4):
    def run(tasks, results, proxy_ips, user_agents):
        while True:
            film = tasks.get()
            logging.info('{film} was taken'.format(film=film))
            results.append(grab(film, proxy_ips, user_agents))
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
    ids_with_ratings = grab_with_threads(popular_movies, proxy_ips, user_agents,
                                       grab=download_and_parse_ids_and_ratings)
    logging.info(ids_with_ratings)
    return Counter(dict(ids_with_ratings)).most_common(top_count)


def download_afisha_schedule_cinema_page(proxy_ips, user_agents,
        afisha_cinema_url='https://www.afisha.ru/msk/schedule_cinema/'):
    rnd_proxy = compose_proxy_url(get_random(proxy_ips))
    rnd_header = produce_headers(get_random(user_agents))
    response = requests.get(
        afisha_cinema_url,
        headers=rnd_header,
        proxies=rnd_proxy,
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
            film_title = film_div.a.text
            film_afisha_link = film_div.a['href']
            popular_movies.append((film_title, film_afisha_link))
    logging.info(popular_movies)
    return popular_movies


@cache.memoize(60*60*24)
def fetch_top_movies_with_data(top_count=10, pop_level=30):
    start = datetime.now()
    logging.info('Starting...')
    proxy_ips = fetch_proxy_ip_list()
    user_agents = make_useragents_list()
    popular_movies = find_afisha_popular_movies(pop_level, proxy_ips,
                                                user_agents,)
    films_kinopoisk_ids_and_ratings = fetch_ids_and_ratings_from_kinopoisk(
                            popular_movies, proxy_ips, user_agents, top_count,)
    films_full_info = grab_with_threads(films_kinopoisk_ids_and_ratings,
                            proxy_ips, user_agents,
                            grab=download_and_parse_film_info_from_afisha,)
    logging.info('Total time: {}'.format(datetime.now() - start))
    return films_full_info
