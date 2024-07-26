import numpy as np
from tensorflow.keras.models import load_model
import PIL.Image
import shutil
import time

def preprocess_img(path):
    arr = np.array(PIL.Image.open(path),dtype=np.uint16)
    return arr/65535

def consult_CNN(directories, verbosity):
    t1 = time.perf_counter()
    if verbosity > 0:
        print("CNN")
    
    paths = list(directories["cutouts"].glob('*.png'))
    image_seq = np.array([preprocess_img(path) for path in paths])
    model = load_model(directories["CONSULT_CNN"]/'CNNmodel.keras')
    predictions = (model.predict(image_seq))
    binary_predictions = (predictions > 0.5).astype(int).flatten()
    for i in range(len(binary_predictions)):
        if binary_predictions[i] == 1:
            shutil.move(paths[i],directories["dwarf"])
        else:
            shutil.move(paths[i],directories["nondwarf"])

    t2 = time.perf_counter()
    if verbosity > 0:
        print(f"CNN TIME: {t2-t1}")

    