import os
import tkinter as tk
import customtkinter as ctk
from fuzzywuzzy import process
import threading
import json
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

file_path = ""

def create_user_data_directory():
    """Create the User Data directory if it does not exist."""
    user_data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'User Data')
    if not os.path.exists(user_data_dir):
        os.makedirs(user_data_dir)

def wait_for_login(driver, wait):
    login_button_selector = By.ID, 'btnLogin'
    target_url = 'https://app.ezlynx.com/applicantportal/Commissions/DirectBill/AddStatement'

    while True:
        current_url = driver.current_url
        if current_url == target_url:
            print('Target URL reached. Refreshing the page twice.')
            driver.refresh()
            break

        try:
            # Check if login button is present
            wait.until(EC.presence_of_element_located(login_button_selector))
            print('Login button found. Please log in.')
            time.sleep(5)
        except Exception:
            print('Login button not found or another issue.')
            time.sleep(5)

def read_combined_json_file(file_path):
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except Exception as e:
        print(f"Error reading JSON file {file_path}: {e}")
        return {"nameMappings": [], "skipList": []}

def write_combined_json_file(file_path, data):
    try:
        with open(file_path, 'w') as file:
            json.dump(data, file, indent=4)
    except Exception as e:
        print(f"Error writing JSON file {file_path}: {e}")

def apply_name_mappings(team_list, mappings):
    mapped_list = []
    for name in team_list:
        mapped_name = next((item['mapped'] for item in mappings if item['original'] == name), name)
        if mapped_name != name:
            print(f"Remapping '{name}' to '{mapped_name}'")
        mapped_list.append(mapped_name)
    return mapped_list

def select_closest_option(driver, dropdown_id, user_input):
    # Locate the dropdown
    select_element = driver.find_element(By.ID, dropdown_id)

    # Find all option elements within the dropdown
    options = select_element.find_elements(By.TAG_NAME, 'option')
    
    # Extract and filter option texts
    option_texts = [option.text.strip() for option in options if not option.text.strip().endswith("(private)")]

    # Find the closest match using fuzzy matching
    closest_match, score = process.extractOne(user_input, option_texts)

    # Print closest match and its score
    print(f"Closest match: '{closest_match}' with a score of {score}")

    # Select the closest match if the score is above a threshold (e.g., 80)
    if score >= 80:
        # Re-fetch the options to get the full list again
        options = select_element.find_elements(By.TAG_NAME, 'option')
        # Find the exact option that matches the closest match
        for option in options:
            if option.text.strip() == closest_match:
                option.click()
                print(f"Selected option: {closest_match}")
                return
        print(f"Option '{closest_match}' not found in the dropdown.")
    else:
        print(f"No suitable match found for '{user_input}'.")

def show_custom_message(title, message, icon=None):
    global app  # Ensure app is accessible here
    if app is None:
        print("Error: Main app widget is not initialized.")
        return
    
    # Create a new top-level window for the message
    message_window = ctk.CTkToplevel(app)
    message_window.title(title)
    
    # Make the message window always on top and ensure it is centered
    message_window.attributes('-topmost', True)
    message_window.transient(app)
    
    # Update the prompt window to ensure it is fully created
    message_window.update_idletasks()
    
    # Get parent window's geometry
    parent_x = app.winfo_rootx()
    parent_y = app.winfo_rooty()
    parent_width = app.winfo_width()
    parent_height = app.winfo_height()
    
    # Define prompt window size
    prompt_width = 300
    prompt_height = 150
    
    # Calculate position to center the prompt window
    prompt_x = parent_x + (parent_width - prompt_width) // 2
    prompt_y = parent_y + (parent_height - prompt_height) // 2
    
    # Set geometry for the prompt window
    message_window.geometry(f"{prompt_width}x{prompt_height}+{prompt_x}+{prompt_y}")
    
    # Add content to the message window
    message_label = ctk.CTkLabel(message_window, text=message, padx=10, pady=10)
    message_label.pack(pady=(10, 5))
    
    close_button = ctk.CTkButton(message_window, text="OK", command=message_window.destroy)
    close_button.pack(pady=(0, 10))
    
    # Ensure the message window updates and stays on top
    message_window.update_idletasks()
    message_window.lift()  # Bring the window to the front


