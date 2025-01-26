import os
import json
import time  # For adding delay
import requests
from pymongo import MongoClient
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

# Global variables to avoid duplicate scraping
visited_urls = set()
base_url = "https://ihec.rnu.tn/fr"  # Replace with your target website

# MongoDB configuration
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")  # Use localhost if MongoDB is running locally
MONGO_DB = os.environ.get("MONGO_DB", "ihec")

# Delay between requests (in seconds)
REQUEST_DELAY = 2  # Adjust this value as needed

def is_html_page(url):
    """
    Check if the URL points to a valid HTML page by inspecting the Content-Type header.
    """
    try:
        response = requests.head(url, allow_redirects=True)
        content_type = response.headers.get('Content-Type', '')
        return 'text/html' in content_type
    except Exception as e:
        print(f"Error checking {url}: {e}")
        return False

def extract_table_data(table):
    """
    Extract data from an HTML table and return it as a list of dictionaries.
    """
    rows = table.find_all('tr')
    headers = [th.get_text(strip=True) for th in rows[0].find_all('th')] if rows[0].find_all('th') else None
    table_data = []

    for row in rows[1:]:  # Skip the header row if it exists
        cells = row.find_all(['td', 'th'])
        row_data = {}
        for i, cell in enumerate(cells):
            if headers and i < len(headers):
                key = headers[i]
            else:
                key = f"column_{i}"
            row_data[key] = cell.get_text(strip=True)
        table_data.append(row_data)

    return table_data

def scrape_page(url, topic, path):
    if url in visited_urls:
        return
    visited_urls.add(url)

    print(f"Scraping: {url}")

    try:
        # Fetch the page with explicit UTF-8 encoding
        response = requests.get(url)
        response.encoding = 'utf-8'  # Ensure UTF-8 encoding
        response.raise_for_status()

        # Check if the page is HTML
        if not is_html_page(url):
            print(f"Skipping non-HTML page: {url}")
            return

        # Parse the page with BeautifulSoup using UTF-8 encoding
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract all paragraphs
        paragraphs = soup.find_all('p')
        for i, p in enumerate(paragraphs):
            paragraph_text = p.get_text(strip=True)
            if not paragraph_text:
                continue

            # Extract file links (e.g., PDFs, images)
            files = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                if any(href.endswith(ext) for ext in ['.pdf', '.png', '.jpg', '.jpeg', '.doc', '.docx']):
                    file_url = urljoin(url, href)
                    file_name = os.path.basename(file_url)
                    files.append({"name": file_name, "url": file_url})

            # Extract tables
            tables = soup.find_all('table')
            table_data = [extract_table_data(table) for table in tables]

            # Create JSON data for the paragraph
            data = {
                "topic": topic,
                "path": path,
                "text": paragraph_text,
                "files": files,
                "tables": table_data  # Include table data in the JSON
            }

            # Save JSON to a file with UTF-8 encoding
            output_dir = "scraped_data"
            os.makedirs(output_dir, exist_ok=True)
            file_name = f"{output_dir}/{topic}_{len(visited_urls)}_{i}.json"
            with open(file_name, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)  # Ensure non-ASCII characters are preserved

            # Insert data into MongoDB
            try:
                client = MongoClient(MONGO_URI)
                db = client[MONGO_DB]
                site_collection = db.web
                site_collection.insert_one(data)
                print(f"Inserted data into MongoDB for {url}")
            except Exception as e:
                print(f"Error inserting data into MongoDB: {e}")
            finally:
                client.close()  # Close the MongoDB connection

        # Recursively scrape all internal links
        for link in soup.find_all('a', href=True):
            href = link['href']
            full_url = urljoin(url, href)

            # Ensure the link is from the same domain and not already visited
            if full_url.startswith(base_url) and full_url not in visited_urls:
                # Extract the new topic and path
                parsed_url = urlparse(full_url)
                new_topic = parsed_url.path.strip('/').split('/')[-1]
                new_path = parsed_url.path.strip('/')

                # Recursively scrape the new page
                time.sleep(REQUEST_DELAY)  # Add delay between requests
                scrape_page(full_url, new_topic, new_path)

    except Exception as e:
        print(f"Error scraping {url}: {e}")

