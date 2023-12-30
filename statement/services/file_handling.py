import os
from django.conf import settings


class FileHandling():
    def __init__(self, file) -> None:
        self.file = file
        self.extention = file.name.split('.')[-1].lower()
        self.path = os.path.join(settings.MEDIA_ROOT, 'uploads', file.name)
        self.__handle_file()

    def __handle_file(self):
        self.__save_file()
        content = self.__read_file()
        print(content)
        self.__remove_file()

    def __save_file(self):
        with open(self.path, 'wb+') as destination:
            for chunk in self.file.chunks():
                destination.write(chunk)

    def __read_file(self):
        if self.extention == 'txt':
            with open(self.path, 'r') as file:
                content = file.read()
            return content
    
    def __remove_file(self):
        try:
            os.remove(self.path)
            print(f'Arquivo {self.file.name} removido.')
        except FileNotFoundError:
            print(f'Arquivo {self.file.name} não encontrado.')
