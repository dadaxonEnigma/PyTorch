import os
import sys
import urllib3
from urllib.parse import urlparse
import pandas as pd
import itertools
import shutil
import requests
from urllib3.util import Retry
from concurrent.futures import ThreadPoolExecutor, as_completed

# Отключаем предупреждения о небезопасных запросах
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Классы для загрузки
classes = ["cat", "fish"]
set_types = ["train", "test", "val"]

# Функция для проверки доступности URL
def is_url_accessible(url):
    try:
        # Отправляем HEAD запрос, чтобы проверить доступность URL
        response = requests.head(url, timeout=10)
        # Проверяем, что статус код 200 (OK)
        return response.status_code == 200
    except requests.RequestException as e:
        # В случае ошибки, выводим сообщение
        print(f"Error checking URL {url}: {e}")
        return False

# Функция для загрузки изображений
def download_image(url, klass, data_type):
    basename = os.path.basename(urlparse(url).path)
    filename = "{}/{}/{}".format(data_type, klass, basename)
    
    # Проверка, существует ли уже файл
    if not os.path.exists(filename):
        # Проверка доступности URL перед загрузкой
        if is_url_accessible(url):
            try: 
                # Настроим пул запросов с автоматическими попытками
                http = urllib3.PoolManager(retries=Retry(connect=1, read=1, redirect=2))
                with http.request("GET", url, preload_content=False) as resp, open(
                    filename, "wb"
                ) as out_file:
                    if resp.status == 200:
                        shutil.copyfileobj(resp, out_file)
                        print(f"Downloaded: {filename}")
                    else:
                        print(f"Error downloading {url}: Status code {resp.status}")
                resp.release_conn()
            except Exception as e:
                print(f"Error downloading {url}: {str(e)}")
        else:
            print(f"Skipping {url} (URL is not accessible)")

# Основной блок программы
if __name__ == "__main__":
    if not os.path.exists("images.csv"):
        print("Error: can't find images.csv!")
        sys.exit(0)

    # Считываем CSV файл
    imagesDF = pd.read_csv("images.csv", names=["url", "class", "type"], header=None)

    # Создаем папки для хранения изображений, если их нет
    for set_type, klass in list(itertools.product(set_types, classes)):
        path = "./{}/{}".format(set_type, klass)
        if not os.path.exists(path):
            print(f"Creating directory {path}")
            os.makedirs(path)

    # Загрузка изображений с использованием параллельной загрузки
    print(f"Downloading {len(imagesDF)} images...")

    # Инициализация пула потоков для параллельной загрузки
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = []
        for index, row in imagesDF.iterrows():
            url = row['url']
            klass = row['class']
            data_type = row['type']
            
            # Добавляем задачу в пул потоков
            future = executor.submit(download_image, url, klass, data_type)
            futures.append(future)

        # Ожидаем завершения всех потоков
        for future in as_completed(futures):
            future.result()

    print("All downloads complete!")
    sys.exit(0)
