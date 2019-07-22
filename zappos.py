# Import libraries
import os
import re
import sys
import json
import s3fs
import urllib
import requests
import pandas as pd
import numpy as np
import coremltools
import turicreate as tc
from tqdm import tqdm
from skafos import models
from datetime import datetime
from bs4 import BeautifulSoup


# Some constants
DATASET_ID_FORMAT = "%Y%m%d%H%M%S"
BASE_URL = "https://www.zappos.com/"
WOMENS_BOOTS_URL = BASE_URL + "women-boots/CK_XARCz1wHAAQHiAgMBAhg.zso"
N = 1  # track page number

# Model constants
RETRAIN_THRESH = 1
MODEL_NAME = "ImageSimilarity"
COREML_MODEL_NAME = MODEL_NAME + ".mlmodel"
APP_NAME = "BootFinder"
MODEL_TYPE = "resnet-50"

# S3 Filesystem
S3_CNX = s3fs.S3FileSystem(anon=False)
BUCKET = "skafos.bootfinder/"
IMG_PATH = '/boot_images/'
META_FILE = 'boots_meta_data.json'


# Functions
def upload_boots_to_s3(s3, meta_data):
    # Upload new data to s3
    dataset = datetime.now().strftime(DATASET_ID_FORMAT)
    # Write the meta data dictionary locally and to s3
    print("Writing meta data json file to local and s3", flush=True)
    with open(META_FILE, 'w') as f:
        f.write(json.dumps(meta_data))
    with s3.open(BUCKET + dataset + '/' + META_FILE, 'w') as f:
        f.write(json.dumps(meta_data))
    # Write new images to s3
    print("Fetching and Saving images to s3", flush=True)
    for img in tqdm(meta_data):
        with s3.open(BUCKET + dataset + IMG_PATH + img['boot_id'], 'wb') as f:
            f.write(requests.get(img['image_source']).content)
    return dataset


def retrain_image_similarity_model(s3, dataset):
    print("\nRetraining image similarity model on dataset {}!".format(dataset), flush=True)
    # Pull in boot images from S3
    _local_dir = 'boot_images'
    if not os.path.exists(_local_dir):
        os.makedirs(_local_dir)
    # List out boots
    boots = s3.ls("s3://skafos.bootfinder/{}/boot_images/".format(dataset))
    # Download boot images from s3
    print("Pulling boot images to train model", flush=True)
    for b in tqdm(boots):
        _local_file = "/".join(b.split("/")[-1:])
        _local_path = _local_dir + "/" + _local_file
        s3.get("s3://" + b, _local_path)
    # Create boot SFrame
    boot_data  = tc.image_analysis.load_images('boot_images')
    boot_data = boot_data.add_row_number()
    # Build image similarity model using Resnet
    model = tc.image_similarity.create(boot_data, model=MODEL_TYPE)
    return model


def upload_model_to_s3(s3, dataset, new_skus):
    print("\nUploading trained model to s3", flush=True)
    with open(COREML_MODEL_NAME, 'rb') as model_data:
        with s3.open(BUCKET + dataset + '/' + COREML_MODEL_NAME, 'wb') as f:
            f.write(model_data.read())
    print("Uploading list of new skus included in the model since last run")
    with s3.open(BUCKET + dataset + '/new_skus.json', 'w') as f:
        f.write(json.dumps(new_skus))


def upload_model_to_skafos(dataset, new_skus_count, boots_count):
    # Uses API Token, Org Name Env Vars
    print("\nUploading trained model and meta data to skafos", flush=True)
    res = models.upload_version(
        files=[COREML_MODEL_NAME, META_FILE],
        description="Dataset: {}. New Boots: {}. Total Boots: {}. Model Type: {}".format(dataset, new_skus_count, boots_count, MODEL_TYPE),
        model_name=MODEL_NAME,
        app_name=APP_NAME
    )
    return res


