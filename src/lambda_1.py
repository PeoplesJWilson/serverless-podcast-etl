from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

import boto3
import time
import json
import os

BUCKET_NAME = os.environ['ENV_VAR_1']
print(f"Bucket name is: {BUCKET_NAME}")
s3 = boto3.client('s3')


def get_rss_feeds(event, context):

    try:
    # Get the podcast name from the SQS message body
        search_url = event['Records'][0]['body']


    except Exception as e:
        print(f"Error: {e}")
    
    print("fixing podcast to conform with format")
    search_url = search_url.replace(' ','+')

    url = f"https://podcastaddict.com/?q={search_url}"

    # Setup chrome options
    chrome_options = Options()
    chrome_options.binary_location = '/opt/headless-chromium'
    chrome_options.add_argument("--headless") # Ensure GUI is off
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--single-process")
    chrome_options.add_argument("--disable-dev-shm-usage")


    # Choose Chrome Browser
    browser = webdriver.Chrome('/opt/chromedriver', chrome_options=chrome_options)
    browser.get(url=url)

    time.sleep(10)
    results = browser.find_elements(By.CLASS_NAME, "clickeableItemRow")


    # extract link from each result
    result_links = [result.get_attribute('href') for result in results]

    # only collect a maximum of 10 feeds from a search
    num_links = min(10, len(result_links))

    result_links = result_links[0:num_links]

    feeds = []
    # following loop collects all feeds
    for count,link in enumerate(result_links):
        browser.get(url = link)     # navigate to specific result
        elements = browser.find_elements(By.TAG_NAME,"link")
        links = [element.get_attribute('href') for element in elements] # extract all links on the page

        feeds.append([feed for feed in links if "feed" in feed or "rss" in feed]) # keep only the links containing substrings

        print(f"number of links found on result {count}: {len(links)}")
        print(f"number of feeds found on result {count}: {len(feeds)}")

    browser.quit()

    # prepend some feeds not contained in search results
    feeds = [feed[0] for feed in feeds]
    feeds = ["https://feeds.megaphone.fm/the-watch"] + feeds
    feeds = ["https://feeds.megaphone.fm/the-bill-simmons-podcast"] + feeds

    # transform feeds 
    data = [(feed.split('/')[-1], feed) for feed in feeds]
    data = [("podcast_name", "rss_feed")] + data

    # load into s3
    # json_data = json.dumps(data)
    json_data = json.dumps(data)
    key_name = f"{BUCKET_NAME}.json"
    s3.put_object(Body=json_data, Bucket=BUCKET_NAME, Key=key_name)