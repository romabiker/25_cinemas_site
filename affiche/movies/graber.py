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


def fetch_proxy_ip_list(provider='http://www.freeproxy-list.ru/api/proxy'):
    response = requests.get(
                provider, params={'anonymity': 'false', 'token': 'demo'})
    if response.ok:
        return response.text.splitlines()


def make_useragents_list(from_file='affiche/user_agents.txt'):
    with open(from_file, 'r') as file_handler:
        return file_handler.read().splitlines()


def compose_proxy_url(from_ip):
    if from_ip:
        return {'http': 'http://{}'.format(from_ip),}


def download_kinopoisk_search_html(
        title,
        proxy_ips,
        user_agents,
        min_delay=2,
        max_delay=5,
        from_url='https://www.kinopoisk.ru/index.php',
    ):
    rnd_proxy = compose_proxy_url(get_random(proxy_ips))
    rnd_header = produce_headers(get_random(user_agents))
    delay = random.choice(range(min_delay, max_delay))
    logging.info('got delay {}'.format(delay))
    time.sleep(delay)
    return requests.get(
        from_url,
        params={'first': 'no',
                'what': '',
                'kp_query': title},
        headers=rnd_header,
        proxies=rnd_proxy,
    )


def download_kinopoisk_film_html(
        link,
        proxy_ips,
        user_agents,
        min_delay=2,
        max_delay=5,
    ):
    rnd_proxy = compose_proxy_url(get_random(proxy_ips))
    rnd_header = produce_headers(get_random(user_agents))
    delay = random.choice(range(min_delay, max_delay))
    logging.info('got delay {}'.format(delay))
    time.sleep(delay)
    return requests.get('https://www.kinopoisk.ru{}'.format(link),
        headers=rnd_header,
        proxies=rnd_proxy,
    )


def extract_rating(soup):
    most_wanted = soup.find('div', class_='element most_wanted')
    if most_wanted:
        return soup.find('div', class_='rating').text


def extract_film_link(soup):
    most_wanted = soup.find('div', class_='element most_wanted')
    if most_wanted:
        return most_wanted.find('div', class_='info').p.a['data-url']
    return soup.find('link', rel='canonical')['href']


def get_random(from_iterable):
    if from_iterable:
        return random.choice(from_iterable)


def produce_headers(user_agent):
    logging.info(user_agent)
    return {'User-Agent': user_agent}


def parse_rating_and_link_from(kinopoisk_html):
    soup = BeautifulSoup(kinopoisk_html, 'html.parser')
    return extract_film_link(soup), extract_rating(soup)


def download_and_parse_film_ratings(title, proxy_ips, user_agents):
    response = download_kinopoisk_search_html(title, proxy_ips, user_agents)
    if response.ok:
        return parse_rating_and_link_from(response.text)


def extract_kinopoisk_title(soup):
    return soup.find('h1', class_='moviename-big').text


def extract_kinopoisk_img_link(from_soup):
    img_a = from_soup.find('a', class_='popupBigImage')
    if img_a:
        return img_a.img['src']


def extract_kinopoisk_description(from_soup):
    description = from_soup.find('div', class_='brand_words film-synopsys')
    if description:
        return description.text.strip()


def extract_kinopoisk_rating(from_soup):
    ratings_tag = from_soup.find(class_='rating_ball')
    if ratings_tag:
        return ratings_tag.text.strip()


def clean_noises(film_info_dict):
    if film_info_dict.get('сборы'):
        film_info_dict['сборы'] = re.sub(r'\bvar.*', r'', film_info_dict['сборы'])
    if film_info_dict.get('жанр'):
        film_info_dict['жанр'] = re.sub(r'слова', r'', film_info_dict['жанр'])
    return film_info_dict


def extract_kinopoisk_info(from_soup):
    from_soup = BeautifulSoup(from_soup.prettify(), 'html.parser') # add extra spaces to use split()
    film_info_dict = {}
    table_tag = from_soup.find('table', class_="info")
    if table_tag:
        for tr_tag in table_tag.find_all('tr'):
            film_info = tr_tag.text.split()
            film_info_dict[film_info[0]] = ' '.join(film_info[1:])
        film_info_dict = clean_noises(film_info_dict)
    return film_info_dict


