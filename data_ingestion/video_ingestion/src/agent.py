import os  
import cv2  
import json  
import numpy as np  
from PIL import Image  
from concurrent.futures import ThreadPoolExecutor,as_completed
from dotenv import load_dotenv  
import azure.cognitiveservices.speech as speechsdk  
  
import os  
import cv2  
from scenedetect import detect  
from scenedetect.detectors import ContentDetector, HistogramDetector, AdaptiveDetector
from moviepy import AudioFileClip, VideoFileClip  
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type  
import os  
from azure.core.exceptions import ServiceRequestError, HttpResponseError  
import openai    
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
@retry(  
    stop=stop_after_attempt(5),  # Retry up to 5 times  
    wait=wait_fixed(60),         # Wait 60 seconds between retries  
    retry=retry_if_exception_type(Exception)  # Retry on any exception  
)  
def transcribe_audio(audio_path):  
    """  
    Transcribes a single audio file using Azure Speech Service with retry logic.  
  
    Args:  
        audio_path (str): Path to the audio file.  
  
    Returns:  
        str: Transcription text.  
  
    Raises:  
        Exception: If transcription fails after the maximum number of retries.  
    """  
    # Get Azure Speech Service configuration from environment variables  
    speech_key = os.getenv("AZURE_SPEECH_KEY")  
    speech_region = os.getenv("AZURE_SPEECH_REGION")  
      
    if not speech_key or not speech_region:  
        raise ValueError("Azure Speech Service key and region must be set in the environment variables.")  
  
    # Create a SpeechConfig and AudioConfig  
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)  
    audio_config = speechsdk.audio.AudioConfig(filename=audio_path)  
  
    # Create a speech recognizer  
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)  
  
    try:  
        # Perform the transcription  
        print(f"Transcribing audio file: {audio_path}")  
        result = speech_recognizer.recognize_once()  
  
        # Check result status  
        if result.reason == speechsdk.ResultReason.RecognizedSpeech:  
            print(f"Transcription succeeded for {audio_path}: {result.text}")  
            return result.text  
        elif result.reason == speechsdk.ResultReason.NoMatch:  
            print(f"No speech could be recognized in {audio_path}.")  
            return ""  
        elif result.reason == speechsdk.ResultReason.Canceled:  
            cancellation_details = result.cancellation_details  
            print(f"Transcription canceled for {audio_path}: {cancellation_details.reason}")  
            if cancellation_details.reason == speechsdk.CancellationReason.Error:  
                print(f"Error details: {cancellation_details.error_details}")  
            raise Exception(f"Transcription canceled for {audio_path}: {cancellation_details.reason}")  
    except Exception as e:  
        print(f"Unexpected error transcribing {audio_path}: {e}")  
        raise  

# Whisper Transcription with Chunk Splitting  
# Retry decorator for transcribing audio  
# @retry(  
#     stop=stop_after_attempt(5),  # Retry up to 5 times  
#     wait=wait_fixed(60),  # Wait 60 seconds between retries  
#     retry=retry_if_exception_type(openai.RateLimitError)  # Retry only on RateLimitError  
# )  
# def transcribe_audio(audio_path):  
#     """  
#     Transcribes a single audio file using Azure OpenAI Whisper with retry logic for rate limiting.  
  
#     Args:  
#         audio_path (str): Path to the audio file.  
  
#     Returns:  
#         str: Transcription text.  
  
#     Raises:  
#         Exception: If transcription fails after the maximum number of retries.  
#     """  
#     deployment_id = os.getenv("WHISPER_DEPLOYMENT_ID")  
      
#     try:  
#         with open(audio_path, "rb") as audio_file:  
#             # Call the Azure OpenAI Whisper API  
#             result = client.audio.transcriptions.create(  
#                 file=audio_file,  
#                 model=deployment_id  
#             )  
#         print(f"Transcribed audio file successfully: {audio_path}")  
#         print(result.text)  
#         return result.text  # Return the transcription result if successful  
  
#     except openai.RateLimitError as e:  
#         # Log the RateLimitError and let tenacity handle retries  
#         print(f"Rate limit reached for {audio_path}. Retrying...")  
#         raise  
  
#     except (ServiceRequestError, HttpResponseError) as e:  
#         # Handle retryable errors (e.g., network issues or server errors)  
#         print(f"Service error while transcribing {audio_path}: {e}")  
#         raise  
  
