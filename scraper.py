import csv
import requests
import time
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime, timedelta

def get_all_series_from_url(url):
    data = {'series': ''}
    options = []

    try:
        response = requests.post(url, data=data)
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
                        options.append({'value': value, 'text': text})
            else:
                print("No select tag found with id 'series'")
        else:
            print("POST request failed with status code:", response.status_code)
    except Exception as e:
        print("An error occurred:", str(e))

    return options

def get_series_data(url, series_value):
    data = {'series': series_value}

    try:
        filename = f'raw_data/{series_value}.txt'
        timestamp_file = f'raw_data/{series_value}_timestamp.txt'
        
        # Check if the timestamp file exists and its content
        if os.path.exists(timestamp_file):
            with open(timestamp_file, 'r') as tf:
                last_updated = datetime.fromisoformat(tf.read())
                if datetime.now() - last_updated < timedelta(days=1):
                    print(f"Data for series value {series_value} is up to date.")
                    return
        # If timestamp file doesn't exist or data is outdated, execute the post request
        response = requests.post(url, data=data)
        if response.status_code == 200:
            print(f"POST request successful for series value: {series_value}")
            
            if not os.path.exists('raw_data'):
                os.makedirs('raw_data')
                
            # Write response to file
            with open(filename, "w") as file:
                file.write(response.text)
            print(f"Response written to {filename}")
            
            # Write current timestamp to timestamp file
            with open(timestamp_file, 'w') as tf:
                tf.write(datetime.now().isoformat())
                
            print(f"Timestamp updated for series value: {series_value}")
            time.sleep(1)
        else:
            print(f"POST request failed with status code {response.status_code} for series value: {series_value}")
    except Exception as e:
        print(f"An error occurred for series value {series_value}: {str(e)}")

def extract_card_data(html_content, series_id):
    soup = BeautifulSoup(html_content, 'html.parser')
    cards = []

    # Find all dl elements with class modalCol
    card_elements = soup.find_all('dl', class_='modalCol')

    for card_element in card_elements:
        card_data = {}

        # Extract card name from the div with class cardName
        card_data['name'] = card_element.find(class_='cardName').get_text(strip=True).replace("(", "").replace(")", "")

        # Extract information from the infoCol div
        info_col = card_element.find(class_='infoCol')
        spans = info_col.find_all('span')
        card_data['id'] = spans[0].get_text(strip=True) if len(spans) > 0 else None
        card_data['rarity'] = spans[1].get_text(strip=True) if len(spans) > 1 else None
        card_data['type'] = spans[2].get_text(strip=True) if len(spans) > 2 else None

        # Extract other information
        attributes = card_element.find('div', class_='attribute')
        attribute_text = attributes.find('i').get_text(strip=True) if attributes.find('i') else None
        if attribute_text:
            card_data['attribute'] = attribute_text
        else:
            attribute_h3 = attributes.find('h3')
            if attribute_h3:
                card_data['attribute'] = attribute_h3.next_sibling.strip()

        power = card_element.find('div', class_='power')
        if power:
            power_text = power.find(string=True, recursive=False)
            card_data['power'] = power_text.strip() if power_text else None

        counter = card_element.find('div', class_='counter')
        if counter:
            counter_text = counter.find(string=True, recursive=False)
            card_data['counter'] = counter_text.strip() if counter_text else None

        color = card_element.find('div', class_='color')
        if color:
            color_text = color.find(string=True, recursive=False)
            card_data['color'] = color_text.strip() if color_text else None

        card_type = card_element.find('div', class_='feature')
        if card_type:
            card_type_text = card_type.get_text(strip=True).replace('Type', '').strip()
            card_data['card_type'] = card_type_text

        effect = card_element.find('div', class_='text')
        if effect:
            effect_text = effect.get_text(strip=True).replace('Effect', '').strip()
            card_data['effect'] = effect_text

        # Extract image URL
        image = card_element.find('div', class_='frontCol').find('img')
        if image:
            image_src = image['src']
            if image_src.startswith('..'):
                image_src = image_src[2:]  # Remove the '..' from the beginning of the URL
            image_url = urljoin('https://en.onepiece-cardgame.com/', image_src)
            card_data['image_url'] = image_url

            # Determine if it's alternate art
            if '_p' in image_src:
                card_data['alternate_art'] = True
            else:
                card_data['alternate_art'] = False

        card_data['series_id'] = series_id

        cards.append(card_data)

    return cards

