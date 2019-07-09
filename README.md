# Boot Finder Data and ML Training Pipeline

## Data Ingest
Zappos maintains a collection of ~4500 Women's boots that are updated daily as new items
are added or removed from the inventory. Data is collected from `https://zappos.com/women-boots/CK_XARCz1wHAAQHiAgMBAhg.zso` on a weekly basis.

Each week, this app scrapes all available boots, paginating through each chunk of 100. Meta data is collected for each boot as a list of dictionaries with the following keys:

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

Once all data has been scraped, the app checks the previous dataset saved to s3 to see if enough new boots have been released. If there are at least `retain_threshold` number of new boots since last ingest, we retrain the model.

Before retraining, all meta data and boot images are persisted to an s3 bucket with a timestamp dataset id.

## Model Training
Given the dataset id, the app pulls down boot images from s3 and trains a Turi Create Image Similarity model. Once trained, it is saved back to s3 and uploaded to the Skafos platform.
