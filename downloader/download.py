# ------------------------------------------------------------------------------
# Downloads google images based on the query classes into ImageNet-style dataset
# 2020 Manal El Aidouni
# email mm.elaidouni@gmail.com
# ------------------------------------------------------------------------------


import argparse
import csv
import os
import json
import time
import winreg

from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path
from sys import platform
from typing import List, Tuple, Union

from bs4 import BeautifulSoup
from PIL import Image
import requests
from requests.exceptions import Timeout, HTTPError, ConnectionError

# =================
# Utility functions
# =================

def path_dir(dir_string: Union[str, Path]) -> Union[Path, str]:
    """ Checks if the given directory string is a valid directory.

    Args:
        dir_string: The directory string given by the user.
    Raises:
        NotADirectoryError: If the given directory is not a valid one.
    """

    if Path(dir_string).is_dir():
        return dir_string
    raise NotADirectoryError(f'No such directory, please enter a valid directory path.')


def default_path_downloads() -> Path:
    """ Downloads the images folder to the Downloads directory in Windows/ Linux/ Mac OS.

    """

    if platform == 'win32' or platform == 'win64' :
        # open the windows registry key for the current user
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders') as key:
            # get the registry value for the 'Downloads' directory path based on its GUID.
            location = winreg.QueryValueEx(key, "{374DE290-123F-4565-9164-39C4925E467B}")[0] # returns a tuple, the first element is the value of the registry

    else:
        location = Path.home()/ 'Downloads'

    return Path(location) 


def create_folder(output_dir: Union[Path, str], folder_name: str) -> Path:
    """ Creates a folder in the given or default path directory and returns its Path object.
    
    Args:
        output_dir: Main directory where the folder containing the images is saved.
        folder_name: Name of folder conataining the images.
    
    Returns:
        A folder created in the main directory 'output_dir'.
    """

    if Path(output_dir).exists():
        folder = Path(output_dir)/folder_name
        folder.mkdir(parents=True, exist_ok=True)
        return folder


def default_query_name(query: str) -> str:
    """ Converts a query string into a string format appropriate for file or/and folder naming if not specified by user.

    Args:
        query: A query string.
    """

    query_string = str(query.strip("['']")).replace('+', '_')
    name = query_string.replace(' ', '_') if ' ' in query_string else query_string
    return name
 

def save_urls_csv(data: List[Tuple[str, str]], output_dir: Union[Path, str], name: str) -> None:
    """ Takes a list of url images and their extensions and saves them into a csv file into path.
    
    Args:
        data: List of image urls and their corresponding extensions.
        output_dir: Main directory where the folder containing the images is saved.
        name: Given csv filename.
    """

    p = Path(output_dir)
    filename = name + '_urls.csv'

    if Path(output_dir).exists():
        with open(p/filename, 'w') as f:
            writer = csv.writer(f)
            writer.writerow(['image_url', 'extension'])
            writer.writerows(data)



# ======================
# Command line arguments
# ======================

def get_user_input() -> dict:
    """ Parses command-line arguments.
    
    Returns: 
        Argument namespace dictionary.
    """

    parser = argparse.ArgumentParser(description='Downloads images in bulk.')
    parser.add_argument('-q', '--query', type=str, nargs='*', help='The search query.')
    parser.add_argument('-n', '--num_images', type=int, default=100, help='Number of images to download. Defaults to 100 if unspecified.')
    parser.add_argument('-l', '--list_queries', action='append', nargs='*', help='List of different queries to download at the same time.')
    parser.add_argument('-o', '--output_dir', type=path_dir, help='Main directory path where the folder containg the images would be saved. Defaults to "Downloads" directory if unspecified.')
    parser.add_argument('-fn', '--folder_name', type=str, help='Name of the folder in the main directory that will contain the image for a search query. Names the folder after the search query if unspecified.')
    parser.add_argument('-s', '--urls_to_csv', action='store_true', help='Save the image urls and their extensions to a csv file.')
    parser.add_argument('-jc', '--just_csv_no_download', action='store_true', help='Save urls and their extensions in a csv format without downloading images.')

    args = parser.parse_args()
    return vars(args)


def fetch_image_urls(url: str, query: str) -> List[Tuple[str, str]]:
    """ Get the content of google search based on a query and parse the html for urls and extensions.

    Args:
        url: The url for Google image with the query string. 
        query: A query string.

    Returns: 
        list of tuples of image urls and their corresponding extensions.

    Raises:
        Timeout: If the request times out.
        HTTPError: If there is an invalid HTTP response.
    """

    headers = {'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5)AppleWebKit/605.1.15 (KHTML, like Gecko)Version/12.1.1 Safari/605.1.15'}

    # Send a request to the google image page with query and get an html response
    # Parse the html response using BeautifulSoup
    try:
        response = requests.get(url, headers=headers, timeout=10)
        time.sleep(1)
        soup = BeautifulSoup(response.content, 'html.parser')
        
    except Timeout as e:
        print(f'The request has timed out, check your connection or/and proxy settings \n{e}')
    
    except HTTPError as e:
        print(f'An invalid HTTP response. \n{e}')

    
    # parse the html for the image urls and their extensions, save them to Images list of tuples 
    images = []
    parse_result = soup.find_all('div', {'class':'rg_meta notranslate'})
    
    for a in parse_result:
        img_url = json.loads(a.text)['ou']
        img_extension = json.loads(a.text)['ity']
        # save the image urls and extensions to 'images' list
        images.append((img_url, img_extension))
    
    return images



