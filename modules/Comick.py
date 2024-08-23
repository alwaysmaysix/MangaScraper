import google_colab_selenium as gs
from selenium.webdriver.chrome.options import Options
from random import choice
import time
import json
from bs4 import BeautifulSoup
from utils.models import Manga  # Ensure you have the correct import path for your Manga model

# User-Agent rotation
user_agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
    'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; AS; rv:11.0) like Gecko',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.1 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.96 Safari/537.36'
]

# Function to set up Selenium in Google Colab
def setup_selenium():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--incognito")
    options.add_argument(f'--user-agent={choice(user_agents)}')
    driver = gs.Chrome(options=options)
    return driver

# Function to fetch page content using Selenium
def get_page_content(url, driver, request_interval=2, page_load_delay=2):
    driver.get(url)
    time.sleep(request_interval)
    html_content = driver.page_source
    time.sleep(page_load_delay)
    return html_content

# Comick class using Selenium for scraping
class Comick(Manga):
    domain = 'comick.io'
    logo = 'https://comick.io/static/icons/unicorn-256_maskable.png'
    headers = {'Referer': 'https://comick.io/'}
    download_images_headers = headers

    @staticmethod
    def get_info(manga):
        driver = setup_selenium()  # Initialize the Selenium driver
        url = f'https://comick.io/comic/{manga}'
        html_content = get_page_content(url, driver)  # Get page content via Selenium
        driver.quit()
        
        soup = BeautifulSoup(html_content, 'html.parser')
        data = json.loads(soup.find('script', {'id': '__NEXT_DATA__'}).get_text(strip=True))['props']['pageProps']
        extras = {item['md_genres']['group']: [d['md_genres']['name'] for d in data['comic']['md_comic_md_genres'] if d.get('md_genres', {}).get('group') == item['md_genres']['group']] for item in data['comic']['md_comic_md_genres']}
        extras['Artinsts'] = [ti['name'] for ti in data['artists']]
        extras['Authors'] = [ti['name'] for ti in data['authors']]
        extras['demographic'] = data['demographic']
        extras['Published'] = data['comic']['year']
        extras['Publishers'] = [ti['mu_publishers']['title'] for ti in data['comic']['mu_comics']['mu_comic_publishers']]
        extras['Categories'] = [ti['mu_categories']['title'] for ti in data['comic']['mu_comics']['mu_comic_categories']]
        return {
            'Cover': f'https://meo3.comick.pictures/{data["comic"]["md_covers"][0]["b2key"]}',
            'Title': data['comic']['title'],
            'Alternative': ', '.join([ti['title'] for ti in data['comic']['md_titles']]),
            'Summary': data['comic']['desc'],
            'Rating': float(data['comic']['bayesian_rating'])/2,
            'Status': 'Ongoing' if data['comic']['status'] == 1 else 'Completed',
            'Extras': extras
        }

    @staticmethod
    def get_chapters(manga):
        driver = setup_selenium()  # Initialize the Selenium driver
        url = f'https://comick.io/comic/{manga}'
        html_content = get_page_content(url, driver)  # Get page content via Selenium
        driver.quit()
        
        soup = BeautifulSoup(html_content, 'html.parser')
        script = soup.find('script', {'id': '__NEXT_DATA__'})
        hid = json.loads(script.get_text(strip=True))['props']['pageProps']['comic']['hid']
        chapters_urls = []
        page = 1
        while True:
            response, session = Comick.send_request(f'https://api.comick.io/comic/{hid}/chapters?lang=en&chap-order=1&page={page}', session=session)
            response = response.json()
            if not response['chapters']:
                break
            chapters_urls.extend([f'{chapter["hid"]}-chapter-{chapter["chap"]}-en' for chapter in response['chapters'] if chapter['chap']])
            page += 1
        chapters = [{
            'url': chapter_url,
            'name': Comick.rename_chapter(chapter_url)
        } for chapter_url in chapters_urls]
        return chapters

    @staticmethod
    def get_images(manga, chapter):
        driver = setup_selenium()  # Initialize the Selenium driver
        url = f'https://comick.io/comic/{manga}/{chapter["url"]}'
        html_content = get_page_content(url, driver)  # Get page content via Selenium
        driver.quit()
        
        soup = BeautifulSoup(html_content, 'html.parser')
        script = soup.find('script', {'id': '__NEXT_DATA__'})
        images = json.loads(script.get_text(strip=True))['props']['pageProps']['chapter']['md_images']
        images = [f'https://meo3.comick.pictures/{image["b2key"]}' for image in images]
        save_names = [f'{i+1:03d}.{images[i].split(".")[-1]}' for i in range(len(images))]
        return images, save_names

    @staticmethod
    def search_by_keyword(keyword, absolute):
        from requests.exceptions import HTTPError
        driver = setup_selenium()  # Initialize the Selenium driver
        url = f'https://comick.io/search'
        html_content = get_page_content(url, driver)  # Get page content via Selenium
        driver.quit()

        soup = BeautifulSoup(html_content, 'html.parser')
        script = soup.find('script', {'id': '__NEXT_DATA__'}).get_text(strip=True)
        genres = {genre['id']: genre['name'] for genre in json.loads(script)['props']['pageProps']['genres']}
        page = 1
        while True:
            try:
                response, session = Comick.send_request(f'https://api.comick.io/v1.0/search?q={keyword}&limit=300&page={page}', session=session)
            except HTTPError:
                yield {}
            mangas = response.json()
            results = {}
            for manga in mangas:
                if absolute and keyword.lower() not in manga['title'].lower():
                    continue
                results[manga['title']] = {
                    'domain': Comick.domain,
                    'url': manga['slug'],
                    'latest_chapter': manga['last_chapter'],
                    'thumbnail': f'https://meo.comick.pictures/{manga["md_covers"][0]["b2key"]}' if manga['md_covers'] else '',
                    'genres': ', '.join([genres[genre_id] for genre_id in manga['genres']]),
                    'page': page
                }
            yield results
            page += 1

    @staticmethod
    def get_db():
        return Comick.search_by_keyword('', False)

    @staticmethod
    def rename_chapter(chapter):
        chapter = chapter.split('-', 1)[1]
        new_name = ''
        reached_number = False
        for ch in chapter:
            if ch.isdigit():
                new_name += ch
                reached_number = True
            elif ch in '-.' and reached_number and new_name[-1] != '.':
                new_name += '.'
        if not reached_number:
            return chapter
        new_name = new_name.rstrip('.')
        try:
            return f'Chapter {int(new_name):03d}'
        except:
            return f'Chapter {new_name.split(".", 1)[0].zfill(3)}.{new_name.split(".", 1)[1]}'
