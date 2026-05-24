# main.py
import time
import schedule
import config
import security
import mailguard_db
import mail_processor

def job():
    """The main job to be run on a schedule."""
    print(f"\n--- Mail Guard starting run at {time.ctime()} ---")
    
    # 1. Get user credentials from DB
    user_data = mailguard_db.get_user_credentials(config.USER_EMAIL)
    if not user_data:
        print("❌ User not found in database. Please run database_setup.py first.")
        return

    try:
        # 2. Securely decrypt the password for this session ONLY
        decrypted_password = security.decrypt_data(user_data['encrypted_password'])
        
        # 3. Process emails with the decrypted password
        mail_processor.process_emails(
            email_user=config.USER_EMAIL,
            email_pass=decrypted_password,
            imap_server=config.IMAP_SERVER
        )
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        # In a real app, you might want more specific error handling
    finally:
        # Ensure the decrypted password is cleared from memory (good practice)
        decrypted_password = None
    
    print("--- Run finished. Waiting for next scheduled run... ---")


if __name__ == "__main__":
    print("🚀 Mail Guard Virtual Assistant is starting...")
    print("First run will start immediately.")
    
    # Run the job once immediately
    job()
    
    # Schedule the job to run every 10 minutes
    schedule.every(10).minutes.do(job)
    
    print("🕒 Assistant is now running in the background. It will check emails every 10 minutes.")
    print("Press Ctrl+C to stop the assistant.")

    while True:
        schedule.run_pending()
        time.sleep(1)