def download_image_from_url(image_tuple: Tuple[str, str], query: str, idx: int, output_dir: Path, folder_name: str) -> None:
    """ Requests the image url from 'image_tuple' and saves the returned image into a folder, either in a given/Downloads directory.
    
    Args:
        image_list: An image url and its corresponding extension.
        query: A query string. 
        idx: A number keeping count of the image to download,it's used in the image filename.
        output_dir: Main directory where the folder containing the images is saved. 
        folder_name: Name of folder conataining the images.

    Raises:
        IOError: If the path or/and filename are not valid.
        Timeout: If the request for an image times out.
        HTTPError: If there is an invalid HTTP response.
        ConnectionError: If there is a network problem.
    """ 

    img_url, extension = image_tuple
    headers = {'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5)AppleWebKit/605.1.15 (KHTML, like Gecko)Version/12.1.1 Safari/605.1.15'}
    try:
        # request the image url 
        res = requests.get(img_url, stream=True, headers=headers, timeout=(20, 40)) # pass a (connect, read) timeout
        res.raw.decode_content = True # raw content is not decoded automatically by requests
        res = res.raw

        filename = 'image_'+ str(idx) + '.' + extension
        
        # create and get the folder path in the output directory or in Downloads if not specified.
        output_dir = default_path_downloads() if output_dir is None else output_dir
        folder_name = default_query_name(query) if folder_name  is None else  folder_name
        
        path = create_folder(output_dir, folder_name) 
        
        try:
            # save image in folder
            with open(path/filename, 'wb') as f:  
                for chunck in res:
                    f.write(chunck)
        
        except IOError as e:
            print(f'Failed to save the image. \n{e}')


    # Timeout catchs both connect and read timeouts
    except Timeout as e:
        print(f'The request for one image has timed out, check your connection or/and proxy settings \n{e}\nDownloading continues ..')
        
    except HTTPError as e:
        print(f'An invalid HTTP response. \n{e}\nDownloadingcontinues ..')

    except ConnectionError as e:
        print(f'Connection error occurred. Please try again \n{e}\nDownloading continues ..')
        


def download_images_single_query_async(query: str, output_dir: Union[Path, str], folder_name: str, just_csv_no_download: bool, urls_to_csv: bool) -> None: 
    """  fetch image urls from google search and download them in a folder in the main directory.

    Args:
        query: A search query.
        output_dir: Main directory where the folder containing the images is saved.
        folder_name: Name of folder conataining the images.
        just_csv_no_download: Downloads the image urls with their extensions in a csv format without downloading the images.
        urls_to_csv: Saves the image urls with their extensions in a csv format.
    """

    # for multi-word queries 
    query = str(query).replace(' ', '+')
    url = f'https://www.google.co.in/search?q={query}&source=lnms&tbm=isch'
    

    # Request the query and parse for image urls and extensions
    images = fetch_image_urls(url, query)

    csv_filename = default_query_name(query)
    
    # If the user wants to download the images
    if not just_csv_no_download:

        with ThreadPoolExecutor(max_workers=5) as executor:
            future = (executor.submit(download_image_from_url, image, query, idx, output_dir, folder_name) for idx, image in enumerate(images))
            for f_instance in as_completed(future):
                f_instance

    # Save the 'images' list to a csv file when the flag is called
    if urls_to_csv or just_csv_no_download: 
        save_urls_csv(images, output_dir, csv_filename)


def download_list_queries(list_queries: List, output_dir: Union[Path, str], folder_name: str, just_csv_no_download: bool, urls_to_csv: bool) -> None:
    """ Downloads a list of queries concurrently.
    
    Args:
        output_dir: Main directory where the folder containing the images is saved.
        list_queries:  A list of search queries.
        folder_name: Name of folder conataining the images.
        just_csv_no_download: Downloads the image urls with their extensions in a csv format without downloading the images.
        urls_to_csv: Saves the image urls with their extensions in a csv format.
    """
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        future = (executor.submit(download_images_single_query_async, query, output_dir, folder_name, just_csv_no_download, urls_to_csv) for query in list_queries)
        for f_instance in as_completed(future):
            f_instance   



# Put conditions in main() 
if __name__ == '__main__':
    
    inputs = get_user_input()
    # Unpack the dictionary keys
    query = inputs['query']
    urls_to_csv = inputs['urls_to_csv']
    output_dir = inputs['output_dir']
    num_images = inputs['num_images']
    folder_name = inputs['folder_name']
    just_csv_no_download = inputs['just_csv_no_download']
    list_queries = inputs['list_queries']

    if query:
        download_images_single_query_async(query, output_dir, folder_name, just_csv_no_download, urls_to_csv)

    # list of queries CLI input example: -l dog -l cat -l horse
    if list_queries:
        print(list_queries)
        # Turn [['dog'], ['horse'], ['cat'], ['red', 'bear']] into a list of strings
        list_queries = map(lambda query: ' '.join(c for c in query if c not in "[''],"), list_queries)
        download_list_queries(list_queries, output_dir, folder_name, just_csv_no_download, urls_to_csv)
    
    