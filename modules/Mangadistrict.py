from bs4 import BeautifulSoup
from utils.models import Manga

class Mangadistrict(Manga):
    domain = 'mangadistrict.com'
    logo = 'https://mangadistrict.com/wp-content/uploads/2021/02/cropped-Copie-de-Copie-de-MANGADISTRICT_5-192x192.png'

    def get_chapters(manga, wait=True):
        response = Mangadistrict.send_request(f'https://mangadistrict.com/read-scan/{manga}/ajax/chapters/', method='POST', wait=wait)
        soup = BeautifulSoup(response.text, 'html.parser')
        divs = soup.find_all('li', {'class':'wp-manga-chapter'})
        chapters_urls = [div.find('a')['href'].split('/')[-2] for div in divs[::-1]]
        chapters = [{
            'url': chapter_url,
            'name': Mangadistrict.rename_chapter(chapter_url)
        } for chapter_url in chapters_urls]
        return chapters

    def get_images(manga, chapter, wait=True):
        response = Mangadistrict.send_request(f'https://mangadistrict.com/read-scan/{manga}/{chapter["url"]}/', wait=wait)
        soup = BeautifulSoup(response.text, 'html.parser')
        images = soup.find('div', {'class':'reading-content'}).find_all('img')
        images = [image['src'].strip() for image in images]
        save_names = []
        for i in range(len(images)):
            save_names.append(f'{i+1:03d}.{images[i].split(".")[-1]}')
        return images, save_names

    def search_by_keyword(keyword, absolute, wait=True):
        from contextlib import suppress
        from requests.exceptions import HTTPError
        page = 1
        template = f'https://mangadistrict.com/page/P_P_P_P/?s={keyword}&post_type=wp-manga'
        if not keyword:
            template = 'https://mangadistrict.com/page/P_P_P_P/?s&post_type=wp-manga&m_orderby=alphabet'
        while True:
            try:
                response = Mangadistrict.send_request(template.replace('P_P_P_P', str(page)), wait=wait)
            except HTTPError:
                yield {}
            soup = BeautifulSoup(response.text, 'html.parser')
            mangas = soup.find_all('div', {'class': 'row c-tabs-item__content'})
            results = {}
            for manga in mangas:
                tilink = manga.find('div', {'class', 'post-title'})
                if absolute and keyword.lower() not in tilink.get_text(strip=True).lower():
                    continue
                latest_chapter, authors, artists, genres, status, release_date = '', '', '', '', '', ''
                contents = manga.find_all('div', {'class': 'post-content_item'})
                for content in contents:
                    with suppress(Exception):
                        if 'Authors' in content.text:
                            authors = content.find('div', {'class': 'summary-content'}).get_text(strip=True)
                        if 'Artists' in content.text:
                            artists = content.find('div', {'class': 'summary-content'}).get_text(strip=True)
                        if 'Genres' in content.text:
                            genres = content.find('div', {'class': 'summary-content'}).get_text(strip=True)
                        if 'Status' in content.text:
                            status = content.find('div', {'class': 'summary-content'}).get_text(strip=True)
                        if 'Release' in content.text:
                            release_date = content.find('a').get_text(strip=True)
                with suppress(Exception): latest_chapter = manga.find('span', {'class': 'font-meta chapter'}).find('a')['href'].split('/')[-2]
                results[tilink.get_text(strip=True)] = {
                    'domain': Mangadistrict.domain,
                    'url': tilink.find('a')['href'].split('/')[-2],
                    'latest_chapter': latest_chapter,
                    'thumbnail': manga.find('img')['src'],
                    'genres': genres,
                    'authors': authors,
                    'artists': artists,
                    'status': status,
                    'release_date': release_date,
                    'page': page
                }
            yield results
            page += 1

    def get_db(wait=True):
        return Mangadistrict.search_by_keyword('', False, wait=wait)