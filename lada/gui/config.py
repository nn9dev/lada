import logging
import json
import os
from pathlib import Path
from appdirs import user_config_dir

from lada import MODEL_WEIGHTS_DIR, LOG_LEVEL

logger = logging.getLogger(__name__)
logging.basicConfig(level=LOG_LEVEL)

MODEL_FILES_TO_NAMES = {
    os.path.join(MODEL_WEIGHTS_DIR, 'lada_mosaic_restoration_model_generic.pth'): 'basicvsrpp-generic-1.0',
    os.path.join(MODEL_WEIGHTS_DIR, 'lada_mosaic_restoration_model_generic_v1.1.pth'): 'basicvsrpp-generic-1.1',
    os.path.join(MODEL_WEIGHTS_DIR, 'lada_mosaic_restoration_model_generic_v1.2.pth'): 'basicvsrpp-generic-1.2',
    os.path.join(MODEL_WEIGHTS_DIR, '3rd_party', 'clean_youknow_video.pth'): 'deepmosaics-clean-youknow',
}

MODEL_NAMES_TO_FILES = {v: k for k, v in MODEL_FILES_TO_NAMES.items()}


class Config:
    def __init__(self):
        self.preview_mode = None
        self.mosaic_restoration_model = None
        self.export_codec = None
        self.export_crf = None
        self.preview_buffer_duration = None
        self.max_clip_duration = None
        self.device = None
        self.mute_audio = None

        self.set_defaults()

    def set_defaults(self):
        self.preview_mode = 'mosaic-removal'
        self.mosaic_restoration_model = self.get_default_restoration_model()
        self.export_codec = 'h264'
        self.export_crf = 20
        self.preview_buffer_duration = 0
        self.max_clip_duration = 180
        self.device = 'cuda:0'
        self.mute_audio = False

    def get_default_restoration_model(self):
        return 'basicvsrpp-generic-1.2'

    def save(self):
        config_file_path = get_config_file_path()
        if not config_file_path.parent.exists():
            config_file_path.parent.mkdir(parents=True)
        with open(config_file_path, 'w') as f:
            config_dict = self._as_dict()
            json.dump(config_dict, f)
            logger.info(f"saved config file {config_file_path}: {config_dict}")

    def load_config(self):
        config_file_path = get_config_file_path()
        success = False
        if not config_file_path.exists():
            logger.info(f"config file doesnt exist at f{config_file_path}")
        else:
            try:
                with open(config_file_path, 'r') as f:
                    config_dict = json.load(f)
                    self._from_dict(config_dict)
                    logger.info(f"loaded config file {config_file_path}: {config_dict}")
                    success = True
            except Exception as e:
                logger.error(f"error loading config file {config_file_path}, fall back to defaults: {e}")
                self.set_defaults()
        if not success:
            self.save()

    def _as_dict(self) -> dict:
        return dict(
            preview_mode=self.preview_mode,
            mosaic_restoration_model=self.mosaic_restoration_model,
            export_codec=self.export_codec,
            export_crf=self.export_crf,
            preview_buffer_duration=self.preview_buffer_duration,
            max_clip_duration=self.max_clip_duration,
            device=self.device,
            mute_audio=self.mute_audio
        )

    def _from_dict(self, dict):
        def update_prop(key):
            if key in dict and dict[key] is not None:
                setattr(self, key, dict[key])

        update_prop('preview_mode')
        update_prop('mosaic_restoration_model')
        update_prop('export_codec')
        update_prop('export_crf')
        update_prop('preview_buffer_duration')
        update_prop('max_clip_duration')
        update_prop('device')
        update_prop('mute_audio')


def get_config_file_path() -> Path:
    config_dir = user_config_dir('lada', appauthor=False)
    return Path(config_dir).joinpath('lada.conf')
