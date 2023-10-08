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

def unpack_entity_output(bucket, key): 
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

    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            json_data = json.loads(f.read())
        return json_data
       
    else:
        print(f"JSON file '{filename}' not found in the extracted contents.")


def lambda_handler(event, context):
    input_bucket = event['Records'][0]['s3']['bucket']['name']
    print(f"Put trigger from bucket {input_bucket}")
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    print(f"Put object has key: {key}")

    entity_output = unpack_entity_output(bucket=input_bucket, key=key)
    entities = entity_output["Entities"]

    podcast_title = key.split('/')[0]
    episode_id = key.split('/')[1]

    KEY = podcast_title + "/" + episode_id + ".json"
    
    s3 = boto3.client('s3')
    obj = s3.get_object(Bucket=SENTENCE_STAGING_BUCKET, Key=KEY)
    sentences = json.loads(obj['Body'].read())
    sentences = [sentence + "\n" for sentence in sentences]
    

    episode_id = int(episode_id.split("_")[-1])


    indices = []
    old_index = 0
    for sentence in sentences:
        new_index = old_index + len(sentence)
        indices.append((old_index, new_index))
        old_index = new_index
        



    entity_sentence_indices = []
    num_sentences = len(indices)

    sentence_index = 0
    entity_index = 0
    num_entites = len(entities)
    
    while entity_index < num_entites:
        
        entity_datum = entities[entity_index]
        lower_index = entity_datum["BeginOffset"]
        upper_index = entity_datum["EndOffset"]
        
        current_lower_index = indices[sentence_index][0]
        current_upper_index = indices[sentence_index][1]
        
        if (lower_index > current_upper_index):
            #print("Entity mention range:")
            #print(lower_index)
            #print(upper_index)
            #print("Sentence index range")
            #print(current_lower_index)
            #print(current_upper_index)
            sentence_index += 1
            #print("Actual sentence index:")
            #print(sentence_index)
            #print("out of how many sentences:")
            #print(num_sentences)
        
        elif (current_lower_index < lower_index) and (upper_index < current_upper_index):
            #print("Clean capture")
            print(f"Text of entity:{entity_datum['Text']}")
            print(f"Text of sentence: {sentences[sentence_index]}")
            entity_sentence_indices.append(sentence_index)
            
            entity_index += 1
            
        else:
            #print("Messy capture")
            entity_sentence_indices.append(sentence_index)
            entity_index += 1
            
            

    
    entity_data = []
    for i,entity_datum in enumerate(entities):
        entity_text = entity_datum["Text"]
        entity_type = entity_datum["Type"]
        sentence_index = entity_sentence_indices[i]
        entity_data.append(
            (episode_id,
            entity_text,
            entity_type,
            sentence_index)
        )



    connection = mysql.connector.connect(
            host = RDS_ENDPOINT,
            user = USER_NAME,
            password = PASSWORD,
            database = DB_NAME
            )
    print("Connected!!!")

    insert_query = """
        INSERT IGNORE INTO entity_dimension (
            episode_id,
            entity_text,
            entity_type,
            sentence_index
            )
        VALUES (%s, %s, %s, %s)
    """

    cursor = connection.cursor()

    cursor.executemany(insert_query, entity_data)
        
    connection.commit()
    cursor.close()
    connection.close()
