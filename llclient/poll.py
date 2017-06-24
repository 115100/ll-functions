"""Logic for polling and uploading files to load link."""
import argparse
import glob
from os.path import basename, expanduser, isfile, splitext
import os
import struct
import subprocess
import tempfile
from time import sleep
import wave

from wand.image import Image
import numpy
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

from .service import Service

PATTERNS = [
    '*.flac',
    '*.jpg',
    '*.jpeg',
    '*.json',
    '*.mkv',
    '*.mp3',
    '*.mp4',
    '*.png',
    '*.torrent',
    '*.txt',
    '*.wav',
]

class _UploadHandler(PatternMatchingEventHandler):
    def __init__(self, args, patterns,
                 ignore_patterns=None, case_sensitive=False, ignore_directories=True):
        super(_UploadHandler, self).__init__(
            patterns=patterns,
            ignore_patterns=ignore_patterns,
            ignore_directories=ignore_directories,
            case_sensitive=case_sensitive
        )
        self.service = Service()

        self.base_dir = args.base_dir
        self.volume = args.volume
        self.sound = None
        self.new_wav = None

        try:
            os.makedirs(args.base_dir, 0o755)
        except os.error:
            pass
        self._init_sound()
        self._reprocess()

    def on_created(self, event):
        sleep(1) # Assume file takes at most 1s to finish writing
        self._upload_file(event.src_path)

    def cleanup(self):
        """Remove temporary files."""
        if self.new_wav:
            os.remove(self.new_wav)

    def _upload_file(self, path):
        ul_fn = path

        _, ext = splitext(path)
        if ext == '.png':
            _, tmp_fn = tempfile.mkstemp()
            with Image(filename=path) as img:
                img.compression_quality = 9
                img.save(filename=tmp_fn)
            ul_fn = tmp_fn
            os.remove(path)

        link = self.service.upload(ul_fn, basename(path))
        os.remove(ul_fn)

        print('\nUploaded {} to {}'.format(path, link))
        subprocess.Popen('echo -n %s | xclip -selection clipboard' % link, shell=True)
        if self.sound:
            subprocess.Popen('aplay -q ' + self.sound, shell=True)


    def _init_sound(self):
        wav_loc = expanduser('~/.config/llclient/completed.wav')
        if not isfile(wav_loc):
            print('No completed.wav found. '
                  'If you\'d like to play a sound on upload, '
                  'place a wav file at ~/.config/llclient/completed.wav.')
            return

        self.sound = wav_loc
        if self.volume == 100:
            return

        old_wave = wave.open(wav_loc, 'rb')
        params = old_wave.getparams()
        sound = old_wave.readframes(params.nframes)
        old_wave.close()

        sound = numpy.fromstring(sound, numpy.int16) * (self.volume / 100)
        sound = struct.pack('h' * len(sound), *sound.astype(int))

        _, new_wave_filename = tempfile.mkstemp()
        new_wave = wave.open(new_wave_filename, 'wb')
        new_wave.setparams(params)
        new_wave.writeframes(sound)
        new_wave.close()

        self.new_wav = new_wave_filename
        self.sound = new_wave_filename

    def _reprocess(self):
        for pattern in PATTERNS:
            for file_path in glob.glob(os.path.join(self.base_dir, pattern)):
                self._upload_file(file_path)


def main(): # pylint: disable=missing-docstring
    args = _parse_args()
    handler = _UploadHandler(args, patterns=';'.join(PATTERNS))
    observer = Observer()
    observer.schedule(handler, path=args.base_dir)
    observer.start()

    try:
        while True:
            sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        observer.join()
        handler.cleanup()
        raise

def _parse_args():
    parser = argparse.ArgumentParser(description='Upload all files in dir to '
                                                 'load_link server.')
    parser.add_argument('-b', '--base',
                        dest='base_dir',
                        help='Base directory to upload.',
                        required=True,
                       )
    parser.add_argument('--volume',
                        dest='volume',
                        type=int,
                        default=100,
                        help='Sound notification volume.',
                       )
    return parser.parse_args()