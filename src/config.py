from pathlib import Path
from urllib.parse import urljoin

BASE_URL="https://en.onepiece-cardgame.com"
CARD_LIST_URL= urljoin(BASE_URL, "cardlist/")
RAW_DATA_DIR = Path("../raw_data")
RESULTS_DIR = Path("../results")