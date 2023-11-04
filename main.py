import zipfile

from fastapi import FastAPI, UploadFile, File
from typing import Union
from fastapi.responses import HTMLResponse, RedirectResponse

import uvicorn
import os

app = FastAPI()

#сюда попадут все файлы
UPLOAD_DIR = './ups/'


@app.get("/")
def read_root():
    with open("./static/index.html") as f:
        data = f.read()
    return HTMLResponse(content=data)


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
