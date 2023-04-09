import natsort, time, sys, os
from termcolor import colored
from utils import assets, exceptions
from requests.exceptions import RequestException, HTTPError, Timeout

def download_single(manga, url, source, sleep_time, is_all, last, ranged, chapters, merge, convert_to_pdf):
    chapters_to_download = get_name_of_chapters(manga, url, source, is_all, last, ranged, chapters)
    inconsistencies = download_manga(manga, url, source, sleep_time, chapters_to_download, merge, convert_to_pdf)
    if inconsistencies:
        print(colored(f'There were some inconsistencies with the following chapters: {", ".join(inconsistencies)}', 'red'))

def get_name_of_chapters(manga, url, source, is_all, last, ranged, c_chapters):
    ctd = []
    sys.stdout.write(f'\r{manga}: Getting name of chapters...')
    chapters = source.get_chapters(url)
    if is_all:
        ctd = chapters.copy()
    if last:
        reached_last_downloaded_chapter = False
        last_downloaded_chapter = source.rename_chapter(str(last))
        for chapter in chapters:
            if source.rename_chapter(chapter) == last_downloaded_chapter:
                reached_last_downloaded_chapter = True
                continue
            if reached_last_downloaded_chapter:
                ctd.append(chapter)
    if ranged:
        reached_beginning_chapter = False
        beginning_chapter = source.rename_chapter(str(ranged[0]))
        ending_chapter = source.rename_chapter(str(ranged[1]))
        for chapter in chapters:
            renamed_chapter = source.rename_chapter(chapter)
            if renamed_chapter == beginning_chapter:
                reached_beginning_chapter = True
            if reached_beginning_chapter:
                ctd.append(chapter)
            if renamed_chapter == ending_chapter:
                break
    if c_chapters:
        renamed_chapters = [source.rename_chapter(str(c)) for c in c_chapters]
        ctd += [chapter for chapter in chapters if (source.rename_chapter(chapter) in renamed_chapters and chapter not in ctd)]
    print(f'\r{manga}: There are totally {len(ctd)} chapters to download.')
    return sorted(ctd, key=lambda _: (source.rename_chapter, natsort.os_sorted))

def download_manga(manga, url, source, sleep_time, chapters, merge, convert_to_pdf):
    inconsistencies = []
    last_truncated = None
    fixed_manga = assets.fix_name_for_folder(manga)
    assets.create_folder(fixed_manga)
    while len(chapters) > 0:
        chapter = chapters[0]
        renamed_chapter = source.rename_chapter(chapter)
        try:
            sys.stdout.write(f'\r{manga}: {chapter}: Getting image links...')
            images, save_names = source.get_images(url, chapter)
            sys.stdout.write(f'\r{manga}: {chapter}: Creating folder...')
            assets.create_folder(f'{fixed_manga}/{renamed_chapter}')
            adder = 0
            for i in range(len(images)):
                sys.stdout.write(f'\r{manga}: {chapter}: Downloading image {i+adder+1}/{len(images)+adder}...')
                if not save_names:
                    if f'{i+adder+1}' not in images[i].split('/')[-1]:
                        adder += 1
                        inconsistencies.append(f'{manga}/{chapter}/{i+adder:03d}.{images[i].split(".")[-1]}')
                        print(colored(f' Warning: Inconsistency in order of images!!!. Skipped image {i + adder}', 'red'))
                        sys.stdout.write(f'\r{manga}: {chapter}: Downloading  image {i+adder+1}/{len(images)+adder}...')
                    save_path = f'{fixed_manga}/{renamed_chapter}/{i+adder+1:03d}.{images[i].split(".")[-1]}'
                else:
                    save_path = f'{fixed_manga}/{renamed_chapter}/{save_names[i]}'
                if not os.path.exists(save_path):
                    time.sleep(sleep_time)
                    try:
                        response = source.send_request(images[i])
                    except HTTPError:
                        print(f'Could not download image {i+adder+1}: {images[i]}')
                        continue
                    with open(save_path, 'wb') as image:
                        image.write(response.content)
                    if not assets.validate_corrupted_image(save_path):
                        print(colored(f' Warning: Image {i+adder+1} is corrupted. will not be able to merge this chapter', 'red'))
                        continue
                    if not assets.validate_truncated_image(save_path) and last_truncated != save_path:
                        raise exceptions.TruncatedException(save_path)
            print(colored(f'\r{manga}: {chapter}: Finished downloading, {len(images)} images were downloaded.', 'green'))
            del chapters[0]
            if merge:
                from utils.image_merger import merge_folder
                merge_folder(f'{manga}/{renamed_chapter}', f'Merged/{manga}/{renamed_chapter}', f'{manga}: {chapter}')
            if convert_to_pdf:
                from utils.pdf_converter import convert_folder
                convert_folder(f'{manga}/{renamed_chapter}', manga, f'{manga}_{renamed_chapter}.pdf', f'{manga}: {chapter}')
        except (Timeout, HTTPError, exceptions.ImageMergerException, exceptions.PDFConverterException) as error:
            print(colored(error, 'red'))
        except RequestException:
            assets.waiter()
        except exceptions.TruncatedException as error:
            last_truncated = error.save_path
            os.remove(last_truncated)
            print(colored(error, 'red'))
    return inconsistencies