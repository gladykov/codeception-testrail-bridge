import pip

packages = ['configparser', 'junitparser', 'requests']

def install(packages):
    for package in packages:
        pip.main(['install', package])


if __name__ == '__main__':
    install(packages)