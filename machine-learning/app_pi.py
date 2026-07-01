import os
import io
import tempfile
import uvicorn
from PIL import Image
from ultralytics import YOLO
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse

MODEL_PATH = os.path.join(os.path.dirname(__file__), "best.pt")
model = YOLO(MODEL_PATH)
CONFIDENCE_THRESHOLD = 0.4

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

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("app_pi:app", host="0.0.0.0", port=7860)
