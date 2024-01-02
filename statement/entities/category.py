class Category:
    def __init__(self, type, description, color, icon, ignore, user):
        self.type = type
        self.description = description
        self.color = color
        self.icon = icon
        self.ignore = ignore
        self.user = user

    def __str__(self) -> str:
        return self.description
