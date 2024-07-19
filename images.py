from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import boto3
from botocore.exceptions import NoCredentialsError
import os, io
from dotenv import load_dotenv
from openai import OpenAI
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
import openai

load_dotenv()


BUCKET_NAME = 'vcomics'
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_REGION = os.getenv('AWS_REGION')
S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME')

s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)

class ScenarioInput(BaseModel):
    scenario: str

def upload_image_to_s3(image_data, file_name):
    try:
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=file_name,
            Body=image_data,
            ContentType='image/jpeg'
        )
        image_url = f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{file_name}"
        return image_url
    except Exception as e:
        print(f"Error uploading image to S3: {e}")
        return None
    # except NoCredentialsError:
    #     raise HTTPException(status_code=403, detail="AWS credentials not available")
   
def delete_image_from_s3(file_name: str):
    try:
        s3_client.delete_object(Bucket=S3_BUCKET_NAME, Key=file_name)
    except NoCredentialsError:
        raise HTTPException(status_code=403, detail="AWS credentials not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