#     except Exception as e:  
#         # Handle non-retryable errors or unexpected exceptions  
#         print(f"Unexpected error transcribing {audio_path}: {e}")  
#         raise    
# Extract audio and split based on frame timestamps  
def extract_and_split_audio(video_path, frame_batches):  
    """  
    Extracts audio for each batch, transcribes it, and aligns it with the video frames.  
  
    Args:  
        video_path (str): Path to the video file.  
        frame_batches (list): List of frame batches containing start and end times.  
  
    Returns:  
        list: List of transcriptions aligned with each batch in chronological order.  
    """  
    # Extract full audio from the video  
    audio_path = video_path.replace(".mp4", ".wav")  
    video_clip = VideoFileClip(video_path)  
    video_clip.audio.write_audiofile(audio_path)  
  
    # Load the full audio using pydub  
    audio = AudioSegment.from_file(audio_path)  
    os.remove(audio_path)  # Clean up temporary audio file  
  
    # Transcribe audio batch by batch  
    transcriptions = [None] * len(frame_batches)  # Placeholder list to maintain order  
    with ThreadPoolExecutor() as executor:  
        futures = {}  
        for idx, batch in enumerate(frame_batches):  
            start_time_ms = int(batch["start_time"] * 1000)  # Convert start time to milliseconds  
            end_time_ms = int(batch["end_time"] * 1000)  # Convert end time to milliseconds  
  
            # Extract the audio segment for this batch  
            audio_segment = audio[start_time_ms:end_time_ms]  
  
            # Save the audio segment as a temporary file  
            segment_path = f"{audio_path}_segment_{batch['start_time']:.2f}_{batch['end_time']:.2f}.wav"  
            audio_segment.export(segment_path, format="wav")  
  
            # Submit the transcription task and map it to the batch index  
            futures[executor.submit(transcribe_audio, segment_path)] = (segment_path, idx)  
  
        for future in as_completed(futures):  
            segment_path, idx = futures[future]  
            try:  
                # Store the transcription result in the correct order  
                transcriptions[idx] = future.result()  
            finally:  
                # Clean up the temporary segment file  
                os.remove(segment_path)  
    print("transcriptions", transcriptions)
    return transcriptions  
def get_frames_from_video(video_path, output_folder, max_frames_per_scene=30, max_frames_per_batch=10, max_batch_duration=300):  
    """  
    Extracts frames based on scene detection and divides them into batches with continuous start/end times.  
  
    Args:  
        video_path (str): Path to the video file.  
        output_folder (str): Folder to save the extracted frames.  
        max_frames_per_scene (int): Maximum number of frames to extract per scene.  
        max_frames_per_batch (int): Maximum number of frames per batch.  
        max_batch_duration (int): Maximum duration (in seconds) for each batch.  
  
    Returns:  
        list: List of dictionaries containing batch details (frames, start_time, end_time).  
    """  
    # Initialize video capture and scene detector  
    video_capture = cv2.VideoCapture(video_path)  
    fps = video_capture.get(cv2.CAP_PROP_FPS)  # Frames per second  
    total_frames = int(video_capture.get(cv2.CAP_PROP_FRAME_COUNT))  # Total number of frames  
    duration = total_frames / fps  # Total duration of the video in seconds  
  
    # Detect scenes using HistogramDetector  
    content_detector = ContentDetector(threshold=22)  # You can use ContentDetector for more precise detection  
    scenes = detect(video_path, content_detector)  
    print(f"Number of scenes detected: {len(scenes)}")  
  
    frame_timestamps = []  # Stores batch information  
    current_batch = []  # Stores frames for the current batch  
    current_batch_start_time = 0  # Start time for the current batch  
    previous_batch_end_time = 0  # End time of the last batch for continuity  
  
    total_frames_extracted = 0  
  
    # Iterate over detected scenes  
    for scene_idx, scene in enumerate(scenes):  
        # Determine the number of frames to extract from this scene  
  
        # Extract frames from the current scene  
        frame_ids, frames = get_frames_from_scene(scene, video_capture, max_frames_per_scene)  
        print("total number of frames in scene: ", len(frame_ids))
  
        # Save extracted frames and group into batches  
        for frame_num, (frame_id, frame) in enumerate(zip(frame_ids, frames)):  
            # Calculate the timestamp for the frame  
            timestamp = get_frame_time(video_capture, frame_id)  
  
            # Save the frame as an image  
            frame_filename = f"scene_{scene_idx+1}_frame_{frame_id}_{frame_num+1}.jpg"  
            frame_path = os.path.join(output_folder, frame_filename)  
            save_frame_image(frame, frame_path)  
  
            # Add frame to the current batch  
            current_batch.append({"path": frame_path, "timestamp": timestamp})  
  
            # Set the start time for the current batch (if it's the first frame in the batch)  
            if len(current_batch) == 1:  
                current_batch_start_time = max(previous_batch_end_time, timestamp)  
  
            # Update end time for the current batch  
            current_batch_end_time = timestamp  
  
            # Check if the batch exceeds constraints (max frames or max duration)  
            if len(current_batch) >= max_frames_per_batch or (current_batch_end_time - current_batch_start_time) >= max_batch_duration:  
                # Save the batch  
                frame_timestamps.append({  
                    "frames": current_batch,  
                    "start_time": current_batch_start_time,  
                    "end_time": current_batch_end_time  
                })  
                # Reset the batch  
                current_batch = []  
                previous_batch_end_time = current_batch_end_time  # Update for continuity  
  
            total_frames_extracted += 1  
  
  
    # Add any remaining frames as the last batch  
    if current_batch:  
        frame_timestamps.append({  
            "frames": current_batch,  
            "start_time": current_batch_start_time,  
            "end_time": current_batch_end_time  
        })  
  
    video_capture.release()  
    print("number of batches: ", len(frame_timestamps))
    print("total frames extracted: ", total_frames_extracted)
    return frame_timestamps  

