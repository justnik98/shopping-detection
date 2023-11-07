import random
import time
import copy
import zipfile
import cv2
from fastapi.staticfiles import StaticFiles
from fastapi import Request
from fastapi import FastAPI, UploadFile, File
from typing import Union
from fastapi.responses import RedirectResponse, FileResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from ultralytics import YOLO
import uvicorn
import os

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
# сюда попадут все файлы
UPLOAD_DIR = './ups/'

templates = Jinja2Templates(directory="templates")

some_file_path = "./static/test.mp4"
cap = cv2.VideoCapture("rtsp://127.0.0.1:8554/test.mp4")


#cap = cv2.VideoCapture("rtsp://admin:A1234567@188.170.176.190:8027/Streaming/Channels/101?transportmode=unicast&profile=Profile_1")
# url_rtsp = 'rtsp://127.0.0.1:8554/screenlive'

# def iterfile():
#     cap = cv2.VideoCapture("rtsp://127.0.0.1:8554/screenlive")
#     while (cap.isOpened()):
#         time.sleep(0.2)
#         ret, frame = cap.read()
#         print(frame)
#         print(type(frame))
#         cv2.imshow('frame', frame)
#         yield frame
@app.get("/")
def read_root(request: Request):
    # return FileResponse("./static/index.html")
    return templates.TemplateResponse("index.html", {"request": request, "id": 2})


def model(frame):
    model_path = "./weights/best.pt"
    model = YOLO(model_path)
    detections = model.predict(frame, imgsz=(640, 384))
    res = []
    for detected_boxes in detections[0]:
        list_ = detected_boxes.boxes.xyxy[0].tolist()
        bbox = ((int(list_[0]), int(list_[1])), (int(list_[2]), int(list_[3])))
        print(bbox)
        print(type(bbox[0][0]))
        res.append(bbox)
    return res


@app.get("/video")
def video_feed():
    def mock_nn():  # заменяем рандомом BB
        res = []
        r = random.random()
        while r < 0.3:
            x1 = 1240 + random.randint(-200, 200)
            y1 = 637 + random.randint(-200, 200)
            x2 = 225 + random.randint(-200, 200)
            y2 = 897 + random.randint(-200, 200)
            res.append(((x1, y1), (x2, y2)))
            r = random.random()
        return res

    def iterfile():  #
        count = 0
        n = 120
        k = 5
        while (cap.isOpened()):
            # скипаем кадры в буфере (какой чудак придумал стримить по TCP)
            for i in range(k):
                cap.grab()
                count += 1
            ret, frame = cap.read()
            dim = (640, 384)
            resized = cv2.resize(frame, dim, interpolation=cv2.INTER_AREA)
            # print(count)
            # print(ret)
            if not ret:
                continue
            count += 1
            # тут будем скипать кадры для отправки в модель
            if count % n == 0:
                res = model(frame)
                for rec in res:
                    cv2.rectangle(frame, rec[0], rec[1], thickness=3, color=(0, 0, 255))
                count -= n
                # Иммитация обработки
            # print(frame)
            # print(type(frame))
            # time.sleep(0.002)
            # cv2.imshow('frame', frame)

            (flag, encodedImage) = cv2.imencode(".jpg", frame)
            # res = mock_nn()
            # (flag, encodedImage) = cv2.imencode(".jpg", frame)

            if not flag:
                continue
            if cv2.waitKey(20) & 0xFF == ord('q'):
                break
            yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' +
                   bytearray(encodedImage) + b'\r\n')

            # frame = imutils.resize(frame, width=680)

        # with open(some_file_path, mode="rb") as file_like:  #
        #     yield from file_like  #

    return StreamingResponse(iterfile(), media_type="multipart/x-mixed-replace;boundary=frame")


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}


@app.post("/upload-files")
async def upload_file(file: UploadFile):
    if file.filename == "":
        return "error-42"
    data = file.file
    path = os.path.join(UPLOAD_DIR, file.filename)
    with open(path, 'wb') as f:
        f.write(data.read())
    if str(file.filename).endswith(".zip"):
        with zipfile.ZipFile(path, 'r') as zip_ref:
            zip_ref.extractall(UPLOAD_DIR)
        os.remove(path)
    return RedirectResponse("/", status_code=302)  # {"filename": file.filename}


if __name__ == '__main__':
    uvicorn.run(app, host="127.0.0.1", port=8000)
