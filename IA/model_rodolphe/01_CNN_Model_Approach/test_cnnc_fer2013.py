# -*- coding: utf-8 -*-
"""test_cnnc_fer2013.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1D8h2sQOHXRhyQ3KizghT2JkERD5haS3I
"""

!pip install mtcnn
!pip install lz4

import tensorflow as tf
import numpy as np
import cv2
from mtcnn import MTCNN
import os

import matplotlib.pyplot as plt
import seaborn as sns
import tensorflow as tf
import keras
from keras.preprocessing import image
from keras.models import Sequential
from keras.layers import Conv2D, MaxPool2D, Flatten,Dense,Dropout,BatchNormalization
from tensorflow.keras.callbacks import ModelCheckpoint, EarlyStopping, ReduceLROnPlateau, TensorBoard
from tensorflow.keras.preprocessing.image import ImageDataGenerator

# --- Téléchargement et décompression du dataset ---
#!rm -rf /content/FER2013
#!kaggle datasets download msambare/fer2013 -p /content/FER2013
#!unzip -q /content/FER2013/fer2013.zip -d /content/FER2013

# --- Définir les chemins vers les données ---
data_dir_train = '/content/FER2013/train'
data_dir_test = '/content/FER2013/test'

# --- Création des datasets avec tf.data ---
batch_size = 64
img_size = (48, 48)

categories = os.listdir(data_dir_train)

image_counts = {category: len(os.listdir(os.path.join(data_dir_train, category))) for category in categories}

plt.figure(figsize=(10, 5))
sns.barplot(x=list(image_counts.keys()), y=list(image_counts.values()), palette="viridis")
plt.xlabel("Emotion Category")
plt.ylabel("Number of Images")
plt.title("Number of Images in Each Emotion Category")
plt.xticks(rotation=45)
plt.show()

categories = os.listdir(data_dir_train)

plt.figure(figsize=(10, 6))

for i, category in enumerate(categories):
    category_path = os.path.join(data_dir_train, category)
    image_path = os.path.join(category_path, os.listdir(category_path)[0])  # Get first image
    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)  # Read in grayscale
    plt.subplot(2, 4, i+1)
    plt.imshow(image, cmap='gray')
    plt.title(category)
    plt.axis('off')

plt.tight_layout()
plt.show()

train_datagen = ImageDataGenerator(
    width_shift_range=0.1,           #  shifts the image horizontally by 10% of the total width
    height_shift_range=0.1,          # shifts the image vertically by 10% of the total height
    horizontal_flip=True,            # A left-facing car image might be flipped to a right-facing one
    rescale=1./255,                  #  improving training stability , Faster Convergence
    validation_split=0.2
)


test_datagen = ImageDataGenerator(rescale=1./255)

train_generator = train_datagen.flow_from_directory(
    directory=data_dir_train,
    target_size=(48, 48),
    batch_size=64,
    color_mode="grayscale",
    class_mode="categorical",
    subset="training"
)

validation_generator = train_datagen.flow_from_directory(
    directory=data_dir_train,  # Use train_dir for validation
    target_size=(48, 48),
    batch_size=64,
    color_mode="grayscale",
    class_mode="categorical",
    subset="validation"
)

test_generator = test_datagen.flow_from_directory(
    directory=data_dir_test,
    target_size=(48, 48),
    batch_size=64,
    color_mode="grayscale",
    class_mode="categorical"
)

model = tf.keras.Sequential([
        # input layer
        tf.keras.layers.Input(shape=(48,48,1)),  # Input() instead of input_shape in Conv2D
        tf.keras.layers.Conv2D(64,(3,3), padding='same', activation='relu' ),
        tf.keras.layers.BatchNormalization(),
        tf.keras.layers.MaxPooling2D(2,2),
        tf.keras.layers.Dropout(0.25),

        # 1st hidden dense layer
        tf.keras.layers.Conv2D(128,(5,5), padding='same', activation='relu'),
        tf.keras.layers.BatchNormalization(),
        tf.keras.layers.MaxPooling2D(2,2),
        tf.keras.layers.Dropout(0.25),

        # 2nd hidden dense layer
        tf.keras.layers.Conv2D(512,(3,3), padding='same', activation='relu',kernel_regularizer=tf.keras.regularizers.l2(0.01)),
        tf.keras.layers.BatchNormalization(),
        tf.keras.layers.MaxPooling2D(2,2),
        tf.keras.layers.Dropout(0.25),

        # 3rd hidden dense layer
        tf.keras.layers.Conv2D(512,(3,3), padding='same', activation='relu',kernel_regularizer=tf.keras.regularizers.l2(0.01)),
        tf.keras.layers.BatchNormalization(),
        tf.keras.layers.MaxPooling2D(2,2),
        tf.keras.layers.Dropout(0.25),

        # Flatten layer
        tf.keras.layers.Flatten(),

        tf.keras.layers.Dense(256, activation='relu'),
        tf.keras.layers.BatchNormalization(),
        tf.keras.layers.Dropout(0.25),

        tf.keras.layers.Dense(512, activation='relu'),
        tf.keras.layers.BatchNormalization(),
        tf.keras.layers.Dropout(0.25),

        # output layer
        tf.keras.layers.Dense(7, activation='softmax')
    ])

optimizer = tf.keras.optimizers.Adam(learning_rate=0.0001)
model.compile(optimizer=optimizer,
                  loss='categorical_crossentropy',
                  metrics=['accuracy'])

model.summary()

# Définition des callbacks
callbacks = [
    # Sauvegarder le meilleur modèle
    ModelCheckpoint(filepath='best_model.h5',
                    monitor='val_accuracy',
                    save_best_only=True,
                    mode='max',
                    verbose=1),

    # Arrêter l'entraînement si la performance ne s'améliore plus
    EarlyStopping(monitor='val_loss',
                  patience=10,
                  restore_best_weights=True,
                  verbose=1),

    # Réduction du learning rate si la validation n'améliore pas
    ReduceLROnPlateau(monitor='val_loss',
                      factor=0.5,
                      patience=5,
                      verbose=1),
]

strategy = tf.distribute.MirroredStrategy()  # si vous avez plusieurs GPU

history = model.fit(x = train_generator,epochs = 70 ,
                    validation_data = validation_generator,
                    callbacks=callbacks)
# You can go for 100 epochs

loss, acc = model.evaluate(test_generator)
print(f"Final Test Accuracy: {acc * 100:.2f}%")

plt.figure(figsize=(12, 5))

# Courbe de précision
plt.subplot(1, 2, 1)
plt.plot(history.history['accuracy'], label='Train')
plt.plot(history.history['val_accuracy'], label='Validation')
plt.xlabel('Epoch')
plt.ylabel('Accuracy')
plt.legend()
plt.title('Courbe de Précision')

# Courbe de perte
plt.subplot(1, 2, 2)
plt.plot(history.history['loss'], label='Train')
plt.plot(history.history['val_loss'], label='Validation')
plt.xlabel('Epoch')
plt.ylabel('Loss')
plt.legend()
plt.title('Courbe de Perte')

plt.show()

