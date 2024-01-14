class Flag:
    def __init__(self, description, icon):
        self.description = description
        self.icon = icon

    def __str__(self) -> str:
        return self.description
