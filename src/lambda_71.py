import os
import tarfile
import boto3
import json
import urllib

import mysql.connector

#Triggered from sentiment output
SENTENCE_STAGING_BUCKET = os.environ["ENV_VAR_1"] # name of bucket for concatenated transcripts
USER_NAME = os.environ["ENV_VAR_2"] 
PASSWORD = os.environ["ENV_VAR_3"]
RDS_ENDPOINT = os.environ["ENV_VAR_4"]
DB_NAME = os.environ["ENV_VAR_5"]

def unpack_sentiment_output(bucket, key):
    

    # Initialize AWS S3 client
    s3_client = boto3.client('s3')

    # Download the .tar.gz archive from S3
    archive_dir = "/tmp"
    os.makedirs(archive_dir, exist_ok=True)
    archive_path = os.path.join(archive_dir, 'temp.tar.gz')
    s3_client.download_file(bucket, key, archive_path)

    # Extract the archive
    with tarfile.open(archive_path, 'r:gz') as tar:
        tar.extractall(path=archive_dir)

    # Locate and retrieve the file from the extracted contents
    filename = 'output'
    file_path = os.path.join(archive_dir, filename)
    json_data = []

    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            for line in f:
                json_data.append(json.loads(line))

        return json_data
       
    else:
        print(f"JSON file '{filename}' not found in the extracted contents.")



def lambda_handler(event, context):
    input_bucket = event['Records'][0]['s3']['bucket']['name']
    print(f"Put trigger from bucket {input_bucket}")
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    print(f"Put object has key: {key}")

    sentiment_output = unpack_sentiment_output(bucket=input_bucket, key=key)

    podcast_title = key.split('/')[0]
    episode_id = key.split('/')[1]

    KEY = podcast_title + "/" + episode_id + ".json"
    
    s3 = boto3.client('s3')
    obj = s3.get_object(Bucket=SENTENCE_STAGING_BUCKET, Key=KEY)
    sentences = json.loads(obj['Body'].read())

    episode_id = int(episode_id.split("_")[-1])


    print(len(sentences) == len(sentiment_output))


    sentence_data = []

    for i in range(0,len(sentences)):
        sentence_text = sentences[i]
        
        overall_sentiment = sentiment_output[i]["Sentiment"]
        negative_score = sentiment_output[i]["SentimentScore"]["Negative"]
        neutral_score = sentiment_output[i]["SentimentScore"]["Neutral"]
        positive_score = sentiment_output[i]["SentimentScore"]["Positive"]
        mixed_score = sentiment_output[i]["SentimentScore"]["Mixed"]
        sentence_data.append((sentence_text,
                            episode_id,
                            overall_sentiment,
                            negative_score,
                            neutral_score,
                            positive_score,
                            mixed_score, 
                            i))
        



    connection = mysql.connector.connect(
            host = RDS_ENDPOINT,
            user = USER_NAME,
            password = PASSWORD,
            database = DB_NAME
    )

    print("Connected!!!")

    insert_query = """
        INSERT IGNORE INTO sentence_dimension (
            sentence_text,
            episode_id, 
            overall_sentiment, 
            negative_score,
            neutral_score, 
            positive_score,
            mixed_score,
            sentence_index
            )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """

    cursor = connection.cursor()

    cursor.executemany(insert_query, sentence_data)
        
    connection.commit()
    cursor.close()
    connection.close()
