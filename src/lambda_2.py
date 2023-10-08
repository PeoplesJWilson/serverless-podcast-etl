import mysql.connector
import xmltodict
import requests

import boto3
import json
import os
from datetime import datetime
    

BUCKET_NAME = os.environ["ENV_VAR_1"]
KEY = f"{BUCKET_NAME}.json"

USER_NAME = os.environ["ENV_VAR_2"]
PASSWORD = os.environ["ENV_VAR_3"]
RDS_ENDPOINT = os.environ["ENV_VAR_4"]
DB_NAME = os.environ["ENV_VAR_5"]

s3 = boto3.client('s3')

#___________________________________________
#           QUERIES

create_time_dimension_query = """
    CREATE TABLE IF NOT EXISTS time_dimension (
        date DATE PRIMARY KEY,
        year INT,
        month VARCHAR(10),
        month_number INT,
        day INT
    )
    """

create_podcast_dimension_query = """
    CREATE TABLE IF NOT EXISTS podcast_dimension (
        podcast_id INT AUTO_INCREMENT PRIMARY KEY,
        podcast_title VARCHAR(255) UNIQUE,
        description TEXT
    )
    """

create_episode_dimension_query = """
    CREATE TABLE IF NOT EXISTS episode_dimension (
        episode_id INT AUTO_INCREMENT PRIMARY KEY,
        link VARCHAR(255) UNIQUE,
        podcast_id INT,
        episode_release_date DATE,
        episode_title VARCHAR(255),
        episode_description TEXT,
        downloaded BOOLEAN NOT NULL DEFAULT FALSE,
        num_chunks INT NOT NULL DEFAULT 0,
    FOREIGN KEY (podcast_id) REFERENCES podcast_dimension(podcast_id),
    FOREIGN KEY (episode_release_date) REFERENCES time_dimension(date)
    )
    """

create_sentence_dimension_query = """
    CREATE TABLE IF NOT EXISTS sentence_dimension (
        sentence_id INT AUTO_INCREMENT PRIMARY KEY,
        sentence_text TEXT,
        sentence_index INT,
        overall_sentiment VARCHAR(20),
        negative_score FLOAT(4,4),
        neutral_score FLOAT(4,4),
        positive_score FLOAT(4,4),
        mixed_score FLOAT(4,4),
        episode_id INT,
        UNIQUE KEY (sentence_index, episode_id),
    FOREIGN KEY (episode_id) REFERENCES episode_dimension(episode_id)
    )
    """
    
create_entity_dimension_query = """
    CREATE TABLE IF NOT EXISTS entity_dimension (
        entity_id INT AUTO_INCREMENT PRIMARY KEY,
        episode_id INT,
        entity_text VARCHAR(255),
        entity_type VARCHAR(255), 
        sentence_index INT,
    FOREIGN KEY (sentence_index, episode_id) REFERENCES entity_dimension(sentence_index, episode_id)
    )
    """

queries = [create_time_dimension_query, 
           create_podcast_dimension_query,
           create_episode_dimension_query,
           create_sentence_dimension_query,
           create_entity_dimension_query]

#___________________________________________
#           Date data processing items
     
month_number_to_name = {
    1: 'January',
    2: 'February',
    3: 'March',
    4: 'April',
    5: 'May',
    6: 'June',
    7: 'July',
    8: 'August',
    9: 'September',
    10: 'October',
    11: 'November',
    12: 'December'
}

def string_to_datetime(date_string, format='%a, %d %b %Y %H:%M:%S %z'):
    try:
        dt_object = datetime.strptime(date_string, format)
        return dt_object
    except ValueError:
        print("Invalid date string format.")
        return None

#___________________________________________
#           process episodes helper function

def process_episodes(episode_data, title_to_id):
    processed_data = []
    for episode in episode_data:
        link = episode[0]
        podcast_id = title_to_id[episode[1]]
        date = string_to_datetime(episode[2]).date()
        episode_description = episode[2]
        episode_title = episode[3]
        episode_description = episode[4]
        processed_data.append(
            (link, podcast_id, date, episode_title, episode_description)
        )
    return processed_data

#___________________________________________
#           MAIN LAMBDA HANDLER FUNCTION 

def save_metadata(event, context):

    connection = mysql.connector.connect(
            host = RDS_ENDPOINT,
            user = USER_NAME,
            password = PASSWORD,
            database = DB_NAME
            )
    print("Connected!!!")

    cursor = connection.cursor()

    for query in queries:
        cursor.execute(query)
    
    connection.commit()

    #__________________________________

    obj = s3.get_object(Bucket=BUCKET_NAME, Key=KEY)
    data = json.loads(obj['Body'].read())
    data.pop(0)

    feeds = []
    for datum in data:
        feed = datum[1]
        feeds.append(feed)
    
    date_data = []
    podcast_data = []
    episode_data = []

    for feed in feeds:
        print(feed)
        req = requests.get(feed)
        feed = xmltodict.parse(req.text)

        podcast_level = feed["rss"]["channel"]
        podcast_description = podcast_level["description"]
        podcast_title = podcast_level["title"]

        podcast_data.append((podcast_title, podcast_description))

        episode_level = feed["rss"]["channel"]["item"]

        for episode in episode_level:
            episode_data.append((episode["enclosure"]["@url"],
                                podcast_title,
                                episode["pubDate"],
                                episode["title"], 
                                episode["description"],
                                ))
        
            date_data.append(episode["pubDate"])


    time_data = []
    for date in date_data:
        dt_obj = string_to_datetime(date)
        d_obj = dt_obj.date()
        day = d_obj.day
        month_number = d_obj.month
        month = month_number_to_name[month_number]
        year = d_obj.year
        time_data.append((d_obj,year,month,month_number,day))

    time_data = list(set(time_data))


    insert_query = """
        INSERT IGNORE INTO time_dimension (date, year, month, month_number, day)
        VALUES (%s, %s, %s, %s, %s)
    """
    cursor.executemany(insert_query, time_data) 
    connection.commit()


    insert_query = """
        INSERT IGNORE INTO podcast_dimension (podcast_title, description)
        VALUES (%s, %s)
    """
    cursor.executemany(insert_query, podcast_data)
    connection.commit()



    extract_podcast_ids_query = """
        SELECT podcast_title, podcast_id
        FROM podcast_dimension
    """
    cursor.execute(extract_podcast_ids_query)
    podcast_id_data = cursor.fetchall()

    title_to_id = dict(podcast_id_data)
    processed_episodes = process_episodes(episode_data, title_to_id)


    insert_query = """
        INSERT IGNORE INTO episode_dimension (link, podcast_id, episode_release_date, episode_title, episode_description)
        VALUES (%s, %s, %s, %s, %s)
    """
    cursor.executemany(insert_query, processed_episodes)    
    connection.commit()

    
    cursor.close()
    connection.close()