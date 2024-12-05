import tensorflow as tf
import numpy as np
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.metrics import BinaryAccuracy, Precision, Recall
from tensorflow.keras.callbacks import LearningRateScheduler
import matplotlib.pyplot as plt
import PIL
import PIL.Image
from PIL import Image
from pathlib import Path
import argparse

def configure_paths(dataset_path):
    TRAIN_CNN_dir = Path.cwd()
    dataset_dir = dataset_path
    train_dir = dataset_dir/'train'
    train_dwarfs_dir = train_dir/'dwarfs'
    train_nondwarfs_dir = train_dir/'nondwarfs'
    validate_dir = dataset_dir/'validate'
    validate_dwarfs_dir = validate_dir/'dwarfs'
    validate_nondwarfs_dir = validate_dir/'nondwarfs'
    test_dir = dataset_dir/'test'
    test_dwarfs_dir = test_dir/'dwarfs'
    test_nondwarfs_dir = test_dir/'nondwarfs'
    paths = {"TRAIN_CNN":TRAIN_CNN_dir,
             "dataset":dataset_dir,
             "train":train_dir,
             "train_dwarfs":train_dwarfs_dir,
             "train_nondwarfs":train_nondwarfs_dir,
             "validate":validate_dir,
             "validate_dwarfs":validate_dwarfs_dir,
             "validate_nondwarfs":validate_nondwarfs_dir,
             "test":test_dir,
             "test_dwarfs":test_dwarfs_dir,
             "test_nondwarfs":test_nondwarfs_dir,
            }
    return paths

def add_positional_encoding(image, img_size):
    batch_size = tf.shape(image)[0]
    grid_x, grid_y = tf.meshgrid(tf.linspace(-32768., 32768., img_size), tf.linspace(-32768., 32768., img_size))
    grid_x = tf.expand_dims(grid_x, axis=-1)
    grid_y = tf.expand_dims(grid_y, axis=-1)
    positional_encoding = tf.concat([grid_x, grid_y], axis=-1)
    positional_encoding = tf.expand_dims(positional_encoding, axis=0)
    positional_encoding = tf.tile(positional_encoding, [batch_size,1,1,1])
    image_with_positional_encoding = tf.concat([image, positional_encoding], axis=-1)
    return image_with_positional_encoding

