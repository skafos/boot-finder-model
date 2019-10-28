# Import libraries
import os
import re
import sys
import json
import boto3
from zipfile import ZipFile
import urllib
import requests
from datetime import datetime
from bs4 import BeautifulSoup


# Some constants
DATASET_ID_FORMAT = "%Y%m%d%H%M%S"
BASE_URL = "https://www.zappos.com/"
WOMENS_BOOTS_URL = BASE_URL + "women-boots/CK_XARCz1wHAAQHiAgMBAhg.zso"

S3_OUTPUT_BUCKET = "skafos.bootfinder/"
IMG_PATH = "images/"
IMG_ZIPFILE = "input_images.zip"
META_FILE = "image-metadata.json"


def check_create_dir(dir_name: str):
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)


class Boot:
    def __init__(self, boot_id, rating, buy_link, src_url, label):
        self.boot_id = boot_id
        self.rating = rating
        self.buy_link = buy_link
        self.image_source = src_url
        self.boot_name = label.split('. By')[0]
        self.brand = re.search("By (.*?) \$", label).group(1).strip('.')
        self.price = "$" + re.search("\$(.*?) ", label).group(1).strip('.')
        self.style = re.search("Style: (.*?)\.", label).group(1)

    def download(self):
        try:
            with open(IMG_PATH + self.boot_id, "wb") as f:
                f.write(requests.get(self.image_source).content)
            return True
        except:
            print("Bad Link: {}".format(self.image_source), flush=True)
            return False


class Zappos:
    def __init__(self):
        self.boots = []
        self.boot_ids = set()
        self.dataset_id = datetime.now().strftime(DATASET_ID_FORMAT)

    def scrape(self):
        n = 1
        while True:
            print("Processing page {} of boots".format(n), flush=True)
            url = WOMENS_BOOTS_URL + "?p={}".format(n)
            page = urllib.request.urlopen(url)
            soup = BeautifulSoup(page, 'html.parser')
            all_links = soup.find_all('a')
            valid_page_links = 0
            # Process data
            for link in all_links:
                aria_label = link.get('aria-label')
                buy_link = link.get('href')
                if aria_label and link.img and buy_link:
                    # Sort to make sure that what we get back has a price, ensuring it is a boot we want to include
                    if aria_label.find('$') != -1:
                        valid_page_links += 1
                        # Use the image name as the id
                        _id = link.img['src'].split('/')[-1]
                        # Check for a rating in the label
                        rating = re.search("Rated (.*?)\.", aria_label)
                        if rating:
                            rating = rating.group(1)
                        # Create a boot and add to list
                        boot = Boot(boot_id=_id,
                                    rating=rating,
                                    buy_link=BASE_URL + buy_link.strip('/'),
                                    src_url=link.img['src'],
                                    label=aria_label)
                        res = boot.download()
                        if res:
                            self.boots.append(boot)
            if valid_page_links == 0:
                print("No more valid boot links found. Done ingesting.\n", flush=True)
                break
            n += 1

    def _make_metadata(self):
        for d in self.boots:
            if d.boot_id not in self.boot_ids:
                self.boot_ids.add(d.boot_id)
        # Pull out boots meta data, ensure uniqueness, and sort by boot id
        boots_metadata = sorted(list({b['boot_id']:b for b in [boot.__dict__ for boot in self.boots]}.values()), key=lambda x: x['boot_id'])
        assert len(boots_metadata) == len(self.boot_ids), "Meta Data and IDs don't match!! Don't go any further."
        with open(META_FILE, 'w') as f:
            json.dump(boots_metadata, f)

    def _zip_images(self):
        with ZipFile(IMG_ZIPFILE, 'w') as zipf:
            for f in os.listdir(IMG_PATH):
                if not f.startswith("."):
                    zipf.write(IMG_PATH + f)

    def _write_file_s3(self, bucket, filepath):
        obj = self.dataset_id + "/" + filepath
        s3 = boto3.resource('s3')
        s3_bucket = s3.Bucket(bucket)
        with open(filepath, 'rb') as data:
            s3_bucket.put_object(Key=obj, Body=data)

    def upload_boots(self, bucket):
        if not self.boots:
            print("No boots to upload...", flush=True)
            sys.exit(1)
        self._make_metadata()
        print("Uploading metadata", flush=True)
        self._write_file_s3(bucket, META_FILE)
        self._zip_images()
        print("Uploading images zipfile", flush=True)
        self._write_file_s3(bucket, IMG_ZIPFILE)


if __name__ == "__main__":
    # create folder for our boot images
    check_create_dir(IMG_PATH)

    zappos = Zappos()
    zappos.scrape()
    zappos.upload_boots(bucket=S3_OUTPUT_BUCKET)
    print("Done.", flush=True)
