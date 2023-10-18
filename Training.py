import numpy as np
import matplotlib.pyplot as plt
import os
import argparse
from imutils import paths
from keras.utils import load_img
from keras.utils import img_to_array
from keras.models import load_model
from keras.applications.mobilenet_v2 import preprocess_input
from sklearn.preprocessing import LabelBinarizer
from keras.utils import to_categorical
from sklearn.model_selection import train_test_split
from keras.preprocessing.image import ImageDataGenerator
from keras.applications import MobileNetV2
from keras.layers import Input
from keras.layers import AveragePooling2D
from keras.layers import Flatten
from keras.layers import Dense
from keras.layers import Dropout
from keras.models import Model
from keras.optimizers import Adam
from sklearn.metrics import classification_report

ap = argparse.ArgumentParser()
ap.add_argument("-d", "--dataset", type=str, default="dataset", help="path to input dataset")
ap.add_argument("-m", "--model", type=str, default="mask_detector.model", help="path to output face mask detector model")
args = vars(ap.parse_args())

INIT_LR = 1e-4
EPOCHS = 20
BS = 32

# with_mask: 690 images
# without_mask: 686 images
print("loading images...")
imagePaths = list(paths.list_images(args["dataset"]))
data = []
labels =  []

for imagePath in imagePaths:
    label = imagePath.split(os.path.sep)[-2]
    image = load_img(imagePath, target_size=(224,224))
    image = img_to_array(image)
    image = preprocess_input(image) # normalization
    
    data.append(image)
    labels.append(label)
    
data = np.array(data,dtype="float32")
labels = np.array(labels)

lb = LabelBinarizer()
labels = lb.fit_transform(labels) # [0],   [1],   [1],   [0] ...
labels = to_categorical(labels) #   [1,0], [0,1], [0,1], [1,0] ...

(train_x,test_x,train_y,test_y) = train_test_split(data,labels,test_size=0.20, 
                                stratify=labels, random_state=42)

aug = ImageDataGenerator(rotation_range=20,	zoom_range=0.15, 
                        width_shift_range=0.2, height_shift_range=0.2,	
                        shear_range=0.15, horizontal_flip=True,	fill_mode="nearest")

# Image Classification
baseModel = MobileNetV2(weights="imagenet", include_top=False, input_tensor=Input(shape=(224, 224, 3)))

headModel = baseModel.output

# Average pooling method smooths out the image
headModel = AveragePooling2D(pool_size=(7,7))(headModel)
headModel = Flatten(name="flatten")(headModel)
headModel = Dense(128, activation="relu")(headModel)
headModel = Dropout(0.5)(headModel) # prevents overfitting
headModel = Dense(2, activation="softmax")(headModel)

model = Model(inputs=baseModel.input, outputs=headModel)

# loop over all layers in the base model and freeze them so they will
# *not* be updated during the first training process

for layer in baseModel.layers:
	layer.trainable = False

print("Compiling model...")
opt = Adam(lr=INIT_LR, decay=INIT_LR / EPOCHS)
model.compile(loss="binary_crossentropy", optimizer=opt,
	metrics=["accuracy"])

print("Training head...")
H = model.fit(aug.flow(train_x,train_y,batch_size=BS), steps_per_epoch=len(train_x)//BS, validation_data=(train_x,train_y), validation_steps=len(test_x)//BS, epochs=EPOCHS)

print("evaluation network...")
predIdxs = model.predict(test_x, batch_size=BS)

predIdxs = np.argmax(predIdxs, axis=1)

print(classification_report(test_y.argmax(axis=1), predIdxs, target_names=lb.classes_))

print("saving mask detector model...")
model.save(args["model"], save_format="h5")

N = EPOCHS
plt.style.use("ggplot")
plt.figure()
plt.plot(np.arange(0, N), H.history["loss"], label="train_loss")
plt.plot(np.arange(0, N), H.history["val_loss"], label="val_loss")
plt.plot(np.arange(0, N), H.history["accuracy"], label="train_acc")
plt.plot(np.arange(0, N), H.history["val_accuracy"], label="val_acc")
plt.title("Training Loss and Accuracy")
plt.xlabel("Epoch #")
plt.ylabel("Loss/Accuracy")
plt.legend(loc="lower left")