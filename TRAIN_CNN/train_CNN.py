import tensorflow as tf
import numpy as np
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Flatten, Dense, Dropout
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

def display_batch(generator,batch_size,suptitle):
    images, labels = next(generator)
    strlabels = ['dwarf' if i==1 else 'nondwarf' for i in labels]
    fig, axs = plt.subplots(4,8,figsize=(20, 15))
    for i in range(batch_size):
        r, c = i//8, i%8
        axs[r,c].imshow(images[i].reshape(512, 512), cmap='gray')
        axs[r,c].set_title(strlabels[i])
        axs[r,c].axis('off')
    plt.suptitle(suptitle)
    plt.show()

def configure_paths(dataset_dir):
    train_dir = dataset_dir/'train'
    train_dwarf_dir = train_dir/'dwarf'
    train_nondwarf_dir = train_dir/'nondwarf'
    validate_dir = dataset_dir/'validate'
    validate_dwarf_dir = validate_dir/'dwarf'
    validate_nondwarf_dir = validate_dir/'nondwarf'
    test_dir = dataset_dir/'test'
    test_dwarf_dir = test_dir/'dwarf'
    test_nondwarf_dir = test_dir/'nondwarf'
    paths = {"dataset":dataset_dir,
             "train":train_dir,
             "train_dwarf":train_dwarf_dir,
             "train_nondwarf":train_nondwarf_dir,
             "validate":validate_dir,
             "validate_dwarf":validate_dwarf_dir,
             "validate_nondwarf":validate_nondwarf_dir,
             "test":test_dir,
             "test_dwarf":test_dwarf_dir,
             "test_nondwarf":test_nondwarf_dir,
            }
    return paths

def train_CNN(dataset_dir,batch_size,num_epochs,display):

    paths = configure_paths(dataset_dir)

    print(f"dataset: {paths['dataset']}\nbatch size: {batch_size}\nnumber of epochs: {num_epochs}")

    train_datagen = ImageDataGenerator()
    validation_datagen = ImageDataGenerator()#preprocessing_function = lambda x: x/65535,)
    test_datagen = ImageDataGenerator()#preprocessing_function = lambda x: x/65535,)

    train_generator = train_datagen.flow_from_directory(
        paths["train"],
        target_size=(512, 512),
        batch_size=batch_size,
        color_mode='grayscale',
        class_mode='binary',
        classes=['non_dwarf','dwarf'],
        shuffle=True,
    )

    validation_generator = validation_datagen.flow_from_directory(
        paths["validate"],
        target_size=(512, 512),
        batch_size=batch_size,
        color_mode='grayscale',
        class_mode='binary',
        classes=['non_dwarf','dwarf'],
        shuffle=True,
    )

    test_generator = test_datagen.flow_from_directory(
        paths["test"],
        target_size=(512, 512),
        batch_size=batch_size,
        color_mode='grayscale',
        class_mode='binary',
        classes=['non_dwarf','dwarf'],
        shuffle=False,
    )

    if display:
        display_batch(train_generator, batch_size, 'train batch #0')
        display_batch(validation_generator, batch_size, 'validation batch #0')
        display_batch(test_generator, batch_size, 'test batch #0')

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

    '''inputs = tf.keras.layers.Input(shape=(512, 512, 1))
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
'''

    model = Sequential([
        Conv2D(32, (3, 3), activation='relu', input_shape=(512, 512, 1)),
        MaxPooling2D(pool_size=(2, 2)),
        Conv2D(64, (3, 3), activation='relu'),
        MaxPooling2D(pool_size=(2, 2)),
        Conv2D(128, (3, 3), activation='relu'),
        MaxPooling2D(pool_size=(2, 2)),
        Flatten(),
        Dense(128, activation='relu'),
        Dropout(0.5),
        Dense(1, activation='sigmoid')
    ])

    '''model = tf.keras.models.Sequential([
        tf.keras.layers.Conv2D(32, (7, 7), activation='relu', input_shape=(512, 512, 1)),
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
    ])'''

    '''model_C = ''

    if model_choice == 'A':
        model = model_A
    elif model_choice == 'B':
        model = model_B
    elif model_choice == 'C':
        model = model_C'''

    optimizer = Adam(learning_rate=0.001)

    model.compile(
    optimizer=optimizer,
    loss='binary_crossentropy',
    metrics=[BinaryAccuracy(), Precision(), Recall()])

    '''import datetime
    log_dir = "logs/fit/" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    tensorboard_callback = tf.keras.callbacks.TensorBoard(log_dir=log_dir, histogram_freq=1)'''

    #lr_scheduler = LearningRateScheduler(step_decay)

    history = model.fit(
    train_generator,
    epochs=num_epochs,
    validation_data=validation_generator,
    )

    '''model.fit(
    train_generator,
    validation_data=validation_generator,
    epochs=num_epochs,
    callbacks=[lr_scheduler]
    )'''

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
    #parser.add_argument('-model', choices=['A','B','C'], default='A', help='Model to use for training. Choose A, B, or C.')
    parser.add_argument('--display', action='store_true', default=False, help='Displays plots showing the batch cutouts used for training.')

    args = parser.parse_args()
    dataset_path = Path(args.dataset_path).resolve()
    batch_size = args.batch_size
    num_epochs = args.num_epochs
    #model_choice = args.model
    display = args.display

    train_CNN(dataset_path,batch_size,num_epochs,display)