def start_script():
    # Disable UI elements
    disable_main_window_widgets()

    create_user_data_directory()

    # Get the content from text areas
    names = names_text_area.get("1.0", tk.END).strip().split('\n')
    amounts = amounts_text_area.get("1.0", tk.END).strip().split('\n')

    if len(names) != len(amounts):
        show_custom_message("Error", "Names and amounts must have the same number of lines.")
        enable_main_window_widgets()
        return

    statement_number = statement_number_entry.get()
    comment = comment_entry.get()
    desired_carrier = carrier_name_entry.get().strip()

    combined_file_path = os.path.join(user_data_dir, 'combinedData.json')

    data = read_combined_json_file(combined_file_path)
    name_mappings = data.get("nameMappings", [])
    skip_list = data.get("skipList", [])

    team_list = apply_name_mappings(names, name_mappings)
    amount_list = [float(amount) for amount in amounts]

    filtered_team_list = []
    filtered_amount_list = []
    for name, amount in zip(team_list, amount_list):
        if name not in skip_list:
            filtered_team_list.append(name)
            filtered_amount_list.append(amount)
        else:
            print(f"Removed: Name '{name}', Amount '{amount}'")

    if len(filtered_team_list) != len(filtered_amount_list):
        print("Error: TeamList and AmountList must have the same length.")
        enable_main_window_widgets()
        return

    script_dir = os.path.dirname(os.path.abspath(__file__))
    chrome_driver_dir = os.path.join(script_dir, 'chromedriver-win64')
    chrome_driver_path = os.path.join(chrome_driver_dir, 'chromedriver.exe')
    user_data_dir = os.path.join(script_dir, 'User Data')

    chrome_options = Options()
    chrome_options.add_argument(f"user-data-dir={user_data_dir}")
    chrome_options.add_argument('profile-directory=Default')
    chrome_options.add_argument("--window-size=1024,768")

    service = Service(chrome_driver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    wait = WebDriverWait(driver, 10)

    def run_script():
        try:
            driver.get("https://app.ezlynx.com/applicantportal/Commissions/DirectBill/AddStatement")
            wait_for_login(driver, wait)
            driver.get('https://app.ezlynx.com/applicantportal/Commissions/DirectBill/AddStatement')
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'CarrierID')))
            time.sleep(3)

            select_closest_option(driver, 'CarrierID', desired_carrier)

            # Fill out form fields
            statement_number_input = driver.find_element(By.ID, 'StatementNumber')
            statement_number_input.send_keys(statement_number)

            statement_date_input = driver.find_element(By.ID, 'StatementDate')
            formatted_date = datetime.now().strftime('%m/%d/%Y')
            statement_date_input.send_keys(formatted_date)

            today_btn = driver.find_element(By.CLASS_NAME, "ui-datepicker-current")
            today_btn.click()

            premium_input = driver.find_element(By.ID, 'Premium')
            premium_input.send_keys('0')

            commission_input = driver.find_element(By.ID, 'Commission')
            commission_input.send_keys('0')

            comment_textarea = driver.find_element(By.ID, 'Comment')
            comment_textarea.send_keys(comment)

            add_btn = driver.find_element(By.CSS_SELECTOR, "#AddStatementBtn")
            add_btn.click()

            time.sleep(7)

            # Search and select
            applicant_input = driver.find_element(By.CSS_SELECTOR, "#policySearchTerm")
            applicant_input.send_keys("Gold Service Fee")
            time.sleep(2)
            applicant_input.send_keys(Keys.ARROW_DOWN)
            time.sleep(2)
            applicant_input.send_keys(Keys.ENTER)

            add_team_btn = driver.find_element(By.CSS_SELECTOR, "#CommissionInfo > div:nth-child(2) > fieldset > div > div:nth-child(1) > h4 > button")
            for _ in range(len(filtered_team_list)):
                add_team_btn.click()

            time.sleep(2)

            # Select elements and fill in amounts
            select_elements = driver.find_elements(By.CSS_SELECTOR, "#serviceTeamTable > tbody > tr:nth-child(n) > td:nth-child(1) > div > select")
            if len(filtered_team_list) > len(select_elements):
                print("Warning: There are more names in TeamList than select elements.")

            for i in range(min(len(filtered_team_list), len(select_elements))):
                name_to_check = filtered_team_list[i]
                select = select_elements[i]
                options = select.find_elements(By.TAG_NAME, 'option')
                option_texts = [option.text.replace(" (Producer)", "").strip() for option in options]

                if name_to_check in option_texts:
                    options[option_texts.index(name_to_check)].click()
                else:
                    log_message = f"Name '{name_to_check}' not found in select element {i + 1}. Skipping.\n"
                    print(log_message)

            amount_elements = driver.find_elements(By.CSS_SELECTOR, "#serviceTeamTable > tbody > tr:nth-child(n) > td.input-append > input")
            for i in range(min(len(filtered_amount_list), len(amount_elements))):
                amount_input = amount_elements[i]
                amount_value = filtered_amount_list[i]
                amount_input.clear()
                amount_input.send_keys(amount_value)

            # Select transaction type
            select_trans_type = driver.find_element(By.CSS_SELECTOR, "select[name='TransactionType']")
            transaction_option = select_trans_type.find_element(By.CSS_SELECTOR, "option[value='PMT']")
            transaction_option.click()

            date_now_input = driver.find_element(By.ID, "TransactionDate")
            date_now_input.click()
            date_now_btn = driver.find_element(By.CLASS_NAME, "ui-datepicker-current")
            date_now_btn.click()

            prem_input = driver.find_element(By.ID, 'Premium')
            comm_input = driver.find_element(By.NAME, 'CommissionAmount')

            prem_input.clear()
            prem_input.send_keys('0')

            comm_input.clear()
            comm_input.send_keys('0')

            # Inject event listener (if applicable)
            add_button = driver.find_element(By.CSS_SELECTOR, 'button.btn.btn-primary.ng-binding')
            WebDriverWait(driver, 10).until(EC.visibility_of(add_button))
            driver.execute_script("""
                const addButton = document.querySelector('button.btn.btn-primary.ng-binding');
                if (addButton) {
                    addButton.addEventListener('click', () => {
                        console.log('Add button clicked by user! Quitting WebDriver...');
                        window.seleniumQuitTriggered = true;
                    });
                }
            """)

            while not driver.execute_script("return window.seleniumQuitTriggered"):
                time.sleep(1)

            print("Driver is quitting...")
            time.sleep(1)

        finally:
            driver.quit()
            enable_main_window_widgets()

    script_thread = threading.Thread(target=run_script)
    script_thread.start()

