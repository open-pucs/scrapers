import os

S3_CLOUD_REGION = os.environ.get("S3_CLOUD_REGION", "sfo3")
S3_ENDPOINT = os.environ.get("S3_ENDPOINT", "https://sfo3.digitaloceanspaces.com")
S3_SCRAPER_INTERMEDIATE_BUCKET = os.environ.get(
    "S3_SCRAPER_INTERMEDIATE_BUCKET", "opescraper-intermediates"
)

S3_ACCESS_KEY = os.environ["S3_ACCESS_KEY"]
S3_SECRET_KEY = os.environ["S3_SECRET_KEY"]
