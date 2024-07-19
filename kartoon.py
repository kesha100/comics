
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import boto3
import os, json, io
from dotenv import load_dotenv
from openai import OpenAI
load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=api_key)
from images import upload_image_to_s3, delete_image_from_s3
from generate_panels import generate_panels
import openai
from database import save_panel_to_db, connect_to_database
from stability_ai import text_to_image
from add_text import add_text_to_panel
from create_strip import create_and_save_strips, create_strip
from PIL import Image
from typing import List

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME')
AWS_REGION = os.getenv('AWS_REGION')

@app.post("/describe_image/")
async def describe_image(image_data):
    try:
        file_name = "uploaded_image.jpeg"
        image_url = upload_image_to_s3(image_data, file_name)
        print(f"Uploaded file URL: {image_url}")

        # Use the file URL to generate the prompt for GPT-4
        system_prompt = "You are the best image describer. Describe the following image."
        user_prompt = (
                       "Please answer the following questions:\n"
                       "0. What is this or who is this?\n"
                       "1. Is this a girl or boy?\n"
                       "2. What is this person wearing?\n"
                       "3. What is this person doing and what is the background?\n"
                       "4. What is the person's expression and mood?\n"
                       "7. What is the person's skin color?")

        # Sending the request to GPT-4 (Assuming you have set up OpenAI's API)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                }
            ],
            temperature=0.5,
            max_tokens=300
        )

        # Extract the description from the response
        description = response.choices[0].message.content

        # Delete the image from S3 after processing
        delete_image_from_s3(file_name)

        return {"description": description}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
class ScenarioInput(BaseModel):
    scenario: str

def convert_jpg_to_jpeg(image_data):
    with io.BytesIO() as output:
        image = Image.open(io.BytesIO(image_data))
        image.save(output, format="JPEG")
        return output.getvalue()
    
@app.post("/generate-comics")
async def generate_comics(file: UploadFile = File(...), scenario: str = Form("")):
    print(f"File received: {file.filename}")
    print(f"Scenario received: {scenario}")
    style = "american comic, colored"

    try:
        # Read the file data
        image_data = await file.read()

        # Convert 'jpg' to 'jpeg' if necessary
        if file.filename.lower().endswith('.jpg'):
            image_data = convert_jpg_to_jpeg(image_data)
        
        # Describe the uploaded image using OpenAI's GPT-4
        description_response = await describe_image(image_data)
        description = description_response["description"]
        print(f"Description from GPT-4: {description}")

        # Combine the image description with the user-provided scenario
        combined_scenario = f"Characters: {description}. {scenario}"
        print(f"Combined scenario: {combined_scenario}")

        # Generate comic panels based on the combined scenario
        panels = generate_panels(combined_scenario)
        print(f"Generated panels: {panels}")

        # Style for the comic panels
        style = "american comic, colored"

        # Function to save panel images to S3
        def save_panel_images_to_s3(panels):
            panel_images = []

            for panel in panels:
                if "description" in panel and panel["description"]:
                    panel_prompt = panel["description"] + ", cartoon box, " + style
                else:
                    print(f"Warning: Panel {panel['number']} does not have a valid description.")
                    continue

                # Generate image for the panel based on the prompt
                panel_image = text_to_image(panel_prompt)

                # Convert the image to JPEG bytes
                buffered = io.BytesIO()
                panel_image.save(buffered, format="JPEG")
                image_data = buffered.getvalue()

                # Add text to the panel if 'text' exists in the panel
                if 'text' in panel and panel["text"]:
                    panel_image_with_text = add_text_to_panel(panel["text"], panel_image)
                    buffered_with_text = io.BytesIO()
                    panel_image_with_text.save(buffered_with_text, format="JPEG")
                    image_data_with_text = buffered_with_text.getvalue()
                else:
                    image_data_with_text = image_data

                # Upload the final image (with or without text) to S3
                image_url = upload_image_to_s3(image_data_with_text, f"panels/panel-{panel['number']}.jpeg")
                save_panel_to_db(panel.get("text", ""), image_url)  # Save empty string if 'text' is not present
                if image_url is None:
                    raise HTTPException(status_code=500, detail="Failed to upload image to S3")

                panel_images.append(image_url)

            return panel_images

        # Save panel images to S3
        saved_panel_images = save_panel_images_to_s3(panels)

        return {"message": "Panels generated and saved", "panels": panels, "imageUrls": saved_panel_images}
    

    except Exception as e:
        print(f"Error in generate_comics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
def get_panels():
    conn = connect_to_database()
    cur = conn.cursor()
    cur.execute('SELECT panelId, image_url FROM "Panel";')
    try:
        cur.execute(
            'SELECT panelId, image_url FROM "Panel"'
        )
        panels = cur.fetchall
        conn.commit()
    except Exception as e:
        print(f"Error saving panel to database: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()
        return panels

class Panel(BaseModel):
    panelId: int
    image_url: str

@app.get("/images/", response_model=List[Panel])
def read_image_urls():
    try:
        panels = get_panels()
        return [{"panelId": panel[0], "image_url": panel[1]} for panel in panels]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))