# Process frames and audio  
def process_frames_and_audio(frame_batches, transcriptions):  
    """  
    Processes frames and audio transcription batch by batch to generate an accurate and detailed textual description of the video.  
  
    Args:  
        frame_batches (list): List of frame batches with frame details and timestamps.  
        transcriptions (list): List of audio transcriptions corresponding to each batch.  
  
    Returns:  
        str: Final, comprehensive textual description of the video.  
    """  
    video_transcription = ""  
  
    # Prompt part for incremental updates  
    prompt_part1 = """  
    You are an AI assistant tasked with analyzing and combining visual and audio content from a video to create a comprehensive and detailed textual description.   
    Your task involves processing the video in batches, where each batch contains:  
      - Visual details derived from frames (images) in the batch.  
      - Corresponding audio transcription for the same batch.  
      
    This is an incremental process. Each time you receive a new batch, you must:  
      1. Incorporate the new details from the current batch.  
      2. Update and expand the ongoing transcription to reflect the latest information.  
      3. Ensure the transcription is cohesive, accurate, and detailed, combining both audio and visual elements.  
  
    Below is the transcription of the video so far (if this is the first batch, it will be blank):  
    ### Past Transcription:  
    {video_transcription}  
  
    Here is the new information for the current batch:  
    ### Audio Transcript:  
    {audio_text}  
  
    ### Attached Images:  
    (The image file paths are listed below. Images are also attached in base64 format.)  
    """  
  
    prompt_part2 = """  
    Using the new batch of audio and visual data, update the transcription. Ensure the updated transcription:  
      - Includes newly observed details from the audio transcript and visual frames.  
      - Maintains a cohesive, flowing narrative when combined with the past transcription.  
      - Reflects any changes, transitions, or new elements observed in the video.  
  
    Provide the updated transcription in raw markdown format under the following section:  
    ## Updated Transcription  
    """  
  
    # Process each batch  
    for batch, transcription in zip(frame_batches, transcriptions):  
        # Extract image paths for the current batch  
        batch_images = [frame["path"] for frame in batch["frames"]]  
        batch_audio_text = transcription  
  
        # Prepare the GPT input for the current batch  
        message_content = [  
            {  
                "type": "text",  
                "text": prompt_part1.format(  
                    video_transcription=video_transcription,  
                    audio_text=batch_audio_text,  
                ),  
            }  
        ]  
  
        # Encode images in base64 and attach them to the input  
        base64_images = [encode_image(image_path) for image_path in batch_images]  
        for base64_image, image_path in zip(base64_images, batch_images):  
            message_content.append({"type": "text", "text": image_path})  
            message_content.append(  
                {  
                    "type": "image_url",  
                    "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},  
                }  
            )  
  
        # Add the instruction for updating the transcription  
        message_content.append({"type": "text", "text": prompt_part2})  
  
        # Call GPT for response  
        raw_response = get_gpt_response(message_content)  
  
        # Extract and update the transcription  
        description_marker = "## Updated Transcription"  
        if description_marker in raw_response:  
            start_index = raw_response.index(description_marker) + len(description_marker)  
            video_transcription = raw_response[start_index:].strip()  
        else:  
            video_transcription = raw_response.strip()  
  
    return video_transcription     
def get_frames_from_scene(scene, video_capture, n=-1):  
    """  
    Extracts a specific number of frames from a scene, or all frames if n=-1.  
    Handles cases where a scene has fewer frames than n.  
  
    Args:  
        scene (tuple): Start and end frames of the scene.  
        video_capture (cv2.VideoCapture): Video capture object.  
        n (int): Number of frames to extract (use -1 to extract all frames).  
  
    Returns:  
        tuple: List of frame IDs and corresponding frames.  
    """  
    start_frame = scene[0].frame_num  
    end_frame = scene[1].frame_num  
    total_frames_in_scene = end_frame - start_frame + 1  
  
    # Determine the frame IDs to extract  
    if n == -1 or total_frames_in_scene <= n:  
        # Extract all frames if n=-1 or the scene has fewer frames than n  
        frame_ids = list(range(start_frame, end_frame + 1))  
    else:  
        # Extract n frames evenly distributed across the scene  
        frame_step = max(1, total_frames_in_scene // n)  
        frame_ids = [start_frame + i * frame_step for i in range(n)]  
  
    frames = []  
    for frame_id in frame_ids:  
        # Set the video capture to the specific frame  
        video_capture.set(cv2.CAP_PROP_POS_FRAMES, frame_id)  
        success, frame = video_capture.read()  
        if success:  
            # Convert the frame to a PIL image and store it  
            frames.append(Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))  
  
    return frame_ids, frames    
def save_frame_image(frame, output_path):  
    frame.save(output_path)  
  
def get_frame_time(video_capture, frame_id):  
    fps = video_capture.get(cv2.CAP_PROP_FPS)  
    seconds = frame_id / fps  
    return seconds  
  