def gather_all_card_data():
    cards_data = []

    file_list = os.listdir('raw_data')
    for file_name in file_list:
        series_id = os.path.splitext(file_name)[0]
        file_path = f'raw_data/{file_name}'
        with open(file_path, 'r') as file:
            html_content = file.read()
        cards_data += extract_card_data(html_content, series_id)

    return cards_data

def format_card_data(cards_data, header):
    formatted_data = []
    
    # Get the maximum length for each column
    max_lengths = {key: max(len(str(card[key])) for card in cards_data) for key in header}
    
    # Format the header
    formatted_header = [field.replace('_', ' ').title().ljust(max(max_lengths[field], len(field))) for field in header]
    header_line = ' | '.join(formatted_header)
    
    # Add the header line
    formatted_data.append(header_line)

    # Add the separator line
    separator_line = '-' * len(header_line)
    formatted_data.append(separator_line)
    
    # Format each row of data
    for card_data in cards_data:
        formatted_row = ""
        for key in header:
            value = card_data[key]
            formatted_value = str(value).ljust(max(max_lengths[key], len(key)))
            formatted_row += formatted_value + ' | '
        formatted_data.append(formatted_row[:-3])  # Remove the trailing ' | '

    return formatted_data

def write_results_to_file(formatted_data, header, filename):
    if not os.path.exists('results'):
        os.makedirs('results')

    with open(filename, 'w') as file:
        for line in formatted_data:
            file.write(line + '\n')

def write_results_to_csv(cards_data, header, filename):
    if not os.path.exists('results'):
        os.makedirs('results')

    with open(filename, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=header, delimiter='|')
        writer.writeheader()
        for card_data in cards_data:
            writer.writerow(card_data)

def get_converter_csv(input_file, output_file):
    with open(input_file, 'r', newline='') as infile, open(output_file, 'w', newline='') as outfile:
        reader = csv.DictReader(infile, delimiter='|')
        fieldnames = ['id', 'name']
        writer = csv.DictWriter(outfile, fieldnames=fieldnames, delimiter='|')
        writer.writeheader()
        for row in reader:
            if row['alternate_art'] != 'True':
                writer.writerow({'id': row['id'], 'name': row['name']})

def main():
    url = "https://en.onepiece-cardgame.com/cardlist/"
    options = get_all_series_from_url(url)
    integer_options = [option for option in options if option['value'].isdigit()]

    for option in integer_options:
        series_value = option['value']
        get_series_data(url, series_value)

    cards_data = gather_all_card_data()

    # Check if any card data contains '|' because if it does, we can't be using '|' as delimiter
    for card_data in cards_data:
        for value in card_data.values():
            if '|' in str(value):
                print("Error: '|' found in card data.")
                return

    header = ['id', 'name', 'rarity', 'type', 'attribute', 'power', 'counter', 'color', 'card_type', 'effect', 'image_url', 'alternate_art', 'series_id']
    formatted_data = format_card_data(cards_data, header)
    write_results_to_file(formatted_data, header, 'results/card_data.txt')
    write_results_to_csv(cards_data, header, 'results/card_data.csv')

    # Distill CSV
    input_csv = 'results/card_data.csv'
    output_csv = 'results/converter_card_data.csv'
    get_converter_csv(input_csv, output_csv)

if __name__ == "__main__":
    main()
