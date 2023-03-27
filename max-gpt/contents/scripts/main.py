import os
import sys
import re
from pymxs import runtime as mxs


macro_mxs_template = '''
    try(
        macroScript JokerMartini_{uid} category:"{category}" tooltip:"{name}" buttonText:"{name}"
        (
            local filepath = pathConfig.normalizePath @"{filepath}"
            if doesFileExist filepath then
            (
                filein filepath
            )
            else
            (
                messagebox \"The file or script is missing!\"
            )
        )
    )catch(
        format "*** % ***\n" (getCurrentException())
    )
'''

macro_python_template = '''
    try(
        macroScript {uid} category:"{category}" tooltip:"{name}" buttonText:"{name}"
        (
            local filepath = pathConfig.normalizePath @"{filepath}"
            if doesFileExist filepath then
            (
                python.executeFile filepath
            )
            else
            (
                messagebox \"The file or script is missing!\"
            )
        )
    )catch(
        format "*** % ***\n" (getCurrentException())
    )
'''


def create_macroscript_for_file(category, name, filepath):
    '''
    Creates a macroscript for maxscript or python file.
    The name will be formatted to replace all spaces with underscores.
    If the name is not supplied it uses the name of the file

    Returns (string):
        The macroscript's unique name
    '''
    if not os.path.isfile(filepath):
        log.warning('Missing file {}'.format(filepath))
        return None

    ext = os.path.splitext(os.path.basename(filepath))[-1].lower()

    # Remove Invalid Chars [A-z0-9_]
    safe_name = re.sub(r'\W+', '_', name.title())
    uid = '_'.join([category, safe_name])
    text = uid.replace('_', ' ')

    # Create command for click action
    if ext in ['.ms', '.mse', '.mcr', '.mzp']:
        cmd = macro_mxs_template.format(uid=uid, category=category, name=name, filepath=filepath)
        mxs.execute(cmd)
    elif ext in ['.py', '.pyc']:
        cmd = macro_python_template.format(uid=uid, category=category, name=name, filepath=filepath)
        mxs.execute(cmd)
    else:
        log.warning('Invalid file format {}'.format(filepath))
    return uid


def main():
	contents = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
	
	sitePackages = os.path.join(contents, 'site-packages')
	sys.path.append(sitePackages)
	
	filepath = os.path.join(contents, 'main.py')
	create_macroscript_for_file('JokerMartini', 'MaxGPT', filepath)


if __name__ == '__main__':
	main()