if __name__ == "__main__":
    # Data containers
    raw_meta_data = []
    new_meta_data = []
    new_boot_ids = set()

    ## Step 1: Ingest New Zappos Boots Data ##
    # Parse data based on the structure of the page
    # We are going to create a list of dictionaries that we will write to file
    while True:
        print("Processing page {} of boots".format(N), flush=True)
        url = WOMENS_BOOTS_URL + "?p={}".format(N)
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
                    # Append items to the meta dictionary one by one (zero indexed)
                    raw_meta_data.append({
                        'boot_id': _id,
                        'boot_name': aria_label.split('. By')[0],
                        'brand': re.search("By (.*?) \$", aria_label).group(1).strip('.'),
                        'price': "$" + re.search("\$(.*?) ", aria_label).group(1).strip('.'),
                        'style': re.search("Style: (.*?)\.", aria_label).group(1),
                        'rating': rating,
                        'image_source': link.img['src'],
                        'buy_link': BASE_URL + buy_link.strip('/')
                    })
        if valid_page_links == 0:
            print("..No more valid boot links found. Done ingesting.\n", flush=True)
            break
        N += 1

    # Sort and organize meta data and newly collected boot ids
    if not raw_meta_data:
        sys.exit("No boots found.. packing up and going home.")
    # Clean out potential duplicates
    print("Checking for duplicates..", flush=True)
    for d in raw_meta_data:
         if d['boot_id'] not in new_boot_ids:
             new_boot_ids.add(d['boot_id'])
             new_meta_data.append(d)
    new_meta_data = sorted(new_meta_data, key=lambda d: d['boot_id'])
    assert len(new_meta_data) == len(new_boot_ids), "Meta Data and IDs don't match!! Don't go any further."


    ## Step 2: Check to see how many new boots we have since last ingest ##
    previous_dataset = sorted([file.split('/')[1] for file in S3_CNX.ls(BUCKET)], key=lambda k: datetime.strptime(k, DATASET_ID_FORMAT), reverse=True)[0]
    previous_boot_ids = set(img.split('/')[-1] for img in S3_CNX.ls(BUCKET + previous_dataset + IMG_PATH))

    # Extract the new skus since last ingest
    new_skus = [boot['image_source'] for sku in new_boot_ids.difference(previous_boot_ids) for boot in new_meta_data if sku == boot['boot_id']]
    total_new_skus = len(new_skus)
    total_boots = len(new_meta_data)

    ## Step 3: If we have enough new ones, retrain the model ##
    print("Found {} new boots since last ingest!".format(total_new_skus), flush=True)
    if total_new_skus >= RETRAIN_THRESH:
        print("New boots: {}\n".format(new_skus), flush=True)

        # Upload data to s3
        new_dataset = upload_boots_to_s3(
            s3=S3_CNX,
            meta_data=new_meta_data
        )

        # Retrain model
        new_model = retrain_image_similarity_model(
            s3=S3_CNX,
            dataset=new_dataset
        )

        # Convert model to coreml
        print("\nConverting model to coreml format and coercing to half precision", flush=True)
        new_model.export_coreml(COREML_MODEL_NAME)
        # Create half precision version of this model and overwrite the other one
        model_spec = coremltools.utils.load_spec(COREML_MODEL_NAME)
        model_fp16_spec = coremltools.utils.convert_neural_network_spec_weights_to_fp16(model_spec)
        coremltools.utils.save_spec(model_fp16_spec, COREML_MODEL_NAME)

        # Upload model to s3
        upload_model_to_s3(
            s3=S3_CNX,
            dataset=new_dataset,
            new_skus=new_skus
        )

        # Upload model to Skafos
        res = upload_model_to_skafos(
            dataset=new_dataset,
            new_skus_count=total_new_skus,
            boots_count=total_boots
        )
        print(res)
    else:
        # Do nothing - close out
        sys.exit("Not enough new boots.. Packing up and going home.")


    print("\nDone.", flush=True)
