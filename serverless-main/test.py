import os
import boto3
import json
import requests
from google.cloud import storage
from google.oauth2 import service_account
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import base64
import time
# Load environment variables from .env file
import uuid

def lambda_handler(event, context):
    try:
        # Extract message from SNS event
        message = event['Records'][0]['Sns']['Message']

        # Parse the SNS message
        message_lines = message.split('\n')
        submission_url = message_lines[0].split(': ')[1]
        user_email = message_lines[1].split(': ')[1]

        # Retrieve environment variables
        gcs_bucket_name = os.environ['GCS_BUCKET_NAME']
        print(gcs_bucket_name)
        gcs_service_account_key = os.environ['GCP_SERVICE_ACCOUNT_KEY']
        gcs_service_account_key = gcs_service_account_key.strip()
        print(gcs_service_account_key)

        # GitHub repository details (Modify as needed)
        release_endpoint = submission_url
        print(release_endpoint)

        # DynamoDB details
        dynamodb_table_name = os.environ['DYNAMODB_TABLE_NAME']

        # Download the file
        response = requests.get(submission_url)
        if response.status_code != 200:
            msg=send_email_via_mailgun(user_email, "Download Error", "Failed to download the file from the provided URL : incorrect URL.")
            time.sleep(25)
            status_after_waiting = check_email_status(user_email)

            # Check the status
            dynamodb = boto3.resource('dynamodb')
            print("i am running")
            table = dynamodb.Table(dynamodb_table_name)
            dynamodb_item = {'email': user_email, 'status': status_after_waiting}
            print("DynamoDB Item:", dynamodb_item)           
            # return {"message": "Failed to download the file."}

        # Check if the file is a zip
        file_content_type = response.headers.get('content-type')
        if file_content_type != 'application/zip' and not submission_url.endswith('.zip'):
            msg=send_email_via_mailgun(user_email, "Download Error", "The downloaded file is not a zip file.")
            time.sleep(25)
            status_after_waiting = check_email_status(user_email)

             # Log to DynamoDB
            dynamodb = boto3.resource('dynamodb')
            print("i am running")
            table = dynamodb.Table(dynamodb_table_name)
            dynamodb_item = {'email': user_email, 'status': status_after_waiting}
            print("DynamoDB Item:", dynamodb_item) 

        # Download the latest release from GitHub
        response = requests.get(release_endpoint)
        if response.status_code == 200:
            # Assuming the release is a zip file (Modify as needed)
            with open("/tmp/github_release.zip", "wb") as f:
                f.write(response.content)

            try:
                # Decode from base64
                gcs_service_account_info_json = base64.b64decode(gcs_service_account_key).decode('utf-8')
                # Load as JSON
                gcs_service_account_info = json.loads(gcs_service_account_info_json)
                print(gcs_service_account_info_json)
                print(gcs_service_account_info)
            except json.JSONDecodeError as e:
                print("Error decoding JSON:", e)
                print("Content of gcs_service_account_key:", repr(gcs_service_account_info))

            # Authenticate with GCS
            credentials = service_account.Credentials.from_service_account_info(gcs_service_account_info)
            storage_client = storage.Client(credentials=credentials)
            unique_object_name = f"{user_email}_{str(uuid.uuid4())}.zip"

            # Upload to GCS
            bucket = storage_client.bucket(gcs_bucket_name)
            blob = bucket.blob(unique_object_name)
            blob.upload_from_filename("/tmp/github_release.zip")

            # Send email via Mailgun
            email_status = send_email_via_mailgun(user_email, "Download Complete", "The latest release has been downloaded and uploaded to GCS.")
             # Wait for 15 seconds
            time.sleep(25)

            # Check the status
            status_after_waiting = check_email_status(user_email)
            # Log to DynamoDB
            dynamodb = boto3.resource('dynamodb')
            print("i am running")
            table = dynamodb.Table(dynamodb_table_name)
            dynamodb_item = {'email': user_email, 'status': status_after_waiting}
            print("DynamoDB Item:", dynamodb_item)

            try:
                table.put_item(Item=dynamodb_item)
                print("Item successfully added to DynamoDB")
            except Exception as e:
                print(f"Failed to put item in DynamoDB: {str(e)}")

            return {"message": "Process completed successfully"}
        else:
            return {"message": "Failed to download the release from GitHub"}
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return {"message": "Error occurred during execution."}
    

