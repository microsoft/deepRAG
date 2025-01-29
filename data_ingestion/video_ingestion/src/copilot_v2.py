import streamlit as st  
from agent_v2 import extract_and_split_audio, load_file_content, get_frames_from_video,process_frames_and_audio  
import tempfile  
import os  
import re  
import base64  
from pathlib import Path  
from weasyprint import HTML  # Import WeasyPrint for HTML to PDF conversion  
  
# Helper functions for handling images and markdown  
def markdown_images(markdown):  
    images = re.findall(r'(!\[(?P<image_title>[^\]]+)\]\((?P<image_path>[^\)"\s]+)\s*([^\)]*)\))', markdown)  
    return images  
  
def img_to_bytes(img_path):  
    img_bytes = Path(img_path).read_bytes()  
    encoded = base64.b64encode(img_bytes).decode()  
    return encoded  
  
def img_to_html(img_path, img_alt):  
    img_format = img_path.split(".")[-1]  
    img_html = f'<img src="data:image/{img_format.lower()};base64,{img_to_bytes(img_path)}" alt="{img_alt}" style="max-width: 100%;">'  
    return img_html  
  
def markdown_insert_images(markdown):  
    images = markdown_images(markdown)  
    for image in images:  
        image_markdown = image[0]  
        image_alt = image[1]  
        image_path = image[2]  
        if os.path.exists(image_path):  
            markdown = markdown.replace(image_markdown, img_to_html(image_path, image_alt))  
    return markdown  
  
def save_report_as_pdf(report_html, output_path):  
    HTML(string=report_html).write_pdf(output_path)  
  
# Main function for Streamlit app  
def main():  
    st.title("Video Summary Generator with Audio Transcription")  
    st.write("Upload a video to generate a comprehensive summary using both frames and audio transcription.")  
  
    template_content = load_file_content("template.md")  
  
    uploaded_file = st.file_uploader("Upload Video", type=["mp4", "avi", "mov"])  
  
    if uploaded_file:  
        with tempfile.TemporaryDirectory() as temp_dir:  
            video_path = os.path.join(temp_dir, uploaded_file.name)  
            with open(video_path, "wb") as f:  
                f.write(uploaded_file.getbuffer())  
  
            st.text(f"Processing video: {uploaded_file.name}...")  
  
            # Extract frames and timestamps  
            frame_timestamps = get_frames_from_video(video_path, temp_dir)  
  
            # Transcribe and align audio with frames  
            transcription = extract_and_split_audio(video_path, frame_timestamps)  
  
            # Generate summary  
            report = process_frames_and_audio(frame_timestamps, transcription, template_content)  
            report_html = markdown_insert_images(report)  
  
            # Display the report  
            st.markdown(report_html, unsafe_allow_html=True)  
  
            # Save as PDF  
            pdf_output_path = os.path.join(temp_dir, "summary_report.pdf")  
            save_report_as_pdf(report_html, pdf_output_path)  
  
            with open(pdf_output_path, "rb") as pdf_file:  
                st.download_button(  
                    "Download Summary Report as PDF",  
                    data=pdf_file,  
                    file_name="summary_report.pdf",  
                    mime="application/pdf"  
                )   
  
if __name__ == "__main__":  
    main()  