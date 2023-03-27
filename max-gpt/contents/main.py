import os
import sys

# sys.path.append('C:/Python37/Lib/site-packages')

import openai

from pprint import pprint
from PySide2 import QtWidgets, QtGui, QtCore
from pymxs import runtime as mxs


class MaxOpenAi(QtCore.QObject):

    API_MODELS = [
        'gpt-3.5-turbo'
    ]

    LANGUAGES = [
        'maxscript', 
        'python'
    ]

    MXS_CMD_TEMPLATE = '''Write a 3ds Max maxcript script.
    - I only need the script body. Do not add any explanation.
    The task is described as follows:
    {}
    '''

    PYMXS_CMD_TEMPLATE = '''Using 3ds Max python module 'pymxs' create a python script.
    - I only need the script body. Do not add any explanation.
    - Import entire modules instead of parts
    - Do not respond with anything that is not python code.
    The task is described as follows:
    {}
    '''

    history_changed = QtCore.Signal()

    def __init__(self, api_key=''):
        super(MaxOpenAi, self).__init__()
        self._api_key = api_key
        self._history = []


    @property
    def api_key(self):
        return self._api_key
    

    @api_key.setter
    def api_key(self, value):
        self._api_key = value


    @property
    def history(self):
        return self._history


    # methods
    def append_history(self, item):
        '''
        Appends response to history
        '''
        self._history.append(item)
        self.history_changed.emit()



    def clear_history(self):
        self._history = []
        self.history_changed.emit()


    def dict_get(self, dct, keys, default=None):
        '''
        Get nested dictionary value safely from given dict
        '''
        head = keys[0]
        tail = keys[1:]
        try:
            return dict_get(dct.get(head, {}), tail, default) if tail else dct.get(head, default)
        except:
            return default


    def wrap_command(self, cmd, language='maxscript'):
        '''
        Sets context of command script request language
        '''
        if language == 'python':
            return self.PYMXS_CMD_TEMPLATE.format(cmd)
        else:
            return self.MXS_CMD_TEMPLATE.format(cmd)
    

    def fetch_command(self, cmd, language='maxscript'):
        '''
        Uses chat gpt to build and retrieve execute command
        '''
        msg = {
            'role': 'user',
            'content': self.wrap_command(cmd, language),
        }
        self.append_history(msg)

        # include history to build context
        messages = [{'role': x['role'], 'content': x['content']} for x in self._history]
        messages.append(msg)
        openai.api_key = self.api_key
        resp = openai.ChatCompletion.create(
            model='gpt-3.5-turbo',
            messages= messages,
            max_tokens=2048
        )

        if resp and 'choices' in resp:
            choice = resp['choices'][0]
            item = choice['message']
            self.append_history({
                'role': item['role'],
                'content': item['content'],
                'language': language,
                })
            
            clipboard = QtWidgets.QApplication.clipboard()
            clipboard.setText(item['content'])

            return item
        return None


    def execute_string(self, s, language='maxscript'):
        '''
        executes string command as language specified
        '''
        cmd = ''
        if language == 'python':
            cmd = 'try( python.execute("{}") )catch(print (getCurrentException()))'.format(s)
        elif language == 'maxscript':
            cmd = 'try({})catch(print (getCurrentException()))'.format(s)

        print(cmd)
        mxs.execute(cmd)


class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(SettingsDialog, self).__init__(parent)
        self.resize(400,100)
        self.setWindowTitle('Settings')
        self.settings = QtCore.QSettings('jokermartini', 'openai')

        self.uiKey = QtWidgets.QLineEdit()
        self.uiKey.setPlaceholderText('ChatGPT API generated key')
        self.uiKey.setText(self.settings.value('key', ''))

        self.uiAccept = QtWidgets.QPushButton("OK")
        self.uiCancel = QtWidgets.QPushButton("Cancel")

        self.formLayout = QtWidgets.QFormLayout()
        self.formLayout.addRow('API Key', self.uiKey)

        self.buttonLayout = QtWidgets.QHBoxLayout()
        self.buttonLayout.addStretch()
        self.buttonLayout.addWidget(self.uiAccept)
        self.buttonLayout.addWidget(self.uiCancel)

        self.mainLayout = QtWidgets.QVBoxLayout()
        self.mainLayout.addLayout(self.formLayout)
        self.mainLayout.addLayout(self.buttonLayout)

        self.setLayout(self.mainLayout)

        self.uiAccept.clicked.connect(self.accept)
        self.uiCancel.clicked.connect(self.reject) 


    def accept(self):
        self.settings.setValue('key', self.uiKey.text())
        super().accept()


