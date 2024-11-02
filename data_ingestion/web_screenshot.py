from selenium import webdriver
from PIL import Image
from selenium.webdriver.chrome.options import Options
import time
import os

url = 'https://intercom.help/sixfold/en/articles/6023034-visibility-control-center-for-shippers-lsps'

# Initialize the WebDriver
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("--hide-scrollbars")
driver = webdriver.Chrome(options=chrome_options)

driver.get(url)
time.sleep(3)  # Pause to let the page load

# Get the total height of the page
total_height = driver.execute_script("return document.body.scrollHeight")
viewport_height = driver.execute_script("return window.innerHeight")
print(f"Total height: {total_height}, Viewport height: {viewport_height}")

# Create a directory to save screenshots
if not os.path.exists('screenshots'):
    os.makedirs('screenshots')

# Scroll and capture screenshots
scroll_position = 0
screenshot_index = 0

while scroll_position < total_height:
    driver.execute_script(f"window.scrollTo(0, {scroll_position})")
    time.sleep(1)  # Pause to let the page render
    screenshot_path = f'screenshots/screenshot_{screenshot_index}.png'
    driver.save_screenshot(screenshot_path)
    print(f"Saved screenshot: {screenshot_path}")
    scroll_position += viewport_height
    screenshot_index += 1

driver.close()

# Optionally, stitch screenshots together
def stitch_screenshots(screenshot_folder, output_path):
    screenshots = [Image.open(os.path.join(screenshot_folder, f)) for f in sorted(os.listdir(screenshot_folder))]
    total_width = screenshots[0].width
    total_height = sum(img.height for img in screenshots)
    
    stitched_image = Image.new('RGB', (total_width, total_height))
    y_offset = 0
    for img in screenshots:
        stitched_image.paste(img, (0, y_offset))
        y_offset += img.height
    
    stitched_image.save(output_path)
    print(f"Stitched image saved as: {output_path}")

stitch_screenshots('screenshots', 'stitched_screenshot.png')