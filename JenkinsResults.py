from junitparser import JUnitXml, Attr, TestCase


class MyTestCase(TestCase):
    """Helper class to read extra attributes from XML file."""
    file = Attr()

class JenkinsResults:
    """Parses and retrieves data from Codeception generated junit XML files."""

    def __init__(self, path):
        """Initiates JUniXML object.

        Args:
            path (str): Path to XML file
        """
        self.junit_results = JUnitXml.fromfile(path)

    def get_results(self):
        """Parses results.

        Returns:
            lst: List of dicts, where every dicts is one test result.
        """

        def _get_test_case_name(separator, *strings):
            """Helper to create test name.

            Args:
                separator (str): Separator between string parts of test name.
                *strings (str): Strings to be joined

            Returns:
                str: Test case name, to be used in TestRail.
            """
            testname = ''
            for string in strings:
                testname += string + separator

            return testname[:-1]

        parsed_results = []
        for suite in self.junit_results:
            for case in suite:
                case = MyTestCase.fromelem(case)
                file_path_list = case.file.split('/')
                feature = file_path_list[-2]
                subsection = file_path_list[-1].replace('Cest.php', '')
                test_name = _get_test_case_name('.', subsection, case.name)
                time = str(int(round(case.time))) + 's'
                message = ''

                if case.result is not None:
                    result = case.result._tag
                    if case.result._tag != 'skipped':
                        message = case.result._elem.text
                else:
                    result = 'passed'

                parsed_results.append({
                    'result'     : result,
                    'feature'    : feature,
                    'subsection' : subsection,
                    'test_name'  : test_name,
                    'message'    : message,
                    'time'       : time
                })

        return parsed_results

    @staticmethod
    def get_section_names_from_results(results):
        """Get all section names, by iterating over parsed result.

        Args:
            results (lst): Parsed list of results, with every test case represented by one dict.

        Returns:
              lst: List of unique section names in test result.
        """
        section_names = []
        for result in results:
            section_names.append(result['feature'])
        return list(set(section_names))
