import os  
import cv2  
import json  
import numpy as np  
from PIL import Image  
from scenedetect import detect, AdaptiveDetector  
import concurrent.futures  
from dotenv import load_dotenv  

  
from openai import AzureOpenAI
import base64
load_dotenv()
client = AzureOpenAI(
  api_key=os.environ.get("AZURE_OPENAI_API_KEY"),  
  api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
  azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT"),
)
  
def encode_image(image_path):  
    with open(image_path, "rb") as image_file:  
        return base64.b64encode(image_file.read()).decode('utf-8')  
  
def get_gpt_response(message_content, max_tokens=3500, json_output=False):  
    # Prepare the message content  
    if json_output:  
        response = client.chat.completions.create(  
            model=os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT"),  
            messages=[  
                {  
                    "role": "user",  
                    "content": message_content,  
                }  
            ],  
            max_tokens=max_tokens,  
            response_format={"type": "json_object"}  
        )  
    else:  
        response = client.chat.completions.create(  
            model=os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT"),  
            messages=[  
                {  
                    "role": "user",  
                    "content": message_content,  
                }  
            ],  
            max_tokens=max_tokens,  
        )  
      
    # Return the response content  
    print(response.choices[0].message.content)
    return response.choices[0].message.content  
def load_file_content(file_path):  
    with open(file_path, 'r') as file:  
        return file.read()  
  
def process_images_from_folder(folder_path, template_content, batch_size=4):  
    # Get list of image files in the folder  
    image_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]  
    print("Total number of images", len(image_files))  
  
    # Initialize summary content  
    summary_content = ""  
  
    # Updated prompt for generic summary creation  
    prompt_part1 = """  
    You are an AI assistant tasked with analyzing visual content from images extracted from a video.   
    Your role is to create a comprehensive and concise summary based on the visual details observed in the images.   
    Below you will find the instructions for generating the summary:  
  
    {instruction}  
  
    Given the volume of images you need to review, you will update the summary content batch by batch.   
    Each time you review a new batch of images, incorporate the new findings into the existing summary.   
    Avoid duplicating information that has already been included in the summary.  
  
    Here is the summary content up to the last batch of images as a starting point (if blank, this is the first batch):  
    {summary_content}  
  
    ### Here are the images attached in this batch:  
    """  
  
    prompt_part2 = """  
    Please create/update the summary with the latest information from the images and output in raw markdown format under the "## Summary" section.   
    Do not include any additional details outside of this format.  
  
    ## Summary  
    """  
  
    # Process images in batches  
    for i in range(0, len(image_files), batch_size):  
        batch = image_files[i:i + batch_size]  
        print("Batch length: ", len(batch), batch)  
  
        # Prepare GPT input  
        message_content = [{"type": "text", "text": prompt_part1.format(instruction=template_content, summary_content=summary_content)}]  
        base64_images = [encode_image(image_path) for image_path in batch]  
  
        for base64_image, image_path in zip(base64_images, batch):  
            message_content.append({"type": "text", "text": image_path})  
            message_content.append({  
                "type": "image_url",  
                "image_url": {  
                    "url": f"data:image/jpeg;base64,{base64_image}",  
                },  
            })  
  
        message_content.append({"type": "text", "text": prompt_part2})  
  
        # Call GPT for response  
        raw_response = get_gpt_response(message_content)  
  
        # Extract the content below ## Summary  
        summary_marker = "## Summary"  
        if summary_marker in raw_response:  
            start_index = raw_response.index(summary_marker) + len(summary_marker)  
            summary_content = raw_response[start_index:].strip()  
        else:  
            summary_content = raw_response.strip()  
  
    return summary_content  
  
  
   
def get_frames_from_scene(scene, video_capture, n):  
    start_frame = scene[0].frame_num  
    end_frame = scene[1].frame_num  
    frame_step = (end_frame - start_frame) // (n + 1)  
  
    frames = []  
    frame_ids = []  
  
    for i in range(1, n + 1):  
        frame_id = start_frame + i * frame_step  
        video_capture.set(cv2.CAP_PROP_POS_FRAMES, frame_id)  
        _, frame = video_capture.read()  
        frames.append(Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))  
        frame_ids.append(frame_id)  
  
    return frame_ids, frames  
  
def save_frame_image(frame, output_path):  
    frame.save(output_path)  
  
def get_frame_time(video_capture, frame_id):  
    fps = video_capture.get(cv2.CAP_PROP_FPS)  
    seconds = frame_id / fps  
    return seconds  
  
  
import os  
import cv2  
from scenedetect import detect  
from scenedetect.detectors import ContentDetector, HistogramDetector, AdaptiveDetector
  
def get_frames_from_video(video_path, output_folder, max_frames=100):  
    # Initialize video capture and detect scenes using ContentDetector  
    video_capture = cv2.VideoCapture(video_path)  
    content_detector = HistogramDetector()  # Adjust threshold and min_scene_len as needed  
    content_list = detect(video_path, content_detector)  
    print("number of scenes", len(content_list))
    total_frames_extracted = 0  
  
    for scene_idx, scene in enumerate(content_list):  
        if total_frames_extracted >= max_frames:  
            break  
  
        # Determine the number of frames to extract from this scene  
        frames_in_scene = min(max_frames - total_frames_extracted, 3)  # Max 3 frames per scene  
  
        # Extract frames from the current scene  
        frame_ids, frames = get_frames_from_scene(scene, video_capture, frames_in_scene)  
  
        # Save extracted frames  
        for frame_num, (frame_id, frame) in enumerate(zip(frame_ids, frames)):  
            frame_filename = f"scene_{scene_idx+1}_frame_{frame_id}_{frame_num+1}.jpg"  
            frame_output_path = os.path.join(output_folder, frame_filename)  
            save_frame_image(frame, frame_output_path)  
            total_frames_extracted += 1  
  
            if total_frames_extracted >= max_frames:  
                break  
  
    # Return list of saved frame paths  
    return [os.path.join(output_folder, f) for f in os.listdir(output_folder) if f.endswith('.jpg')]  
    