def step_decay(epoch):
    initial_lr = 0.001
    drop_rate = 0.1
    epochs_drop = 5
    lr = initial_lr * (drop_rate ** (epoch // epochs_drop))
    return lr

def plot_images(indices, test_generator, title, batch_size):
    plt.figure(figsize=(15, 15))
    for i, idx in enumerate(indices[:32]):
        batch_idx = idx // batch_size
        within_batch_idx = idx % batch_size
        batch_imgs, _ = test_generator[batch_idx]
        img = batch_imgs[within_batch_idx]
        plt.subplot(4, 8, i+1)
        plt.imshow(img, cmap='gray',)
        plt.axis('off')
    plt.suptitle(title)
    plt.show()

def train_CNN(dataset_path,batch_size,num_epochs,model_choice,display):

    paths = configure_paths(dataset_path)

    with Image.open(next(paths["train_dwarfs"].iterdir())) as im:
        img_size, _ = im.size

    print(f"""
        dataset: {paths["dataset"]}
        image dimensions: {img_size}x{img_size}

        batch size: {batch_size}
        number of epochs: {num_epochs}
    """)

    train_datagen = ImageDataGenerator(
        #preprocessing_function = lambda x: x/65535,
        #rotation_range=360,
        #horizontal_flip=True,
        #vertical_flip=True,
        #fill_mode='reflect',
    )
    validation_datagen = ImageDataGenerator()#preprocessing_function = lambda x: x/65535,)
    test_datagen = ImageDataGenerator()#preprocessing_function = lambda x: x/65535,)

    train_generator = train_datagen.flow_from_directory(
        paths["train"],
        target_size=(img_size, img_size),
        batch_size=batch_size,
        color_mode='grayscale',
        class_mode='binary',
        classes=['nondwarfs','dwarfs'],
        shuffle=True,
    )

    validation_generator = validation_datagen.flow_from_directory(
        paths["validate"],
        target_size=(img_size, img_size),
        batch_size=batch_size,
        color_mode='grayscale',
        class_mode='binary',
        classes=['nondwarfs','dwarfs'],
        shuffle=True,
    )

    test_generator = test_datagen.flow_from_directory(
        paths["test"],
        target_size=(img_size, img_size),
        batch_size=batch_size,
        color_mode='grayscale',
        class_mode='binary',
        classes=['nondwarfs','dwarfs'],
        shuffle=False,
    )

    if display:
        images, labels = next(train_generator)
        strlabels = ['dwarf' if i==1 else 'nondwarf' for i in labels]
        plt.figure(figsize=(20, 15))
        for i in range(batch_size):
            plt.subplot(4, 8, i + 1)
            plt.imshow(images[i].reshape(img_size, img_size), cmap='gray')
            plt.title(strlabels[i])
            plt.axis('off')
        plt.suptitle('training batch #0')
        plt.show()

        images, labels = next(validation_generator)
        strlabels = ['dwarf' if i==1 else 'nondwarf' for i in labels]
        plt.figure(figsize=(20, 15))
        for i in range(batch_size):
            plt.subplot(4, 8, i + 1)
            plt.imshow(images[i].reshape(img_size, img_size), cmap='gray')
            plt.title(strlabels[i])
            plt.axis('off')
        plt.suptitle('validation batch #0')
        plt.show()

        images, labels = next(test_generator)
        strlabels = ['dwarf' if i==1 else 'nondwarf' for i in labels]
        plt.figure(figsize=(20, 15))
        for i in range(batch_size):
            plt.subplot(4, 8, i + 1)
            plt.imshow(images[i].reshape(img_size, img_size), cmap='gray')
            plt.title(strlabels[i])
            plt.axis('off')
        plt.suptitle('test batch #0')
        plt.show()

    '''model_A = tf.keras.models.Sequential([
        tf.keras.layers.Conv2D(32, (3, 3), activation='relu', input_shape=(img_size, img_size, 1)),
        tf.keras.layers.BatchNormalization(),
        tf.keras.layers.MaxPooling2D((2, 2)),
        tf.keras.layers.Conv2D(64, (3, 3), activation='relu'),
        tf.keras.layers.BatchNormalization(),
        tf.keras.layers.MaxPooling2D((2, 2)),
        tf.keras.layers.Conv2D(128, (3, 3), activation='relu'),
        tf.keras.layers.BatchNormalization(),
        tf.keras.layers.MaxPooling2D((2, 2)),
        tf.keras.layers.Flatten(),
        tf.keras.layers.Dense(128, activation='relu'),
        tf.keras.layers.Dropout(0.5),
        tf.keras.layers.Dense(1, activation='sigmoid')
    ])'''

    inputs = tf.keras.layers.Input(shape=(img_size, img_size, 1))
    #x = tf.keras.layers.Lambda(lambda img: add_positional_encoding(img, img_size), output_shape=(img_size, img_size, 3))(inputs)
    x = tf.keras.layers.Conv2D(32, (3, 3), activation='relu')(inputs)
    x = tf.keras.layers.BatchNormalization()(x)
    x = tf.keras.layers.MaxPooling2D((2, 2))(x)
    x = tf.keras.layers.Conv2D(64, (3, 3), activation='relu')(x)
    x = tf.keras.layers.BatchNormalization()(x)
    x = tf.keras.layers.MaxPooling2D((2, 2))(x)
    x = tf.keras.layers.Conv2D(128, (3, 3), activation='relu')(x)
    x = tf.keras.layers.BatchNormalization()(x)
    x = tf.keras.layers.MaxPooling2D((2, 2))(x)
    x = tf.keras.layers.Flatten()(x)
    x = tf.keras.layers.Dense(128, activation='relu')(x)
    x = tf.keras.layers.Dropout(0.5)(x)
    outputs = tf.keras.layers.Dense(1, activation='sigmoid')(x)
    model_A = tf.keras.models.Model(inputs=inputs, outputs=outputs)

    model_B = tf.keras.models.Sequential([
        tf.keras.layers.Conv2D(32, (7, 7), activation='relu', input_shape=(img_size, img_size, 1)),
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

    model_C = ''

    if model_choice == 'A':
        model = model_A
    elif model_choice == 'B':
        model = model_B
    elif model_choice == 'C':
        model = model_C

    optimizer = Adam(learning_rate=0.001)

    model.compile(
    optimizer=optimizer,
    loss='binary_crossentropy',
    metrics=[BinaryAccuracy(), Precision(), Recall()])

    '''import datetime
    log_dir = "logs/fit/" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    tensorboard_callback = tf.keras.callbacks.TensorBoard(log_dir=log_dir, histogram_freq=1)'''

    lr_scheduler = LearningRateScheduler(step_decay)

    model.fit(
    train_generator,
    validation_data=validation_generator,
    epochs=num_epochs,
    callbacks=[lr_scheduler]
    )

    model.save('CNNmodel.keras')

    test_dict = model.evaluate(test_generator,return_dict=True)
    print("True test data metrics:")
    for metric, value in test_dict.items():
        print(f"{metric}: {value}")
    
    '''from sklearn.metrics import classification_report
    print(classification_report(answer_key,binary_predictions))'''

    if display:
        predictions = model.predict(test_generator)
        binary_predictions = (predictions > 0.5).astype(int).flatten()
        answer_key = test_generator.classes
        false_pos_inds = np.where((binary_predictions==1)&(answer_key==0))[0]
        false_neg_inds = np.where((binary_predictions==0)&(answer_key==1))[0]
        plot_images(false_pos_inds,test_generator,'False Positives',batch_size)
        plot_images(false_neg_inds,test_generator,'False Negatives',batch_size)

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('dataset_path', help='Path to the dataset folder containing the train/validate/test data.')
    parser.add_argument('batch_size', type=int, help='Batch size used to train the CNN.')
    parser.add_argument('num_epochs', type=int, help='Number of epochs used to train the CNN.')
    parser.add_argument('-model', choices=['A','B','C'], default='A', help='Model to use for training. Choose A, B, or C.')
    parser.add_argument('--display', action='store_true', default=False, help='Displays plots showing the batch cutouts used for training.')

    args = parser.parse_args()
    dataset_path = Path(args.dataset_path).resolve()
    batch_size = args.batch_size
    num_epochs = args.num_epochs
    model_choice = args.model
    display = args.display

    train_CNN(dataset_path,batch_size,num_epochs,model_choice,display)