# Start scraping from the base URL
parsed_base_url = urlparse(base_url)
initial_topic = parsed_base_url.path.strip('/').split('/')[-1]
initial_path = parsed_base_url.path.strip('/')

scrape_page(base_url, initial_topic, initial_path)

# import os
# import json
# import requests
# from pymongo import MongoClient
# from bs4 import BeautifulSoup
# from urllib.parse import urljoin, urlparse

# # Global variables to avoid duplicate scraping
# visited_urls = set()
# base_url = "https://ihec.rnu.tn/fr"  # Replace with your target website

# def is_html_page(url):
#     """
#     Check if the URL points to a valid HTML page by inspecting the Content-Type header.
#     """
#     try:
#         response = requests.head(url, allow_redirects=True)
#         content_type = response.headers.get('Content-Type', '')
#         return 'text/html' in content_type
#     except Exception as e:
#         print(f"Error checking {url}: {e}")
#         return False

# def extract_table_data(table):
#     """
#     Extract data from an HTML table and return it as a list of dictionaries.
#     """
#     rows = table.find_all('tr')
#     headers = [th.get_text(strip=True) for th in rows[0].find_all('th')] if rows[0].find_all('th') else None
#     table_data = []

#     for row in rows[1:]:  # Skip the header row if it exists
#         cells = row.find_all(['td', 'th'])
#         row_data = {}
#         for i, cell in enumerate(cells):
#             if headers and i < len(headers):
#                 key = headers[i]
#             else:
#                 key = f"column_{i}"
#             row_data[key] = cell.get_text(strip=True)
#         table_data.append(row_data)

#     return table_data

# def scrape_page(url, topic, path):
#     client = MongoClient(MONGO_URI)
#     db = client[MONGO_DB]
#     site_collection = db.web

#     if url in visited_urls:
#         return
#     visited_urls.add(url)

#     print(f"Scraping: {url}")

#     try:
#         # Fetch the page with explicit UTF-8 encoding
#         response = requests.get(url)
#         response.encoding = 'utf-8'  # Ensure UTF-8 encoding
#         response.raise_for_status()

#         # Check if the page is HTML
#         if not is_html_page(url):
#             print(f"Skipping non-HTML page: {url}")
#             return

#         # Parse the page with BeautifulSoup using UTF-8 encoding
#         soup = BeautifulSoup(response.text, 'html.parser')

#         # Extract all paragraphs
#         paragraphs = soup.find_all('p')
#         for i, p in enumerate(paragraphs):
#             paragraph_text = p.get_text(strip=True)
#             if not paragraph_text:
#                 continue

#             # Extract file links (e.g., PDFs, images)
#             files = []
#             for link in soup.find_all('a', href=True):
#                 href = link['href']
#                 if any(href.endswith(ext) for ext in ['.pdf', '.png', '.jpg', '.jpeg', '.doc', '.docx']):
#                     file_url = urljoin(url, href)
#                     file_name = os.path.basename(file_url)
#                     files.append({"name": file_name, "url": file_url})

#             # Extract tables
#             tables = soup.find_all('table')
#             table_data = [extract_table_data(table) for table in tables]

#             # Create JSON data for the paragraph
#             data = {
#                 "topic": topic,
#                 "path": path,
#                 "text": paragraph_text,
#                 "files": files,
#                 "tables": table_data  # Include table data in the JSON
#             }
#             site_collection.insert_one(data)


#             # Save JSON to a file with UTF-8 encoding
#             output_dir = "scraped_data"
#             os.makedirs(output_dir, exist_ok=True)
#             file_name = f"{output_dir}/{topic}_{len(visited_urls)}_{i}.json"
#             with open(file_name, 'w', encoding='utf-8') as f:
#                 json.dump(data, f, indent=4, ensure_ascii=False)  # Ensure non-ASCII characters are preserved