def open_settings():
    # Disable all relevant widgets in the main window
    disable_main_window_widgets()

    # Create the settings window
    settings_window = ctk.CTkToplevel(app)
    settings_window.title("Settings")

    # Make the settings window always on top and center it relative to the main window
    settings_window.attributes('-topmost', True)
    settings_window.transient(app)  # Keeps the settings window on top of the main window

    main_window_x = app.winfo_rootx()
    main_window_y = app.winfo_rooty()
    main_window_width = app.winfo_width()
    main_window_height = app.winfo_height()

    settings_window_width = 400
    settings_window_height = 500

    settings_window_x = main_window_x + (main_window_width - settings_window_width) // 2
    settings_window_y = main_window_y + (main_window_height - settings_window_height) // 2

    settings_window.geometry(f"{settings_window_width}x{settings_window_height}+{settings_window_x}+{settings_window_y}")

    # Variable to track if settings have been saved
    settings_saved = [False]

    def center_prompt(prompt, parent_window):
        # Wait for the prompt to be fully created before calculating geometry
        prompt.update_idletasks()  # Ensure all pending events are processed
        parent_x = parent_window.winfo_rootx()
        parent_y = parent_window.winfo_rooty()
        parent_width = parent_window.winfo_width()
        parent_height = parent_window.winfo_height()

        prompt_width = 450
        prompt_height = 125

        prompt_x = parent_x + (parent_width - prompt_width) // 2
        prompt_y = parent_y + (parent_height - prompt_height) // 2

        prompt.geometry(f"{prompt_width}x{prompt_height}+{prompt_x}+{prompt_y}")

    def save_settings():
        mappings = []
        for mapping in mappings_text.get("1.0", tk.END).strip().split('\n'):
            parts = mapping.split(' -> ')
            if len(parts) == 2:
                original, mapped = parts
                mappings.append({"original": original.strip(), "mapped": mapped.strip()})

        skip_names = skip_names_text.get("1.0", tk.END).strip().split('\n')

        data = {
            "nameMappings": mappings,
            "skipList": skip_names
        }
        write_combined_json_file('combinedData.json', data)
        show_custom_message("Info", "Settings Saved!")
        settings_saved[0] = True
        settings_window.destroy()
        enable_main_window_widgets()

    def on_closing():
      if not settings_saved[0]:
          prompt = ctk.CTkToplevel(settings_window)
          prompt.title("Unsaved Changes")
          prompt.attributes('-topmost', True)
          prompt.transient(settings_window)
          message = ctk.CTkLabel(prompt, text="You have unsaved changes. Are you sure you want to exit without saving?", padx=10, pady=10)
          message.pack()
          button_frame = ctk.CTkFrame(prompt)
          button_frame.pack(pady=(0, 10))
          def confirm_exit():
              if settings_window:
                  settings_window.destroy()
              if prompt:
                  prompt.destroy()
              enable_main_window_widgets()
          def cancel_exit():
              if prompt:
                  prompt.destroy()
          yes_button = ctk.CTkButton(button_frame, text="Yes", command=confirm_exit)
          yes_button.pack(side=tk.LEFT, padx=5, pady=5)
          no_button = ctk.CTkButton(button_frame, text="No", command=cancel_exit)
          no_button.pack(side=tk.RIGHT, padx=5, pady=5)
          prompt.update_idletasks()
          center_prompt(prompt, settings_window)
      else:
          if settings_window:
              settings_window.destroy()
          enable_main_window_widgets()

    # Bind the close event to `on_closing`
    settings_window.protocol("WM_DELETE_WINDOW", on_closing)

    # Create widgets for the settings window
    current_data = read_combined_json_file('combinedData.json')
    mappings_text = tk.Text(settings_window, height=10, width=40)
    for item in current_data.get("nameMappings", []):
        mappings_text.insert(tk.END, f"{item['original']} -> {item['mapped']}\n")

    skip_names_text = tk.Text(settings_window, height=10, width=40)
    skip_names_text.insert(tk.END, '\n'.join(current_data.get("skipList", [])))

    name_mappings_label = ctk.CTkLabel(settings_window, text="Name Mappings\n(Format: Original Name -> Mapped Name)")
    name_mappings_label.pack(padx=10, pady=(10, 5))
    mappings_text.pack(padx=10, pady=(0, 10))

    skip_list_label = ctk.CTkLabel(settings_window, text="Skip List\n(One name per line)")
    skip_list_label.pack(padx=10, pady=(10, 5))
    skip_names_text.pack(padx=10, pady=(0, 10))

    save_button = ctk.CTkButton(settings_window, text="Save", command=save_settings)
    save_button.pack(pady=10)

