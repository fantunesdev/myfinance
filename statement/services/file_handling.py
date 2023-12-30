import os
from django.conf import settings


class FileHandling():
    def __init__(self, file) -> None:
        self.file = file
        self.extention = file.name.split('.')[-1].lower()
        self.path = os.path.join(settings.MEDIA_ROOT, 'uploads', file.name)
        self.__save_file()

    def __save_file(self):
        print(self.extention)
        with open(self.path, 'wb+') as destination:
            for chunk in self.file.chunks():
                destination.write(chunk)

    def read_file(self):
        with open(self.path, 'r') as file:
            content = file.read()
            print(content)