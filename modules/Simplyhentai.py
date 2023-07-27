from bs4 import BeautifulSoup
from utils.models import Doujin

class Simplyhentai(Doujin):
    domain = 'simplyhentai.org'

    def get_title(code):
        response = Simplyhentai.send_request(f'https://simplyhentai.org/g/{code}')
        soup = BeautifulSoup(response.text, 'html.parser')
        title = soup.find('h1', {'class', 'title'}).find('span').get_text(strip=True)
        return title

    def get_images(code):
        response = Simplyhentai.send_request(f'https://simplyhentai.org/g/{code}/')
        soup = BeautifulSoup(response.text, 'html.parser')
        divs = soup.find_all('a', {'class': 'gallerythumb'})
        images = [div.find('img')['src'] for div in divs]
        new_images = []
        for image in images:
            name = image.rsplit('/', 1)[1]
            name = name.replace('t.', '.')
            new_images.append(f'{image.rsplit("/", 1)[0]}/{name}')
        return new_images, False

    def search_by_keyword(keyword, absolute):
        from requests.exceptions import HTTPError
        page = 1
        while True:
            try:
                response = Simplyhentai.send_request(f'https://simplyhentai.org/search?q={keyword}&page={page}')
            except HTTPError:
                yield {}
            soup = BeautifulSoup(response.text, 'html.parser')
            doujins = soup.find_all('div', {'class': 'gallery'})
            if len(doujins) == 0:
                yield {}
            results = {}
            for doujin in doujins:
                if absolute and keyword.lower() not in doujin.get_text(strip=True).lower():
                    continue
                results[doujin.get_text(strip=True)] = {
                    'domain': Simplyhentai.domain,
                    'code': doujin.find('a')['href'].split('/')[-2],
                    'page': page
                }
            yield results
            page += 1

    def get_db():
        return Simplyhentai.search_by_keyword('', False)