from PyQt5.QtCore import QObject, QRunnable, QThreadPool, Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QSplitter,
    QTextEdit,
    QToolBar,
    QVBoxLayout,
    QWidget
)
import sys, os, socket

class ServerSignals(QObject):
    serverListening = pyqtSignal(tuple)
    clientConnected = pyqtSignal(object, tuple)

class Server(QRunnable):
    def __init__(self):
        QRunnable.__init__(self)
        self.sock = None
        self.serverSignals = ServerSignals()

    @pyqtSlot()
    def run(self):
        self.sock = socket.create_server(("0.0.0.0", 8224))
        while True:
            conn, addr = self.sock.accept()
            self.serverSignals.clientConnected.emit(conn, addr)

class DataReceptionSignals(QObject):
    received_or_fail = pyqtSignal(dict, object)

class DataReception(QRunnable):
    def __init__(self, conn):
        QRunnable.__init__(self)
        self.sock = conn
        self.signals = DataReceptionSignals()
    
    @pyqtSlot()
    def run(self):
        while True:
            try:
                data = self.sock.recv(1024)
                self.signals.received_or_fail.emit({"error": False, "data": data.decode()}, self.sock)
            except Exception as e:
                self.signals.received_or_fail.emit({"error": True, "error_message": str(e)}, self.sock)

class MainWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.setWindowTitle("Terror")
        self.source_dir = os.path.abspath(os.path.dirname(__file__))
        self.icon = QIcon(os.path.join(self.source_dir, "images/scream.ico"))
        self.setWindowIcon(self.icon)
        self.setWindowOpacity(1.0)
        self.connections = []
        self.messages = []

        #Backend
        self.threadPool = QThreadPool()
        self.threadPool.setMaxThreadCount(20)

        self.server = Server()
        self.server.serverSignals.clientConnected.connect(self.add_to_connections)
        self.threadPool.start(self.server)

        #Toolbar
        self.toolBar = QToolBar()
        self.addToolBar(self.toolBar)
        self.toolBar.addAction(QIcon(os.path.join(self.source_dir, "images/connection.svg")), "Connect").triggered.connect(self.ConnectDialog)

        #Central Widget and base layout and splitter
        self.central = QWidget()
        self.setCentralWidget(self.central)

        self.base_layout = QVBoxLayout()
        self.central.setLayout(self.base_layout)

        self.splitter = QSplitter()
        self.base_layout.addWidget(self.splitter)

        #first and second splitter base widgets
        self.messages_widget = QWidget()
        self.splitter.addWidget(self.messages_widget)
        self.messages_widget_layout = QVBoxLayout()
        self.messages_widget.setLayout(self.messages_widget_layout)

        self.second_widget = QWidget()
        self.splitter.addWidget(self.second_widget)
        self.second_widget_layout = QVBoxLayout()
        self.second_widget.setLayout(self.second_widget_layout)

        self.connections_widget = QWidget()
        self.splitter.addWidget(self.connections_widget)
        self.connections_widget_layout = QVBoxLayout()
        self.connections_widget.setLayout(self.connections_widget_layout)

        #Messages list widget
        self.messages_heading = QLabel(text="Messages")
        self.messages_widget_layout.addWidget(self.messages_heading)
        self.messages_list_widget = QListWidget()
        self.messages_list_widget.currentRowChanged.connect(self.read_message)
        self.messages_widget_layout.addWidget(self.messages_list_widget)

        #Connections list widget
        self.connections_heading = QLabel(text="Connections")
        self.connections_widget_layout.addWidget(self.connections_heading)
        self.connections_list_widget = QListWidget()
        self.connections_list_widget.itemClicked.connect(self.write_messageDialog)
        self.connections_widget_layout.addWidget(self.connections_list_widget)
        self.show_connections()

        #Message view
        self.text_view = QTextEdit()
        self.text_view.setReadOnly(True)
        self.second_widget_layout.addWidget(self.text_view)

        self.reply_button = QPushButton(text="Reply")
        self.reply_button.clicked.connect(lambda: self.reply_messageDialog(self.messages_list_widget.currentItem()))
        self.reply_button.setIcon(QIcon(os.path.join(self.source_dir, "images/reply.svg")))
        self.second_widget_layout.addWidget(self.reply_button)
    
    def test(self):
        print(self.messages_list_widget.currentItem())
    #Dialogs
    ##Reply message dialog
    def reply_messageDialog(self, item=None):
        if item != None:
            index = self.messages_list_widget.indexFromItem(item).row()
            m = self.messages[index]
            dlg = QDialog()
            dlg.setWindowTitle("Reply message")
            dlg.setWindowIcon(self.icon)

            layout = QVBoxLayout()
            dlg.setLayout(layout)

            receiver_addr = m["conn"].getpeername()[0]+":"+str(m["conn"].getpeername()[1])
            receiver_addr_label = QLabel(text=receiver_addr)
            layout.addWidget(receiver_addr_label)

            layout.addWidget(QLabel(text="Message:"))

            text_edit = QTextEdit()
            layout.addWidget(text_edit)

            send_button = QPushButton(text="Send", icon=QIcon(os.path.join(self.source_dir, "images/send.svg")))
            layout.addWidget(send_button)
            send_button.clicked.connect(dlg.accept)

            buttonBox = QDialogButtonBox(QDialogButtonBox.Cancel)
            buttonBox.rejected.connect(dlg.reject)
            layout.addWidget(buttonBox)

            dlg.accepted.connect(lambda: self.send_message(m["conn"], text_edit.toHtml()))

            dlg.exec_()

    ##Write message dialog
    def write_messageDialog(self, item=None):
        if item != None:
            index = self.connections_list_widget.indexFromItem(item).row()
            c = self.connections[index]
            dlg = QDialog()
            dlg.setWindowTitle("Write message")
            dlg.setWindowIcon(self.icon)

            layout = QVBoxLayout()
            dlg.setLayout(layout)

            receiver_addr = c["addr"][0]+":"+str(c["addr"][1])
            receiver_addr_label = QLabel(text=receiver_addr)
            layout.addWidget(receiver_addr_label)

            layout.addWidget(QLabel(text="Message:"))

            text_edit = QTextEdit()
            layout.addWidget(text_edit)

            send_button = QPushButton(text="Send", icon=QIcon(os.path.join(self.source_dir, "images/send.svg")))
            layout.addWidget(send_button)
            send_button.clicked.connect(dlg.accept)

            buttonBox = QDialogButtonBox(QDialogButtonBox.Cancel)
            buttonBox.rejected.connect(dlg.reject)
            layout.addWidget(buttonBox)

            dlg.accepted.connect(lambda: self.send_message(c["conn"], text_edit.toHtml()))

            dlg.exec_()
    
    def send_message(self, conn, message):
        try:
            conn.send(message.encode())
        except Exception as e:
            self.statusBar().showMessage(str(e))
    
    ##Connect dialog
    def ConnectDialog(self):
        dlg = QDialog()
        dlg.setWindowTitle("Create connection")
        dlg.setWindowIcon(self.icon)

        layout = QVBoxLayout()
        dlg.setLayout(layout)

        layout.addWidget(QLabel(text="Enter IP address:"))

        line_edit = QLineEdit()
        layout.addWidget(line_edit)

        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttonBox.rejected.connect(dlg.reject)
        buttonBox.accepted.connect(dlg.accept)
        layout.addWidget(buttonBox)

        dlg.accepted.connect(lambda: self.connect_to_server(line_edit.text()))

        dlg.exec_()
    
    def connect_to_server(self, ip):
        if ip:
            try:
                conn = socket.create_connection((ip,8224))
                self.add_to_connections(conn, conn.getpeername())
            except Exception as e:
                self.statusBar().showMessage(str(e))
    
    def add_to_connections(self, conn, addr):
        if self.threadPool.activeThreadCount() < self.threadPool.maxThreadCount():
            dataReception = DataReception(conn)
            dataReception.signals.received_or_fail.connect(self.handle_data_reception)
            self.threadPool.start(dataReception)
            self.connections.append({"conn":conn, "addr":addr})
            self.show_connections()
        else:
            self.statusBar().showMessage("Maximum connections reached!")
    
    def handle_data_reception(self, response, conn):
        if response["error"]:
            self.statusBar().showMessage(response["error_message"])
        else:
            self.messages.append({"conn":conn, "message": response["data"]})
            self.show_messages()
    
    def read_message(self, index):
        m = self.messages[index]
        self.text_view.setHtml(m["message"])
    
    def show_messages(self):
        self.messages_list_widget.clear()
        for m in self.messages:
            b = QListWidgetItem()
            b.setText(m["conn"].getpeername()[0]+":"+str(m["conn"].getpeername()[1]))
            self.messages_list_widget.addItem(b)
    
    def show_connections(self):
        self.connections_list_widget.clear()
        for c in self.connections:
            a = QListWidgetItem()
            a.setText(c["addr"][0]+":"+str(c["addr"][1]))
            self.connections_list_widget.addItem(a)
    
    def closeEvent(self, e):
        self.threadPool.thread().terminate()
        print("Closing the programme")

app = QApplication(sys.argv)

window = MainWindow()
window.show()

app.exec_()