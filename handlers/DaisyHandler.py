import requests
from datetime import datetime

class DaisyHandler:
    def __init__(self, config):
        self.auth = (config['user'], config['password'])
        self.url = config['url'].rstrip('/')

    def search(self, query):
        if query == 'students':
            return self.getCurrentStudents()
        else:
            raise Exception('Invalid argument: {}'.format(query))

    def getSemesterStudents(self, semester, distance=False):
        params = {'department': 4,
                  'realm': 'SU.SE',
                  'offCampusCourses': distance,
                  'semester': semester}
        requestpath = '{}/student/registeredStudents'.format(self.url)
        r = requests.get(requestpath, params=params, auth=self.auth)
        if r.status_code == 200:
            return r.json()
        return False

    def getCurrentStudents(self):
        now = datetime.now()
        year = now.year
        term = 1
        if now.month >= 7:
            term = 2
        valid_semesters = []
        for i in range(0, 10):
            valid_semesters.append('{}{}'.format(year, term))
            if term == 2:
                term = 1
            else:
                year -= 1
                term = 2
        active_students = set()
        for semester in valid_semesters:
            active_students.update(self.getSemesterStudents(semester))
            active_students.update(self.getSemesterStudents(semester, distance=True))
        return active_students
