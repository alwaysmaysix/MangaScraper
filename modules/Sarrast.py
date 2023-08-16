from bs4 import BeautifulSoup
from utils.models import Manga

class Sarrast(Manga):
    domain = 'sarrast.com'

    def get_chapters(manga):
        response = Sarrast.send_request(f'https://sarrast.com/series/{manga}')
        soup = BeautifulSoup(response.text, 'html.parser')
        divs = soup.find('div', {'class': 'text-white mb-20 mt-8 relative px-4'}).find_all('a')
        chapters_urls = [div['href'].split('/')[-1] for div in divs[::-1]]
        chapters = [{
            'url': chapter_url,
            'name': Sarrast.rename_chapter(chapter_url)
        } for chapter_url in chapters_urls]
        return chapters

    def get_images(manga, chapter):
        response = Sarrast.send_request(f'https://sarrast.com/series/{manga}/{chapter["url"]}')
        soup = BeautifulSoup(response.text, 'html.parser')
        images = soup.find('div', {'class': 'episode w-full flex flex-col items-center'}).find_all('img')
        images = [f'https://sarrast.com{image["src"]}' for image in images]
        save_names = []
        for i in range(len(images)):
            save_names.append(f'{i+1:03d}.{images[i].split(".")[-1]}')
        return images, save_names

    def search_by_keyword(keyword, absolute):
        from requests.exceptions import HTTPError
        try:
            response = Sarrast.send_request(f'https://sarrast.com/search?value={keyword}')
            mangas = response.json()
            results = {}
            for manga in mangas:
                results[manga['title']] = {
                    'domain': Sarrast.domain,
                    'url': manga['slug'],
                }
            yield results
        except HTTPError:
            yield {}
        yield {}

    def get_db():
        return Sarrast.search_by_keyword('', False)