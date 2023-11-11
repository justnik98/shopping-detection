"""
This is an example of my message
"""

import os
import zipfile
from typing import Union

import cv2
import uvicorn
from fastapi import FastAPI, UploadFile, Request, Form
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from imutils.video import VideoStream
from ultralytics import YOLO

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

UPLOAD_DIR = './ups/'

cap = []


@app.get("/")
def read_root(request: Request):
    """
    Обрабатывает get-запрос основной страницы сервиса.

    Args:
        request: get-запрос

    Returns:
        Nothing
    """
    return templates.TemplateResponse("index.html", {"request": request, "id": 2})


def model(frame):
    """
    Предобученная модель, распознающая на картинке объекты нестационарной торговли.

    Args:
        frame: изображение (стопкадр из видео)

    Returns:
        Список прямоугольников, ограничивающих объекты нестационарной торговли на кадре
    """
    model_path = "./weights/best.pt"
    _model = YOLO(model_path)
    detections = _model.predict(frame, imgsz=(640, 384), conf=0.26)
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
    """
        Обрабатывает get-запрос для видеострима.
            Вызывает метод обработки видеопотока.

        Args:
            index: индекс стрима (номер подключенный камеры или видео)

        Returns:
            Кадр с размеченными областями в которых находятся объекты нестационарной торговли.
        """
    index = item_id
    print(index)

    def iterfile(index: int):  #
        """
            Метод обработки видеопотока.

        Args:
            index: индекс стрима (номер подключенный камеры или видео)

        Returns:
            Кадр с размеченными областями в которых находятся объекты нестационарной торговли.
        """
        count = 0
        n = 250
        k = 5

        if index >= len(cap):
            return
        while cap[index]:
            # скипаем кадры в буфере (какой чудак придумал стримить по TCP)
            for i in range(k):
                cap[index].read()
                count += 1
            frame = cap[index].read()
            if frame is None:
                continue
            count += 1

            # скипаем кадры для отправки в модель для детектирвоания
            if count % n == 0:
                res = model(frame)
                for rec in res:
                    cv2.rectangle(frame, rec[0], rec[1], thickness=3, color=(0, 0, 255))
                count -= n

            (flag, encoded_image) = cv2.imencode(".jpg", frame)

            if not flag:
                continue
            if cv2.waitKey(20) & 0xFF == ord('q'):
                break
            yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' +
                   bytearray(encoded_image) + b'\r\n')

    return StreamingResponse(iterfile(index), media_type="multipart/x-mixed-replace;boundary=frame")


@app.post("/upload-files")
async def upload_file(file: UploadFile):
    """
    Обрабатывает get-запрос загрузки файлов.
    Позволяет загружать файлы на сервер.
    Перенаправляет на основную страницу и добавляет на нее стим с подключенной камеры.

    Args:
        file:  название файла (mp4 or zip)
    Returns:
        Nothing
    """

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
    cap.append(VideoStream(path).start())
    return RedirectResponse("/", status_code=302)


@app.post("/add_source")
def add_source(login=Form(), password=Form(), url=Form()):
    """
    Обрабатывает get-запрос добавления источника видео (RTSP камеры).
    Добавляет источник на панель стримов.
    Перенаправляет на основную страницу и добавляет на нее стим с подключенной камеры.

    Args:
        login: логин (может быть пустым)
        password: пароль камеры (может быть пустым)
        url: (ip и порт камеры)

    Returns:
        Nothing
    """
    res = f"rtsp://{login}:{password}@{url}"
    print(f"cap len = {len(cap)}")
    if len(cap) > 8:
        cap[0] = cv2.VideoCapture(res)
    else:
        cap.append(VideoStream(res).start())
    return RedirectResponse("/", status_code=302)


if __name__ == '__main__':
    uvicorn.run(app, host="127.0.0.1", port=8000)
