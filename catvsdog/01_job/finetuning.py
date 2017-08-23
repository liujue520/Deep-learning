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
        from keras.models import Sequential, Model
        from keras.layers import Input, Activation, Dropout, Flatten, Dense
        from keras import optimizers
        from keras.utils.vis_utils import plot_model
        import numpy as np


        if not os.path.exists(config.result_dir):
            os.mkdir(config.result_dir)

        # VGG16モデルと学習済み重みをロード
        # Fully-connected層（FC）はいらないのでinclude_top=False）
        input_tensor = Input(shape=(config.img_height, config.img_width, 3))
        vgg16_model = VGG16(include_top=False, weights='imagenet', input_tensor=input_tensor)
        # FC層を構築
        # Flattenへの入力指定はバッチ数を除く
        top_model = Sequential()
        top_model.add(Flatten(input_shape=vgg16_model.output_shape[1:]))
        top_model.add(Dense(256, activation='relu'))
        top_model.add(Dropout(0.5))
        top_model.add(Dense(1, activation='sigmoid'))
        # 二つのモデルを結合する
        model = Model(inputs=vgg16_model.input, outputs=top_model(vgg16_model.output))
        # 最後のconv層の直前までの層をfreeze
        for layer in model.layers[:15]:
            layer.trainable = False

        model.compile(
            loss='binary_crossentropy',
            optimizer=optimizers.SGD(lr=1e-4, momentum=0.9),
            metrics=['accuracy']
        )

        #model.summary()
        plot_model(model, to_file='model.png')

        # 訓練データを生成するジェネレータを作成
        train_datagen = ImageDataGenerator(
            rescale=1.0 / 255,
            shear_range=0.2,
            zoom_range=0.2,
            horizontal_flip=True
        )
        train_generator = train_datagen.flow_from_directory(
            config.train_dir,
            target_size=(150, 150),
            batch_size=32,
            class_mode='binary'
        )

        # 検証データを生成するジェネレータを作成
        test_datagen = ImageDataGenerator(rescale=1.0 / 255)
        validation_generator = test_datagen.flow_from_directory(
            config.validation_dir,
            target_size=(150, 150),
            batch_size=32,
            class_mode='binary'
        )

        print(train_generator.class_indices)

        # 訓練
        history = model.fit_generator(
            generator=train_generator,
            steps_per_epoch=int(np.floor(2000/32)),
            epochs=50,
            validation_data=validation_generator,
            validation_steps=int(np.floor(800/32))
        )
        utils.plot_history(history)

        # 結果を保存
        model.save(os.path.join(config.result_dir, 'finetuning_model.h5'))
        model.save_weights(os.path.join(config.result_dir, 'finetuning_weights.h5'))
        utils.save_history(history, os.path.join(config.result_dir, 'finetuning_history.txt'))

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
