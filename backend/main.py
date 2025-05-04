from firebase_functions import https_fn
from firebase_admin import initialize_app, messaging
import json
import os
from datetime import datetime, timedelta
from google.cloud import tasks_v2
import google.auth

# Initialize the Firebase app
initialize_app()

# Get project details
_, project_id = google.auth.default()
project_id = os.environ.get('PROJECT_ID', project_id)
location = os.environ.get('CLOUD_REGION', 'us-central1')
queue_name = os.environ.get('TASK_QUEUE', 'fcm-notification-queue')

# Create a Cloud Tasks client
tasks_client = tasks_v2.CloudTasksClient()

@https_fn.on_call()
def send_test_notification(req: https_fn.CallableRequest) -> dict:
    """
    Callable function to send a test FCM notification to a device
    
    Expected request data:
    {
        "token": "FCM device token",
        "title": "Notification title",
        "body": "Notification body"
    }
    """
    try:
        # Get data from request
        data = req.data
        
        if not data.get("token"):
            return {"success": False, "error": "Missing device token"}
        
        # Create message
        message = messaging.Message(
            notification=messaging.Notification(
                title=data.get("title", "Test Notification"),
                body=data.get("body", "This is a test notification from Firebase")
            ),
            token=data.get("token"),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        badge=1,
                        sound="default"
                    )
                )
            )
        )
        
        # Send message
        response = messaging.send(message)
        return {"success": True, "message_id": response}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@https_fn.on_request()
def schedule_notification(req: https_fn.Request) -> https_fn.Response:
    """
    HTTP function to schedule a notification to be sent after a delay
    
    Expected request body:
    {
        "token": "FCM device token",
        "title": "Notification title",
        "body": "Notification body",
        "delay": 60  # Delay in seconds
    }
    """
    if req.method != "POST":
        return https_fn.Response(
            json.dumps({"error": "Only POST requests are accepted"}),
            status=405,
            content_type="application/json"
        )
    
    try:
        # Get request body
        request_data = req.get_json()
        
        if not request_data.get("token"):
            return https_fn.Response(
                json.dumps({"error": "Missing device token"}),
                status=400,
                content_type="application/json"
            )
        
        # Get the token and notification data
        token = request_data.get("token")
        title = request_data.get("title", "Scheduled Notification")
        body = request_data.get("body", "This is a scheduled notification from Firebase")
        delay_seconds = int(request_data.get("delay", 60))
        
        # Calculate the scheduled time
        scheduled_time = datetime.utcnow() + timedelta(seconds=delay_seconds)
        
        # Construct the parent queue path
        parent = tasks_client.queue_path(project_id, location, queue_name)
        
        # Construct the target URL (this is the URL of the function that will send the notification)
        function_url = f"https://{location}-{project_id}.cloudfunctions.net/send_notification"
        
        # Create task payload
        payload = {
            "token": token,
            "notification": {
                "title": title,
                "body": body
            }
        }
        
        # Convert payload to bytes (required by Cloud Tasks)
        payload_bytes = json.dumps(payload).encode()
        
        # Create the task
        task = {
            "http_request": {
                "http_method": tasks_v2.HttpMethod.POST,
                "url": function_url,
                "headers": {"Content-Type": "application/json"},
                "body": payload_bytes
            },
            "schedule_time": scheduled_time.isoformat() + "Z"
        }
        
        # Create the task in Cloud Tasks
        response = tasks_client.create_task(parent=parent, task=task)
        
        # Return success
        return https_fn.Response(
            json.dumps({
                "success": True,
                "scheduled": True,
                "task_name": response.name,
                "scheduled_time": scheduled_time.isoformat(),
                "message": f"Notification scheduled for {scheduled_time.isoformat()}"
            }),
            status=200,
            content_type="application/json"
        )
        
    except Exception as e:
        return https_fn.Response(
            json.dumps({"error": str(e)}),
            status=500,
            content_type="application/json"
        )

@https_fn.on_request()
def send_notification(req: https_fn.Request) -> https_fn.Response:
    """
    HTTP function that actually sends the notification
    This is called by Cloud Tasks when a scheduled task is due
    """
    if req.method != "POST":
        return https_fn.Response("Only POST requests are accepted", status=405)
    
    try:
        # Get the request data
        request_data = req.get_json()
        
        # Extract notification data
        token = request_data.get("token")
        notification_data = request_data.get("notification", {})
        
        if not token:
            return https_fn.Response("Missing token", status=400)
        
        # Create and send the FCM message
        message = messaging.Message(
            notification=messaging.Notification(
                title=notification_data.get("title", "Notification"),
                body=notification_data.get("body", "You have a notification")
            ),
            token=token,
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        badge=1,
                        sound="default"
                    )
                )
            )
        )
        
        # Send the message
        response = messaging.send(message)
        
        return https_fn.Response(
            json.dumps({"success": True, "message_id": response}),
            status=200,
            content_type="application/json"
        )
    
    except Exception as e:
        return https_fn.Response(
            json.dumps({"error": str(e)}),
            status=500,
            content_type="application/json"
        )