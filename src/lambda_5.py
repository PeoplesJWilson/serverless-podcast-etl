import boto3
import urllib.parse
import os 
import json

import mysql.connector
import nltk

s3 = boto3.client('s3')

BUCKET_NAME = os.environ["ENV_VAR_1"] # name of bucket for concatenated transcripts
USER_NAME = os.environ["ENV_VAR_2"] 
PASSWORD = os.environ["ENV_VAR_3"]
RDS_ENDPOINT = os.environ["ENV_VAR_4"]
DB_NAME = os.environ["ENV_VAR_5"]


def reduce(event, context): 
    bucket = event['Records'][0]['s3']['bucket']['name']
    print(f"Put trigger from bucket {bucket}")
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    print(f"Put object has key: {key}")

    directories = key.split('/')
    podcast_name = directories[0]
    episode_id = directories[1]
    prefix = os.path.join(podcast_name,episode_id) + '/'

    results = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)["Contents"]
    results = [result['Key'] for result in results if result['Key'].endswith(".json")]

    num_objects = len(results)
    




    id = int(episode_id.split('_')[-1])
    connection = mysql.connector.connect(
            host = RDS_ENDPOINT,
            user = USER_NAME,
            password = PASSWORD,
            database = DB_NAME
            )

    cursor = connection.cursor()

    select_links_query = f"""
        SELECT episode_id, num_chunks 
        FROM episode_dimension
        WHERE episode_id = %s
        LIMIT 1
        """
    
    cursor.execute(select_links_query, (id,))

    result = cursor.fetchone()
    cursor.close()
    connection.close()


    num_chunks = result[1]


    if num_objects < num_chunks:
        error = f"only {num_objects} transcribed in bucket, but expected {num_chunks}. Waiting for all transcriptions to finish."
        print(error)
        return error


    transcription = ""
    for chunk_num in range(1,num_chunks + 1):
        current_chunk = f"chunk_{chunk_num}.json"
        current_key = prefix + current_chunk

        obj = s3.get_object(Bucket=bucket, Key=current_key)
        data = json.loads(obj['Body'].read())

        current_chunk_text = data['results']['transcripts'][0]['transcript']

        transcription = transcription + current_chunk_text + " "


    nltk.data.path.append("/tmp")
    nltk.download("punkt", download_dir="/tmp")

    sentences = nltk.tokenize.sent_tokenize(transcription)
    json_data = json.dumps(sentences)

    transcription = "\n".join(sentences)
    byte_data = bytes(transcription,"utf-8")

    transcription_key_name = podcast_name + "/" + episode_id + ".txt"
    sentence_key_name = podcast_name + "/" + episode_id + ".json"


    s3.put_object(Body=byte_data, Bucket=BUCKET_NAME, Key=transcription_key_name)
    s3.put_object(Body=json_data, Bucket=BUCKET_NAME, Key=sentence_key_name)