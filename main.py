import random
import time
import zipfile
import cv2
from fastapi.staticfiles import StaticFiles
from fastapi import Request
from fastapi import FastAPI, UploadFile, File
from typing import Union
from fastapi.responses import RedirectResponse, FileResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

import uvicorn
import os

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
#сюда попадут все файлы
UPLOAD_DIR = './ups/'

templates = Jinja2Templates(directory="templates")

some_file_path = "./static/test.mp4"
cap = cv2.VideoCapture("rtsp://127.0.0.1:8554/test.mp4")
url_rtsp = 'rtsp://127.0.0.1:8554/screenlive'

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
    #return FileResponse("./static/index.html")
    return templates.TemplateResponse("index.html", {"request": request, "id": 2})

count = 0
@app.get("/video")
async def video_feed():
    def iterfile():  #
        global count
        while (cap.isOpened()):
            ret, frame = cap.read()
            count += 1
            if count % 5 != 0:
                continue
            # print(frame)
            # print(type(frame))
            #time.sleep(0.002)
            #cv2.imshow('frame', frame)
            outputFrame = frame
            cv2.rectangle(frame, (1240 + random.randint(-200,200),637+ random.randint(-200,200)), (225+ random.randint(-200,200), 897+ random.randint(-200,200)),thickness= 3,color=(0,0,255))
            (flag, encodedImage) = cv2.imencode(".jpg", outputFrame)
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
    return RedirectResponse("/", status_code=302)#{"filename": file.filename}


if __name__ == '__main__':
    uvicorn.run(app, host="127.0.0.1", port=8000)
