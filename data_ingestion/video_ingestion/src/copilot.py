import streamlit as st  
from agent import process_images_from_folder, load_file_content, get_frames_from_video  
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
    # Update the title and description for a generic summary generator  
    st.title("Video and Image Summary Generator")  
    st.write(  
        "Upload a video or a set of images, and this app will generate a comprehensive summary "  
        "of the content. The summary will be created in batches for large inputs, and you can download it as a PDF."  
    )  
  
    # Load the generic template for generating summaries  
    template_content = load_file_content("template.md")  # Ensure template.md is generic  
  
    # Allow users to upload files  
    uploaded_files = st.file_uploader(  
        "Upload Images or Video",   
        accept_multiple_files=True,   
        type=["png", "jpg", "jpeg", "mp4", "avi", "mov"]  
    )  
  
    if uploaded_files:  
        with tempfile.TemporaryDirectory() as temp_dir:  
            image_file_paths = []  
  
            # Process each uploaded file  
            for uploaded_file in uploaded_files:  
                file_path = os.path.join(temp_dir, uploaded_file.name)  
                with open(file_path, "wb") as f:  
                    f.write(uploaded_file.getbuffer())  
  
                if uploaded_file.name.lower().endswith(('.mp4', '.avi', '.mov')):  # Process video files  
                    st.text(f"Processing video: {uploaded_file.name}...")  
                    frame_paths = get_frames_from_video(file_path, temp_dir)  
                    image_file_paths.extend(frame_paths)  
                else:  # Collect image files  
                    image_file_paths.append(file_path)  
  
            if image_file_paths:  
                st.text("Processing images...")  
                # Generate summary report using the updated function  
                report = process_images_from_folder(temp_dir, template_content)  
                report_html = markdown_insert_images(report)  
  
                # Display the report in the app  
                with st.container():  
                    st.markdown(report_html, unsafe_allow_html=True)  
  
                # Save the report as a PDF and provide a download option  
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