def parse_kinopisk_film_page(film_html):
    soup = BeautifulSoup(film_html, 'html.parser')
    film_info_dict = {'rating': extract_kinopoisk_rating(soup),
                      'title': extract_kinopoisk_title(soup),
                      'img_link': extract_kinopoisk_img_link(soup),
                      'description': extract_kinopoisk_description(soup),}
    film_info_dict.update(extract_kinopoisk_info(soup))
    return film_info_dict


def download_and_parse_film_info(link, proxy_ips, user_agents):
    response = download_kinopoisk_film_html(link, proxy_ips, user_agents)
    logging.info('{} : {}'.format(link, response.status_code))
    if response.ok:
        film_info = parse_kinopisk_film_page(response.text)
        film_info.update({'film_link':
            'https://www.kinopoisk.ru{}'.format(link)})
        logging.info(film_info)
        return film_info


def fetch_ratings_and_links(popular_movies,
                            proxy_ips,
                            user_agents,
                            workers_number=4):
    def run(tasks, results, proxy_ips, user_agents):
        while True:
            title = tasks.get()
            logging.info('{} was taken'.format(title))
            results.append(
                download_and_parse_film_ratings(title, proxy_ips, user_agents))
            logging.info('{} was done'.format(title))
            tasks.task_done()
    tasks = Queue()
    for title in popular_movies:
        tasks.put(title)
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


def fetch_films_info(top_rated, proxy_ips, user_agents, workers_number=4):
    def run(tasks, results, proxy_ips, user_agents):
        while True:
            link = tasks.get()
            logging.info('{} was taken'.format(link))
            results.append(
                download_and_parse_film_info(link, proxy_ips, user_agents))
            logging.info('{} was done'.format(link))
            tasks.task_done()
    tasks = Queue()
    for film_link, rating in top_rated:
        tasks.put(film_link)
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


def fetch_top_films_info_from_kinopoisk(popular_movies,
                                        proxy_ips, user_agents, top_count):
    links_with_ratings = fetch_ratings_and_links(popular_movies, proxy_ips,
                                                 user_agents)
    logging.info(links_with_ratings)
    counter = Counter(dict(links_with_ratings))
    top_rated = counter.most_common(top_count)
    logging.info(top_rated)
    fake_request = requests.get(
        'https://www.kinopoisk.ru/afisha/new/city/2/sort_by/rating/#sort')
    return fetch_films_info(top_rated, proxy_ips, user_agents)


def download_afisha_schedule_cinema_page(
        afisha_cinema_url='https://www.afisha.ru/msk/schedule_cinema/'):
    response = requests.get(afisha_cinema_url)
    if not response.ok:
        response.raise_for_status()
    return response.text


def is_popular_by(cinemas_num, pop_level):
    return cinemas_num > pop_level


def find_popular_movies(pop_level, proxy_ips, user_agents):
    afisha_page = download_afisha_schedule_cinema_page()
    logging.info('Fetched afisha page')
    afisha_soup = BeautifulSoup(afisha_page, 'html.parser')
    popular_movies = []
    film_tags = afisha_soup.find_all('div', class_='m-disp-table')
    for film_div in film_tags:
        film_title = film_div.a.text
        cinemas_number = len(film_div.find_next('table').find_all('tr'))
        if is_popular_by(cinemas_number, pop_level):
            popular_movies.append(film_title)
    logging.info('\n'.join(popular_movies))
    return popular_movies


@cache.memoize(60*60*24)
def fetch_top_movies_with_data(top_count=10, pop_level=30):
    start = datetime.now()
    logging.info('Starting...')
    proxy_ips = fetch_proxy_ip_list()
    user_agents = make_useragents_list()
    popular_movies = find_popular_movies(pop_level, proxy_ips, user_agents)
    logging.info('Start fetching movies info')
    films_kinopoisk_info = fetch_top_films_info_from_kinopoisk(popular_movies,
                                                               proxy_ips,
                                                               user_agents,
                                                               top_count)
    logging.info('Total time: {}'.format(datetime.now() - start))
    return films_kinopoisk_info
