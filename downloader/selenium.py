from download import get_user_input

#from selenium import webdriver
import selenium

# browser = webdriver.Chrome()
# query = str(query).replace(' ', '+')
# url = f'https://www.google.co.in/search?q={query}&source=lnms&tbm=isch'
# # Wait for the content of the url to load completely - onload mode
# #browser.get(url)

# This is the path I use
# DRIVER_PATH = '.../Desktop/Scraping/chromedriver 2'
# Put the path for your ChromeDriver here
DRIVER_PATH = '/home/manal/Downloads/chromedriver'
wd = webdriver.Chrome(executable_path=DRIVER_PATH)