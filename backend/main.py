from firebase_functions import https_fn
from firebase_admin import initialize_app, messaging
import json

# Initialize the Firebase app
initialize_app()

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
        
        # In a real implementation, you would use Cloud Tasks or Cloud Scheduler
        # to schedule the notification for later delivery
        # For this example, we'll just return a success message
        
        return https_fn.Response(
            json.dumps({
                "success": True,
                "scheduled": True,
                "message": f"Notification scheduled to be sent in {request_data.get('delay', 60)} seconds"
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