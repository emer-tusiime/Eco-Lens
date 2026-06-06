from api import start_session, record_event, end_session
from camera import capture_image


def main():
    print("\n===== EcoLens Pi Client =====\n")

    user_code = input("Enter user code: ").strip()

    try:
        # Start session
        session_response = start_session(user_code)

        session_id = session_response["session"]["id"]
        user_name = session_response["userName"]

        print(f"\nWelcome {user_name}")
        print(f"Session ID: {session_id}")

        input("\nPress ENTER to capture image...")

        # Capture image
        image_path = capture_image()

        print(f"\nImage captured: {image_path}")

        # --------------------------------------------------
        # Temporary mock result until cloud ML is connected
        # --------------------------------------------------

        classified_as = "plastic_bottle"
        confidence = 0.95
        is_plastic = True

        print("\nClassification Result")
        print(f"Class: {classified_as}")
        print(f"Confidence: {confidence:.2%}")

        # Record event
        event_response = record_event(
            session_id=session_id,
            classified_as=classified_as,
            confidence=confidence,
            is_plastic=is_plastic
        )

        print("\nBackend Response:")
        print(event_response["message"])

        # End session
        end_response = end_session(session_id)

        print("\nSession Complete")
        print(end_response["message"])

    except Exception as e:
        print("\nERROR:")
        print(str(e))


if __name__ == "__main__":
    main()