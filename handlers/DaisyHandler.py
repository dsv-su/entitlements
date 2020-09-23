import requests
from datetime import datetime

class DaisyHandler:
    def __init__(self, config):
        self.auth = (config['user'], config['password'])
        self.headers = {'Accept': 'application/json'}
        self.url = config['url'].rstrip('/')

    def _get(self, path, params={}):
        requestpath = '{}{}'.format(self.url, path)
        r = requests.get(requestpath,
                         params,
                         headers=self.headers,
                         auth=self.auth)
        if not r.status_code == 200:
            raise Exception('Got bad response from Daisy API: {}'
                            .format(r.status_code))
        return r.json()

    def search(self, query):
        if query == 'students':
            return self._getCurrentStudents()
        elif query.startswith('course:'):
            _, _, course = query.partition(':')
            return self._getCourseParticipants(course)
        else:
            raise Exception('Invalid argument: {}'.format(query))

    def _getSemesterStudents(self, semester):
        params = {'department': 4,
                  'realm': 'SU.SE',
                  'includeReregs': True,
                  'semester': semester}
        return self._get('/student/registeredStudents', params=params)

    def _getCurrentStudents(self):
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
            active_students.update(self._getSemesterStudents(semester))
        return active_students

    def _getCourseParticipants(self, courseId):
        requestpath = '/courseSegment/{}/participants'.format(courseId)
        json = self._get(requestpath, params={'realm':'SU.SE'})
        usernames = set([item['userName'] for item in json])
        return usernames