def send_email_via_mailgun(recipient, subject, body):
    # Retrieve Mailgun environment variables
    mailgun_api_key = os.environ['MAILGUN_API_KEY']
    mailgun_domain = os.environ['MAILGUN_DOMAIN']
    sender_email = os.environ['SENDER_EMAIL']

    # Mailgun API URL
    mailgun_url = f"https://api.mailgun.net/v3/{mailgun_domain}/messages"
    # Prepare the email data
    email_data = {
        "from": sender_email,
        "to": recipient,
        "subject": subject,
        "text": body
    }

    try:
        # Send the email
        response = requests.post(
            mailgun_url,
            auth=("api", mailgun_api_key),
            data=email_data
        )

        # Check if the request was successful
        response.raise_for_status()

        # Capture the response content
        response_content = response.text

        # Parse JSON if possible
        try:
            response_json = response.json()
            delivery_status = response_json.get("delivery-status", {})
            event_type = response_json.get("event", "")
            print(event_type)
            # Check for the event type in the response
            if event_type == 'accepted':
                return "Email accepted for delivery"
            elif event_type == 'delivered':
                return "Email delivered successfully"
            elif event_type == 'failed':
                return "Email delivery failed"
            else:
                return "Unknown email event"
        except json.JSONDecodeError:
            pass  # Ignore JSON decoding errors

        return "Email queued for delivery"
    except requests.exceptions.RequestException as e:
        return f"Failed to send email: {str(e)}"
    except Exception as e:
        return f"Failed to send email: {str(e)}"
    



def check_email_status(recipient):
    # Retrieve Mailgun environment variables
    mailgun_api_key = os.environ['MAILGUN_API_KEY']
    mailgun_domain = os.environ['MAILGUN_DOMAIN']
    dynamodb_table_name = os.environ['DYNAMODB_TABLE_NAME']

    # Get the latest message for the recipient
    messages_url = f"https://api.mailgun.net/v3/{mailgun_domain}/events"
    params = {'recipient': recipient}
    headers = {'Authorization': f'Basic {base64.b64encode(f"api:{mailgun_api_key}".encode()).decode()}'}

    max_attempts = 10  # Adjust the number of attempts based on your requirements
    for attempt in range(max_attempts):
        try:
            response = requests.get(messages_url, params=params, headers=headers)
            response.raise_for_status()
            response_json = response.json()

            # Check if there are any events
            if response_json['items']:
                latest_event = response_json['items'][0]
                event_type = latest_event.get('event', '')

                if event_type == 'accepted':
                    return "Email accepted for delivery"
                elif event_type == 'delivered':
                    return "Email delivered successfully"
                elif event_type == 'failed':
                    # Log the failure in DynamoDB
                    log_email_failure_in_dynamodb(recipient, latest_event)
                    return "Email delivery failed"
                else:
                    print(f"Attempt {attempt + 1}/{max_attempts}: Email event type is {event_type}. Waiting for 10 seconds...")
        except requests.exceptions.RequestException as e:
            return f"Failed to check email status: {str(e)}"
        except Exception as e:
            return f"Failed to check email status: {str(e)}"

        time.sleep(10)  # Wait for 10 seconds before checking again

    return "Max attempts reached. Email status not confirmed."

def log_email_failure_in_dynamodb(recipient, event_data):
    # DynamoDB details
    dynamodb_table_name = os.environ['DYNAMODB_TABLE_NAME']

    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(dynamodb_table_name)
        dynamodb_item = {'email': recipient, 'status': f"Email delivery failed. Event data: {json.dumps(event_data)}"}
        table.put_item(Item=dynamodb_item)
        print("Item successfully added to DynamoDB")
    except Exception as e:
        print(f"Failed to put item in DynamoDB: {str(e)}")
