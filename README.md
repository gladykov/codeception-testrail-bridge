# Push test results from Jenkins into TestRail, using Codeception generated Junit.XML

Simple module, to push Codeception generated Junit XML results into Testrail.
It parses results, creates test cases in Testrail if they do not exist, and pushes results to newly created test runs.

Based on few assumptions:
- you have one project per repository for automatic tests
- you have one root folder with automatic tests
- automatic tests are grouped in Testrail subsections
  - subsections names are equal to Codeception folders with tests
  - allows to iterate over smaller amount of items
  - means you cannot have same test name in files in folder
  - this combination - section name + test name should be always unique

It also contains crippled Testrail API client - no `update` and `delete` methods, only few requiered to create sections, test cases, test runs and pushing test results. Still easy to extend.

## Installation

Copy to you repo, execute `install.py` on your Jenkins node, to install required modules.

## Config

```
[API]
URL = https://project.testrail.io/index.php?/api/v2/
# Username and password stored in Jenkins, inject as TESTRAIL_USERNAME and TESTRAIL_PASSWORD

[paths]
xml_file = ../output/report.xml
project = TestRail Project
automation_section = Automated Tests Section
default_type = Automated
test_run_name = %s Jenkins test run on %s using %s group
```

Modify `test_run_name` and `get_new_test_run_name` for your needs, as it uses Jenkins variables, which differ in your environemnts.