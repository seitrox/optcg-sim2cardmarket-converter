import csv
from dataclasses import fields, asdict
from datetime import datetime, timedelta
from typing import List
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from data.ProductSeries import ProductSeries
from config import BASE_URL, RAW_DATA_DIR, CARD_LIST_URL, RESULTS_DIR
from data.Card import Card


def get_product_series(url: str):
    request_data= {'series': ''}
    products = []

    try:
        response = requests.post(url, data=request_data)
        if response.status_code == 200:
            print("POST request successful!")
            soup = BeautifulSoup(response.text, 'html.parser')
            select_tag = soup.find('select', id='series')
            if select_tag:
                option_tags = select_tag.find_all('option')
                for option_tag in option_tags:
                    value = option_tag.get('value')
                    text = option_tag.get_text(strip=True)
                    if value.isdigit():
                        index = text.find('<br class="spInline">-')
                        if index != -1:
                            text = text[index+len('<br class="spInline">-'):]
                        text = text.replace('"', '')
                        products.append(ProductSeries(value, text))
            else:
                print("No select tag found with id 'series'")
        else:
            print("POST request failed with status code:", response.status_code)
    except Exception as e:
        print("An error occurred:", str(e))

    return products

def fetch_product_series_data(product_series: ProductSeries):
    request_data = {"series": product_series.id}
    filename = RAW_DATA_DIR / f"{product_series.id}.txt"
    timestamp_file = RAW_DATA_DIR / f"{product_series.id}_timestamp.txt"

    # Check if the timestamp file exists and its content
    if timestamp_file.exists():
        with open(timestamp_file, "r") as tf:
            last_updated = datetime.fromisoformat(tf.read())
            if datetime.now() - last_updated < timedelta(days=1):
                print(f"Data for series id {product_series.id} is up to date.")
                return None

    try:
        response = requests.post(CARD_LIST_URL, data=request_data)
        if response.status_code == 200:
            print(f"POST request successful for series id: {product_series.id}")
            RAW_DATA_DIR.mkdir(exist_ok=True)

            # Write response to file
            with open(filename, "w", encoding="utf-8") as file:
                file.write(response.text)
            print(f"Response written to {filename}")

            # Write current timestamp to timestamp file
            with open(timestamp_file, "w") as tf:
                tf.write(datetime.now().isoformat())

            print(f"Timestamp updated for series id: {product_series.id}")
        else:
            print(f"POST request failed with status code {response.status_code} for series id: {product_series.id}")
    except Exception as e:
        print(f"An error occurred for series id {product_series.id}: {str(e)}")

def extract_card_data(html_content: str, product: ProductSeries) -> List[Card]:
    soup = BeautifulSoup(html_content, "html.parser")
    cards = []

    # Find all dl elements with class modalCol
    card_elements = soup.find_all("dl", class_="modalCol")

    for card_element in card_elements:
        card_data = Card()

        # Extract card name from the div with class cardName
        card_data.name = card_element.find(class_="cardName").get_text(strip=True).replace("(", "").replace(")", "")

        # Extract information from the infoCol div
        info_col = card_element.find(class_="infoCol")
        spans = info_col.find_all("span")
        card_data.id = spans[0].get_text(strip=True) if spans else ""
        card_data.rarity = spans[1].get_text(strip=True) if len(spans) > 1 else ""
        card_data.type = spans[2].get_text(strip=True) if len(spans) > 2 else ""

        # Extract other information
        attributes = card_element.find("div", class_="attribute")
        attribute_text = attributes.find("i")
        if attribute_text:
            card_data.attribute = attribute_text.get_text(strip=True)
        else:
            attribute_h3 = attributes.find("h3")
            if attribute_h3:
                card_data.attribute = attribute_h3.next_sibling.strip()

        power = card_element.find("div", class_="power")
        if power:
            power_text = power.find(string=True, recursive=False)
            card_data.power = power_text.strip() if power_text else ""

        counter = card_element.find("div", class_="counter")
        if counter:
            counter_text = counter.find(string=True, recursive=False)
            card_data.counter = counter_text.strip() if counter_text else ""

        color = card_element.find("div", class_="color")
        if color:
            color_text = color.find(string=True, recursive=False)
            card_data.color = color_text.strip() if color_text else ""

        card_type = card_element.find("div", class_="feature")
        if card_type:
            card_type_text = card_type.get_text(strip=True).replace("Type", "").strip()
            card_data.card_type = card_type_text

        effect = card_element.find("div", class_="text")
        if effect:
            effect_text = effect.get_text(strip=True).replace("Effect", "").strip()
            card_data.effect = effect_text

        # Extract image URL
        image = card_element.find("div", class_="frontCol").find("img")
        if image:
            image_src = image["data-src"]
            if image_src.startswith(".."):
                image_src = image_src[2:]  # Remove the '..' from the beginning of the URL
            image_url = urljoin(BASE_URL, image_src)
            card_data.image_url = image_url

            # Determine if it's alternate art
            card_data.alternate_art = "_p" in image_src

        card_data.series_id = product.id
        card_data.series_name = product.name

        cards.append(card_data)
    return cards

