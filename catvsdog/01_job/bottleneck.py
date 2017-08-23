#coding=utf-8
import os
import utils
import config
import traceback
import logging.config
from luna import LunaExcepion


logging.config.fileConfig("logging.conf")
logger = logging.getLogger()


if __name__ == '__main__':
    try:
        logger.info("------ start ------")
        utils.lock()


        from keras.applications.vgg16 import VGG16
        from keras.preprocessing.image import ImageDataGenerator
        from keras.models import Sequential
        from keras.layers import Activation, Dropout, Flatten, Dense
        from keras import optimizers
        from keras.utils.vis_utils import plot_model
        import numpy as np


        if not os.path.exists(config.result_dir):
            os.mkdir(config.result_dir)

        # VGG16モデルと学習済み重みをロード
        # Fully-connected層（FC）はいらないのでinclude_top=False）
        model = VGG16(include_top=False, weights='imagenet')
        # model.summary()

        # 訓練データを生成するジェネレータを作成
        train_datagen = ImageDataGenerator(rescale=1.0 / 255)
        train_generator = train_datagen.flow_from_directory(
            config.train_dir,
            target_size=(150, 150),
            batch_size=32,
            class_mode=None,
            shuffle=False
        )
        # ジェネレータから生成される画像を入力し、VGG16の出力をファイルに保存
        bottleneck_features_train = model.predict_generator(train_generator, 2000/32)
        np.save(os.path.join(config.result_dir, 'bottleneck_features_train.npy'), bottleneck_features_train)

        # 検証データを生成するジェネレータを作成
        test_datagen = ImageDataGenerator(rescale=1.0 / 255)
        validation_generator = test_datagen.flow_from_directory(
            config.validation_dir,
            target_size=(150, 150),
            batch_size=32,
            class_mode=None,
            shuffle=False
        )
        # ジェネレータから生成される画像を入力し、VGG16の出力をファイルに保存
        bottleneck_features_validation = model.predict_generator(validation_generator, 800/32)
        np.save(os.path.join(config.result_dir, 'bottleneck_features_validation.npy'), bottleneck_features_validation)

        # print(train_generator.class_indices)

        # 訓練データをロード
        # ジェネレータではshuffle=Falseなので最初の1000枚がcat、次の1000枚がdog
        train_data = np.load(os.path.join(config.result_dir, 'bottleneck_features_train.npy'))
        train_labels = np.array([0] * int(2000 / 2) + [1] * int(2000 / 2))

        # バリデーションデータをロード
        validation_data = np.load(os.path.join(config.result_dir, 'bottleneck_features_validation.npy'))
        validation_labels = np.array([0] * int(800 / 2) + [1] * int(800 / 2))

        # FCネットワークを構築
        model = Sequential()
        model.add(Flatten(input_shape=train_data.shape[1:]))
        model.add(Dense(256, activation='relu'))
        model.add(Dropout(0.5))
        model.add(Dense(1, activation='sigmoid'))

        model.compile(
            loss='binary_crossentropy',
            optimizer=optimizers.SGD(lr=1e-4, momentum=0.9),
            metrics=['accuracy']
        )

        #model.summary()
        plot_model(model, to_file='model.png')

        # 訓練
        history = model.fit(
            train_data,
            train_labels,
            batch_size=32,
            epochs=50,
            validation_data=(validation_data, validation_labels)
        )
        utils.plot_history(history)

        # 結果を保存
        model.save(os.path.join(config.result_dir, 'bottleneck_model.h5'))
        model.save_weights(os.path.join(config.result_dir, 'bottleneck_weights.h5'))
        utils.save_history(history, os.path.join(config.result_dir, 'bottleneck_history.txt'))

    except (KeyboardInterrupt, SystemExit):
        utils.unlock()
        utils.error(config.syserr)
    except LunaExcepion as e:
        utils.error(e.value)
        if (e.value == config.locked):
            exit()
            logger.info("------ end ------")
    except Exception as e:
        logger.error(e)
        logger.error(traceback.format_exc())
        utils.error(config.syserr)
    utils.unlock()
    logger.info("------ end ------")
