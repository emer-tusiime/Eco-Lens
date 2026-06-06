import requests

# Change this to your backend URL
API_BASE = "http://YOUR_BACKEND_URL/api"

# Example during local testing:
# API_BASE = "http://192.168.1.100:3000/api"


def start_session(user_code):
    """
    Start a disposal session.
    """

    response = requests.post(
        f"{API_BASE}/disposal/sessions/start",
        json={
            "userCode": user_code
        }
    )

    response.raise_for_status()
    return response.json()


def record_event(session_id, classified_as, confidence, is_plastic):
    """
    Record a classified disposal event.
    """

    response = requests.post(
        f"{API_BASE}/disposal/events",
        json={
            "sessionId": session_id,
            "classifiedAs": classified_as,
            "confidence": confidence,
            "isPlastic": is_plastic
        }
    )

    response.raise_for_status()
    return response.json()


def end_session(session_id):
    """
    End a disposal session.
    """

    response = requests.post(
        f"{API_BASE}/disposal/sessions/end",
        json={
            "sessionId": session_id
        }
    )

    response.raise_for_status()
    return response.json()