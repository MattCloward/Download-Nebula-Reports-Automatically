import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define the downloads folder (change this if needed)
DOWNLOAD_FOLDER = os.path.expanduser("~/Downloads")

# Number of downloads after which the page should be refreshed
REFRESH_AFTER_DOWNLOADS = 5

# Setup the WebDriver with options
chrome_options = Options()
chrome_options.add_argument("--start-maximized")
chrome_options.add_experimental_option("prefs", {
    "download.default_directory": DOWNLOAD_FOLDER,
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
    "safebrowsing.enabled": True
})

driver = webdriver.Chrome(service=Service(), options=chrome_options)

LOGIN_URL = "https://portal.nebula.org/reporting/library"

# Set to track completed reports
completed_reports = set()
download_count = 0

# Initialize the list of files in the download folder
downloaded_files = set(os.listdir(DOWNLOAD_FOLDER))

# Replace any " .pdf" with ".pdf" in downloaded_files
downloaded_files = set(file_name.replace(" .pdf", ".pdf") for file_name in downloaded_files)

def is_file_downloaded(study_name):
    """Check if the file is already downloaded."""
    file_name = f"{study_name}.pdf"
    return file_name in downloaded_files

def wait_for_download_to_start(study_name, timeout=30):
    """Wait until a new file, or the downloaded file appears in the downloads directory."""
    file_name = f"{study_name}.pdf"
    initial_files = downloaded_files.copy()
    end_time = time.time() + timeout
    while time.time() < end_time:
        current_files = set(os.listdir(DOWNLOAD_FOLDER))
        current_files = set(file_name.replace(" .pdf", ".pdf") for file_name in current_files)
        if current_files != initial_files or file_name in current_files:
            return True
        time.sleep(1)
    return False

def login_and_wait_for_reports():
    """Navigate to the login page and wait for the user to log in."""
    driver.get(LOGIN_URL)
    logging.info("Please log in manually. Enter your credentials and complete any two-factor authentication if required.")
    logging.info("Waiting for 'View Full Report' buttons to appear...")

    # Wait indefinitely for the "View Full Report" button to appear
    while True:
        try:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//button[contains(text(), 'View Full Report')]")))
            logging.info("Login and authentication complete!")
            break
        except:
            time.sleep(1)  # Check every second if the element is available

def process_reports():
    """Process each report by clicking the 'View Full Report' button and downloading the PDF."""
    global download_count
    while True:
        # Find all "View Full Report" buttons
        view_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'View Full Report')]")

        # Process each button if not already completed
        new_report_found = False
        for button in view_buttons:
            try:
                # Get the study name from the associated "title-link"
                study_name_element = button.find_element(By.XPATH, "./ancestor::div[@class='paper']//a[contains(@class, 'title-link')]")
                study_name = study_name_element.text.strip()

                # Check if the file is already downloaded
                if is_file_downloaded(study_name):
                    if study_name not in completed_reports:
                        completed_reports.add(study_name)
                        logging.info(f"{len(completed_reports)}. Already Downloaded: {study_name}")
                    continue

                completed_reports.add(study_name)
                new_report_found = True

                # Click on the "View Full Report" button
                button.click()

                # Wait for the popup to appear and locate the download buttons
                WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "share-button-download")))
                time.sleep(2)

                # Find the "DOWNLOAD AS PDF" button specifically
                download_buttons = driver.find_elements(By.CLASS_NAME, "share-button-download")
                button_found = False
                for download_button in download_buttons:
                    if "DOWNLOAD AS PDF" in download_button.text:
                        download_button.click()
                        if wait_for_download_to_start(study_name):
                            logging.info(f"{len(completed_reports)}. Downloaded: {study_name}")
                            download_count += 1
                            # Update the list of downloaded files
                            downloaded_files = set(os.listdir(DOWNLOAD_FOLDER))
                            downloaded_files = set(file_name.replace(" .pdf", ".pdf") for file_name in downloaded_files)
                        else:
                            logging.warning(f"Download did not start for: {study_name}")
                        button_found = True
                        break

                if not button_found:
                    logging.warning("Download button not found")
                    continue

                # Find and click the "fas fa-arrow-left" button to close the popup
                back_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CLASS_NAME, "fas.fa-arrow-left")))
                back_button.click()

                # Wait a moment before moving to the next button
                time.sleep(1)

                # Refresh the page every `REFRESH_AFTER_DOWNLOADS` new downloads
                if download_count >= REFRESH_AFTER_DOWNLOADS:
                    logging.info("Refreshing the page...")
                    driver.refresh()
                    time.sleep(5)  # Wait for the page to reload
                    download_count = 0
                    break  # Exit the loop to re-locate elements after refresh

            except Exception as e:
                logging.error(f"An error occurred: {e}")
                continue

        # Scroll to the bottom of the page to load new reports
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)  # Wait for new reports to load

        # Check if there are new reports loaded
        new_view_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'View Full Report')]")
        if len(new_view_buttons) == len(view_buttons):
            # If no new reports are loaded, exit the loop
            break

try:
    login_and_wait_for_reports()
    process_reports()

finally:
    # Close the browser
    driver.quit()
    logging.info("Script completed.")
