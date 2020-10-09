from handlers.Handler import Handler

class UserHandler(Handler):
    def search(self, username):
        return set([username])
    
