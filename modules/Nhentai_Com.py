from utils.models import Doujin
from user_agents import LEECH

class Nhentai_Com(Doujin):
    domain = 'nhentai.com'
    logo = 'https://cdn.nhentai.com/nhentai/images/icon.png'
    headers = {'User-Agent': LEECH}
    is_coded = False

    def get_info(code):
        from datetime import datetime
        response, _ = Nhentai_Com.send_request(f'https://nhentai.com/api/comics/{code}', headers=Nhentai_Com.headers)
        response = response.json()
        return {
            'Cover': response['image_url'],
            'Title': response['title'],
            'Pages': response['pages'],
            'Alternative': response['alternative_title'],
            'Extras': {
                'Parodies': [tag['name'] for tag in response['parodies']],
                'Characters': [tag['name'] for tag in response['characters']],
                'Tags': [tag['name'] for tag in response['tags']],
                'Artists': [tag['name'] for tag in response['artists']],
                'Authors': [tag['name'] for tag in response['authors']],
                'Groups': [tag['name'] for tag in response['groups']],
                'Languages': response['language']['name'] if response['language'] else '',
                'Category': response['category']['name'] if response['category'] else '',
                'Relationships': [tag['name'] for tag in response['relationships']]
            },
            'Dates': {
                'Uploaded At': datetime.strptime(response['uploaded_at'], '%Y-%m-%d').strftime('%Y-%m-%d %H:%M:%S') if response['uploaded_at'] else ''
            }
        }

    def get_title(code):
        response, _ = Nhentai_Com.send_request(f'https://nhentai.com/api/comics/{code}', headers=Nhentai_Com.headers)
        return response.json()['title']

    def get_images(code):
        response, _ = Nhentai_Com.send_request(f'https://nhentai.com/api/comics/{code}/images', headers=Nhentai_Com.headers)
        images = [image['source_url'] for image in response.json()['images']]
        return images, False

    def search_by_keyword(keyword, absolute):
        from contextlib import suppress
        page = 1
        tail = '&sort=title' if not keyword else ''
        session = None
        while True:
            response, session = Nhentai_Com.send_request(f'https://nhentai.com/api/comics?page={page}&q={keyword}{tail}', session=session, headers=Nhentai_Com.headers)
            doujins = response.json()['data']
            if not doujins:
                yield {}
            results = {}
            for doujin in doujins:
                if absolute and keyword.lower() not in doujin['title'].lower():
                    continue
                category, language, tags = '', '', ''
                with suppress(Exception): category = doujin['category']['name']
                with suppress(Exception): language = doujin['language']['name']
                with suppress(Exception): tags = ', '.join([tag['name'] for tag in doujin['tags']])
                results[doujin['title']] = {
                    'domain': Nhentai_Com.domain,
                    'code': doujin['slug'],
                    'thumbnail': doujin['image_url'],
                    'category': category,
                    'language': language,
                    'tags': tags,
                    'page': page
                }
            yield results
            page += 1

    def get_db():
        return Nhentai_Com.search_by_keyword('', False)