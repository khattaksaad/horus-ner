from itertools import chain

import shorttext
import tensorflow as tf
import os
import matplotlib.pyplot as plt
import numpy as np
from tensorflow.contrib.framework import arg_scope
from tensorflow.contrib.slim.python.slim.nets import inception
from nltk.corpus import wordnet as wn

from src.classifiers.text_classification.topic_modeling_short_cnn import TopicModelingShortCNN
from src.classifiers.util.inception import dataset_utils, imagenet, inception_preprocessing
from src.config import HorusConfig
from src.core.util import definitions


class InceptionCV():
    def __init__(self, config, version='V3'):
        try:
            self.config = config
            self.config.logger.debug('loading InceptionCV')
       

            self.DIR_MODELS = config.dir_models + "/inception/"
            self.TF_MODELS_URL = "http://download.tensorflow.org/models/"
            self.INCEPTION_V3_URL = self.TF_MODELS_URL + "inception_v3_2016_08_28.tar.gz"
            self.INCEPTION_V4_URL = self.TF_MODELS_URL + "inception_v4_2016_09_09.tar.gz"
            self.INCEPTION_V3_CKPT_PATH = self.DIR_MODELS + "inception_v3.ckpt"
            self.INCEPTION_V4_CKPT_PATH = self.DIR_MODELS + "inception_v4.ckpt"

            if not tf.gfile.Exists(self.DIR_MODELS):
                tf.gfile.MakeDirs(self.DIR_MODELS)

            if not os.path.exists(self.INCEPTION_V3_CKPT_PATH):
                dataset_utils.download_and_uncompress_tarball(self.INCEPTION_V3_URL, self.DIR_MODELS)

            if not os.path.exists(self.INCEPTION_V4_CKPT_PATH):
                dataset_utils.download_and_uncompress_tarball(self.INCEPTION_V4_URL, self.DIR_MODELS)

            self.class_names = imagenet.create_readable_names_for_imagenet_labels()
            self.version = version
            tf.reset_default_graph()
            self.X = tf.placeholder(tf.float32, [None, 299, 299, 3], name="X")
            if self.version.upper() == 'V3':
                self.model_ckpt_path = self.INCEPTION_V3_CKPT_PATH
                with arg_scope(inception.inception_v3_arg_scope()):
                    # Set the number of classes and is_training parameter
                    self.logits, self.end_points = inception.inception_v3(self.X, num_classes=1001, is_training=False)

            elif self.version.upper() == 'V4':
                self.model_ckpt_path = self.INCEPTION_V4_CKPT_PATH
                with arg_scope(inception.inception_v3_arg_scope()):
                    # Set the number of classes and is_training parameter
                    # Logits
                    self.logits, self.end_points = inception.inception_v4(self.X, num_classes=1001, is_training=False)

            self.predictions = self.end_points.get('Predictions', 'No key named predictions')
            self.saver = tf.train.Saver()
            with tf.Session() as sess:
                self.saver.restore(sess, self.model_ckpt_path)
                sess.run(tf.global_variables_initializer())

        except Exception as e:
            raise e

    def process_image(self, image):
        with open(image, "rb") as f:
            image_str = f.read()

        if image.endswith('jpg'):
            raw_image = tf.image.decode_jpeg(image_str, channels=3)
        elif image.endswith('png'):
            raw_image = tf.image.decode_png(image_str, channels=3)
        else:
            self.config.logger.debug('image must be either jpg or png')
            raise Exception

        image_size = 299  # ImageNet image size, different models may be sized differently
        processed_image = inception_preprocessing.preprocess_image(raw_image, image_size,
                                                                   image_size, is_training=False)

        with tf.Session() as sess:
            #sess.run(tf.global_variables_initializer())
            raw_image, processed_image = sess.run([raw_image, processed_image])

        return raw_image, processed_image.reshape(-1, 299, 299, 3)

    def plot_color_image(self, image):
        plt.figure(figsize=(10, 10))
        plt.imshow(image.astype(np.uint8), interpolation='nearest')
        plt.axis('off')

    def predict(self, image, top=5):
        '''
        :param image: a path for an image
        :param version: inception's model version
        :return: top 10 predictions
        '''
        try:
            #tf.reset_default_graph()

            # Process the image
            raw_image, processed_image = self.process_image(image)


            # Create a placeholder for the images
            #X = tf.placeholder(tf.float32, [None, 299, 299, 3], name="X")

            '''
            inception_v3 function returns logits and end_points dictionary
            logits are output of the network before applying softmax activation
            '''
            '''
            if version.upper() == 'V3':
                model_ckpt_path = self.INCEPTION_V3_CKPT_PATH
                with arg_scope(inception.inception_v3_arg_scope()):
                    # Set the number of classes and is_training parameter
                    logits, end_points = inception.inception_v3(X, num_classes=1001, is_training=False)

            elif version.upper() == 'V4':
                model_ckpt_path = self.INCEPTION_V4_CKPT_PATH
                with arg_scope(inception.inception_v3_arg_scope()):
                    # Set the number of classes and is_training parameter
                    # Logits
                    logits, end_points = inception.inception_v4(X, num_classes=1001, is_training=False)

            predictions = end_points.get('Predictions', 'No key named predictions')
            saver = tf.train.Saver()
            '''

            with tf.Session() as sess:
                #self.saver.restore(sess, self.model_ckpt_path)
                prediction_values = self.predictions.eval({self.X: processed_image},session=sess)

            try:
                # Add an index to predictions and then sort by probability
                prediction_values = [(i, prediction) for i, prediction in enumerate(prediction_values[0, :])]
                prediction_values = sorted(prediction_values, key=lambda x: x[1], reverse=True)

                # Plot the image
                #self.plot_color_image(raw_image)
                #plt.show()
                #print("Using Inception_{} CNN\nPrediction: Probability\n".format(version))
                # Display the image and predictions
                out = []
                for i in range(0,top):
                    predicted_class = self.class_names[prediction_values[i][0]]
                    probability = prediction_values[i][1]
                    out.append((predicted_class, probability))
                    #print("{}: {:.2f}%".format(predicted_class, probability * 100))

                return out

            # If the predictions do not come out right
            except:
                raise
                #print(predictions)
        except:
            raise

    def detect_faces(self, image):
        '''
        ImageNET taxonomy: detect person?
        :param image:
        :return:
        '''
        try:
            out = self.predict(image)
            print(out)
        except Exception as e:
            self.config.logger.error(e)
            return 0

    def detect_logo(self, image):
        try:
            out = self.predict(image)
            print(out)
        except Exception as e:
            self.config.logger.error(e)
            return 0

    def detect_place(self, image):
        try:
            out = self.predict(image)
            print(out)
        except Exception as e:
            self.config.logger.error(e)
            return [0] * 10