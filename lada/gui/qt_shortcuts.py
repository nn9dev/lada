from PyQt6.QtCore import QObject

class ShortcutsManager(QObject):
    def __init__(self):
        super().__init__()
        self.groups = {}
        self.shortcuts = {}
    
    def register_group(self, name: str, title: str):
        self.groups[name] = title
    
    def add(self, group: str, name: str, key: str, callback, description: str):
        if group not in self.groups:
            raise ValueError(f"Group {group} not registered")
        
        if group not in self.shortcuts:
            self.shortcuts[group] = {}
        
        self.shortcuts[group][name] = {
            'key': key,
            'callback': callback,
            'description': description
        } 