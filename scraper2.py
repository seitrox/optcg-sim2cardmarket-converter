import csv
import os
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://en.onepiece-cardgame.com"
CARD_LIST_URL = urljoin(BASE_URL, "cardlist/")
RAW_DATA_DIR = Path("raw_data2")
RESULTS_DIR = Path("results2")

def get_series_options() -> List[Dict[str, str]]:
    """
    Retrieves the available series options from the card list website.

    Returns:
        A list of dictionaries containing the series value and text.
    """
    response = requests.post(CARD_LIST_URL, data={"series": ""})
    if response.status_code == 200:
        print("POST request successful!")
        soup = BeautifulSoup(response.text, "html.parser")
        series_select = soup.find("select", id="series")
        if series_select:
            options = []
            for option_tag in series_select.find_all("option"):
                value = option_tag.get("value")
                text = option_tag.get_text(strip=True)
                if value.isdigit():
                    index = text.find("<br class='spInline'>-")
                    if index != -1:
                        text = text[index + len("<br class='spInline'>-"):]
                    text = text.replace('"', "")
                    options.append({"value": value, "text": text})
            return options
    print(f"Error: Failed to retrieve series options (status code: {response.status_code})")
    return []

def fetch_series_data(series_value: str) -> Optional[str]:
    """
    Fetches the card data for a given series value from the website and stores it in a file.

    Args:
        series_value: The value representing the series to fetch.

    Returns:
        The file path where the data was stored, or None if an error occurred.
    """
    data = {"series": series_value}
    filename = RAW_DATA_DIR / f"{series_value}.txt"
    timestamp_file = RAW_DATA_DIR / f"{series_value}_timestamp.txt"

    # Check if the timestamp file exists and its content
    if timestamp_file.exists():
        with open(timestamp_file, "r") as tf:
            last_updated = datetime.fromisoformat(tf.read())
            if datetime.now() - last_updated < timedelta(days=1):
                print(f"Data for series value {series_value} is up to date.")
                return None

    try:
        response = requests.post(CARD_LIST_URL, data=data)
        if response.status_code == 200:
            print(f"POST request successful for series value: {series_value}")
            RAW_DATA_DIR.mkdir(exist_ok=True)

            # Write response to file
            with open(filename, "w", encoding="utf-8") as file:
                file.write(response.text)
            print(f"Response written to {filename}")

            # Write current timestamp to timestamp file
            with open(timestamp_file, "w") as tf:
                tf.write(datetime.now().isoformat())

            print(f"Timestamp updated for series value: {series_value}")
            time.sleep(1)
            return str(filename)
        print(f"POST request failed with status code {response.status_code} for series value: {series_value}")
    except Exception as e:
        print(f"An error occurred for series value {series_value}: {str(e)}")
    return None

