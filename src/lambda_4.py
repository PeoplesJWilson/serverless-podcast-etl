import boto3
import urllib.parse
import os 

transcribe = boto3.client('transcribe')

OUTPUT_BUCKET = os.environ['ENV_VAR_1']


def transcribe_podcast(event, context): 
    bucket = event['Records'][0]['s3']['bucket']['name']
    print(f"Put trigger from bucket {bucket}")
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    print(f"Put object has key: {key}")

    job_name = key.replace('_','-').replace('.','-').replace('/','-')
    job_uri = 's3://{0}/{1}'.format(bucket, key)

    output_key = key.replace("mp3","json")

    response = transcribe.start_transcription_job(
        TranscriptionJobName = job_name,
        Media = {
            'MediaFileUri': job_uri
        },
        OutputBucketName = OUTPUT_BUCKET,
        OutputKey = output_key, 
        LanguageCode = 'en-US', 
        Settings = {
            'ChannelIdentification':True #,
            #'MaxSpeakerLabels': 7,
            #'ShowSpeakerLabels': True
        }
    )

    print(response)