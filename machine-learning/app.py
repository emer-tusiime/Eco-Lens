import os
import io
import tempfile
import uvicorn
import gradio as gr
from PIL import Image
from ultralytics import YOLO
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse

# Load model once
MODEL_PATH = "best.pt"
model = YOLO(MODEL_PATH)
CONFIDENCE_THRESHOLD = 0.5

# FastAPI app
app = FastAPI()

@app.post("/classify")
async def classify(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert("RGB")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            image.save(tmp.name)
            temp_path = tmp.name

        results = model(temp_path)
        boxes = results[0].boxes

        if len(boxes) == 0:
            return JSONResponse({
                "isPlastic": False,
                "classifiedAs": "no_detection",
                "confidence": 0.0,
                "message": "No objects detected"
            })

        best_box = max(boxes, key=lambda b: float(b.conf[0].item()))
        cls_id     = int(best_box.cls[0].item())
        confidence = float(best_box.conf[0].item())
        class_name = model.names.get(cls_id, str(cls_id))
        is_plastic = confidence >= CONFIDENCE_THRESHOLD

        return JSONResponse({
            "isPlastic": is_plastic,
            "classifiedAs": class_name,
            "confidence": round(confidence, 4),
            "message": f"Detected {class_name} with {confidence:.2%} confidence"
        })

    except Exception as e:
        return JSONResponse(
            {"error": str(e), "isPlastic": False, "classifiedAs": "error", "confidence": 0.0},
            status_code=500
        )
    finally:
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)


# Gradio UI for testing
def predict_image(image):
    if image is None:
        return None, "Please upload an image."
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
        image.save(tmp.name)
        temp_path = tmp.name
    try:
        results = model(temp_path)
        plotted  = results[0].plot()
        boxes    = results[0].boxes
        count    = len(boxes)
        if count == 0:
            summary = "No objects detected."
        else:
            lines = [f"Detected {count} object(s):"]
            for i, box in enumerate(boxes, start=1):
                cls_id     = int(box.cls[0].item())
                conf       = float(box.conf[0].item())
                class_name = model.names.get(cls_id, str(cls_id))
                lines.append(f"{i}. {class_name} ({conf:.2%})")
            summary = "\n".join(lines)
        return plotted, summary
    except Exception as e:
        return None, f"Error: {str(e)}"
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


demo = gr.Interface(
    fn=predict_image,
    inputs=gr.Image(type="pil", label="Upload image"),
    outputs=[
        gr.Image(type="numpy", label="Prediction"),
        gr.Textbox(label="Detection Summary")
    ],
    title="EcoLens Model Tester",
)

app = gr.mount_gradio_app(app, demo, path="/ui")

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=7860)