import requests
import time

# Replace with the actual URL of your FastAPI application
fastapi_url = "http://localhost:8000/healthz"

# Define a maximum number of retries and delay between retries
max_retries = 30  # Adjust as needed
retry_delay = 1  # Seconds

# Loop to make a GET request to /healthz and wait for FastAPI to start
for _ in range(max_retries):
    try:
        response = requests.get(fastapi_url)

        # If the response status code is 200, FastAPI is running
        if response.status_code == 200:
            break

    except Exception as e:
        pass

    # Wait for a while before the next retry
    time.sleep(retry_delay)
else:
    print("FastAPI did not start within the expected time.")