def disable_main_window_widgets():
    widgets = [statement_number_entry, comment_entry, names_text_area, amounts_text_area, start_button, settings_button, carrier_name_entry]
    for widget in widgets:
        if widget is not None:
            widget.configure(state='disabled')

def enable_main_window_widgets():
    widgets = [statement_number_entry, comment_entry, names_text_area, amounts_text_area, start_button, settings_button, carrier_name_entry]
    for widget in widgets:
        if widget is not None:
            widget.configure(state='normal')

app = ctk.CTk()
app.title("Manual Import")
app.geometry("600x500")

ctk.set_appearance_mode("dark")

app.grid_columnconfigure(0, weight=1)
app.grid_columnconfigure(1, weight=1)
app.grid_rowconfigure(0, weight=0)
app.grid_rowconfigure(1, weight=0)
app.grid_rowconfigure(2, weight=0)
app.grid_rowconfigure(3, weight=0)
app.grid_rowconfigure(4, weight=0)
app.grid_rowconfigure(5, weight=1)
app.grid_rowconfigure(6, weight=0)

carrier_name_label = ctk.CTkLabel(app, text="Carrier Name")
carrier_name_label.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="ew")

carrier_name_entry = ctk.CTkEntry(app)
carrier_name_entry.grid(row=1, column=0, padx=30, pady=(0, 10), sticky="ew")
carrier_name_entry.insert(0, "Fortegra Specialty")

statement_number_label = ctk.CTkLabel(app, text="Statement Number")
statement_number_label.grid(row=2, column=0, padx=10, pady=(10, 0), sticky="ew")

statement_number_entry = ctk.CTkEntry(app)
statement_number_entry.grid(row=3, column=0, padx=30, pady=(0, 10), sticky="ew")
statement_number_entry.insert(0, "MVR083124")

comment_label = ctk.CTkLabel(app, text="Comment")
comment_label.grid(row=2, column=1, padx=10, pady=(10, 0), sticky="ew")

comment_entry = ctk.CTkEntry(app)
comment_entry.grid(row=3, column=1, padx=30, pady=(0, 10), sticky="ew")
comment_entry.insert(0, "Gold Fee Apr24 04156722")

names_label = ctk.CTkLabel(app, text="Names")
names_label.grid(row=4, column=0, padx=10, pady=(10, 0), sticky="n")

names_text_area = ctk.CTkTextbox(app, height=15, width=40, wrap="word")
names_text_area.grid(row=5, column=0, padx=30, pady=(0, 10), sticky="nsew")

amounts_label = ctk.CTkLabel(app, text="Amounts")
amounts_label.grid(row=4, column=1, padx=10, pady=(10, 0), sticky="n")

amounts_text_area = ctk.CTkTextbox(app, height=15, width=40, wrap="word")
amounts_text_area.grid(row=5, column=1, padx=30, pady=(0, 10), sticky="nsew")

start_button = ctk.CTkButton(app, text="Start", command=start_script)
start_button.grid(row=6, column=0, padx=10, pady=10, sticky="ew")

settings_button = ctk.CTkButton(app, text="Settings", command=open_settings)
settings_button.grid(row=6, column=1, padx=10, pady=10, sticky="ew")

app.mainloop()
