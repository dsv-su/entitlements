from handlers.Handler import Handler

class NoneHandler(Handler):
    def search(self, query):
        return set()
    