class MaxAiWindow(QtWidgets.QMainWindow):

    def __init__(self, parent=None):
        super(MaxAiWindow, self).__init__(parent)
        self.resize(300,400)
        self.setWindowTitle('Max OpenAI BETA - v0.0.1')
        self.settings = QtCore.QSettings('jokermartini', 'openai')
        
        # vars
        self.ai = MaxOpenAi()
        self.ai.api_key = self.settings.value('key', '')
        self.ai.history_changed.connect(self.populate_history)

        # actions
        self.showSettingsAct = QtWidgets.QAction('Settings...', self)
        self.showSettingsAct.triggered.connect(self.show_settings)

        # controls
        self.uiHistoryView = QtWidgets.QTextEdit()
        self.uiHistoryView.setReadOnly(True)

        self.uiLanauge = QtWidgets.QComboBox()
        self.uiLanauge.addItems(['maxscript', 'python'])

        self.uiInput = QtWidgets.QPlainTextEdit()
        self.uiInput.setPlaceholderText('Type your request...')
        self.uiInput.setPlainText('create a box')
        self.uiInput.textChanged.connect(self.update_controls)

        self.uiClear = QtWidgets.QPushButton('Clear')
        self.uiClear.setToolTip('Clears conversation history')
        self.uiClear.clicked.connect(self.ai.clear_history)

        self.uiFetch = QtWidgets.QPushButton('Fetch')
        self.uiFetch.setToolTip('Fetches request code and appends to history, does not execute.')
        self.uiFetch.clicked.connect(self.fetch_request)

        self.uiExecute = QtWidgets.QPushButton('Execute')
        self.uiExecute.setToolTip('Fetches request code and immediately executes it.')
        self.uiExecute.clicked.connect(self.execute_request)

        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self.splitter.addWidget(self.uiInput)
        self.splitter.addWidget(self.uiHistoryView)

        self.buttonLayout = QtWidgets.QHBoxLayout()
        self.buttonLayout.addWidget(self.uiClear)
        self.buttonLayout.addStretch()
        self.buttonLayout.addWidget(self.uiFetch)
        self.buttonLayout.addWidget(self.uiExecute)

        self.mainLayout = QtWidgets.QVBoxLayout()
        self.mainLayout.addWidget(self.uiLanauge)
        self.mainLayout.addWidget(self.splitter)
        self.mainLayout.addLayout(self.buttonLayout)

        self.mainWidget = QtWidgets.QWidget()
        self.mainWidget.setLayout(self.mainLayout)
        self.setCentralWidget(self.mainWidget)

        # menu
        self.mainMenu = QtWidgets.QMenu('File', self)
        self.mainMenu.addAction(self.showSettingsAct)        

        self.menuBar().addMenu(self.mainMenu)

        self.update_controls()
        self.statusBar().showMessage('Ready...', 3000)
        self.populate_history()


    def update_controls(self):
        state = bool(self.uiInput.toPlainText().strip())
        self.uiFetch.setEnabled(state)
        self.uiExecute.setEnabled(state)


    def show_settings(self):
        dlg = SettingsDialog(self)
        res = dlg.exec()
        if res:
            self.ai.api_key = self.settings.value('key', '')


    def valid(self):
        if not self.settings.value('key', ''):
            QtWidgets.QMessageBox.warning(self, 'Error', 'An API Key is required. Please create a key from your account page https://platform.openai.com/account/api-keys and insert into the settings dialog of this tool before continuing.')
            return False
        return True


    def fetch_request(self):
        if not self.valid():
            return
        self.statusBar().showMessage('Fetching command...')
        QtCore.QCoreApplication.processEvents()
        self.ai.fetch_command(self.uiInput.toPlainText(), language=self.uiLanauge.currentText())
        self.statusBar().showMessage('Fetching complete!', 3000)


    def execute_request(self):
        if not self.valid():
            return
        self.statusBar().showMessage('Fetching command...')
        QtCore.QCoreApplication.processEvents()
        self.ai.fetch_command(self.uiInput.toPlainText(), language=self.uiLanauge.currentText())
        
        item = self.ai.history[-1]
        if item:
            self.ai.execute_string(item['content'], item['language'])

        self.statusBar().showMessage('Execution complete!', 3000)


    def populate_history(self):
        self.uiHistoryView.clear()

        html = ''
        for item in self.ai.history:
            txt = ''
            if item['role'] == 'assistant':
                txt = '''
                    <div>
                        <b style='color:#4caf50'>{role}</b> - ({lang})
                        <pre>{content}</pre>
                    <div>
                '''.format(role=item['role'], lang=item['language'], content=item['content'])
            elif item['role'] == 'user':
                txt = '''
                    <div>
                        <b style='color:#2196f3'>{role}</b>
                        <p>{content}</p>
                    <div>
                '''.format(role=item['role'], content=item['content'])

            html += txt

        self.uiHistoryView.setHtml(html)
        scrollbar = self.uiHistoryView.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())


def main():
    win = QtWidgets.QWidget.find(mxs.windows.getMAXHWND())
    dlg = MaxAiWindow(parent=win)
    # dlg = SettingsDialog(parent=win)
    dlg.show()


if __name__ == '__main__':
    main()

    # key = '###'
    # ai = MaxOpenAi(api_key=key)
    # ai.fetch_command('create a grid of teapots')
    # ai.fetch_command('assign a random wirecolor to each teapot', language='python')
    # ai.fetch_command('create a python class called Person with the properties age, name, location', language='python')
    # resp = ai.fetch_command('create a box', language='python')
    # resp = ai.fetch_command('create a python class Person with Age, Location and Name', language='python')
    # if resp:
        # print(resp)
        # ai.execute_string(resp['content'], 'python')
        # ai.execute_string('import os', 'python')
        # ai.execute_string('this is wrong', 'python')
    # pprint(ai.history)
