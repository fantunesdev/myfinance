class Bank:
    def __init__(self, description, code, icon):
        self.description = description
        self.code = code
        self.icon = icon

    def __str__(self) -> str:
        return self.description
