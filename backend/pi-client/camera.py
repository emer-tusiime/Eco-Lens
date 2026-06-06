# camera.py

import os
import time

from picamera2 import Picamera2

from config import IMAGE_DIR, IMAGE_NAME


def ensure_capture_directory():
    """
    Create capture directory if it doesn't exist.
    """

    os.makedirs(IMAGE_DIR, exist_ok=True)


def capture_image():
    """
    Capture an image and return the file path.
    """

    ensure_capture_directory()

    image_path = os.path.join(IMAGE_DIR, IMAGE_NAME)

    picam2 = Picamera2()

    picam2.configure(
        picam2.create_still_configuration()
    )

    picam2.start()

    # Give camera time to adjust exposure
    time.sleep(2)

    picam2.capture_file(image_path)

    picam2.stop()

    return image_path


if __name__ == "__main__":
    path = capture_image()
    print(f"Image saved to: {path}")