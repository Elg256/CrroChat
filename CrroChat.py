import sys
from urllib.request import urlopen

import requests

import codecs

from PyQt5.QtCore import QAbstractListModel, QMargins, QPoint, QSize, Qt, QRect, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QFontMetrics, QPen, QFont, QPixmap, QStandardItemModel, QStandardItem, QIcon, QBrush, \
    QImage, QPalette
from PyQt5 import QtCore
import os
import threading
import time  # pls delete this it is for debug

from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QByteArray, QBuffer, QIODevice, QSize, Qt

# from PyQt5.QtGui import
from PyQt5.QtWidgets import (
    QFileDialog,
    QSpacerItem,
    QMessageBox,
    QAbstractItemView,
    QAction,
    QApplication,
    QLineEdit,
    QListView,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QLayout,
    QWidget,
    QStyledItemDelegate,
)

import sys
import time
from datetime import datetime

from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QTextEdit, QPushButton, QLineEdit, QLabel, QSizePolicy, \
    QDialog, QHBoxLayout
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QColor

from cryptcrro.asymetric import crro
from cryptcrro.symetric import crro as scrro
import re
import hashlib
import base64
import struct

USER_ME = 0
USER_THEM = 1

BUBBLE_COLORS = {USER_ME: "#90caf9", USER_THEM: "#5db67d"}

BUBBLE_PADDING_THEM = QMargins(20, 5, 210, 5)
BUBBLE_PADDING_ME = QMargins(210, 5, 20, 5)

TEXT_PADDING_THEM = QMargins(25, 15, 235, 15)
TEXT_PADDING_ME = QMargins(220, 15, 25, 15)


def decode_base64_to_pixmap(base64_bytes):
    # Decode the base64 bytes
    image_bytes = base64.urlsafe_b64decode(base64_bytes)

    # Convert the bytes back to QPixmap
    image = QImage()
    image.loadFromData(image_bytes)
    return QPixmap.fromImage(image)


