import os  
import cv2  
import json  
import numpy as np  
from PIL import Image  
import concurrent.futures  
from dotenv import load_dotenv  
  
import os  
import cv2  
from scenedetect import detect  
from scenedetect.detectors import ContentDetector, HistogramDetector, AdaptiveDetector
from moviepy import AudioFileClip, VideoFileClip  
  

  
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
  
  
from pydub import AudioSegment  
  
# Whisper Transcription with Chunk Splitting  
def transcribe_audio(audio_path, chunk_duration=120):  
    """  
    Transcribes audio using Azure OpenAI Whisper, splitting the audio into chunks  
    if it exceeds the maximum allowed size.  
      
    Args:  
        audio_path (str): Path to the audio file.  
        chunk_duration (int): Duration of each audio chunk in seconds.  
  
    Returns:  
        tuple: (transcription_text, transcription_segments)  
    """  
    deployment_id = os.getenv("WHISPER_DEPLOYMENT_ID")  
  
    # Load the audio file using pydub  
    audio = AudioSegment.from_file(audio_path)  
  
    # Split audio into chunks of `chunk_duration` seconds  
    audio_chunks = [audio[i * chunk_duration * 1000:(i + 1) * chunk_duration * 1000]  
                    for i in range(len(audio) // (chunk_duration * 1000) + 1)]  
  
    transcription_text = ""  
    transcription_segments = []  
  
    # Process each chunk  
    for idx, chunk in enumerate(audio_chunks):  
        # Save the chunk as a temporary file  
        chunk_path = f"{audio_path}_chunk_{idx}.wav"  
        chunk.export(chunk_path, format="wav")  
  
        # Transcribe the chunk  
        with open(chunk_path, "rb") as audio_file:  
            result = client.audio.transcriptions.create(  
                file=audio_file,  
                model=deployment_id  
            )  
  
        # Append the results  
        transcription_text += result["text"] + " "  
        transcription_segments.extend(result["segments"])  
  
        # Clean up temporary chunk file  
        os.remove(chunk_path)  
  
    return transcription_text.strip(), transcription_segments  
  
# Extract audio and split based on frame timestamps  
def extract_and_split_audio(video_path, frame_timestamps):  
    audio_path = video_path.replace(".mp4", ".wav")  
    video_clip = VideoFileClip(video_path)  
    video_clip.audio.write_audiofile(audio_path)  
  
    # Transcribe audio  
    transcription_text, transcription_segments = transcribe_audio(audio_path)  
    os.remove(audio_path)  # Clean up audio file  
  
    # Split transcription based on frame timestamps  
    split_transcription = []  
    for frame in frame_timestamps:  
        start_time = frame["timestamp"]  
        end_time = frame.get("end_timestamp", start_time + 1)  # Assume 1-second duration if no end time  
        frame_transcription = [  
            segment["text"] for segment in transcription_segments  
            if segment["start"] >= start_time and segment["end"] <= end_time  
        ]  
        split_transcription.append(" ".join(frame_transcription))  
  
    return split_transcription  
  
# Extract frames and timestamps  
def get_frames_from_video(video_path, output_folder, max_frames=100):  
    video_capture = cv2.VideoCapture(video_path)  
    content_detector = HistogramDetector()  
    content_list = detect(video_path, content_detector)  
  
    print("Number of scenes:", len(content_list))  
  
    total_frames_extracted = 0  
    frame_timestamps = []  
  
    for scene_idx, scene in enumerate(content_list):  
        if total_frames_extracted >= max_frames:  
            break  
  
        # Determine the number of frames to extract from this scene  
        frames_in_scene = min(max_frames - total_frames_extracted, 3)  # Max 3 frames per scene  
        frame_ids, frames = get_frames_from_scene(scene, video_capture, frames_in_scene)  
  
        for frame_num, (frame_id, frame) in enumerate(zip(frame_ids, frames)):  
            frame_time = get_frame_time(video_capture, frame_id)  
            frame_filename = f"scene_{scene_idx+1}_frame_{frame_id}_{frame_num+1}.jpg"  
            frame_output_path = os.path.join(output_folder, frame_filename)  
            save_frame_image(frame, frame_output_path)  
  
            frame_timestamps.append({  
                "path": frame_output_path,  
                "timestamp": frame_time,  
                "end_timestamp": get_frame_time(video_capture, frame_id + 1)  # Estimate end timestamp  
            })  
            total_frames_extracted += 1  
  
            if total_frames_extracted >= max_frames:  
                break  
  
    return frame_timestamps  
  
# Process frames and audio  
def process_frames_and_audio(frame_timestamps, transcription, template_content, batch_size=4):  
    summary_content = ""  
    prompt_part1 = """  
    You are an AI assistant tasked with analyzing visual and audio content from a video.  
    Your role is to create a comprehensive and concise summary based on the visual details from frames and the corresponding audio transcription.  
    Incorporate both visual and audio information into the summary.  
  
    {instruction}  
  
    Below is the current summary (if blank, this is the first batch):  
    {summary_content}  
  
    ### Audio Transcript:  
    {audio_text}  
  
    ### Attached Images:  
    """  
    prompt_part2 = """  
    Please create/update the summary with the latest information from both the audio and images.  
    Provide the summary in raw markdown format under the "## Summary" section.  
  
    ## Summary  
    """  
  
    for i in range(0, len(frame_timestamps), batch_size):  
        batch = frame_timestamps[i:i + batch_size]  
        batch_images = [item["path"] for item in batch]  
        batch_audio_text = "\n".join(transcription[i:i + batch_size])  
  
        # Prepare GPT input  
        message_content = [{"type": "text", "text": prompt_part1.format(  
            instruction=template_content,  
            summary_content=summary_content,  
            audio_text=batch_audio_text  
        )}]  
        base64_images = [encode_image(image_path) for image_path in batch_images]  
  
        for base64_image, image_path in zip(base64_images, batch_images):  
            message_content.append({"type": "text", "text": image_path})  
            message_content.append({  
                "type": "image_url",  
                "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},  
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
  
def get_frames_from_video(video_path, output_folder, max_frames=100):  
    # Initialize video capture and detect scenes using ContentDetector  
    video_capture = cv2.VideoCapture(video_path)  
    content_detector = HistogramDetector()  # Adjust threshold and min_scene_len as needed  
    content_list = detect(video_path, content_detector)  
    print("Number of scenes", len(content_list))  
  
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
