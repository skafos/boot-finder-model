# Boot Finder Data and ML Training Pipeline

## Overview

This repository contains code that ingests data from the zappos.com website, uses it to build an image similarity model, and then stores the model, and its associated data and metadata (in the form of a .json file) on S3. The code also exports the model and metadata to Skafos for inclusion in the Skafos BootFinder app. The BootFinder app enables users to photograph a picture of a pair of boots, and the image similarity model identifies the most similar boots currently available on zappos.com, along with a link to purchase. 

This repository contains the following files: 

* `zappos.py`: The script that executes the data ingest, model training, and export.
* `requirements.txt`: Python libraries necessary to run `zappos.py`
* `Dockerfile`: The Dockerfile needed for the Skafos team to containerize and run `zappos.py` at the appropriate scheduled time each week. 
* `notebooks/`: A folder of notebooks used for testing a protyping pipeline and model building updates.
* `README.md`: This README file

## Data Ingest and Validation
Zappos maintains a collection of ~4500 Women's boots that are updated daily as new items are added to or removed from their inventory. 

For this project, data is collected from `https://zappos.com/women-boots/CK_XARCz1wHAAQHiAgMBAhg.zso` on a weekly basis.

The data ingest portion of `zappos.py` scrapes all available boots from the listed URL, paginating through each chunk of 100. Meta data is collected for each boot as a list of dictionaries with the following keys:

```
{
    'boot_id':
    'boot_name':
    'brand':
    'price':
    'style':
    'rating':
    'image_source':
    'buy_link':
}
```

Once all data has been scraped, the script checks the most recent available dataset saved to S3 to see if enough new boots have been added to the Zappos inventory to justify a model retrain. `retrain_threshold` is a variable in the code that specifies the number of new boots needed to trigger a model retrain. Currently, this number is set to 1. 

Before model retraining, all metadata and boot images are persisted to an s3 bucket with a timestamp dataset id. This timeset uniquely identifies the set of boot images and metadata used the train the model. 

## Model Training
Following the image and metadata upload to s3, the code uses these boot images trains a Turi Create Image Similarity model. Once trained, the model is converted to CoreML, saved back s3 along with the data and metadata, and uploaded to the Skafos platform.