def reduce_image_quality(file_path, quality=80, max_image_size=QSize(200, 200)):
    # Load the image from file path
    image = QImage(file_path)

    # Scale the image if it's larger than the max size
    if image.width() > max_image_size.width() or image.height() > max_image_size.height():
        image = image.scaled(max_image_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    # Convert image to bytes with reduced quality
    compressed_bytes = QByteArray()
    buffer = QBuffer(compressed_bytes)
    buffer.open(QIODevice.WriteOnly)
    image.save(buffer, "JPEG", quality)
    buffer.close()

    return compressed_bytes

def try_except(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"Une exception s'est produite : {e}")
            # Vous pouvez également gérer l'exception ici ou laisser le code gérant l'exception en aval.

    return wrapper

def bytes_to_pixmap(image_bytes):
    image = QImage()
    image.loadFromData(image_bytes)
    return QPixmap.fromImage(image)


class CustomTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.on_enter_pressed()
        else:
            super().keyPressEvent(event)

    def on_enter_pressed(self):
        text = self.toPlainText()
        print(f"Enter key pressed! Text: {text}")


class MessageDelegate(QStyledItemDelegate):
    """
    Draws each message.
    """

    def paint(self, painter, option, index):
        user, text, image = index.model().data(index, Qt.DisplayRole)

        if user == USER_ME:
            bubblerect = option.rect.marginsRemoved(BUBBLE_PADDING_ME)
            contentrect = option.rect.marginsRemoved(TEXT_PADDING_ME)
        elif user == USER_THEM:
            bubblerect = option.rect.marginsRemoved(BUBBLE_PADDING_THEM)
            contentrect = option.rect.marginsRemoved(TEXT_PADDING_THEM)

        # Draw the bubble outline
        painter.setPen(QPen(QColor("#000000"), 2))
        painter.drawRoundedRect(bubblerect, 10, 10)

        # Draw the bubble
        painter.setPen(Qt.NoPen)
        color = QColor(BUBBLE_COLORS[user])
        painter.setBrush(color)
        painter.drawRoundedRect(bubblerect, 10, 10)

        # Draw the triangle pointer
        if user == USER_ME:
            p1 = bubblerect.topRight()
        else:
            p1 = bubblerect.topLeft()
        painter.drawPolygon(p1 + QPoint(-20, 0), p1 + QPoint(20, 0), p1 + QPoint(0, 20))

        # Draw the text or image
        painter.setPen(Qt.black)
        if text:
            painter.drawText(contentrect, Qt.TextWordWrap, text)
        elif image:
            # Center the image in the bubble
            img_rect = QRect(contentrect.left(), contentrect.top(), image.width(), image.height())
            img_rect.moveCenter(bubblerect.center())
            painter.drawPixmap(img_rect, image)

    def sizeHint(self, option, index):
        user, text, image = index.model().data(index, Qt.DisplayRole)
        metrics = option.fontMetrics

        if text:
            text_width = option.rect.width() - TEXT_PADDING_ME.left() - TEXT_PADDING_ME.right()
            text_height = metrics.boundingRect(QRect(0, 0, text_width, 0), Qt.TextWordWrap, text).height()
            height = text_height + TEXT_PADDING_ME.top() + TEXT_PADDING_ME.bottom()
        elif image:
            height = image.height() + TEXT_PADDING_ME.top() + TEXT_PADDING_ME.bottom()

        return QSize(option.rect.width(), height)


class MessageModel(QAbstractListModel):
    def __init__(self, main_window, *args, **kwargs):
        super(MessageModel, self).__init__(*args, **kwargs)
        self.messages = []
        self.main_window = main_window

    def data(self, index, role):
        if role == Qt.DisplayRole:
            return self.messages[index.row()]

    def rowCount(self, index):
        return len(self.messages)

    def clear(self):
        self.beginResetModel()
        self.messages = []
        self.endResetModel()

    def add_message(self, who, text=None, image_bytes=None, max_image_size=QSize(200, 200)):
        """
        Add a message to our message list, with text or image.
        If an image is provided, it is resized to fit within max_image_size.
        """
        if text and text.strip():
            self.messages.append((who, text, None))
        elif image_bytes:
            image = bytes_to_pixmap(image_bytes)
            if image.size().width() > max_image_size.width() or image.size().height() > max_image_size.height():
                image = image.scaled(max_image_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.messages.append((who, None, image))
        self.layoutChanged.emit()
        bottom_index = self.createIndex(len(self.messages) - 1, 0)
        self.main_window.text_edit.scrollToBottom()


class Get_Passord(QDialog):
    def __init__(self, main_window, for_what, start=False, parent=None):
        super().__init__(parent)
        self.for_what = for_what
        self.start = start
        self.main_window = main_window  # Référence à l'instance de MainWindow
        self.setWindowTitle('Password')
        self.setWindowIcon(QIcon("logo.png"))

        print("for what: ", self.for_what)

        if self.for_what == "first_time":
            self.label_name = QLabel("Name: ", self)
            self.label_name.setGeometry(10, 0, 180, 20)

            self.champ_name = QLineEdit(self)
            self.champ_name.setGeometry(25, 20, 110, 20)

            self.label_vide = QLabel("If you don't want to set \na Password just don't put one ", self)
            self.label_vide.setGeometry(25, 140, 200, 30)

        self.label = QLabel('Password:', self)
        self.label.setGeometry(10, 50, 110, 20)

        self.input_field = QLineEdit(self)
        self.input_field.setGeometry(25, 70, 200, 20)
        self.input_field.setEchoMode(QLineEdit.Password)

        self.ok_button = QPushButton('Ok', self)
        self.ok_button.setGeometry(25, 100, 200, 30)

        self.ok_button.clicked.connect(self.take_user_input)

    def take_user_input(self):
        print("before funct")
        user_input = self.input_field.text()
        print("before funct")

        if user_input.strip():
            key = hashlib.sha256(user_input.encode()).digest()
        else:
            key = ""

        print("in hash: ", key)
        # try:

        if self.for_what == "first_time":
            if key == "":
                key = False

            self.main_window.first_time(key, self.champ_name.text())

        if self.start == True:
            with open("key_pair.txt", "r") as file:
                data = file.read()

            self.main_window.access_key(key, start=True)

        if self.for_what == "save":
            self.main_window.save_keys(key)
        elif self.for_what == "access":
            self.main_window.access_key(key)

        # except Exception as e:
        # print(e)
        self.accept()


class Get_Contact(QDialog):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)

        try:
            self.setWindowIcon(QIcon("logo.png"))

            self.main_window = main_window  # Référence à l'instance de MainWindow
            self.setWindowTitle('Add contact')

            self.label_name = QLabel("Name:", self)
            self.label_name.setGeometry(10, 50, 110, 20)

            self.champ_name = QLineEdit(self)

            self.champ_name.setGeometry(25, 70, 200, 20)

            self.label_server = QLabel("Server:", self)
            self.label_server.setGeometry(10, 100, 110, 20)

            self.server = QLineEdit(self)
            self.server.setGeometry(25, 120, 300, 20)

            self.label_public_key = QLabel("Public key:", self)
            self.label_public_key.setGeometry(10, 140, 110, 20)

            self.public_key = QLineEdit(self)
            self.public_key.setGeometry(25, 170, 300, 20)

            self.ok_button = QPushButton('Add contact', self)
            self.ok_button.setGeometry(25, 200, 200, 30)

            self.ok_button.clicked.connect(self.take_user_input)

        except Exception as e:
            print(e)

    def take_user_input(self):
        try:
            print("before funct")
            name = self.champ_name.text()

            server = self.server.text()

            public_key = self.public_key.text()

            os.mkdir(f'./chat_data/{name}')

            with open("contacts.txt", "a") as file:
                data = name + ";" + server + ";" + public_key + ";"
                file.write(data)

            self.main_window.refresh_contact_list()

            # except Exception as e:
            # print(e)
            self.accept()
        except Exception as e:
            print(e)


class Downloader(QThread):
    contentReady = pyqtSignal(bytes)

    def __init__(self, url):
        super().__init__()
        self._url = url
        self._content = None
        print("in init download Qthread")

    def run(self):
        print("in run download Qthread")

        data = requests.get(self._url)

        content = data.text.encode()
        self._content = content
        # Open the URL address.
        # with urlopen(self._url) as r:
        # Read the content of the file.
        # content = r.read()
        # Emit the content signal.
        self.contentReady.emit(content)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        oImage = QImage("img_8.png")
        sImage = oImage.scaled(QSize(1000, 800))  # resize Image to widgets size
        palette = QPalette()
        palette.setBrush(QPalette.Window, QBrush(sImage))
        self.setPalette(palette)

        self.show_smiley = 2

        self.all_data = ""

        self.setWindowTitle("CrroChat")
        self.setGeometry(100, 100, 450, 450)
        self.setMinimumWidth(450)

        # self.setStyleSheet("background-color: #6da2d2;")

        # background-image: linear-gradient(rgba(0, 0, 255, 0.5), rgba(255, 255, 0, 0.5)),
        # url("../../media/examples/lizard.png");

        self.setWindowIcon(QIcon("logo.png"))

        self.content = ""

        # central_widget = QWidget()
        # self.setCentralWidget(central_widget)
        # central_widget.setContentsMargins(-5, -5, -5, -5)

        # Création d'un QHBoxLayout pour centrer le QVBoxLayout
        center_layout = QHBoxLayout()
        self.layout = QVBoxLayout()

        center_layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        # center_layout.setAlignment(Qt.AlignCenter)
        center_layout.addLayout(self.layout)

        self.center_widget = QWidget()
        self.center_widget.setStyleSheet("background-color:#6da2d2;"
                                         )
        self.center_widget.setContentsMargins(0, 0, 0, 0)
        self.center_widget.setContentsMargins(0, 0, 0, 5)
        self.center_widget.setMaximumWidth(600)
        self.center_widget.setLayout(center_layout)

        # Créer un widget central et le centrer
        central_widget = QWidget()
        central_widget.setContentsMargins(0, 0, 0, 0)
        central_layout = QHBoxLayout()
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)
        central_layout.addWidget(self.center_widget)
        central_widget.setLayout(central_layout)
        self.setCentralWidget(central_widget)

        self.layout.setAlignment(Qt.AlignTop)

        bar = self.menuBar()

        bar.setStyleSheet(
            "QMenuBar { background-color: #eeeeee; color: black; }"  # Fond de la barre de menu et couleur du texte
            "QMenuBar::item:selected { background-color: #CCCCCC; }"  # Fond de l'élément de menu sélectionné
            "QMenuBar::item:selected { color: black; }"  # Couleur du texte de l'élément de menu sélectionné
            "QMenuBar::item:pressed { background-color: #999999; }"  # Fond de l'élément de menu pressé
            "QMenuBar::item:pressed { color: black; }"  # Couleur du texte de l'élément de menu pressé
            "QMenu { background-color: #eeeeee; }"  # Fond du menu déroulant
            "QMenu::item:selected { background-color: #CCCCCC; }"  # Fond de l'élément de menu sélectionné dans le menu déroulant
            "QMenu::item:selected { color: black; }"
            # Couleur du texte de l'élément de menu sélectionné dans le menu déroulant
        )
        # Menu Fichier
        chat_action = QAction('Chat', self)
        bar.addAction(chat_action)
        chat_action.triggered.connect(self.show_chat)

        contact_action = QAction("Contacts", self)
        bar.addAction(contact_action)
        contact_action.triggered.connect(self.show_contacts)

        server_action = QAction('Server', self)
        bar.addAction(server_action)
        server_action.triggered.connect(self.show_server)

        key_action = QAction("Keys", self)
        bar.addAction(key_action)
        key_action.triggered.connect(self.show_use_key)

        # Menu Keys

        # Menu Edition
        edit_menu = bar.addMenu('About')
        version = QAction('Version 0.1', self)
        creator = QAction('By Elg256', self)
        edit_menu.addAction(version)
        edit_menu.addAction(creator)

        self.h_layout = QHBoxLayout()
        self.h_layout.setContentsMargins(0, 0, 0, 0)
        # self.h_layout.setAlignment(Qt.AlignCenter)

        # Chargement de l'image
        # logo_image = QPixmap("./logo_crro.png")
        # label_image = QLabel(self)
        # label_image.setPixmap(logo_image)
        # label_image.setMaximumWidth(32)
        # self.h_layout.addWidget(label_image)

        # Ajout du texte à droite de l'image
        # label_app_name = QLabel("CrroChat")
        # label_app_name.setFont(QFont('Monospace', 15))
        # self.h_layout.addWidget(label_app_name)

        # Ajout du QHBoxLayout au QVBoxLayout principal
        self.layout.addLayout(self.h_layout)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.name_contact = ""
        self.label_name_current = QLabel(f" Chat with: {self.name_contact}")
        self.label_name_current.setFont(QFont("arial", 11))
        self.label_name_current.setStyleSheet("background-color:#4285c2;"

                                              "color: white;")  # "border-radius: 3px;"
        self.label_name_current.setContentsMargins(0, 5, 0, 5)
        self.layout.addWidget(self.label_name_current)

        self.text_edit = QListView()
        self.layout.addWidget(self.text_edit)

        # Use our delegate to draw items in this view.
        self.text_edit.setItemDelegate(MessageDelegate())
        self.text_edit.setStyleSheet("background-color: #eeeeee;")
        self.text_edit.setItemAlignment(Qt.AlignCenter)
        self.text_edit.setMaximumWidth(600)
        self.text_edit.setContentsMargins(0, 0, 0, 0)

        self.model = MessageModel(self)
        self.text_edit.setModel(self.model)

        self.button_layout = QHBoxLayout()
        self.button_layout.setContentsMargins(4, 2, 4, 2)

        self.widget_button = QWidget()
        self.widget_button.setLayout(self.button_layout)
        self.widget_button.setContentsMargins(0, 0, 0, 0)

        # Définissez la couleur de fond du widget en utilisant un code hexadécimal
        self.widget_button.setStyleSheet("background-color: #b9d7d3;") #c4dcd9

        # Ajoutez le widget parent au layout principal
        self.layout.addWidget(self.widget_button)

        # Bouton 1
        button1 = QPushButton()
        icon = QIcon("logo.png")
        button1.setIcon(icon)

        button1.setStyleSheet("border: none;"
                              "background-color: white;")
        button1.setIconSize(QSize(20, 20))
        button1.setMaximumSize(20, 20)
        button1.clicked.connect(
            lambda: self.insert_smiley("U+1F600"))  # Connectez-le à une fonction de gestion d'événements
        self.button_layout.addWidget(button1, alignment=Qt.AlignLeft)

        button2 = QPushButton()
        button2.setIcon(QIcon("logo.png"))
        button2.setIconSize(QSize(20, 20))
        button2.setMaximumSize(20, 20)
        button2.setStyleSheet("border: none;"
                              "background-color: white;")
        # button1.clicked.connect()  # Connectez-le à une fonction de gestion d'événements

        self.button_layout.addWidget(button2, alignment=Qt.AlignLeft)

        button3 = QPushButton()
        button3.setIcon(QIcon("logo.png"))
        button3.setIconSize(QSize(20, 20))
        button3.setMaximumSize(20, 20)
        # button1.clicked.connect(self.button1_clicked)  # Connectez-le à une fonction de gestion d'événements
        self.button_layout.addWidget(button3, alignment=Qt.AlignLeft)

        button4 = QPushButton()
        button4.setIcon(QIcon("logo.png"))
        button4.setIconSize(QSize(20, 20))
        button4.setMaximumSize(20, 20)
        # button1.clicked.connect(self.button1_clicked)  # Connectez-le à une fonction de gestion d'événements
        self.button_layout.addWidget(button4, alignment=Qt.AlignLeft)



        spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.button_layout.addItem(spacer)

        button_file = QPushButton()
        button_file.setStyleSheet("background-color: #667B68;"
                                  )
        button_file.setIcon(QIcon("add_file.png"))
        button_file.setIconSize(QSize(16, 16))
        button_file.setMaximumSize(20, 20)
        # button1.clicked.connect(self.button1_clicked)  # Connectez-le à une fonction de gestion d'événements
        self.button_layout.addWidget(button_file, alignment=Qt.AlignRight)

        button_img = QPushButton()
        button_img.setStyleSheet("background-color: #667B68;"
                                 )
        button_img.setIcon(QIcon("add_img.png"))
        button_img.setIconSize(QSize(20, 20))
        button_img.setMaximumSize(20, 20)
        button_img.clicked.connect(self.openFileNameDialog)  # Connectez-le à une fonction de gestion d'événements
        self.button_layout.addWidget(button_img, alignment=Qt.AlignRight)



        self.widget_button.hide()

        self.layout_plus_button = QHBoxLayout()
        self.layout_plus_button.setContentsMargins(0, 0, 8, 0)
        self.layout.addLayout(self.layout_plus_button)

        self.empty_label = QLabel("gfjd ")

        # Ajoutez les boutons au layout principal
        self.layout.addLayout(self.button_layout)

        self.champ_message = QTextEdit()
        self.champ_message.setStyleSheet("border-color: white;"
                                         )
        # self.layout.addWidget(self.champ_message)
        self.champ_message.setMaximumWidth(500)
        self.champ_message.setMaximumHeight(60)

        text_fond = "Type in your message..."
        couleur_texte = QColor(128, 128, 128)

        self.champ_message.setStyleSheet("background-color: white;"
                                         "border-color: white;"
                                         "border: none;"
                                         )
        self.champ_message.setPlaceholderText(text_fond)
        self.champ_message.setContentsMargins(0, 0, 0, 0)

        self.layout_send_button_and_champ_message = QHBoxLayout()
        self.layout_send_button_and_champ_message.addWidget(self.champ_message)

        self.widget_send_button_and_champ_message = QWidget()
        self.widget_send_button_and_champ_message.setStyleSheet("background-color: white;")
        self.layout_send_button_and_champ_message.addWidget(self.widget_send_button_and_champ_message,
                                                            alignment=Qt.AlignLeft)

        # self.space_for_send_button = QSpacerItem(QSizePolicy.Expanding, QSizePolicy.Minimum)
        # self.space_for_send_button.setStyleSheet("background-color: white;")

        self.button_smiley = QPushButton("+")
        self.button_smiley.setStyleSheet("""
                    QPushButton {
                        background-color: white;
                        border: none; 
                        border-radius: 4;

                        font-size: 22px;
                    }
                    QPushButton:pressed {
                        background-color: #d2d2d2; 
                    }
                    QPushButton:hover {
                        background-color: #d2d2d2; 
                    }
                """)

        self.button_smiley.setContentsMargins(0, 0, 0, 0)
        self.button_smiley.clicked.connect(self.show_smiley_funct)
        self.button_smiley.setFixedSize(20, 20)
        # self.layout_plus_button.addWidget(self.button_smiley, alignment=Qt.AlignRight)

        self.layout.addLayout(self.layout_send_button_and_champ_message)

        self.layout_for_plus_and_send_button = QVBoxLayout()
        self.layout_for_plus_and_send_button.setContentsMargins(0, 0, 5, 0)
        self.layout_for_plus_and_send_button.setSpacing(0)

        self.widget_send_button_and_champ_message.setContentsMargins(0, 0, 0, 0)
        self.widget_send_button_and_champ_message.setLayout(self.layout_for_plus_and_send_button)

        self.layout_for_plus_and_send_button.addWidget(self.button_smiley, alignment=Qt.AlignLeft)

        # self.send_button = QPushButton(" Send")
        self.send_button = QPushButton()
        icone = QIcon("send.png")
        self.send_button.setIcon(icone)
        self.send_button.setIconSize(QSize(24, 24))

        self.send_button.setStyleSheet("""
            QPushButton {
                background-color: white;
                border: none; /* Supprimer la bordure */
                border-radius: 4;

            }
            QPushButton:pressed {
                background-color: #e0e0e0;
            }
            QPushButton:hover {
                background-color: #d2d2d2;
            }
        """)
        self.send_button.clicked.connect(self.send_message)
        # self.layout.addWidget(self.send_button)
        # self.send_button.setMaximumWidth(100)
        # self.send_button.setMinimumHeight(30)

        # self.widget_send_button_and_champ_message.addWidget(self.send_button, alignment=Qt.AlignLeft)
        # self.layout_send_button_and_champ_message.addItem(self.space_for_send_button)

        self.layout_for_plus_and_send_button.addWidget(self.send_button, alignment=Qt.AlignLeft)

        self.start_contenu = ""
        self.timer = QTimer()
        self.timer.timeout.connect(self.get_contenu)

        self.label_contacts = QLabel("<b>Contacts: </b>")
        self.layout.addWidget(self.label_contacts)

        self.list_contacts = QListView()
        self.list_contacts.setMaximumWidth(600)
        self.list_contacts.setStyleSheet("background: white;"
                                         "font-size: 16px;")
        self.layout.addWidget(self.list_contacts)

        with open("contacts.txt", "r") as file:
            data = file.read()
            self.list_contacts_from_file = data.split("\n")
            data = data.replace("\n", "")

            self.list_contacts_affiche = data.split(";")

        self.only_contacts_name = []

        for i in range(0, len(self.list_contacts_affiche), 3):
            print(len(self.list_contacts_affiche))
            self.only_contacts_name.append(self.list_contacts_affiche[i])
            print("only contact name", self.only_contacts_name)
        self.only_contacts_name.pop()

        model = QStandardItemModel()
        self.list_contacts.setModel(model)

        self.list_contacts.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.list_contacts.doubleClicked.connect(self.fill_info_contact)

        image_path = "./contacts.png"

        for i in self.only_contacts_name:
            item = QStandardItem(i)
            icon = QIcon(QPixmap(image_path))
            item.setIcon(icon)
            model.appendRow(item)

        self.button_add_contact = QPushButton("Add contact")
        self.button_add_contact.clicked.connect(self.show_contact_windows)
        self.layout.addWidget(self.button_add_contact)

        self.label_nom = QLabel("<b>Name: </b>")
        self.layout.addWidget(self.label_nom)

        self.champ_nom = QLineEdit()
        self.champ_nom.setStyleSheet("background-color: white;")
        self.layout.addWidget(self.champ_nom)

        self.label_privee = QLabel("<b>Private key: </b>")
        self.layout.addWidget(self.label_privee)

        self.champ_private_key = QLineEdit()
        self.champ_private_key.setStyleSheet("background-color: white;")
        self.champ_private_key.setEchoMode(QLineEdit.Password)
        self.see = True
        self.layout.addWidget(self.champ_private_key)

        self.see_private_key = QPushButton("See Private Key")
        self.see_private_key.clicked.connect(self.see_private)
        self.layout.addWidget(self.see_private_key)

        self.label_public = QLabel("<b>Public key: </b>")
        self.layout.addWidget(self.label_public)

        self.champ_public_key = QLineEdit()
        self.champ_public_key.setStyleSheet("background-color: white;")
        self.layout.addWidget(self.champ_public_key)

        self.generate_key_button = QPushButton("generate new keys")

        self.generate_key_button.clicked.connect(self.generate_keys)
        self.layout.addWidget(self.generate_key_button)

        self.save_key_button = QPushButton("Save keys")

        self.save_key_button.clicked.connect(self.show_password_windows_save)
        self.layout.addWidget(self.save_key_button)

        self.get_key_button = QPushButton("Acess keys")

        self.get_key_button.clicked.connect(self.show_password_windows_access)
        self.layout.addWidget(self.get_key_button)

        self.url_send = ''
        self.url_contenu = ''

        self.label_name_contact = QLabel("<b>Name: </b>")
        self.layout.addWidget(self.label_name_contact)
        self.label_name_contact.hide()

        self.champ_name_contact = QLineEdit()
        self.champ_name_contact.setStyleSheet("background: white;")
        self.layout.addWidget(self.champ_name_contact)
        self.champ_name_contact.hide()

        self.label_server = QLabel("<b>Server: </b>")
        self.layout.addWidget(self.label_server)
        self.label_server.hide()

        self.champ_server = QLineEdit('')
        self.champ_server.setStyleSheet("background-color: white;")
        self.layout.addWidget(self.champ_server)
        self.champ_server.hide()

        self.label_public_key2 = QLabel("<b>Public_key: </b>")
        self.layout.addWidget(self.label_public_key2)
        self.label_public_key2.hide()

        self.champ_public_key2 = QLineEdit('')
        self.champ_public_key2.setStyleSheet("background-color: white;")
        self.layout.addWidget(self.champ_public_key2)
        self.champ_public_key2.hide()

        self.show_chat()

        self.counter = 0

        with open("key_pair.txt", "r") as file:
            file = file.read().strip()
            if "no encryption: " in file:
                print("in no encryption: ")
                file = file
                self.access_key(key=None, start=True, password=False)
            elif file:
                try:

                    self.show_password_windows_access(start=True)

                except Exception as e:
                    print(e)
            elif not file:
                try:
                    print("in file == None")

                    self.show_fisrt_time_password_windows(start=True)

                except Exception as e:
                    print(e)

    def openFileNameDialog(self):
        options = QFileDialog.Options()
        #options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getOpenFileName(self, "Select a Picture to share  :)", "",
                                                  "Image Files (*.jpeg *jpg *.png);;All Files (*)", options=options)
        if fileName:
            print(fileName)
            reduced_quality_bytes = reduce_image_quality(fileName, quality=80, max_image_size=QSize(200, 200))

            reduced_quality_bytes = base64.urlsafe_b64encode(reduced_quality_bytes)

            reduced_quality_bytes = base64.urlsafe_b64decode(reduced_quality_bytes)

            print("reduced_quality_bytes instante", reduced_quality_bytes)

            private_key = self.champ_private_key.text()

            private_key = int.from_bytes(base64.urlsafe_b64decode(private_key), byteorder="big")

            public_key = eval(self.champ_public_key2.text())

            public_key_sender = eval(self.champ_public_key.text())

            image_encrypt = crro.encrypt(public_key, str(reduced_quality_bytes))

            image_encrypt_for_sender = crro.encrypt(public_key_sender, str(reduced_quality_bytes))

            image_signed = "__IMAGE__" + "\n" + image_encrypt + "\n" + image_encrypt_for_sender

            image_signed = crro.sign(private_key, str(image_signed))


            print("image signed", image_signed)

            public_key_for_x = self.champ_public_key.text().replace("(", "").split(",")
            public_key_sender_for_x = self.champ_public_key2.text().replace("(", "").split(",")
            public_key_for_file_name = str(self.champ_public_key.text()).encode()
            public_key_sender_for_file_name = str(self.champ_public_key2.text()).encode()
            x = int(public_key_for_x[0])
            print("x", x)
            x_sender = int(public_key_sender_for_x[0])
            print("x_sender", x_sender)
            if x_sender < x:
                file_name = hashlib.sha256(public_key_for_file_name + public_key_sender_for_file_name).hexdigest()
            else:
                file_name = hashlib.sha256(public_key_sender_for_file_name + public_key_for_file_name).hexdigest()

            file_name = file_name + ".txt"
            self.url_send = self.champ_server.text() + "/send_messages.php"

            data = {'contenu': image_signed.encode('utf-8') + b"\n\n", "file_name": file_name}
            response_send = requests.post(self.url_send, data=data)
            if response_send.status_code == 200:
                print("image send!")


    def insert_smiley(self, smiley):
        unicode_code = smiley
        emoji = chr(int(unicode_code[2:], 16))
        # print(smiley, "U+1F600".decode())
        self.champ_message.insertPlainText(emoji)

    def show_smiley_funct(self):
        try:
            if self.show_smiley == 1:
                self.widget_button.hide()
                self.show_smiley = 2
            else:
                self.widget_button.show()
                self.show_smiley = 1
        except Exception as e:
            print(e)

    @try_except
    def initDownload(self, url_path):

        print("in init download")

        print(url_path)

        self.downloader = Downloader(
            url_path
        )

        @try_except
        def downloadFinished(content):
            try:
                # Print the content of the file.
                #print("content in download finish", content.decode())  # Assuming content is in bytes
                self.content = content.decode()

                # Delete the thread when no longer needed.
                # self.downloader.deleteLater() #Use this line only on Windows OS

                QTimer.singleShot(1000, self.get_contenu)
            except Exception as e:
                print(e)

        print("after download")
        # Qt will invoke the `downloadFinished()` method once the
        # thread has finished.
        self.downloader.contentReady.connect(downloadFinished)

        self.downloader.start()

        # content = self.downloader.getcontent()

        return self.content

    def refresh_contact_list(self):
        with open("contacts.txt", "r") as file:
            data = file.read()
            self.list_contacts_from_file = data.split("\n")
            self.list_contacts_from_file.pop()
            data = data.replace("\n", "")

            self.list_contacts_affiche = data.split(";")

        self.only_contacts_name = []

        for i in range(0, len(self.list_contacts_affiche), 3):
            self.only_contacts_name.append(self.list_contacts_affiche[i])

        model = QStandardItemModel()
        image_path = "./contacts.png"
        self.only_contacts_name.pop()

        for i in self.only_contacts_name:
            item = QStandardItem(i)
            icon = QIcon(QPixmap(image_path))
            item.setIcon(icon)
            model.appendRow(item)

        self.list_contacts.setModel(model)

    def see_private(self):

        if self.see == True:
            self.see = False
            self.champ_private_key.setEchoMode(QLineEdit.Normal)
        else:
            self.see = True
            self.champ_private_key.setEchoMode(QLineEdit.Password)

    @try_except
    def fill_info_contact(self, index, start=False):
        if start == False:

            contact_index = index.row()
            if 0 <= contact_index < len(self.list_contacts_affiche):
                print("list contact affiche", self.list_contacts_affiche)
                name = self.list_contacts_affiche[contact_index * 3]
                server_contact = self.list_contacts_affiche[contact_index * 3 + 1]
                public_key = self.list_contacts_affiche[contact_index * 3 + 2]
                print("contact-index", contact_index)
                print("public key", public_key)
                print("server_contact", server_contact)
                # self.text_edit.clear(Mask())
                self.champ_public_key2.setText(public_key)
                self.champ_server.setText(server_contact)
                self.model.clear()
                self.start_contenu = ""
                self.champ_name_contact.setText(name)
                self.name_contact = name
                self.label_name_current.setText(f" Chat with: {self.name_contact}")
                self.show_chat()
                self.fill_server_info()
                # self.get_contenu(start=True)
                self.counter = 1
                self.model.clear()

                with open("parameters.txt", "w") as file:
                    file.write(name + ";" + server_contact + ";" + public_key + ";")
        else:
            # if 2 == 1:
            with open("parameters.txt", "r") as file:
                list_contacts_affiche = file.read()

            print("list contact affiche", list_contacts_affiche)
            list_contacts_affiche = list_contacts_affiche.split(";")
            name = list_contacts_affiche[0]
            server_contact = list_contacts_affiche[1]
            public_key = list_contacts_affiche[2]
            print("public key", public_key)
            print("server_contact", server_contact)
            # self.text_edit.clear(Mask())
            self.champ_public_key2.setText(public_key)
            self.champ_server.setText(server_contact)
            self.model.clear()
            self.start_contenu = ""
            self.champ_name_contact.setText(name)
            self.name_contact = name
            self.label_name_current.setText(f" Chat with: {self.name_contact}")
            self.show_chat()
            self.fill_server_info()
            # self.get_contenu(start=True)
            # self.show_chat()

    @try_except
    def send_message(self, another):

        try:

            print("another lolol", another)
        except Exception as e:
            print(e)

        self.text_edit.scrollToBottom()

        message_plaintext = str(self.champ_message.toPlainText())

        if not message_plaintext.strip():
            return

        public_key = str(self.champ_public_key.text())

        public_key_sender = str(self.champ_public_key2.text())

        private_key = self.champ_private_key.text()
        private_key_int = int.from_bytes(base64.urlsafe_b64decode(private_key))

        identifier = hashlib.sha256(public_key.encode()).hexdigest()

        try:

            derivated_key = hashlib.sha256(private_key.encode()).digest()

            public_key = eval(public_key)
            public_key_sender = eval(public_key_sender)
            print("public_key", public_key_sender)

            name = str(self.champ_nom.text())

            time = datetime.now()

            time = time.strftime("%Y-%m-%d %H:%M")
            print(time)

            message_plaintext = f"              {time}" + "\n" + name + ":\n" + message_plaintext

            message = crro.encrypt(public_key_sender, message_plaintext)

            message_for_sender = crro.encrypt(public_key, message_plaintext)

            message = message + "\n" + message_for_sender

            message = identifier + "\n" + message

            message_signed = crro.sign(private_key_int, message)

            if not message.strip():
                return

            public_key_for_x = self.champ_public_key.text().replace("(", "").split(",")

            public_key_sender_for_x = self.champ_public_key2.text().replace("(", "").split(",")

            public_key_for_file_name = str(self.champ_public_key.text()).encode()

            public_key_sender_for_file_name = str(self.champ_public_key2.text()).encode()

            x = int(public_key_for_x[0])

            print("x", x)

            x_sender = int(public_key_sender_for_x[0])

            print("x_sender", x_sender)

            if x_sender < x:
                file_name = hashlib.sha256(public_key_for_file_name + public_key_sender_for_file_name).hexdigest()
            else:
                file_name = hashlib.sha256(public_key_sender_for_file_name + public_key_for_file_name).hexdigest()

            file_name = file_name + ".txt"

            self.url_send = self.champ_server.text() + "/send_messages.php"

            data = {'contenu': message_signed.encode('utf-8') + b"\n\n", "file_name": file_name}
            response_send = requests.post(self.url_send, data=data)
            if response_send.status_code == 200:
                self.champ_message.clear()
                self.fill_server_info()

                print("Contenu ajouté avec succès.")
            else:
                print("La requête a échoué. Code de statut:", response_send.status_code)
        except Exception as e:
            print(e)

    def scroll_to_bottom_manual(self):
        self.text_edit.scrollToBottom()

    def extract_new_messages(self, start_contenu, contenu_actuel_chiffrer):

        new_messages = contenu_actuel_chiffrer.replace(start_contenu, "")

        print("new messages", new_messages)

        return new_messages

    def fill_server_info(self):
        try:

            public_key_for_x = self.champ_public_key.text().replace("(", "").split(",")

            public_key_sender_for_x = self.champ_public_key2.text().replace("(", "").split(",")

            public_key = str(self.champ_public_key.text()).encode()

            public_key_sender = str(self.champ_public_key2.text()).encode()

            x = int(public_key_for_x[0])

            print("x", x)

            x_sender = int(public_key_sender_for_x[0])

            print("x_sender", x_sender)

            if x_sender < x:
                file_name = hashlib.sha256(public_key + public_key_sender).hexdigest()
            else:
                file_name = hashlib.sha256(public_key_sender + public_key).hexdigest()

            file_name = file_name + ".txt"

            self.url_contenu = self.champ_server.text() + f"/{file_name}"
        except Exception as e:
            print(e)

    @try_except
    def get_contenu(self, start=False):

        print("actual time", time.time() - start_time)

        public_key_for_x = self.champ_public_key.text().replace("(", "").split(",")

        public_key_sender_for_x = self.champ_public_key2.text().replace("(", "").split(",")

        public_key_for_file_name = str(self.champ_public_key.text()).encode()

        public_key_sender_for_file_name = str(self.champ_public_key2.text()).encode()

        server = self.champ_server.text()

        x = int(public_key_for_x[0])

        print("x", x)

        x_sender = int(public_key_sender_for_x[0])

        print("x_sender", x_sender)

        if x_sender < x:
            file_name = hashlib.sha256(public_key_for_file_name + public_key_sender_for_file_name).hexdigest()
        else:
            file_name = hashlib.sha256(public_key_sender_for_file_name + public_key_for_file_name).hexdigest()

        print("file name :", file_name)

        url_path = server + "/" + file_name + ".txt"

        print("url_path: ", url_path)

        response = self.initDownload(url_path)

        print("pass exacption")

        if self.counter < 3:
            self.counter += 1

        if self.counter == 2:
            print("after start")

            # self.get_contenu(start=True) #here the crash problem

            self.text_edit.scrollToBottom()

        name = self.champ_name_contact.text()

        if self.counter == 1:
            self.model.add_message(USER_ME, 'please wait loading...        ')

        # if start == True:
        if self.counter == 2:
            print("start = True", start)

            self.model.clear()


            with open(f"./chat_data/{name}/chat_data.txt", "r") as file:
                data = file.read()
                password = self.password
                data = scrro.decrypt(password, data).decode()
                # all_data = ""
                self.all_data = data


            #print("data from chat_data", data)
            try:

                data = data.split("---End_Message---")
                #print("data: ", data)
            except Exception as e:
                print(e)

            try:

                for i in range(0, len(data)):

                    print(f"data in range{i}", data[i])

                    if "---Your_Message---" in data[i]:

                        self.model.add_message(USER_ME, data[i].replace("---Your_Message---", ""))
                        print("Your_Message")
                    elif "---Them_Message---" in data[i]:

                        self.model.add_message(USER_THEM, data[i].replace("---Them_Message---", ""))
                        print("Them_Message")
                    elif "---Your_Image---" in data[i]:

                        #message = base64.urlsafe_b64decode(data[i].replace("---Your_Image---", ""))

                        message = base64.urlsafe_b64decode(data[i].replace("---Your_Image---", ""))

                        print("base64 decode message", message)

                        #message = message[2:-1]
                        # Utiliser codecs.escape_decode pour convertir la chaîne en bytes
                        #message, _ = codecs.escape_decode(message)

                        self.model.add_message(USER_ME, image_bytes=message)
                        print("Your_Image")

                    elif "---Them_Image---" in data[i]:

                        #message = base64.urlsafe_b64decode(data[i].replace("---Your_Image---", ""))

                        message = base64.urlsafe_b64decode(data[i].replace("---Them_Image---", ""))

                        print("base64 decode message", message)

                        #message = message[2:-1]
                        # Utiliser codecs.escape_decode pour convertir la chaîne en bytes
                        #message, _ = codecs.escape_decode(message)

                        self.model.add_message(USER_THEM, image_bytes=message)
                        print("Them_Image")
                    else:
                        print("don't know who send that")

                with open(f"./chat_data/{name}/encrypt_data.txt", "r") as file:
                    data_file = file.read()

                    self.start_contenu = data_file

                #print("data_file", data_file)

            except Exception as e:
                print("in start", e)

        if "Error during connexion" in self.champ_server.text():
            return

        print("im here")

        # if scroll == True:

        # self.text_edit.scrollToBottom()

        try:

            print("response url open", "End response url open")
        except Exception as e:
            with open("parameters.txt", "r") as file:
                if file.read().strip():
                    self.champ_server.setText(f"Error during connexion to: {self.url_contenu} ")
                    QMessageBox.warning(self, 'Error during connexion', f"Error during connexion to the server: {e}")
                    return
                else:
                    print("in else")
                    return

        if response:

            print("response == 200")

            contenu_actuel_chiffrer = response

            pattern = re.compile(r'---BEGIN SIGNED CRRO MESSAGE---(.*?)---END SIGNED CRRO MESSAGE---', re.DOTALL)

            all_messages = []

            # if start == True:
            # start_contenu = self.start_contenu
            # print("im in start = True",start)
            # contenu_actuel_chiffrer_extract = contenu_actuel_chiffrer
            # self.text_edit.scrollToBottom()

            print("im in start = False")
            start_contenu = self.start_contenu

            print("contenu_actuel_chiffrer", contenu_actuel_chiffrer )
            print("self.start_contenu", self.start_contenu)

            if contenu_actuel_chiffrer != self.start_contenu:

                contenu_actuel_chiffrer_extract = self.extract_new_messages(start_contenu, contenu_actuel_chiffrer)

                print("contenu not same")

                # Trouver le premier message correspondant
                match = pattern.search(contenu_actuel_chiffrer_extract)

                private_key = self.champ_private_key.text()

                public_key = eval(str(self.champ_public_key2.text()))

                personal_public_key = self.champ_public_key.text().replace("(", "").replace(")", "")

                personal_public_key = personal_public_key.split(",")

                int_x = int(personal_public_key[0])
                int_y = int(personal_public_key[1])

                personal_public_key = int_x, int_y

                # name = self.cham

                personal_public_key_for_hash = str(self.champ_public_key.text())

                private_key = int.from_bytes(base64.urlsafe_b64decode(private_key), byteorder="big")
                #print("private_key base64 decode", private_key)
                #print("we are in!", contenu_actuel_chiffrer_extract)

                chat_data = []

                name = self.champ_name_contact.text()

                with open(f"./chat_data/{name}/encrypt_data.txt", "w") as file:
                    if not "404 Not Found" in contenu_actuel_chiffrer:
                        file.write(contenu_actuel_chiffrer)

                contenu_actuel = contenu_actuel_chiffrer_extract

                # Tant qu'il y a des correspondances

                password = self.password

                while match:
                    # if 1==1:
                    try:

                        # Récupérer le message avec les balises
                        message = "---BEGIN SIGNED CRRO MESSAGE---" + match.group(1) + "---END SIGNED CRRO MESSAGE---"

                        #print("Message:")
                        #print(message)

                        message_encrypt = str(message)

                        try:

                            sign_yes_or_no, message_only = crro.verify_signature(public_key, message_encrypt)

                        except Exception as e:
                            print(e)

                        #print("sign_yes_or_no", sign_yes_or_no)

                        if sign_yes_or_no == True:
                            #print("Message encode:", message_only)

                            if "---BEGIN SIGNED CRRO IMAGE---" in message_only:
                                message_only = message_only.replace("---BEGIN SIGNED CRRO IMAGE---", "")
                                try:
                                    message = crro.decrypt(private_key, message_only)

                                    message = message[2:-1]
                                    # Utiliser codecs.escape_decode pour convertir la chaîne en bytes
                                    message, _ = codecs.escape_decode(message)

                                except Exception as e:
                                    match = pattern.search(contenu_actuel, match.end())
                                    print("Signature valid but decryption failed the message is pass")
                                    continue



                                self.all_data = self.all_data + "---Them_Image---" + base64.urlsafe_b64encode(message).decode() + "---End_Message---"

                                self.model.add_message(USER_THEM, image_bytes=message)
                            else:



                                try:
                                    message = crro.decrypt(private_key, message_only)#.decode()

                                except Exception as e:
                                    match = pattern.search(contenu_actuel, match.end())
                                    print("Signature valid but decryption failed the message is pass")
                                    continue

                                #print("message", message)

                                message = str(message)

                                #print("decypted message", message)

                                # Ajouter le message au champ de texte
                                # all_messages.append(message)


                                self.all_data = self.all_data + "---Them_Message---" + message + "---End_Message---"


                                self.model.add_message(USER_THEM, message)

                            # Trouver le prochain message correspondant
                            match = pattern.search(contenu_actuel, match.end())




                        else:
                            #print("personal_public_key", personal_public_key, "    message", message)

                            try:

                                sign_yes_or_no, message = crro.verify_signature(personal_public_key, message)
                            except Exception as e:
                                print(e)
                            print("message after signature verify and sign:", sign_yes_or_no, message)

                            if sign_yes_or_no == True:
                                message = message.split("---BEGIN CRRO MESSAGE---")
                                print("Message encode[0] :", message[0])

                                if "__IMAGE__" in message[0]:
                                    print("in if begin Image")
                                    #print("message[2]", message[2])
                                    #print("private_key", private_key)
                                    #print("all data image", "---BEGIN CRRO MESSAGE---" + message[2])

                                    try:
                                        message = crro.decrypt(private_key,
                                                               "---BEGIN CRRO MESSAGE---" + message[2]).decode()

                                        #message = decode_base64_to_pixmap(message)

                                        #print("reduced_quality_bytes after ",message)

                                        message = message[2:-1]
                                        # Utiliser codecs.escape_decode pour convertir la chaîne en bytes
                                        message, _ = codecs.escape_decode(message)


                                    except Exception as e:
                                        match = pattern.search(contenu_actuel, match.end())
                                        print("Signature valid but decryption failed the message is pass")
                                        continue

                                    self.all_data = self.all_data + "---Your_Image---" + base64.urlsafe_b64encode(message).decode() + "---End_Message---"

                                    print("Image bytes: ", message)

                                    self.model.add_message(USER_ME, image_bytes=message)
                                else:

                                    try:
                                        message = crro.decrypt(private_key,
                                                               "---BEGIN CRRO MESSAGE---" + message[2]).decode()

                                    except Exception as e:
                                        print("error: ", e)
                                        match = pattern.search(contenu_actuel, match.end())
                                        print("Signature valid but decryption failed the message is pass")
                                        continue

                                    #print("message", message)

                                    message = str(message)

                                    #print("decypted message", message)

                                    # Ajouter le message au champ de texte
                                    # all_messages.append(message)


                                    self.all_data = self.all_data + "---Your_Message---" + message + "---End_Message---"

                                    self.model.add_message(USER_ME, message)

                                # Trouver le prochain message correspondant
                                match = pattern.search(contenu_actuel, match.end())


                            else:
                                match = pattern.search(contenu_actuel, match.end())

                    except Exception as e:
                        print("error during get contenu", e)

                        # Mettre à jour le contenu affiché dans le champ de texte à la fin
                        # contenu_actuel = "".join(all_messages)

                    try:

                        #print("contenu actuel", contenu_actuel)

                        print("self.all_data", self.all_data)

                        self.start_contenu = contenu_actuel_chiffrer
                    except Exception as e:
                        print("error during after get contenu", e)

                if self.all_data.strip():
                    print("all data ", self.all_data, "End all data")
                    with open(f"./chat_data/{name}/chat_data.txt", "w") as file:
                        print(password)
                        encrypted_data = scrro.encrypt(password, str(self.all_data).encode()).decode()

                        file.write(encrypted_data)

                print("we are out!")

    def save_keys(self, key):

        print("in save key")
        private_key = self.champ_private_key.text()
        name = self.champ_nom.text()
        public_key = self.champ_public_key.text()

        name = name.encode()

        private_key = base64.urlsafe_b64decode(private_key)

        with open("key_pair.txt", "w") as file:
            if key == False:
                encrypted_key = "no encryption: " + str(base64.urlsafe_b64encode(private_key).decode())
                encrypted_name = str(name.decode())
            else:
                encrypted_key = scrro.encrypt(key, private_key, padding=False).decode()
                encrypted_name = scrro.encrypt(key, name).decode()

            encrypted_name_and_keys = encrypted_key + "\n" + encrypted_name + "\n" + public_key
            file.write(encrypted_name_and_keys)

    @try_except
    def first_time(self, password, name):
        self.champ_nom.setText(name)
        self.generate_keys()
        self.champ_server.setText("Error during connexion to: ")

        # mon_thread = threading.Thread(target=self.get_contenu_in_thread())

        # Lancer le thread
        # mon_thread.start()

        self.save_keys(password)

    def show_fisrt_time_password_windows(self, start):
        for_what = "first_time"
        get_password = Get_Passord(self, for_what, start=False)
        get_password.exec_()

    def show_password_windows_access(self, start):
        for_what = "access"
        get_password = Get_Passord(self, for_what, start=True)
        get_password.exec_()

    def show_contact_windows(self, start):
        get_contact = Get_Contact(self)
        get_contact.exec_()

    def show_password_windows_save(self):
        for_what = "save"
        get_password = Get_Passord(self, for_what)
        get_password.exec_()

    def get_contenu_in_thread(self):
        self.fill_server_info()
        # self.timer.start(700)

    def access_key(self, key, start=False, password=True):

        self.password = key
        print("in access")

        print(key)
        with open("key_pair.txt", "r") as file:

            encrypted_name_and_keys = file.read()

            encrypted_key, encrypted_name, public_key = encrypted_name_and_keys.split("\n")

            print("encrypted_private_key", encrypted_key)

            print("encrypted_name", encrypted_name)

            print("public_key", public_key)

            if password == True:

                # encrypted_key = base64.urlsafe_b64decode(encrypted_key)

                # encrypted_name = base64.urlsafe_b64decode(encrypted_name)
                # try:

                decrypted_private_key = scrro.decrypt(key, encrypted_key, padding=False)

                decrypted_name = scrro.decrypt(key, encrypted_name)

                self.champ_private_key.setText(base64.urlsafe_b64encode(decrypted_private_key).decode())
                self.champ_public_key.setText(public_key)
                self.champ_nom.setText(decrypted_name.decode())

            else:
                encrypted_key = encrypted_key.replace("no encryption: ", "")
                self.champ_private_key.setText(encrypted_key)
                self.champ_public_key.setText(public_key)
                self.champ_nom.setText(encrypted_name)

            if start == True:
                print("starr=True", start)

                with open("parameters.txt", "r") as file:
                    data = file.read()
                    data = data.split(";")

                try:
                    # self.champ_name_contact.setText(data[0])
                    # self.champ_server.setText(data[1])
                    # self.champ_public_key2.setText(data[2])
                    # self.label_name_current.setText(f" Chat with: {data[0]}")
                    # self.get_contenu(start=True)
                    self.fill_info_contact(index=0, start=True)

                except Exception as e:
                    print("last contact seems None", e)

                self.get_contenu(start=True)  # initialy with a start = True


            else:

                print("starr False", start)

    def generate_keys(self):

        self.private_key = crro.generate_private_key()

        self.public_key = crro.generate_public_key(self.private_key)

        self.private_key = self.private_key.to_bytes((self.private_key.bit_length() + 7) // 8, byteorder='big')

        self.champ_private_key.setText(base64.urlsafe_b64encode(self.private_key).decode())
        self.champ_public_key.setText(str(self.public_key))

    def show_chat(self):

        self.text_edit.show()
        self.champ_message.show()
        self.send_button.show()
        self.label_name_current.show()
        self.button_smiley.show()
        self.show_smiley = 2

        self.champ_private_key.hide()
        self.champ_public_key.hide()
        self.generate_key_button.hide()
        self.label_privee.hide()
        self.label_public.hide()
        self.champ_server.hide()
        self.label_server.hide()
        self.get_key_button.hide()
        self.save_key_button.hide()
        self.champ_public_key2.hide()
        self.label_public_key2.hide()
        self.champ_nom.hide()
        self.label_nom.hide()
        self.label_contacts.hide()
        self.list_contacts.hide()
        self.button_add_contact.hide()
        self.see_private_key.hide()
        self.label_name_contact.hide()
        self.champ_name_contact.hide()


        self.center_widget.setContentsMargins(0, 0, 0, 0)

        # self.text_edit.scrollToBottom()

    def show_contacts(self):
        self.text_edit.hide()
        self.champ_message.hide()
        self.send_button.hide()
        self.champ_private_key.hide()
        self.champ_public_key.hide()
        self.generate_key_button.hide()
        self.label_privee.hide()
        self.label_public.hide()
        self.champ_server.hide()
        self.label_server.hide()
        self.get_key_button.hide()
        self.save_key_button.hide()
        self.champ_public_key2.hide()
        self.label_public_key2.hide()
        self.champ_nom.hide()
        self.label_nom.hide()
        self.see_private_key.hide()
        self.label_name_current.hide()
        self.label_name_contact.hide()
        self.champ_name_contact.hide()
        self.widget_button.hide()
        self.button_smiley.hide()

        self.label_contacts.show()
        self.list_contacts.show()
        self.button_add_contact.show()

        self.center_widget.setContentsMargins(5, 5, 5, 5)

    def show_server(self):
        self.champ_private_key.hide()
        self.champ_public_key.hide()
        self.generate_key_button.hide()
        self.label_privee.hide()
        self.label_public.hide()
        self.text_edit.hide()
        self.champ_message.hide()
        self.send_button.hide()
        self.get_key_button.hide()
        self.save_key_button.hide()
        self.champ_nom.hide()
        self.label_nom.hide()
        self.label_contacts.hide()
        self.list_contacts.hide()
        self.button_add_contact.hide()
        self.see_private_key.hide()
        self.label_name_current.hide()
        self.widget_button.hide()
        self.button_smiley.hide()

        self.champ_server.show()
        self.label_server.show()
        self.champ_public_key2.show()
        self.label_public_key2.show()
        self.label_name_contact.show()
        self.champ_name_contact.show()

        self.center_widget.setContentsMargins(5, 5, 5, 5)

    def show_use_key(self):
        self.text_edit.hide()
        self.champ_message.hide()
        self.send_button.hide()
        self.champ_server.hide()
        self.label_server.hide()
        self.champ_public_key2.hide()
        self.label_public_key2.hide()
        self.label_contacts.hide()
        self.list_contacts.hide()
        self.button_add_contact.hide()
        self.label_name_contact.hide()
        self.champ_name_contact.hide()
        self.widget_button.hide()
        self.button_smiley.hide()

        self.champ_private_key.show()
        self.champ_public_key.show()
        self.generate_key_button.show()
        self.label_privee.show()
        self.label_public.show()
        self.get_key_button.show()
        self.save_key_button.show()
        self.champ_nom.show()
        self.label_nom.show()
        self.see_private_key.show()

        self.center_widget.setContentsMargins(5, 5, 5, 5)


if __name__ == '__main__':
    start_time = time.time()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())