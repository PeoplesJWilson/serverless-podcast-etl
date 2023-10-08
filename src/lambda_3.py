import requests
import mysql.connector
import os
import boto3

BUCKET_NAME = os.environ["ENV_VAR_1"] #ringer podcats network chunks, NOT RSS BUCKET

USER_NAME = os.environ["ENV_VAR_2"]
PASSWORD = os.environ["ENV_VAR_3"]
RDS_ENDPOINT = os.environ["ENV_VAR_4"]
DB_NAME = os.environ["ENV_VAR_5"]

s3 = boto3.client('s3')


def download(event, context):

    try:
        # Get the podcast name from the SQS message body
        podcast = event['Records'][0]['body']


    except Exception as e:
        print(f"Error: {e}")
    

    print(f"selected podcast {podcast}.")
    #___________________________________________
    # select most recent episode of given podcast
    # which is not already downlaoded
    connection = mysql.connector.connect(
            host = RDS_ENDPOINT,
            user = USER_NAME,
            password = PASSWORD,
            database = DB_NAME
            )

    cursor = connection.cursor()

    extract_podcast_ids_query = """
        SELECT podcast_title, podcast_id
        FROM podcast_dimension
    """

    cursor.execute(extract_podcast_ids_query)
    podcast_id_data = cursor.fetchall()

    title_to_id = dict(podcast_id_data)
    possible_podcasts = list(title_to_id.keys())
    print(f"The following is a list of possible podcasts: {possible_podcasts}")
    if podcast not in possible_podcasts:
        print(f"Error: {podcast} name is not in the database")
        return 
    
    podcast_id = title_to_id[podcast]

    select_links_query = f"""
        SELECT episode_id, episode_title, link 
        FROM episode_dimension
        WHERE podcast_id = %s
        AND downloaded IS FALSE
        ORDER BY episode_release_date DESC
        LIMIT 1
        """
    
    cursor.execute(select_links_query, (podcast_id,))

    result = cursor.fetchone()
    cursor.close()
    connection.close()
    #____________________________________________
    id = result[0]
    title = result[1]
    link = result[2]
    
    

    episode_name = f"episode_id_{id}"
    filename = f"{episode_name}.mp3"
    local_path = os.path.join("/tmp",filename)

    print(f"... Downloading episode: \n {title} from podcast {podcast} ...")

    audio = requests.get(link)

    print("audio downloaded ... saving audio locally")
    with open(local_path, "wb+") as f:
        f.write(audio.content)

    print("audio saved locally. Loading and chopping audio")
    podcast_folder = podcast.lower().replace(' ', '_')
    s3_path_prefix = podcast_folder + '/' + episode_name + '/'
    CHUNK_SIZE = 10000000
    chunk_number = 1
    with open(local_path, 'rb') as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                chunk_number = chunk_number - 1
                break  # End of file, exit the loop
    
            # Write the current chunk to a new file
            with open("/tmp/chunk.mp3", 'wb') as chunk_file:
                chunk_file.write(chunk)
            
            print(f"Saved locally. Uploading chunk {chunk_number} to S3")
            chunk_name = f"chunk_{chunk_number}.mp3"
            key_name = s3_path_prefix + chunk_name
            s3.upload_file(Bucket=BUCKET_NAME, Filename='/tmp/chunk.mp3', Key=key_name)

            print(f"Chunk {chunk_name} uploaded to S3. Removing temp chunk.")
            os.remove('/tmp/chunk.mp3')
            
            chunk_number += 1
    

    print("all chunks successfully uploaded ... updating episode_dimension table to reflect this")
    connection = mysql.connector.connect(
            host = RDS_ENDPOINT,
            user = USER_NAME,
            password = PASSWORD,
            database = DB_NAME
            )

    cursor = connection.cursor()

    update_query = """UPDATE episode_dimension
                  SET downloaded = TRUE,
                      num_chunks = %s
                  WHERE episode_id = %s"""
    
    cursor.execute(update_query, (chunk_number,id))
    connection.commit()

    cursor.close()
    connection.close()