

class ChatUser:
    def __init__(self, username: str):
        self.username: str = username
        self.is_leave: bool = False
    
    def leave_room(self) -> None:
        self.is_leave = True
