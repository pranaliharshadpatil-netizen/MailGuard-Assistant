# mail_processor.py
import imaplib
import email
from email.header import decode_header
import mailguard_db
import sys

def get_header(header_text):
    """Decodes email headers to a readable string."""
    if header_text is None:
        return ""
    decoded_parts = decode_header(header_text)
    header_str = ""
    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            header_str += part.decode(encoding or 'utf-8', errors='ignore')
        else:
            header_str += part
    return header_str

def process_emails(email_user: str, email_pass: str, imap_server: str):
    """Connects to the email server and processes unread emails based on rules."""
    user_data = mailguard_db.get_user_credentials(email_user)
    if not user_data:
        print(f"❌ No configuration found for user {email_user}.")
        return

    rules = mailguard_db.get_active_rules(user_data['id'])
    if not rules:
        print("ℹ️ No security rules found. Exiting.")
        return

    try:
        # Connect to the IMAP server
        mail = imaplib.IMAP4_SSL(imap_server)
        mail.login(email_user, email_pass)
        print("✅ Successfully logged into email server.")
    except imaplib.IMAP4.error as e:
        print(f"❌ IMAP Login Failed: {e}")
        print("Please check your email, app password, and IMAP server in the .env file.")
        sys.exit(1) # Exit because we can't proceed

    mail.select('inbox')
    
    # Search for all unseen emails
    status, messages = mail.search(None, 'UNSEEN')
    if status != 'OK':
        print("❌ Could not search for emails.")
        return

    email_ids = messages[0].split()
    print(f"📧 Found {len(email_ids)} new email(s) to scan.")

    for email_id in email_ids:
        status, msg_data = mail.fetch(email_id, '(RFC822)')
        if status != 'OK':
            continue

        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)

        # Decode email headers
        subject = get_header(msg['Subject'])
        sender = get_header(msg['From'])

        print(f"\nScanning: From='{sender}', Subject='{subject}'")

        # Apply rules
        for rule in rules:
            triggered = False
            if rule['rule_type'] == 'block_sender' and rule['value'].lower() in sender.lower():
                triggered = True
            elif rule['rule_type'] == 'flag_subject' and rule['value'].lower() in subject.lower():
                triggered = True
            
            if triggered:
                action = rule['action']
                details = f"Rule matched: Type='{rule['rule_type']}', Value='{rule['value']}'"
                print(f"  🚨 ACTION: Rule triggered! Performing action: {action.upper()}")

                # Perform the action
                if action == 'delete':
                    mail.store(email_id, '+FLAGS', '\\Deleted')
                elif action == 'move_to_spam':
                    mail.store(email_id, '+X-GM-LABELS', '\\Spam') # Gmail specific
                
                # Log the action
                mailguard_db.log_action(rule['id'], action, sender, subject, details)
                break # Stop processing other rules for this email
    
    # Permanently delete emails marked for deletion
    mail.expunge()
    mail.logout()
    print("\n✅ Email processing complete. Logged out.")