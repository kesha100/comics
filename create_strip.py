# from PIL import Image

# # Function to resize and add a black border to an image
# def resize_and_add_border(image, target_size, border_size):
#     resized_image = Image.new("RGB", target_size, "black")
#     resized_image.paste(image, ((target_size[0] - image.width) // 2, (target_size[1] - image.height) // 2))
#     return resized_image

# def create_strip(images):
#     # Desired grid size
#     columns, rows = 2, 3

#     # Calculate the size of the output image
#     output_width = columns * images[0].width + (columns - 1) * 10  # 10 is the black border width
#     output_height = rows * images[0].height + (rows - 1) * 10  # 10 is the black border width

#     # Create a new image with the calculated size
#     result_image = Image.new("RGB", (output_width, output_height), "white")

#     # Combine images into a grid with black borders
#     for i, img in enumerate(images):
#         x = (i % columns) * (img.width + 10)  # 10 is the black border width
#         y = (i // columns) * (img.height + 10)  # 10 is the black border width

#         resized_img = resize_and_add_border(img, (images[0].width, images[0].height), 10)
#         result_image.paste(resized_img, (x, y))

#     return result_image.resize((1024, 1536))
from PIL import Image, ImageOps
from io import BytesIO
import requests
import os
from images import upload_image_to_s3  # Assuming this function handles S3 uploads correctly
from database import connect_to_database

# Fetch image URLs from the database
def fetch_image_urls():
    connection = connect_to_database()
    cursor = connection.cursor()
    
    try:
        cursor.execute('SELECT image_url FROM "Panel"')
        image_urls = cursor.fetchall()
        return [url[0] for url in image_urls]
    except Exception as e:
        print(f"Error fetching image URLs from database: {e}")
        return []
    finally:
        cursor.close()
        connection.close()

# Download images from the URLs
def download_images(image_urls):
    images = []
    for url in image_urls:
        response = requests.get(url)
        img = Image.open(BytesIO(response.content))
        images.append(img)
    return images

# Function to resize and add a black border to an image
def resize_and_add_border(image, target_size, border_size):
    new_size = (target_size[0] - border_size * 2, target_size[1] - border_size * 2)
    resized_image = ImageOps.fit(image, new_size, method=Image.LANCZOS, centering=(0.5, 0.5))
    bordered_image = ImageOps.expand(resized_image, border=border_size, fill="black")
    return bordered_image

# Create a strip of images
def create_strip(images):
    columns, rows = 2, 2  # Adjusted for 4 images
    output_width = columns * images[0].width + (columns - 1) * 10
    output_height = rows * images[0].height + (rows - 1) * 10

    result_image = Image.new("RGB", (output_width, output_height), "white")

    for i, img in enumerate(images):
        x = (i % columns) * (img.width + 10)
        y = (i // columns) * (img.height + 10)

        resized_img = resize_and_add_border(img, (images[0].width, images[0].height), 10)
        result_image.paste(resized_img, (x, y))

    return result_image.resize((1024, 1024), Image.LANCZOS)  # Adjust size and quality

# Save the strip image URL to the Vcomics table
def save_strip_to_vcomics(strip):
    connection = connect_to_database()
    cursor = connection.cursor()
    
    try:
        cursor.execute(
            'INSERT INTO "Vcomics" (strip) VALUES (%s)',
            (strip,)
        )
        connection.commit()
    except Exception as e:
        print(f"Error saving strip to database: {e}")
        connection.rollback()
    finally:
        cursor.close()
        connection.close()

# Main function to create and save the comic strips
def create_and_save_strips():
    image_urls = fetch_image_urls()
    if not image_urls:
        print("No image URLs fetched.")
        return

    batch_size = 4
    num_strips = 3  # Number of strips to generate
    strip_number = 1

    # Create only three strips
    for j in range(num_strips):
        start_index = j * batch_size
        end_index = start_index + batch_size
        batch_urls = image_urls[start_index:end_index]

        if len(batch_urls) < batch_size:
            print(f"Insufficient images to create strip {j + 1}. Skipping.")
            continue

        images = download_images(batch_urls)
        if not images:
            print(f"Failed to download images for strip {j + 1}. Skipping.")
            continue

        strip_image = create_strip(images)
        buffered = BytesIO()
        strip_image.save(buffered, format="JPEG", quality=95)  # Adjust quality as needed
        strip_image_data = buffered.getvalue()

        strip_image_url = upload_image_to_s3(strip_image_data, f"strips/comic_strip_{strip_number}.jpeg")
        if strip_image_url:
            save_strip_to_vcomics(strip_image_url)
            print(f"Comic strip {strip_number} saved to database with URL: {strip_image_url}")
            strip_number += 1
        else:
            print(f"Failed to upload comic strip {strip_number} to S3.")


 # Adjust size as needed
