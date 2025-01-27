import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Last downloaded study to resume from (keep empty to start from the beginning)
last_downloaded_study = ""  # Set this to the last successfully downloaded study's name

resuming = bool(last_downloaded_study)  # Indicates whether the script is resuming

# Define the downloads folder (change this if needed)
download_folder = os.path.expanduser("~/Downloads")

# Setup the WebDriver (ensure you have the correct WebDriver for your browser)
driver = webdriver.Chrome()  # Replace with your driver if using a different browser
driver.maximize_window()

login_url = "https://portal.nebula.org/reporting/library"

# Set to track completed reports
completed_reports = set()

def wait_for_download_to_start(study_name, timeout=30):
    """
    Wait until a new file, or the downloaded file appears in the downloads directory
    """
    file_name = f"{study_name}.pdf"
    initial_files = set(os.listdir(download_folder))
    end_time = time.time() + timeout
    while time.time() < end_time:
        current_files = set(os.listdir(download_folder))
        if current_files != initial_files or file_name in current_files:
            return True
        time.sleep(1)
    return False

try:
    # Navigate to the login page
    driver.get(login_url)

    # Inform the user to log in manually
    print("Please log in manually. Enter your credentials and complete any two-factor authentication if required.")
    print("Waiting for 'View Full Report' buttons to appear...")

    # Wait indefinitely for the "View Full Report" button to appear
    while True:
        try:
            driver.find_element(By.XPATH, "//button[contains(text(), 'View Full Report')]")
            print("Login and authentication complete!")
            break
        except:
            time.sleep(1)  # Check every second if the element is available

    # Infinite scrolling and report processing
    while True:
        # Find all "View Full Report" buttons
        view_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'View Full Report')]")

        # Process each button if not already completed
        new_report_found = False
        for button in view_buttons:
            # Get the study name from the associated "title-link"
            study_name_element = button.find_element(By.XPATH, "./ancestor::div[@class='paper']//a[contains(@class, 'title-link')]")
            study_name = study_name_element.text.strip()

            if resuming:
                # Skip studies until we find the last downloaded one
                if study_name == last_downloaded_study:
                    resuming = False  # Found the last study; process subsequent studies
                completed_reports.add(study_name)   
                new_report_found = True
                continue  # Skip this study

            # Skip already completed reports
            if study_name in completed_reports:
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
            buttonFound = False
            for download_button in download_buttons:
                if "DOWNLOAD AS PDF" in download_button.text:
                    download_button.click()
                    if wait_for_download_to_start(study_name):
                        print(f"{len(completed_reports)}. Downloaded: {study_name}")
                        last_downloaded_study = study_name  # Update the last downloaded study
                    else:
                        print(f"Download did not start for: {study_name}")
                    buttonFound = True
                    break
            
            if not buttonFound:
                print("Download button not found")
                exit()
    
            # Find and click the "fas fa-arrow-left" button to close the popup
            back_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CLASS_NAME, "fas.fa-arrow-left")))
            back_button.click()
    
            # Wait a moment before moving to the next button
            time.sleep(1)

        # Scroll to the bottom of the page to load new reports
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        # Exit the loop if the last report has been downloaded
        if "Breast cancer (Michailidou, 2013)" in completed_reports:
            if "Breast cancer (Michailidou, 2013).pdf" in set(os.listdir(download_folder)):
                break

finally:
    # Close the browser
    driver.quit()
    print(f"Script completed. Last downloaded study: {last_downloaded_study}")
