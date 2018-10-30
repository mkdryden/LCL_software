import sys,pickle
sys.path.insert(0,'/home/hedwar/installs')
from keras.models import load_model
from keras.callbacks import ModelCheckpoint,CSVLogger,TensorBoard
from keras.preprocessing.image import ImageDataGenerator
import tensorflow as tf
import numpy as np

class MeanIoU(object):
    # taken from http://www.davidtvs.com/keras-custom-metrics/
    def __init__(self, num_classes):
        super().__init__()
        self.num_classes = num_classes

    def mean_iou(self, y_true, y_pred):
        # Wraps np_mean_iou method and uses it as a TensorFlow op.
        # Takes numpy arrays as its arguments and returns numpy arrays as
        # its outputs.
        return tf.py_func(self.np_mean_iou, [y_true, y_pred], tf.float32)

    def np_mean_iou(self, y_true, y_pred):
        # Compute the confusion matrix to get the number of true positives,
        # false positives, and false negatives
        # Convert predictions and target from categorical to integer format
        target = np.argmax(y_true, axis=-1).ravel()
        predicted = np.argmax(y_pred, axis=-1).ravel()

        # Trick from torchnet for bincounting 2 arrays together
        # https://github.com/pytorch/tnt/blob/master/torchnet/meter/confusionmeter.py
        x = predicted + self.num_classes * target
        bincount_2d = np.bincount(x.astype(np.int32), minlength=self.num_classes**2)
        assert bincount_2d.size == self.num_classes**2
        conf = bincount_2d.reshape((self.num_classes, self.num_classes))

        # Compute the IoU and mean IoU from the confusion matrix
        true_positive = np.diag(conf)
        false_positive = np.sum(conf, 0) - true_positive
        false_negative = np.sum(conf, 1) - true_positive

        # Just in case we get a division by 0, ignore/hide the error and set the value to 0
        with np.errstate(divide='ignore', invalid='ignore'):
            iou = true_positive / (true_positive + false_positive + false_negative)
        iou[np.isnan(iou)] = 0

        return np.mean(iou).astype(np.float32)
num_classes = 3

miou_metric = MeanIoU(num_classes)
mean_iou = miou_metric.mean_iou

data_loc = r'/home/hedwar/cell_localization/training_data_normalized.p'

initial_epoch = 18
old_save_loc = '/scratch/hedwar/multiclass_localizer18.hdf5'
x_train, x_val, y_train, y_val = pickle.load(open(data_loc,'rb'))
model = load_model(old_save_loc,custom_objects={'mean_iou': mean_iou})
print('model loaded')

seed = 1
image_gen_args = dict(rotation_range = 90.,
                     width_shift_range = 0.05,
                     height_shift_range = 0.05,
                     vertical_flip = True,
                     horizontal_flip = True) 

mask_gen_args = dict(rotation_range = 90.,
                     width_shift_range = 0.05,
                     height_shift_range = 0.05,
                     vertical_flip = True,
                     horizontal_flip = True)  

image_datagen = ImageDataGenerator(**image_gen_args) 
mask_datagen = ImageDataGenerator(**mask_gen_args)

# image_datagen.fit(x_train, seed=seed) 
# mask_datagen.fit(y_train, seed=seed)


image_generator = image_datagen.flow(x_train, seed=seed, batch_size=8)
mask_generator = mask_datagen.flow(y_train, seed=seed, batch_size=8)

x_val_generator = image_datagen.flow(x_val, seed=seed, batch_size=100)
y_val_generator = mask_datagen.flow(y_val, seed=seed, batch_size=100)

train_generator = zip(image_generator, mask_generator)
val_generator = zip(x_val_generator,y_val_generator)

validation_generator = zip(image_generator, mask_generator)

csv_logger = CSVLogger('/scratch/hedwar/multiclass_localizer_training18_2.log')
# tbCallBack = TensorBoard(log_dir='/scratch/a/awheeler/hedwar/tensorboard', histogram_freq=0, write_graph=True, write_images=True)
tbCallBack = TensorBoard(log_dir='/scratch/hedwar/tensorboard', histogram_freq=0, write_graph=True, write_images=True)
# save_loc = '/scratch/a/awheeler/hedwar/transpose_multiclass_localizer.hdf5'
save_loc = '/scratch/hedwar/multiclass_localizer18_2.hdf5'
checkpointer = ModelCheckpoint(filepath=save_loc, verbose=1, save_best_only=True)

model.fit_generator(train_generator,
                    validation_data = val_generator,
                    validation_steps=600,
                    steps_per_epoch=2000,
                    epochs=1500,
                    initial_epoch = initial_epoch,
                    callbacks = [tbCallBack,checkpointer,csv_logger])