import boto3
import os
import urllib

SENTIMENT_OUTPUT_BUCKET = os.environ["ENV_VAR_1"]
ENTITY_OUTPUT_BUCKET = os.environ["ENV_VAR_2"]
COMPREHEND_ROLE_ARN = os.environ["ENV_VAR_3"]

comprehend = boto3.client("comprehend")

def start_async_detection(event, context):

    input_bucket = event['Records'][0]['s3']['bucket']['name']
    print(f"Put trigger from bucket {input_bucket}")
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    print(f"Put object has key: {key}")
    input_uri = f"s3://{input_bucket}/{key}"    # key should end with .txt

    directories = key.split('/')
    print(directories)
    podcast_name = directories[0]
    episode_id = directories[1][0:-4]
    print(episode_id)


    sentiment_output_uri = f"s3://{SENTIMENT_OUTPUT_BUCKET}/{podcast_name}/{episode_id}"
    sentiment_job_name = episode_id + "_detect_sentiment"

    sentiment_start_response = comprehend.start_sentiment_detection_job(

        InputDataConfig={
            'S3Uri': input_uri,
            'InputFormat': 'ONE_DOC_PER_LINE'
        },

        OutputDataConfig={
            'S3Uri': sentiment_output_uri
        },
        LanguageCode = "en",
        DataAccessRoleArn= COMPREHEND_ROLE_ARN,
        JobName= sentiment_job_name
    )



    entity_output_uri = f"s3://{ENTITY_OUTPUT_BUCKET}/{podcast_name}/{episode_id}"
    entity_job_name = episode_id + "_detect_entities"

    entities_start_response = comprehend.start_entities_detection_job(

        InputDataConfig={
            'S3Uri': input_uri,
            'InputFormat': 'ONE_DOC_PER_FILE'
        },

        OutputDataConfig={
            'S3Uri': entity_output_uri
        },
        LanguageCode = "en",
        DataAccessRoleArn= COMPREHEND_ROLE_ARN,
        JobName= entity_job_name
    )


    return [sentiment_start_response, entities_start_response]






   