import configparser
from datetime import datetime
import JenkinsResults
import logging
import os
import TestrailClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s', datefmt='%H:%M:%S')


class JenkinsTestrailResults:

    def __init__(self):
        logging.info('Initialising pushing results to Testrail.')
        config_file_path = 'config'
        self.test_group = os.environ['TEST_GROUP']
        self.jenkins_job_url = os.environ['BUILD_URL']
        self.test_server = os.environ['TEST_SERVER']
        self.config = self.get_config(config_file_path)
        self.API_client = TestrailClient.TestrailClient(
            self.config['API']['url'],
            os.environ['TESTRAIL_USERNAME'],
            os.environ['TESTRAIL_PASSWORD']
        )
        logging.info('Testing Testrail connection...')
        self.API_client.test_connection()
        logging.info('Testrail connection OK.')

    @staticmethod
    def get_config(path):
        """Reads config file from given path.

        Args:
            path (str): Path to the config file.

        Returns:
            Configparser: Object with all configuration details.
        """
        config = configparser.RawConfigParser()  #RawConfigParser, otherwise '%s' causes errors
        config.read(path)
        return config

    @staticmethod
    def get_dict_value_from_list(list, key, needle, value):
        """Gets value from list of dicts, based on value of given key.

        Args:
            list (lst): List of dicts.
            key (str): Key of dict we are searching by.
            needle (str): Value of key in dict we are searching for.
            value (value): Key in dict we want to get.

        Returns:
            string: If key with needle was found.
            bool: False If key with needle was not found.
        """
        for item in list:
            if item[key] == needle:
                return item[value]
        return False

    def add_sections_if_not_exist(self, jenkins_sections):
        """Adds sections in TestRail if they do not exist.

        Args:
            jenkins_sections (lst): List of expected sections, taken from test result.

        Returns:
            lst: List of sections in Testrail, being child of main automation sections.
        """
        def _get_testrail_sections():
            return {section.get('name'): {'id' : section.get('id')} for section in self.API_client.get_sections() if section['parent_id'] == self.API_client.automation_section_id}

        testrail_sections = _get_testrail_sections()

        not_existing_sections = list(set(jenkins_sections) - set(testrail_sections.keys()))
        if not_existing_sections:
            logging.info('Adding new sections to Testrail:')
            for section in not_existing_sections:
                logging.info(section)
                self.API_client.add_section(section, self.API_client.automation_section_id)
            return _get_testrail_sections()

        return testrail_sections

    def add_tests_if_not_exist(self, jenkins_results, testrail_sections):
        """Creates tests which do not exist in test rail sections.

        Args:
            jenkins_results (lst): Parsed Jenkins results.
            testrail_sections (lst): List of sections.

        Returns:
              lst:  List of sections with tests, including created one.
        """
        def _check_if_test_exist(jenkins_result, testrail_sections):
            """Helper to know if test exists in Testrail.

            Returns:
                bool
            """
            for testrail_tests in testrail_sections[jenkins_result['feature']]['tests']:
                for case_name in testrail_tests:
                    if jenkins_result['test_name'] == case_name:
                        return True

            return False

        def _get_testcases_for_section(id):
            """Helper to get test cases for given section.

            Returns:
                dct: Dict with lists tests in given section.
            """
            return {'tests' : [{t.get('title') : t.get('id')} for t in self.API_client.get_cases(id)]}

        # First get tests from test rail belonging to sections.
        for section_name in testrail_sections.keys():
            testrail_sections[section_name].update(_get_testcases_for_section(testrail_sections[section_name]['id']))

        missing_tests = []

        # Go over test results, and check which tests are not present in section.
        for jenkins_result in jenkins_results:
            if not _check_if_test_exist(jenkins_result, testrail_sections):
                missing_tests.append({'section' : jenkins_result['feature'], 'test_name' : jenkins_result['test_name']})

        if missing_tests:
            logging.info('Adding new tests:')

            # And now create them
            for missing_test in missing_tests:
                logging.info('Adding: ' + missing_test['test_name'])
                section_id = testrail_sections[missing_test['section']]['id']
                self.API_client.add_case(section_id, missing_test['test_name'])

            # Get again all test cases
            for section_name in testrail_sections.keys():
                testrail_sections[section_name].update(_get_testcases_for_section(testrail_sections[section_name]['id']))

        return testrail_sections

    def get_results_for_testrun(self, jenkins_results, testrail_tests):
        """Prepares data for JSON request to Testrail, to POST results.

        Args:
            jenkins_results (lst): Parsed jenkins results.
            testrail_tests (lst): - Corresponding tests from Testrail, with IDs

        Returns:
              tuple: (List of IDs, List of all results).
        """
        results = []
        ids = []
        statuses = self.get_statuses()
        for jenkins_result in jenkins_results:
            for test_case in testrail_tests[jenkins_result['feature']]['tests']:
                for test_name, id in test_case.items():
                    if test_name == jenkins_result['test_name']:
                        if jenkins_result['time'] != '0s':
                            elapsed = jenkins_result['time']
                        else:
                            elapsed = None
                        results.append({
                            'case_id'   : id,
                            'status_id' : statuses[jenkins_result['result']],
                            'comment'   : jenkins_result['message'],
                            'elapsed'   : elapsed
                        })
                        ids.append(id)

        return ids, results

    def get_new_test_run_name(self):
        """Creates new name for test run to be created in Testrail.

        Returns:
            str: New name.
        """
        now = datetime.now()
        return self.config['paths']['test_run_name'] % (now.strftime("%m/%d/%y %H:%M"), self.test_server, self.test_group)

    def get_statuses(self):
        """Helper to map Jenkins statuses to Testrail status IDs.

        Returns:
            dct: Mapping Jenkins statuses to Testrail status IDs.
        """
        status_map = {
            'passed'  : 'passed',
            'skipped' : 'blocked',
            'failure' : 'failed',
            'error'   : 'failed'
        }

        final_status_map = {}

        for jenkins_status_map, testrail_status_map in status_map.iteritems():
            for testrail_status in self.API_client.get_statuses():
                if testrail_status['name'] == testrail_status_map:
                    final_status_map[jenkins_status_map] = testrail_status['id']
                    break

        return final_status_map

    def main(self):
        """Main method for passing tests results from Jenkins to Testrail.
        It will:
        1. read and parse Jenkins results
        2. setup some variables in TestRail class
        3. add sections if they do not exist
        4. add tests if they do not exist
        5. create testrun
        6. post results

        Returns:
            bool: True.
        """
        logging.info('Parsing Jenkins results.')
        jenkins_results = JenkinsResults.JenkinsResults(self.config['paths']['xml_file'])
        results = jenkins_results.get_results()
        jenkins_sections = jenkins_results.get_section_names_from_results(results)

        logging.info('Setting up API variables.')
        self.API_client.project_id = self.get_dict_value_from_list(
            self.API_client.get_projects(),
            'name',
            self.config['paths']['project'],
            'id')

        self.API_client.suite_id = self.get_dict_value_from_list(
            self.API_client.get_suites(),
            'name',
            'Master',
            'id')

        self.API_client.automation_section_id = self.get_dict_value_from_list(
            self.API_client.get_sections(),
            'name',
            self.config['paths']['automation_section'],
            'id')

        if self.API_client.automation_section_id is False:
            self.API_client.add_section(self.config['paths']['automation_section'], None)
            self.API_client.automation_section_id = get_dict_value_from_list(
                self.API_client.get_sections(),
                'name',
                self.config['paths']['automation_section'],
                'id')

        self.API_client.set_default_case_type_id(self.config['paths']['default_type'])
        logging.info('Checking if there are new sections.')
        testrail_sections = self.add_sections_if_not_exist(jenkins_sections)
        logging.info('Checking if there are new tests.')
        testrail_tests = self.add_tests_if_not_exist(results, testrail_sections)
        logging.info('Creating test run.')
        results_for_testrun = self.get_results_for_testrun(results, testrail_tests)
        new_test_run = self.API_client.add_run(self.get_new_test_run_name(), results_for_testrun[0], self.jenkins_job_url)
        logging.info('Writing test results to test run.')
        self.API_client.add_results_for_cases(new_test_run['id'], results_for_testrun[1])
        logging.info('Finished pushing Jenkins results to Testrail to %s .' % new_test_run['url'])

        return True


if __name__ == '__main__':
    push_results = JenkinsTestrailResults()
    push_results.main()
