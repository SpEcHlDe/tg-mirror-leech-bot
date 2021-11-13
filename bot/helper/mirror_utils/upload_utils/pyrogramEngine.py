# Implement By - @anasty17 (https://github.com/r0xtar/tg-mirror-leech-bot/commit/d888a1e7237f4633c066f7c2bbfba030b83ad616)
# (c) https://github.com/r0xtar/tg-mirror-leech-bot
# All rights reserved

import os
import logging
import time

from pyrogram.errors import FloodWait
from hachoir.parser import createParser
from hachoir.metadata import extractMetadata

from bot import app, DOWNLOAD_DIR, AS_DOCUMENT, AS_DOC_USERS, AS_MEDIA_USERS
from bot.helper.ext_utils.fs_utils import take_ss 

LOGGER = logging.getLogger(__name__)
logging.getLogger("pyrogram").setLevel(logging.WARNING)

VIDEO_SUFFIXES = ("MKV", "MP4", "MOV", "WMV", "3GP", "MPG", "WEBM", "AVI", "FLV", "M4V")
AUDIO_SUFFIXES = ("MP3", "M4A", "M4B", "FLAC", "WAV", "AIF", "OGG", "AAC", "DTS", "MID", "AMR", "MKA")
IMAGE_SUFFIXES = ("JPG", "JPX", "PNG", "GIF", "WEBP", "CR2", "TIF", "BMP", "JXR", "PSD", "ICO", "HEIC")


class TgUploader:

    def __init__(self, name=None, listener=None):
        self.__listener = listener
        self.name = name
        self.__app = app
        self.total_bytes = 0
        self.uploaded_bytes = 0
        self.last_uploaded = 0
        self.start_time = time.time()
        self.is_cancelled = False
        self.chat_id = listener.message.chat.id
        self.message_id = listener.uid
        self.user_id = listener.message.from_user.id
        self.as_doc = AS_DOCUMENT
        self.thumb = f"Thumbnails/{self.user_id}.jpg"
        self.sent_msg = self.__app.get_messages(self.chat_id, self.message_id)

    def upload(self):
        msgs_dict = {}
        path = f"{DOWNLOAD_DIR}{self.message_id}"
        self.user_settings()
        for dirpath, subdir, files in sorted(os.walk(path)):
            for file in sorted(files):
                if self.is_cancelled:
                    return
                up_path = os.path.join(dirpath, file)
                self.upload_file(up_path, file, dirpath)
                if self.is_cancelled:
                    return
                msgs_dict[file] = self.sent_msg.message_id
                self.last_uploaded = 0
        LOGGER.info(f"Leech Done: {self.name}")
        self.__listener.onUploadComplete(self.name, None, msgs_dict, None, None)

    def upload_file(self, up_path, file, dirpath):
        cap_mono = f"<code>{file}</code>"
        notMedia = False
        thumb = self.thumb
        try:
            if not self.as_doc:
                duration = 0
                if file.upper().endswith(VIDEO_SUFFIXES):
                    metadata = extractMetadata(createParser(up_path))
                    if metadata.has("duration"):
                        duration = metadata.get("duration").seconds
                    if thumb is None:
                        thumb = take_ss(up_path)
                    if self.is_cancelled:
                        return
                    if not file.upper().endswith(("MKV", "MP4")):
                        file = os.path.splitext(file)[0] + '.mp4'
                        new_path = os.path.join(dirpath, file)
                        os.rename(up_path, new_path)
                        up_path = new_path
                    self.sent_msg = self.sent_msg.reply_video(video=up_path,
                                                              quote=True,
                                                              caption=cap_mono,
                                                              parse_mode="html",
                                                              duration=duration,
                                                              width=480,
                                                              height=320,
                                                              thumb=thumb,
                                                              supports_streaming=True,
                                                              disable_notification=True,
                                                              progress=self.upload_progress)
                    if self.thumb is None and thumb is not None and os.path.lexists(thumb):
                        os.remove(thumb)
                elif file.upper().endswith(AUDIO_SUFFIXES):
                    metadata = extractMetadata(createParser(up_path))
                    if metadata.has("duration"):
                        duration = metadata.get('duration').seconds
                    title = metadata.get("title") if metadata.has("title") else None
                    artist = metadata.get("artist") if metadata.has("artist") else None
                    self.sent_msg = self.sent_msg.reply_audio(audio=up_path,
                                                              quote=True,
                                                              caption=cap_mono,
                                                              parse_mode="html",
                                                              duration=duration,
                                                              performer=artist,
                                                              title=title,
                                                              thumb=thumb,
                                                              disable_notification=True,
                                                              progress=self.upload_progress)
                elif file.upper().endswith(IMAGE_SUFFIXES):
                    self.sent_msg = self.sent_msg.reply_photo(photo=up_path,
                                                              quote=True,
                                                              caption=cap_mono,
                                                              parse_mode="html",
                                                              disable_notification=True,
                                                              progress=self.upload_progress)
                else:
                    notMedia = True
            if self.as_doc or notMedia:
                if file.upper().endswith(VIDEO_SUFFIXES) and thumb is None:
                    thumb = take_ss(up_path)
                if self.is_cancelled:
                    return
                self.sent_msg = self.sent_msg.reply_document(document=up_path,
                                                             quote=True,
                                                             thumb=thumb,
                                                             caption=cap_mono,
                                                             parse_mode="html",
                                                             disable_notification=True,
                                                             progress=self.upload_progress)
                if self.thumb is None and thumb is not None and os.path.lexists(thumb):
                    os.remove(thumb)
            if not self.is_cancelled:
                os.remove(up_path)
        except FloodWait as f:
            LOGGER.info(f)
            time.sleep(f.x)
    def upload_progress(self, current, total):
        if self.is_cancelled:
            self.__app.stop_transmission()
            return
        chunk_size = current - self.last_uploaded
        self.last_uploaded = current
        self.uploaded_bytes += chunk_size

    def user_settings(self):
        if self.user_id in AS_DOC_USERS:
            self.as_doc = True
        elif self.user_id in AS_MEDIA_USERS:
            self.as_doc = False
        if not os.path.lexists(self.thumb):
            self.thumb = None

    def speed(self):
        try:
            return self.uploaded_bytes / (time.time() - self.start_time)
        except ZeroDivisionError:
            return 0

    def cancel_download(self):
        self.is_cancelled = True
        LOGGER.info(f"Cancelling Upload: {self.name}")
        self.__listener.onUploadError('your upload has been stopped!')