def get_all_cards_data(product_series):
    all_cards_data = []
    for product in product_series:
        fetch_product_series_data(product)
        product_series_file = RAW_DATA_DIR / f"{product.id}.txt"
        if product_series_file:
            with open(product_series_file, "r", encoding="utf-8") as file:
                html_content = file.read()
                cards_data = extract_card_data(html_content, product)
                all_cards_data.extend(cards_data)
    return all_cards_data

def write_cards_data_to_csv(cards_data: List[Card]):
    card_data_file = RESULTS_DIR / 'card_data.csv'
    with open(card_data_file,'w') as file:
        header_fields = [fld.name for fld in fields(Card)]
        writer = csv.DictWriter(file, header_fields, delimiter='|')
        writer.writeheader()
        writer.writerows([asdict(prop) for prop in cards_data ])
    print(f"card data csv written!")

def get_converter_csv(input_file: str, output_file: str):
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
    print(f"converter csv written!")

def write_formated_cards_data_to_csv(cards_data: List[Card]):
    max_field_lenghts = {}
    header_fields = [fld.name for fld in fields(Card)]

    for field in header_fields:
        max_field_lenghts[field] = 0

    # Get the maximum length for each column
    for card in cards_data:
        card_fields = asdict(card)
        for field in card_fields:
            if field != 'alternate_art':
                max_field_lenghts[field] = max( max_field_lenghts.get(field) ,len(card_fields[field]))


    # Format the header
    formatted_header = [field.replace("_", " ").title().ljust(max_field_lenghts[field]) for field in header_fields]
    header_line = " | ".join(formatted_header)

    # Add the header line
    formatted_data = [header_line]

    # Add the separator line
    separator_line = "-" * len(header_line)
    formatted_data.append(separator_line)

    # Format each row of data
    for card in cards_data:
        card_fields = asdict(card)
        formatted_row = ""
        for field in card_fields:
            value = card_fields[field]
            formatted_value = str(value).ljust(max_field_lenghts[field])
            formatted_row += formatted_value + " | "
        formatted_data.append(formatted_row[:-3])  # Remove the trailing ' | '

    RESULTS_DIR.mkdir(exist_ok=True)
    file_path = RESULTS_DIR / "card_data.txt"
    with open(file_path, "w", encoding="utf-8") as file:
        for line in formatted_data:
            file.write(line + "\n")

    print(f"formated csv written!")


def main():
    product_series = get_product_series(CARD_LIST_URL)
    all_cards_data = get_all_cards_data(product_series)
    write_cards_data_to_csv(all_cards_data)

    input_csv = RESULTS_DIR / "card_data.csv"
    output_csv = RESULTS_DIR / "converter_card_data.csv"
    get_converter_csv(str(input_csv), str(output_csv))
    write_formated_cards_data_to_csv(all_cards_data)




if __name__ == "__main__":
    main()