def extract_card_data(html_content: str, series_id: str) -> List[Dict[str, str]]:
    """
    Extracts card data from the given HTML content and series ID.

    Args:
        html_content: The HTML content containing the card data.
        series_id: The ID of the series to which the cards belong.

    Returns:
        A list of dictionaries containing the extracted card data.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    cards = []

    # Find all dl elements with class modalCol
    card_elements = soup.find_all("dl", class_="modalCol")

    for card_element in card_elements:
        card_data = defaultdict(str)

        # Extract card name from the div with class cardName
        card_data["name"] = card_element.find(class_="cardName").get_text(strip=True).replace("(", "").replace(")", "")

        # Extract information from the infoCol div
        info_col = card_element.find(class_="infoCol")
        spans = info_col.find_all("span")
        card_data["id"] = spans[0].get_text(strip=True) if spans else ""
        card_data["rarity"] = spans[1].get_text(strip=True) if len(spans) > 1 else ""
        card_data["type"] = spans[2].get_text(strip=True) if len(spans) > 2 else ""

        # Extract other information
        attributes = card_element.find("div", class_="attribute")
        attribute_text = attributes.find("i")
        if attribute_text:
            card_data["attribute"] = attribute_text.get_text(strip=True)
        else:
            attribute_h3 = attributes.find("h3")
            if attribute_h3:
                card_data["attribute"] = attribute_h3.next_sibling.strip()

        power = card_element.find("div", class_="power")
        if power:
            power_text = power.find(string=True, recursive=False)
            card_data["power"] = power_text.strip() if power_text else ""

        counter = card_element.find("div", class_="counter")
        if counter:
            counter_text = counter.find(string=True, recursive=False)
            card_data["counter"] = counter_text.strip() if counter_text else ""

        color = card_element.find("div", class_="color")
        if color:
            color_text = color.find(string=True, recursive=False)
            card_data["color"] = color_text.strip() if color_text else ""

        card_type = card_element.find("div", class_="feature")
        if card_type:
            card_type_text = card_type.get_text(strip=True).replace("Type", "").strip()
            card_data["card_type"] = card_type_text

        effect = card_element.find("div", class_="text")
        if effect:
            effect_text = effect.get_text(strip=True).replace("Effect", "").strip()
            card_data["effect"] = effect_text

        # Extract image URL
        image = card_element.find("div", class_="frontCol").find("img")
        if image:
            image_src = image["data-src"]
            if image_src.startswith(".."):
                image_src = image_src[2:]  # Remove the '..' from the beginning of the URL
            image_url = urljoin(BASE_URL, image_src)
            card_data["image_url"] = image_url

            # Determine if it's alternate art
            card_data["alternate_art"] = "_p" in image_src

        card_data["series_id"] = series_id

        cards.append(card_data)

    return cards

def format_card_data(cards_data: List[Dict[str, str]]) -> List[str]:
    """
    Formats the card data into a list of strings, with each string representing a row.

    Args:
        cards_data: A list of dictionaries containing the card data.

    Returns:
        A list of strings representing the formatted card data.
    """
    header = [
        "id",
        "name",
        "rarity",
        "type",
        "attribute",
        "power",
        "counter",
        "color",
        "card_type",
        "effect",
        "image_url",
        "alternate_art",
        "series_id",
    ]

    # Get the maximum length for each column
    max_lengths = {key: max(len(str(card[key])) for card in cards_data) for key in header}

    # Format the header
    formatted_header = [field.replace("_", " ").title().ljust(max_lengths[field]) for field in header]
    header_line = " | ".join(formatted_header)

    # Add the header line
    formatted_data = [header_line]

    # Add the separator line
    separator_line = "-" * len(header_line)
    formatted_data.append(separator_line)

    # Format each row of data
    for card_data in cards_data:
        formatted_row = ""
        for key in header:
            value = card_data[key]
            formatted_value = str(value).ljust(max_lengths[key])
            formatted_row += formatted_value + " | "
        formatted_data.append(formatted_row[:-3])  # Remove the trailing ' | '

    return formatted_data

def write_results_to_file(formatted_data: List[str], filename: str) -> None:
    """
    Writes the formatted card data to a text file.

    Args:
        formatted_data: A list of strings representing the formatted card data.
        filename: The filename to which the data should be written.
    """
    RESULTS_DIR.mkdir(exist_ok=True)
    file_path = RESULTS_DIR / filename
    with open(file_path, "w", encoding="utf-8") as file:
        for line in formatted_data:
            file.write(line + "\n")

def write_results_to_csv(cards_data: List[Dict[str, str]], filename: str) -> None:
    """
    Writes the card data to a CSV file.

    Args:
        cards_data: A list of dictionaries containing the card data.
        filename: The filename to which the data should be written.
    """
    header = [
        "id",
        "name",
        "rarity",
        "type",
        "attribute",
        "power",
        "counter",
        "color",
        "card_type",
        "effect",
        "image_url",
        "alternate_art",
        "series_id",
    ]

    RESULTS_DIR.mkdir(exist_ok=True)
    file_path = RESULTS_DIR / filename
    with open(file_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=header, delimiter="|")
        writer.writeheader()
        for card_data in cards_data:
            writer.writerow(card_data)

def get_converter_csv(input_file: str, output_file: str) -> None:
    """
    Generates a CSV file containing only the card ID and name for non-alternate art cards.

    Args:
        input_file: The path to the input CSV file containing the card data.
        output_file: The path to the output CSV file to be generated.
    """
    with open(input_file, "r", newline="", encoding="utf-8") as infile, open(
        output_file, "w", newline="", encoding="utf-8"
    ) as outfile:
        reader = csv.DictReader(infile, delimiter="|")
        fieldnames = ["id", "name"]
        writer = csv.DictWriter(outfile, fieldnames=fieldnames, delimiter="|")
        writer.writeheader()
        for row in reader:
            if row["alternate_art"] != "True":
                writer.writerow({"id": row["id"], "name": row["name"]})

def main() -> None:
    """
    The main function that orchestrates the entire scraping process.
    """
    series_options = get_series_options()
    integer_options = [option for option in series_options if option["value"].isdigit()]

    all_cards_data = []
    for option in integer_options:
        series_value = option["value"]
        file_path = fetch_series_data(series_value)
        if file_path:
            with open(file_path, "r", encoding="utf-8") as file:
                html_content = file.read()
            cards_data = extract_card_data(html_content, series_value)
            all_cards_data.extend(cards_data)

    formatted_data = format_card_data(all_cards_data)
    write_results_to_file(formatted_data, "card_data.txt")
    write_results_to_csv(all_cards_data, "card_data.csv")

    # Generate converter CSV
    input_csv = RESULTS_DIR / "card_data.csv"
    output_csv = RESULTS_DIR / "converter_card_data.csv"
    get_converter_csv(str(input_csv), str(output_csv))

if __name__ == "__main__":
    main()