# scripts/fetch_data.py

import requests
import logging

# Setup basic configuration for logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def fetch_wikidata_item(item_id):
    url = f"https://www.wikidata.org/w/api.php?action=wbgetentities&ids={item_id}&format=json&languages=en"
    response = requests.get(url)
    if response.status_code != 200:
        logging.error(f"Failed to fetch data for item {item_id}: {response.status_code}")
        return None
    return response.json()

def add_english_label(item_id, labels):
    if 'en' in labels:
        logging.info(f"Item {item_id} already has an English label.")
        return

    # Find a suitable label to use as English label
    for lang, label in labels.items():
        if lang != 'en':
            english_label = label
            break
    else:
        logging.warning(f"No suitable label found for item {item_id}.")
        return

    # Simulate adding the English label (in a real scenario, this would involve API calls to Wikidata)
    logging.info(f"Adding English label '{english_label}' to item {item_id}.")

def process_wikidata_items(item_ids):
    for item_id in item_ids:
        try:
            data = fetch_wikidata_item(item_id)
            if data and 'entities' in data and item_id in data['entities']:
                labels = data['entities'][item_id].get('labels', {})
                add_english_label(item_id, labels)
            else:
                logging.error(f"No data found for item {item_id}.")
        except Exception as e:
            logging.error(f"Error processing item {item_id}: {e}")

# Example usage
if __name__ == "__main__":
    item_ids = [
        "Q109344668", "Q110305558", "Q114870169", "Q136697621", "Q120971316"
    ]
    process_wikidata_items(item_ids)