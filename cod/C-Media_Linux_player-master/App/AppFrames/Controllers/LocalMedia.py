import os
import requests
import threading

from PySide6 import QtCore

from ..Event import Event

class LocalMedia(QtCore.QObject):
    def __init__(self):
        super().__init__()
        self.download_path = os.path.expanduser('~')+"/C-Media_Player/Media/"
        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path)
        self.thread = None
        self.event = Event("")

    def download_media(self, urls):  
        for url in urls:
            try:  
                filename = url.split('/')[-1]
                filepath = os.path.join(self.download_path, filename)
                with requests.get(url, stream=True) as r:
                    r.raise_for_status()
                    with open(filepath, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
                return filepath
            except Exception as e:
                print(e)
                return None
    QtCore.Slot(list)
    def get_local_media(self, urls):
        local = {}
        download = []
        for url in urls:
            filename = url.split('/')[-1]
            filepath = os.path.join(self.download_path, filename)
            if os.path.exists(filepath):
                local[url] = filepath
            else:
                local[url] = url
                download.append(url)
            self.thread = threading.Thread(target=self.download_media, args=(download, ))
            self.thread.start()
        return local
    
    def get_event(self):
        return self.event


"""
lm = LocalMedia()
print(lm.get_local_media([
    "https://be2719.rcr22.ams01.cdn112.com/download/01/06359/1an0e8sc560r_n/270134%20f3ff8ba7%20a93d%204287%20b804%20339600d0f333%20cnte%202364111%20filemoon%20mp4?t=XGvI9xOmFNBYOZHadgMy4tekHuSyqFzY34Ge6GtYKEk&s=1718569666&e=43200&f=31799244&srv=01&asn=10620&sp=500",
    "https://urd2afmyvrjt.enaak-cdn.com/v/01/01858/cxa5xep516za_n/269614--8b28ce53-c5a4-4df7-8f56-9f6bba608dbb--sdft--2359368-vidhide.mp4?t=t4bYMnOoWyFXYC83WqZqDQl9UgNOlTVu1nQmaBnoq3U&s=1718571148&e=129600&f=9291942&sp=400&i=181.50"
    ]))

"""