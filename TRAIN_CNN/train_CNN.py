#0,1254,834,183

#import os
#os.environ['PYTHONHASHSEED'] = '0'

#import random as rn
#rn.seed(1254)

import tensorflow as tf
import numpy as np

#tf.random.set_seed(834)
#np.random.seed(183)

from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.metrics import BinaryAccuracy, Precision, Recall
import matplotlib.pyplot as plt
import PIL
import PIL.Image
from pathlib import Path

training_data = Path.cwd()/'dataset'
training = training_data/'train'
validation = training_data/'validate'
testing = training_data/'test'

batch_size = 32
img_height = 256
img_width = 256

train_datagen = ImageDataGenerator(
    rescale=1.0/65535,
    rotation_range=360,
    horizontal_flip=True,
    vertical_flip=True,
    fill_mode='reflect',
)
validation_datagen = ImageDataGenerator(rescale=1.0/65535,)
test_datagen = ImageDataGenerator(rescale=1.0/65535,)

train_generator = train_datagen.flow_from_directory(
    training,
    target_size=(img_width, img_height),
    batch_size=batch_size,
    color_mode='grayscale',
    class_mode='binary',
    classes=['nondwarf','dwarf'],
    shuffle=True,
)

validation_generator = validation_datagen.flow_from_directory(
    validation,
    target_size=(img_width, img_height),
    batch_size=batch_size,
    color_mode='grayscale',
    class_mode='binary',
    classes=['nondwarf','dwarf'],
    shuffle=True,
)

test_generator = test_datagen.flow_from_directory(
    testing,
    target_size=(img_width, img_height),
    batch_size=batch_size,
    color_mode='grayscale',
    class_mode='binary',
    classes=['nondwarf','dwarf'],
    shuffle=False,
)

images, labels = next(train_generator)
plt.figure(figsize=(20, 15))
for i in range(32):
    plt.subplot(5, 8, i + 1)
    plt.imshow(images[i].reshape(256, 256), cmap='gray')
    plt.title(labels[i])
    plt.axis('off')
plt.show()

model = tf.keras.models.Sequential([
    tf.keras.layers.Conv2D(32, (7, 7), activation='relu', input_shape=(256, 256, 1)),
    tf.keras.layers.BatchNormalization(),
    tf.keras.layers.MaxPooling2D((2, 2)),
    tf.keras.layers.Conv2D(64, (5, 5), activation='relu'),
    tf.keras.layers.BatchNormalization(),
    tf.keras.layers.MaxPooling2D((2, 2)),
    tf.keras.layers.Conv2D(128, (3, 3), activation='relu'),
    tf.keras.layers.BatchNormalization(),
    tf.keras.layers.MaxPooling2D((2, 2)),
    tf.keras.layers.Conv2D(256, (3, 3), activation='relu'),
    tf.keras.layers.BatchNormalization(),
    tf.keras.layers.MaxPooling2D((2, 2)),
    tf.keras.layers.Flatten(),
    tf.keras.layers.Dense(512, activation='relu', kernel_initializer='he_normal'),
    tf.keras.layers.BatchNormalization(),
    tf.keras.layers.Dropout(0.5),
    tf.keras.layers.Dense(1, activation='sigmoid')
])

model.compile(
  optimizer='adam',
  loss='binary_crossentropy',
  metrics=[BinaryAccuracy(), Precision(), Recall()])

import datetime
log_dir = "logs/fit/" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
tensorboard_callback = tf.keras.callbacks.TensorBoard(log_dir=log_dir, histogram_freq=1)

model.fit(
  train_generator,
  validation_data=validation_generator,
  epochs=5,
  callbacks=[tensorboard_callback]
)

model.save('CNNmodel.keras')

test_dict = model.evaluate(test_generator,return_dict=True)
for key, item in test_dict.items():
    print(f"{key}: {item}")

predictions = model.predict(test_generator)
binary_predictions = (predictions > 0.5).astype(int).flatten()
answer_key = test_generator.classes
from sklearn.metrics import classification_report
print(classification_report(answer_key,binary_predictions))
false_pos_inds = np.where((binary_predictions==1)&(answer_key==0))[0]
false_neg_inds = np.where((binary_predictions==0)&(answer_key==1))[0]

def plot_images(indices, generator, title):
    plt.figure(figsize=(15, 15))
    for i, idx in enumerate(indices[:32]):
        batch_idx = idx // batch_size
        within_batch_idx = idx % batch_size
        batch_imgs, batch_labels = generator[batch_idx]
        img = batch_imgs[within_batch_idx]
        true_label = batch_labels[within_batch_idx]
        pred_label = binary_predictions[idx]
        plt.subplot(4, 8, i+1)
        plt.imshow(img, cmap='gray',)
        plt.title(f'True: {true_label}, Pred: {pred_label}')
        plt.axis('off')
    plt.suptitle(title)
    plt.show()

plot_images(false_pos_inds,test_generator,'False Positives')
plot_images(false_neg_inds,test_generator,'False Negatives')