import requests


class TestrailClient:
    """Simple TestRail client using requests."""

    def __init__(self, url, username, password):
        """
        Prepares class wide variables. It is filled in main.py based on `config` file.
            project_id - id of the project, where automatic tests should be kept.
            automation_section_id - section in project containing other sub sections with automatic tests
            suite_id - needed in API requests, not important unless in multi suite environment.

        Args:
            url (str): API url
            username (str): API username
            password (str): API password
        """
        self.url = url
        self.username = username
        self.password = password
        self.headers = {'Content-Type' : 'application/json'}
        self.project_id = None
        self.suite_id = None
        self.automation_section_id = None
        self.automated_case_type_id = None

    def _request(self, path, payload = None):
        url = self.url + path
        if payload is not None:  # POST
            r = requests.post(url, headers=self.headers, auth=(self.username, self.password), json=payload)
        else:  # GET
            r = requests.get(url, headers=self.headers, auth=(self.username, self.password))
        assert(r.status_code == 200)
        return r.json()

    def _get_request(self, path):
        return self._request(path)

    def _post_request(self, path, payload):
        return self._request(path, payload)

    def test_connection(self):
        assert(requests.get(self.url + 'get_projects', headers=self.headers, auth=(self.username, self.password)).status_code == 200)

    def get_projects(self):
        return self._get_request('get_projects')

    def get_suites(self):
        return self._get_request('get_suites/%i' % self.project_id)

    def get_suite(self):
        return self._get_request('get_suite/$i' % self.suite_id)

    def get_sections(self):
        return self._get_request('get_sections/%i&suite_id=%i' % (self.project_id, self.suite_id))

    def add_section(self, name, parent_id):
        payload = {'name' : name, 'parent_id' : parent_id, 'suite_id' : self.suite_id, 'description' : name}
        return self._post_request('add_section/%i' % self.project_id, payload)

    def get_cases(self, section_id):
        return self._get_request('get_cases/%i&suite_id=%i&section_id=%i' % (self.project_id, self.suite_id, section_id))

    def add_case(self, section_id, title):
        payload = {'title' : title, 'type_id' : self.automated_case_type_id}
        return self._post_request('add_case/%i' % section_id, payload)

    def get_case_types(self):
        return self._get_request('get_case_types')

    def set_default_case_type_id(self, case_type_name):
        for type in self.get_case_types():
            if type['name'] == case_type_name:
                self.automated_case_type_id = type['id']
                break

    def add_run(self, name, case_ids, description = None):
        payload = {'name' : name, 'case_ids' : case_ids, 'description' : description, 'include_all' : False}
        return self._post_request('add_run/%i' % self.project_id, payload)

    def get_statuses(self):
        return self._get_request('get_statuses')

    def add_results_for_cases(self, run_id, results):
        payload = {'results' : results}
        return self._post_request('add_results_for_cases/%i' % run_id, payload)
