from PyQt5.QtWidgets import QApplication
from Application.AppResourceManager import AppResourceManager
import sys
import logging

from Communication.ConnectionHandler import ConnectionHandler
from Utils.PopUpWindow import PopUpWindow

# for windows (PowerShell):
# $env:PYTHONPATH = "."

# for UT:
# $env:PYTHONPATH = ".\Client\"
if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d](%(funcName)s) %(message)s',
        datefmt='%Y-%m-%d:%H:%M:%S',
        level=logging.DEBUG,
    )
    logging.debug('[STARTING] Client is being loaded ...')
    app = QApplication([])
    try:
        connHandler = ConnectionHandler()
    except:
        logging.debug('[SOCKET CONNECTION] Connection to server failed')
        PopUpWindow('Game server is unreachable!')
        exit()

    AppResourceManager = AppResourceManager(connHandler)
    logging.debug('[CLIENT STARTED]')
    AppResourceManager.show_start()
    app_return = app.exec_()
    connHandler.kill_receiver()
    sys.exit(app_return)