#         # Recursively scrape all internal links
#         for link in soup.find_all('a', href=True):
#             href = link['href']
#             full_url = urljoin(url, href)

#             # Ensure the link is from the same domain and not already visited
#             if full_url.startswith(base_url) and full_url not in visited_urls:
#                 # Extract the new topic and path
#                 parsed_url = urlparse(full_url)
#                 new_topic = parsed_url.path.strip('/').split('/')[-1]
#                 new_path = parsed_url.path.strip('/')

#                 # Recursively scrape the new page
#                 scrape_page(full_url, new_topic, new_path)

#     except Exception as e:
#         print(f"Error scraping {url}: {e}")

# MONGO_URI = os.environ.get("MONGO_URI", "mongodb://mongodb:27017")
# MONGO_DB  = os.environ.get("MONGO_DB", "ihec")

# # Start scraping from the base URL
# parsed_base_url = urlparse(base_url)
# initial_topic = parsed_base_url.path.strip('/').split('/')[-1]
# initial_path = parsed_base_url.path.strip('/')

# scrape_page(base_url, initial_topic, initial_path)



# import os
# import json
# import requests
# from bs4 import BeautifulSoup
# from urllib.parse import urljoin, urlparse

# # Global variables to avoid duplicate scraping
# visited_urls = set()
# base_url = "https://ihec.rnu.tn/fr"  # Replace with your target website

# def is_html_page(url):
#     """
#     Check if the URL points to a valid HTML page by inspecting the Content-Type header.
#     """
#     try:
#         response = requests.head(url, allow_redirects=True)
#         content_type = response.headers.get('Content-Type', '')
#         return 'text/html' in content_type
#     except Exception as e:
#         print(f"Error checking {url}: {e}")
#         return False

# def scrape_page(url, topic, path):
#     if url in visited_urls:
#         return
#     visited_urls.add(url)

#     print(f"Scraping: {url}")

#     try:
#         # Fetch the page with explicit UTF-8 encoding
#         response = requests.get(url)
#         response.encoding = 'utf-8'  # Ensure UTF-8 encoding
#         response.raise_for_status()

#         # Check if the page is HTML
#         if not is_html_page(url):
#             print(f"Skipping non-HTML page: {url}")
#             return

#         # Parse the page with BeautifulSoup using UTF-8 encoding
#         soup = BeautifulSoup(response.text, 'html.parser')

#         # Extract all paragraphs
#         paragraphs = soup.find_all('p')
#         for i, p in enumerate(paragraphs):
#             paragraph_text = p.get_text(strip=True)
#             if not paragraph_text:
#                 continue

#             # Extract file links (e.g., PDFs, images)
#             files = []
#             for link in soup.find_all('a', href=True):
#                 href = link['href']
#                 if any(href.endswith(ext) for ext in ['.pdf', '.png', '.jpg', '.jpeg', '.doc', '.docx']):
#                     file_url = urljoin(url, href)
#                     file_name = os.path.basename(file_url)
#                     files.append({"name": file_name, "url": file_url})

#             # Create JSON data for the paragraph
#             data = {
#                 "topic": topic,
#                 "path": path,
#                 "text": paragraph_text,
#                 "files": files
#             }

#             # Save JSON to a file with UTF-8 encoding
#             output_dir = "scraped_data"
#             os.makedirs(output_dir, exist_ok=True)
#             file_name = f"{output_dir}/{topic}_{len(visited_urls)}_{i}.json"
#             with open(file_name, 'w', encoding='utf-8') as f:
#                 json.dump(data, f, indent=4, ensure_ascii=False)  # Ensure non-ASCII characters are preserved

#         # Recursively scrape all internal links
#         for link in soup.find_all('a', href=True):
#             href = link['href']
#             full_url = urljoin(url, href)

#             # Ensure the link is from the same domain and not already visited
#             if full_url.startswith(base_url) and full_url not in visited_urls:
#                 # Extract the new topic and path
#                 parsed_url = urlparse(full_url)
#                 new_topic = parsed_url.path.strip('/').split('/')[-1]
#                 new_path = parsed_url.path.strip('/')

