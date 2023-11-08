import cv2
from fastapi import FastAPI, UploadFile, Request, Form
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import random
from typing import Union
from ultralytics import YOLO
import uvicorn
import zipfile
from imutils.video import VideoStream

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# сюда попадут все файлы
UPLOAD_DIR = './ups/'

some_file_path = "./static/test.mp4"

# cap = cv2.VideoCapture("rtsp://127.0.0.1:8554/test.mp4")

cap = []


# cap.append(cv2.VideoCapture("rtsp://admin:A1234567@188.170.176.190:8027/Streaming/Channels/101?transportmode=unicast&profile=Profile_1"))
# cap.append(cv2.VideoCapture("rtsp://admin:A1234567@188.170.176.190:8028/Streaming/Channels/101?transportmode=unicast&profile=Profile_1"))


# cap = cv2.VideoCapture("rtsp://admin:A1234567@188.170.176.190:8027/Streaming/Channels/101?transportmode=unicast&profile=Profile_1")

@app.get("/")
def read_root(request: Request):
    # return FileResponse("./static/index.html")
    return templates.TemplateResponse("index.html", {"request": request, "id": 2})


def model(frame):
    model_path = "./weights/best.pt"
    _model = YOLO(model_path)
    detections = _model.predict(frame, imgsz=(640, 384))
    res = []
    for detected_boxes in detections[0]:
        list_ = detected_boxes.boxes.xyxy[0].tolist()
        bbox = ((int(list_[0]), int(list_[1])), (int(list_[2]), int(list_[3])))
        print(bbox)
        print(type(bbox[0][0]))
        res.append(bbox)
    return res


@app.get("/video/{item_id}")
async def video_feed(item_id: int):
    index = item_id
    print(index)

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

    def iterfile(index: int):  #
        count = 0
        n = 12000
        k = 5

        if index >= len(cap):
            return
        while cap[index]:
            # скипаем кадры в буфере (какой чудак придумал стримить по TCP)
            for i in range(k):
                cap[index].read()
                count += 1
            frame = cap[index].read()
            if frame is None :
                continue
            # print(count)
            # print(ret)
            count += 1
            # тут будем скипать кадры для отправки в модель
            if count % n == 0:
                res = model(frame)
                for rec in res:
                    cv2.rectangle(frame, rec[0], rec[1], thickness=3, color=(0, 0, 255))
                count -= n

            # res = mock_nn()

            (flag, encoded_image) = cv2.imencode(".jpg", frame)

            if not flag:
                continue
            if cv2.waitKey(20) & 0xFF == ord('q'):
                break
            yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' +
                   bytearray(encoded_image) + b'\r\n')

    return StreamingResponse(iterfile(index), media_type="multipart/x-mixed-replace;boundary=frame")


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
    return RedirectResponse("/", status_code=302)


@app.post("/add_source")
def add_source(login=Form(), password=Form(), url=Form()):
    res = f"rtsp://{login}:{password}@{url}"
    print(f"cap len = {len(cap)}")
    if len(cap) > 8:
        cap[0] = cv2.VideoCapture(res)
    else:
        cap.append(VideoStream(res).start())
    return RedirectResponse("/", status_code=302)


if __name__ == '__main__':
    uvicorn.run(app, host="127.0.0.1", port=8000)