#                 # Recursively scrape the new page
#                 scrape_page(full_url, new_topic, new_path)

#     except Exception as e:
#         print(f"Error scraping {url}: {e}")

# # Start scraping from the base URL
# parsed_base_url = urlparse(base_url)
# initial_topic = parsed_base_url.path.strip('/').split('/')[-1]
# initial_path = parsed_base_url.path.strip('/')

# scrape_page(base_url, initial_topic, initial_path)












# # import os
# # import json
# # import requests
# # from bs4 import BeautifulSoup
# # from urllib.parse import urljoin, urlparse

# # # Global variables to avoid duplicate scraping
# # visited_urls = set()
# # base_url = "https://ihec.rnu.tn/fr"  # Replace with your target website

# # def is_html_page(url):
# #     """
# #     Check if the URL points to a valid HTML page by inspecting the Content-Type header.
# #     """
# #     try:
# #         response = requests.head(url, allow_redirects=True)
# #         content_type = response.headers.get('Content-Type', '')
# #         return 'text/html' in content_type
# #     except Exception as e:
# #         print(f"Error checking {url}: {e}")
# #         return False

# # def scrape_page(url, topic, path):
# #     if url in visited_urls:
# #         return
# #     visited_urls.add(url)

# #     print(f"Scraping: {url}")

# #     try:
# #         # Fetch the page
# #         response = requests.get(url)
# #         response.raise_for_status()

# #         # Check if the page is HTML
# #         if not is_html_page(url):
# #             print(f"Skipping non-HTML page: {url}")
# #             return

# #         soup = BeautifulSoup(response.text, 'html.parser')

# #         # Extract all paragraphs
# #         paragraphs = soup.find_all('p')
# #         for i, p in enumerate(paragraphs):
# #             paragraph_text = p.get_text(strip=True)
# #             if not paragraph_text:
# #                 continue

# #             # Extract file links (e.g., PDFs, images)
# #             files = []
# #             for link in soup.find_all('a', href=True):
# #                 href = link['href']
# #                 if any(href.endswith(ext) for ext in ['.pdf', '.png', '.jpg', '.jpeg', '.doc', '.docx']):
# #                     file_url = urljoin(url, href)
# #                     file_name = os.path.basename(file_url)
# #                     files.append({"name": file_name, "url": file_url})

# #             # Create JSON data for the paragraph
# #             data = {
# #                 "topic": topic,
# #                 "path": path,
# #                 "text": paragraph_text,
# #                 "files": files
# #             }

# #             # Save JSON to a file
# #             output_dir = "scraped_data"
# #             os.makedirs(output_dir, exist_ok=True)
# #             file_name = f"{output_dir}/{topic}_{len(visited_urls)}_{i}.json"
# #             with open(file_name, 'w', encoding='utf-8') as f:
# #                 json.dump(data, f, indent=4)

# #         # Recursively scrape all internal links
# #         for link in soup.find_all('a', href=True):
# #             href = link['href']
# #             full_url = urljoin(url, href)

# #             # Ensure the link is from the same domain and not already visited
# #             if full_url.startswith(base_url) and full_url not in visited_urls:
# #                 # Extract the new topic and path
# #                 parsed_url = urlparse(full_url)
# #                 new_topic = parsed_url.path.strip('/').split('/')[-1]
# #                 new_path = parsed_url.path.strip('/')

# #                 # Recursively scrape the new page
# #                 scrape_page(full_url, new_topic, new_path)

# #     except Exception as e:
# #         print(f"Error scraping {url}: {e}")

# # # Start scraping from the base URL
# # parsed_base_url = urlparse(base_url)
# # initial_topic = parsed_base_url.path.strip('/').split('/')[-1]
# # initial_path = parsed_base_url.path.strip('/')
# # # print(f"Initial topic: {initial_topic}")
# # # print(f"Initial path: {initial_path}")
# # scrape_page(base_url, initial_topic, initial_path)