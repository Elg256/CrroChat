# import sys
# from urllib.request import urlopen

import requests
import shutil
import threading
from multiprocessing import Process, Queue
import json
from json.decoder import JSONDecodeError

# import codecs


from PySide6.QtCore import QAbstractListModel, QMargins, QPoint, QSize, Qt, QRect, QThread, Signal, QUrl
from PySide6.QtGui import QColor, QFontMetrics, QPen, QFont, QPixmap, QStandardItemModel, QStandardItem, QIcon, QBrush, \
    QImage, QPalette, QPolygon
# from PySide6 import QtCore
import os
# import threading
# import time  # pls delete this it is for debug

from PySide6.QtGui import QImage, QPixmap, QAction, QPainterPath, QCursor
from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QSize, Qt, QItemSelectionModel, QModelIndex
from PySide6.QtMultimedia import QSoundEffect, QMediaPlayer, QAudioOutput

# from PySide6.QtGui import
from PySide6.QtWidgets import (
    QFileDialog,
    QSpacerItem,
    QMessageBox,
    QAbstractItemView,

    QApplication,
    QLineEdit,
    QListView,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QLayout,
    QWidget,
    QStyledItemDelegate,
    QMenu
)

import sys
import time
from datetime import datetime, timezone

from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QTextEdit, QPushButton, QLineEdit, QLabel, \
    QSizePolicy, \
    QDialog, QHBoxLayout
from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor, QTextCursor

from cryptcrro.asymetric import crro
from cryptcrro.symetric import crro as scrro
import re
import hashlib
import base64

# import struct

USER_ME = 0
USER_THEM = 1

BUBBLE_COLORS = {USER_ME: "#90caf9", USER_THEM: "#5db67d"}

BUBBLE_PADDING_THEM = QMargins(20, 5, 210, 5)
BUBBLE_PADDING_ME = QMargins(210, 5, 20, 5)

TEXT_PADDING_THEM = QMargins(25, 15, 235, 15)
TEXT_PADDING_ME = QMargins(220, 15, 25, 15)


def kdf(password):
    return hashlib.scrypt(
        password.encode(),
        salt=b"CryptCrroSalt",
        n=2 ** 14,
        r=8,
        p=1,
        dklen=32
    )


def long_poll(file_name, url, queue):
    last_timestamp = None
    # url = "http://crro-server.alwaysdata.net/CrroChat/long_poll.php"
    url = f"{url}/CrroChat/long_poll.php"

    #while not self.stop_event.is_set():
    while True:
        print(f"in loop {file_name}")
        params = {
            "file_name": file_name
        }

        if last_timestamp:
            params["since"] = last_timestamp
            print("last_timestamp", last_timestamp)

        try:
            response = requests.get(url, params=params, timeout=35)
            messages = response.json()
            print(messages)

            if messages:
                for msg in messages:
                    print(f"[{msg['timestamp']}] ➤ {msg['msg']}")
                    # self.decrypt_and_show_message(msg['msg'])
                    queue.put(msg)
                last_timestamp = messages[-1]['timestamp']
        except requests.exceptions.Timeout:
            pass  # Silence, juste une attente normale
        except Exception as e:
            print("Erreur :", e)


def get_contact_by_name(contacts_dict, name):
    for contact in contacts_dict.get("contacts", []):
        if contact.get("name") == name:
            return contact
    return None


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
        image = image.scaled(max_image_size, Qt.AspectRatioMode.KeepAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)

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

    return wrapper


def bytes_to_pixmap(image_bytes):
    image = QImage()
    image.loadFromData(image_bytes)
    return QPixmap.fromImage(image)


""""
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
        print(f"Enter key pressed! Text: {text}")"""


class MessageDelegate(QStyledItemDelegate):
    """
    Dessine chaque message.
    """

    def paint(self, painter, option, index):
        user, text, image = index.model().data(index, Qt.ItemDataRole.DisplayRole)

        if user == USER_ME:
            bubblerect = option.rect.marginsRemoved(BUBBLE_PADDING_ME)
            contentrect = option.rect.marginsRemoved(TEXT_PADDING_ME)
        elif user == USER_THEM:
            bubblerect = option.rect.marginsRemoved(BUBBLE_PADDING_THEM)
            contentrect = option.rect.marginsRemoved(TEXT_PADDING_THEM)

        # Dessinez le contour de la bulle
        painter.setPen(QPen(QColor("#000000"), 1))
        painter.drawRoundedRect(bubblerect, 11, 11)

        # Dessinez la bulle
        painter.setBrush(QColor(BUBBLE_COLORS[user]))
        painter.drawRoundedRect(bubblerect, 11, 11)

        # Dessinez le pointeur du triangle
        if user == USER_ME:
            p1 = bubblerect.topRight()
        else:
            p1 = bubblerect.topLeft()

        polygon = QPolygon([
            p1 + QPoint(-19, 0),
            p1 + QPoint(19, 0),
            p1 + QPoint(0, 19)
        ])
        painter.setPen(QPen(QColor(BUBBLE_COLORS[user]), 1))
        painter.drawPolygon(polygon)

        painter.setPen(QPen(QColor("#000000"), 2))
        if text:
            # Augmentez la taille de la police
            font = QFont()
            font.setPointSize(10)
            painter.setFont(font)
            painter.drawText(contentrect, Qt.TextFlag.TextWordWrap, text)
        elif image:
            # Centrez l'image dans la bulle
            img_rect = QRect(contentrect.left(), contentrect.top(), image.width(), image.height())
            img_rect.moveCenter(bubblerect.center())
            painter.drawPixmap(img_rect, image)

    def sizeHint(self, option, index):
        user, text, image = index.model().data(index, Qt.ItemDataRole.DisplayRole)
        metrics = option.fontMetrics

        if text:
            font = option.font
            font.setPointSize(10)
            metrics = QFontMetrics(font)

            text_width = option.rect.width() - TEXT_PADDING_ME.left() - TEXT_PADDING_ME.right()
            text_height = metrics.boundingRect(QRect(0, 0, text_width, 0), Qt.TextFlag.TextWordWrap, text).height()
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
        if role == Qt.ItemDataRole.DisplayRole:
            return self.messages[index.row()]

    def rowCount(self, index):
        return len(self.messages)

    def clear(self):
        self.beginResetModel()
        self.messages = []
        self.endResetModel()

    def add_message(self, who, text=None, image_bytes=None, max_image_size=QSize(200, 200)):
        if text and text.strip():
            self.messages.append((who, text, None))
        elif image_bytes:
            image = bytes_to_pixmap(image_bytes)
            if image.size().width() > max_image_size.width() or image.size().height() > max_image_size.height():
                image = image.scaled(max_image_size, Qt.AspectRatioMode.KeepAspectRatio,
                                     Qt.TransformationMode.SmoothTransformation)
            self.messages.append((who, None, image))
        self.layoutChanged.emit()
        bottom_index = self.createIndex(len(self.messages) - 1, 0)
        #self.main_window.text_edit.scrollToBottom()




class By_Elg256(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle('About Elg256')
        self.setWindowIcon(QIcon("img/logo.png"))

        self.setWindowFlags(self.windowFlags() | Qt.WindowType.MSWindowsFixedSizeDialogHint)

        pixmap = QPixmap("img/logo_crro.png")
        scaled_pixmap = pixmap.scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatio)

        label_image = QLabel()
        label_image.setPixmap(scaled_pixmap)

        label_image.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.layout = QHBoxLayout(self)

        self.label = QLabel("""
                <p>This software is made by Elg256 and is part of the crro-software project.<br>
                The crro-software project is all the cryptography related software from Elg256 learn more at: <a href="https://crro-projects.neocities.org/">https://crro-projects.neocities.org/</a></p></br>
                <p>Our OpenPGP public key hash is: 08E60E37D69E2787376B578762FB68E055D23FE9</p>
                <p></p>
                <p>For any issus or question you can use our github or email.<br>
                Github: <a href="https://github.com/Elg256">https://github.com/Elg256</a></br>
                <br>Email:elgremonter@gmail.com</p></br>

                """)

        self.label.setOpenExternalLinks(True)
        self.layout.addWidget(label_image)
        self.layout.addWidget(self.label)


class About(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle('About CrroChat')
        self.setWindowIcon(QIcon("img/logo.png"))

        self.setWindowFlags(self.windowFlags() | Qt.WindowType.MSWindowsFixedSizeDialogHint)

        pixmap = QPixmap("img/logo.png")
        scaled_pixmap = pixmap.scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio)

        label_image = QLabel()
        label_image.setPixmap(scaled_pixmap)

        label_image.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.layout = QHBoxLayout(self)

        self.label = QLabel("""
                <p>CrroChat version v0.1.0</p>
                <p>Copyright (C) 2023-2024 Elg256</p>
                <p>Visit <a href="https://crro.neocities.org">https://crro.neocities.org</a> for further information about the software.</p>
                <p>The source code is available from <a href="https://github.com/Elg256/CrroChat">https://github.com/Elg256/CrroChat</a>.</p>
                <p>This is experimental software.<br>
                Distributed under the MIT software license, see the accompanying file COPYING or <a href="https://opensource.org/licenses/MIT">https://opensource.org/licenses/MIT</a></p>
                This product includes software developed by the crro-software Project by using 
                <br>the cryptocrro librairie available at <a href="https://github.com/Elg256/Cryptcrro">https://github.com/Elg256/Cryptcrro</a>.</br>
                </br><p>This program uses PySide version 6 under the LGPLv3 license.
                <br>Please see <a href="https://qt.io/qt-licensing">qt.io/qt-licensing</a> for an overview of Qt licensing.</p>
                """)

        self.label.setOpenExternalLinks(True)
        self.layout.addWidget(label_image)
        self.layout.addWidget(self.label)


class Bitcoin_donation(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle('Bitcoin Donation')
        self.setWindowIcon(QIcon("img/logo.png"))

        self.setWindowFlags(self.windowFlags() | Qt.WindowType.MSWindowsFixedSizeDialogHint)

        self.layout = QHBoxLayout(self)
        self.label = QLabel("Bitcoin address:")
        self.layout.addWidget(self.label)
        self.btc_addr = "bc1q8j946v6gcnpumdjhdem2hhameh33fe4cy4xpqt"
        self.field_addr = QLineEdit(self.btc_addr)
        self.layout.addWidget(self.field_addr)
        self.field_addr.setReadOnly(True)
        self.field_addr.setFixedWidth(self.field_addr.fontMetrics().boundingRect(self.btc_addr).width() + 20)

        self.copy_button = QPushButton("Copy")
        self.layout.addWidget(self.copy_button)
        self.copy_button.clicked.connect(self.copy)

    def copy(self):
        clipboard = QApplication.clipboard()

        clipboard.setText(self.btc_addr)


class Get_Passord(QDialog):
    def __init__(self, main_window, for_what, start=False, parent=None):
        super().__init__(parent)
        self.for_what = for_what
        self.start = start
        self.main_window = main_window
        self.setWindowTitle('Password')
        self.setWindowIcon(QIcon("img/logo.png"))
        self.layout = QVBoxLayout(self)

        if self.for_what == "first_time":
            self.label_name = QLabel("Name: ", self)
            self.layout.addWidget(self.label_name)

            self.champ_name = QLineEdit(self)
            self.layout.addWidget(self.champ_name)

        self.label = QLabel('Password:', self)
        self.layout.addWidget(self.label)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.input_field = QPasswordLineEdit(self)
        self.layout.addWidget(self.input_field)

        self.ok_button = QPushButton('Ok', self)
        self.layout.addWidget(self.ok_button)

        self.ok_button.clicked.connect(self.take_user_input)

        if self.for_what == "first_time":
            self.label.setAlignment(Qt.AlignmentFlag.AlignLeft)
            self.label_vide = QLabel("If you don't want to set \na Password just don't put one ", self)
            self.layout.addWidget(self.label_vide)


    def take_user_input(self, checked=False):
        print("before funct")
        user_input = self.input_field.text()
        print("before funct")

        if user_input.strip():
            print("in user_input.strip()")
            key = kdf(user_input)
            print(key)
        else:
            key = ""

        print("in hash: ", key)
        # try:

        if self.for_what == "first_time":
            if key == "":
                key = False

            self.main_window.first_time(key, self.champ_name.text())

        if self.start == True:

            self.main_window.access_key(key, start=True)

        if self.for_what == "save":
            self.main_window.save_keys(key)
        elif self.for_what == "access":
            self.main_window.access_key(key)


        # except Exception as e:
        # print(e)
        self.accept()



class Find_server(QDialog):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)

        self.setWindowTitle('Find a server')
        self.setWindowIcon(QIcon("img/logo.png"))
        self.layout = QVBoxLayout(self)

        self.text_label = QLabel("You can use your own http server or use a community server.\n"
                                 "you don't need to trust the server for your messages to being secure.\n"
                                 "but a non-trusted server can be down when you don't want it to be.")
        self.layout.addWidget(self.text_label)

        self.server_layout1 = QHBoxLayout()
        self.layout.addLayout(self.server_layout1)

        self.server_layout2 = QHBoxLayout()
        self.layout.addLayout(self.server_layout2)

        self.server_layout3 = QHBoxLayout()
        self.layout.addLayout(self.server_layout3)

        self.label_1 = QLabel("Community server 1:")
        self.field_server1 = QLineEdit("")
        self.field_server1.setReadOnly(True)
        self.field_server1.setMinimumWidth(250)
        self.server_layout1.addWidget(self.label_1)
        self.server_layout1.addWidget(self.field_server1)

        self.button_copy1 = QPushButton("copy")
        self.server_layout1.addWidget(self.button_copy1)
        self.button_copy1.clicked.connect(lambda: self.copy_server_link(link=1))

        self.label_2 = QLabel("Community server 2:")
        self.field_server2 = QLineEdit()
        self.field_server2.setReadOnly(True)
        self.server_layout2.addWidget(self.label_2)
        self.server_layout2.addWidget(self.field_server2)

        self.button_copy2 = QPushButton("copy")
        self.server_layout2.addWidget(self.button_copy2)
        self.button_copy2.clicked.connect(lambda: self.copy_server_link(link=2))

        self.label_3 = QLabel("Community server 3:")
        self.field_server3 = QLineEdit()
        self.field_server3.setReadOnly(True)
        self.server_layout3.addWidget(self.label_3)
        self.server_layout3.addWidget(self.field_server3)

        self.button_copy3 = QPushButton("copy")
        self.server_layout3.addWidget(self.button_copy3)
        self.button_copy3.clicked.connect(lambda: self.copy_server_link(link=3))
        self.button_copy3.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)

    def copy_server_link(self, link):
        if link == 1:
            server = self.field_server1.text()
        elif link == 2:
            server = self.field_server2.text()
        elif link == 3:
            server = self.field_server3.text()
        clipboard = QApplication.clipboard()

        clipboard.setText(server)


class Get_Contact(QDialog):
    def __init__(self, main_window, key, parent=None):
        super().__init__(parent)

        try:
            self.key = key
            self.setWindowIcon(QIcon("img/logo.png"))

            self.main_window = main_window  # Référence à l'instance de MainWindow
            self.setWindowTitle('Add contact')

            # Créer le layout principal vertical
            self.layout = QVBoxLayout(self)

            # Largeur fixe pour les labels
            label_width = 80

            # Layout pour le nom
            self.layout_name = QHBoxLayout()
            self.layout.addLayout(self.layout_name)
            self.layout_name.setContentsMargins(3, 3, 3, 3)

            self.label_nom = QLabel("<b>Name:</b>")
            self.label_nom.setFixedWidth(label_width)
            self.layout_name.addWidget(self.label_nom)

            self.champ_name = QLineEdit()
            # self.champ_nom.setStyleSheet("background-color: white;")
            self.layout_name.addWidget(self.champ_name)
            self.champ_name.setPlaceholderText("Name for the contact list, choosen by you")

            self.layout_private_key = QHBoxLayout()
            self.layout.addLayout(self.layout_private_key)
            self.layout_private_key.setContentsMargins(3, 3, 3, 3)

            self.label_server = QLabel("<b>Server:</b>")
            self.label_server.setFixedWidth(label_width)
            self.layout_private_key.addWidget(self.label_server)

            self.server = QLineEdit()
            self.server.setMinimumWidth(200)
            # self.champ_private_key.setStyleSheet("background-color: white;")
            self.layout_private_key.addWidget(self.server)
            self.server.setPlaceholderText("The server you will discuss on")

            self.button_find_server = QPushButton("Find a server")
            self.layout_private_key.addWidget(self.button_find_server)
            self.button_find_server.clicked.connect(self.show_find_server_windows)
            self.button_find_server.setToolTip("Tips for choosing your server")

            # Layout pour la clé publique
            self.layout_public_key = QHBoxLayout()
            self.layout.addLayout(self.layout_public_key)
            self.layout_public_key.setContentsMargins(3, 3, 3, 3)

            self.label_public = QLabel("<b>Public key: </b>")
            self.label_public.setFixedWidth(label_width)
            self.layout_public_key.addWidget(self.label_public)

            self.public_key = QLineEdit()
            # self.champ_public_key.setStyleSheet("background-color: white;")
            self.layout_public_key.addWidget(self.public_key)
            self.public_key.setPlaceholderText("Enter the key your correspondent gave you")

            self.ok_button = QPushButton('Add contact', self)
            self.layout.addWidget(self.ok_button)
            self.ok_button.clicked.connect(self.take_user_input)

        except Exception as e:
            print("An error occurred:", e)

    def show_find_server_windows(self):

        find_server = Find_server(self)
        find_server.exec()

    def take_user_input(self, checked=False):
        try:

            filename = "contacts.json"
            if os.path.exists(filename):
                with open(filename, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        decrypted_json = scrro.decrypt(self.key, content)
                        data = json.loads(decrypted_json)
                    else:
                        data = {"contacts": []}
            else:
                data = {"contacts": []}

            name = self.champ_name.text()
            if any(c["name"] == name for c in data["contacts"]):
                QMessageBox.information(self, "Contact with same name", "This name is already use.")
                return

            folder_path = f'./chat_data/{name}'
            os.mkdir(folder_path)

            file1_path = os.path.join(folder_path, "client_chat_data")
            file2_path = os.path.join(folder_path, "last_message")

            open(file1_path, "w", encoding="utf-8").close()
            open(file2_path, "w", encoding="utf-8").close()

            print("file created")

            data["contacts"].append({
                "name": name,
                "server": self.server.text(),
                "public_key": self.public_key.text()
            })

            json_text = json.dumps(data, indent=4)
            encrypted_text = scrro.encrypt(self.key, json_text.encode())
            print("self.key", self.key)

            with open(filename, "wb") as f:
                f.write(encrypted_text)

            self.main_window.refresh_contact_list()

            # except Exception as e:
            # print(e)
            self.accept()
        except Exception as e:
            print(e)


class QPasswordLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEchoMode(QLineEdit.EchoMode.Password)

        self.iconShow = QIcon('img/eye_blind.png')
        self.iconHide = QIcon('img/eye.png')

        self.showPassAction = QAction(self.iconShow, 'Show password', self)
        self.addAction(self.showPassAction, QLineEdit.ActionPosition.TrailingPosition)
        self.showPassAction.setCheckable(True)
        self.showPassAction.toggled.connect(self.toggle_password_visibility)

    def toggle_password_visibility(self, show):
        if show:
            self.setEchoMode(QLineEdit.EchoMode.Normal)
            self.showPassAction.setIcon(self.iconHide)
        else:
            self.setEchoMode(QLineEdit.EchoMode.Password)
            self.showPassAction.setIcon(self.iconShow)


class Mod_Contact(QDialog):
    def __init__(self, main_window, contact_name, key, parent=None):
        super().__init__(parent)

        try:
            self.key = key
            self.setWindowIcon(QIcon("img/logo.png"))

            self.main_window = main_window  # Référence à l'instance de MainWindow
            self.setWindowTitle('Contact info')

            # Créer le layout principal vertical
            self.layout = QVBoxLayout(self)

            self.line_to_modif = None
            self.data = None

            # Largeur fixe pour les labels
            label_width = 80

            # Layout pour le serveur (anciennement clé privée)
            self.layout_private_key = QVBoxLayout()
            self.layout.addLayout(self.layout_private_key)
            self.layout_private_key.setContentsMargins(3, 3, 3, 3)

            # Layout pour le nom
            self.layout_name = QHBoxLayout()
            self.layout.addLayout(self.layout_name)
            self.layout_name.setContentsMargins(3, 3, 3, 3)

            self.label_nom = QLabel("<b>Name:</b>")
            self.label_nom.setFixedWidth(label_width)
            self.layout_name.addWidget(self.label_nom)

            self.champ_name = QLineEdit()
            self.champ_name.setText(contact_name)
            # self.champ_nom.setStyleSheet("background-color: white;")
            self.layout_name.addWidget(self.champ_name)

            # Layout pour le serveur
            self.layout_server = QHBoxLayout()
            self.layout.addLayout(self.layout_server)
            self.layout_server.setContentsMargins(3, 3, 3, 3)

            self.label_server = QLabel("<b>Server:</b>")
            self.label_server.setFixedWidth(label_width)
            self.layout_server.addWidget(self.label_server)

            self.champ_server = QLineEdit()
            self.champ_server.setMinimumWidth(350)
            # self.champ_nom.setStyleSheet("background-color: white;")
            self.layout_server.addWidget(self.champ_server)

            # Layout for public key
            self.layout_key = QHBoxLayout()
            self.layout.addLayout(self.layout_key)
            self.layout_key.setContentsMargins(3, 3, 3, 3)

            self.label_key = QLabel("<b>Public key:</b>")
            self.label_key.setFixedWidth(label_width)
            self.layout_key.addWidget(self.label_key)

            self.champ_key = QLineEdit()
            # self.champ_nom.setStyleSheet("background-color: white;")
            self.layout_key.addWidget(self.champ_key)

            self.modify_button = QPushButton('Save change', self)
            self.layout.addWidget(self.modify_button)
            self.modify_button.clicked.connect(self.modify_contact)

            self.take_user_input()

        except Exception as e:
            print("An error occurred:", e)

    def take_user_input(self, checked=False):
        try:
            self.data = None
            self.contact_to_modif = self.champ_name.text()

            with open("./contacts.json", "rb") as file:
                data = file.read()
                if data:
                    decrypted_data = scrro.decrypt(self.key, data)
                    self.data = json.loads(decrypted_data)
            contact = get_contact_by_name(self.data, self.contact_to_modif)
            self.champ_server.setText(contact["server"])
            self.champ_key.setText(contact["public_key"])

            self.main_window.refresh_contact_list()

        except Exception as e:
            print(e)

    def modify_contact(self, checked=False):
        for contact in self.data["contacts"]:
            print(contact, self.contact_to_modif)
            if contact["name"] == self.contact_to_modif:
                contact["name"] = self.champ_name.text()
                contact["server"] = self.champ_server.text()
                contact["public_key"] = self.champ_key.text()
                if contact["name"] != self.contact_to_modif:
                    for entry in os.listdir("./chat_data"):
                        full_path = os.path.join("./chat_data", entry)
                        if os.path.isdir(full_path) and entry == self.contact_to_modif:
                            new_path = os.path.join("./chat_data", contact["name"])
                            os.rename(full_path, new_path)
                            break
                if self.contact_to_modif == self.main_window.current_contact_name:
                    self.main_window.current_contact_name = contact["name"]
                    temp_data = json.dumps({"contact_name": contact["name"], "server": contact["server"],
                                            "public_key": contact["public_key"]}).encode()
                    encrypted_data = scrro.encrypt(self.main_window.password, temp_data).decode('utf-8')
                    with open("parameters.json", "r") as file:
                        content = file.read().strip()
                        if content:
                            file.seek(0)
                            data = json.load(file)
                            data['parameters']['last_contact'] = encrypted_data
                    with open("parameters.json", "w") as file:
                        json.dump(data, file, indent=4)
                    self.main_window.label_name_current.setText(f" Chat with: {self.main_window.current_contact_name}")
            break
        with open("./contacts.json", "wb") as file:
            data = json.dumps(self.data, indent=4)
            data_encrypted = scrro.encrypt(self.key, data.encode())
            print("self.key", self.key)
            file.write(data_encrypted)
        self.main_window.refresh_contact_list()
        self.accept()


class Downloader(QThread):
    contentReady = Signal(bytes)

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
        # Emit the content pyqtSignal.
        self.contentReady.emit(content)


class MainWindow(QMainWindow):
    play_sound_get_signal = Signal()
    play_sound_send_signal = Signal()

    def __init__(self):
        super().__init__()

        self.password = None
        self.list_contacts_affiche = None
        self.only_contacts_name = []

        # start the thread to get all messages from queue
        self.process = None
        self.queue = Queue()

        # This start thread have been move to access key function
        #self.thread = threading.Thread(target=self.get_message, daemon=True)
        #self.thread.start()

        oImage = QImage("img/background.png")
        sImage = oImage.scaled(QSize(1000, 800))  # resize Image to widgets size
        palette = QPalette()
        palette.setBrush(QPalette.ColorRole.Window, QBrush(sImage))
        self.setPalette(palette)

        base_dir = os.path.dirname(__file__)
        sound_path_get = os.path.join(base_dir, "sound", "notif_get.wav")

        self.sound_get = QSoundEffect()
        self.sound_get.setSource(QUrl.fromLocalFile(sound_path_get))
        self.sound_get.setVolume(0.5)
        self.play_sound_get_signal.connect(self.sound_get.play)

        sound_path_send = os.path.join(base_dir, "sound", "notif_send.wav")
        self.sound_send = QSoundEffect()
        self.sound_send.setSource(QUrl.fromLocalFile(sound_path_send))
        self.sound_send.setVolume(0.5)
        self.play_sound_send_signal.connect(self.sound_send.play)


        self.show_emoji = 2

        self.all_data = ""

        self.stop_event = threading.Event()
        self.thread = None

        self.setWindowTitle("CrroChat")
        self.setGeometry(100, 100, 450, 450)
        self.setMinimumWidth(450)

        # self.setStyleSheet("background-color: #6da2d2;")

        # background-image: linear-gradient(rgba(0, 0, 255, 0.5), rgba(255, 255, 0, 0.5)),
        # url("../../media/examples/lizard.png");

        self.setWindowIcon(QIcon("img/logo.png"))

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
        # center_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_layout.addLayout(self.layout)

        self.center_widget = QWidget()
        self.center_widget.setStyleSheet("background-color:#9fc5e8;")

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

        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)

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

        # server_action = QAction('Server', self)
        # bar.addAction(server_action)
        # server_action.triggered.connect(self.show_server)

        key_action = QAction("Keys", self)
        bar.addAction(key_action)
        key_action.triggered.connect(self.show_use_key)

        # Menu Keys

        # Menu Edition
        edit_menu = bar.addMenu('About')
        version = QAction('Version 0.1', self)
        creator = QAction(QIcon('img/logo_crro.png'), 'By Elg256', self)
        support_us = QAction(QIcon('img/real_money.png'), "Support us", self)
        edit_menu.addAction(version)
        edit_menu.addAction(creator)
        edit_menu.addAction(support_us)
        version.triggered.connect(self.show_about_windows)
        creator.triggered.connect(self.show_elg256_windows)
        support_us.triggered.connect(self.show_donation_bitcoin_windows)

        self.h_layout = QHBoxLayout()
        self.h_layout.setContentsMargins(0, 0, 0, 0)
        # self.h_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

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
        self.current_contact_name = ""
        self.label_name_current = QLabel(f" Chat with: {self.current_contact_name}")
        self.label_name_current.setFont(QFont("arial", 11))
        self.label_name_current.setStyleSheet("background-color:#4285c2;"

                                              "color: white;")  # "border-radius: 3px;"
        self.label_name_current.setContentsMargins(0, 5, 0, 5)
        self.layout.addWidget(self.label_name_current)

        self.text_edit = QListView()
        self.layout.addWidget(self.text_edit)

        # Use our delegate to draw items in this view.
        self.text_edit.setItemDelegate(MessageDelegate())
        self.text_edit.setStyleSheet("""
                    QListView {
                        background-color: #eeeeee;
                    }

                    /* Barre de défilement verticale */
                    QScrollBar:vertical {
                        border: 0px solid #555555;
                        background: #6DA2D2;
                        width: 12px;

                    }
                    QScrollBar::handle:vertical {
                        background: #6DA2D2;

                    }
                    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                        background: #555555;
                        height: 5px;
                        subcontrol-position: bottom;
                        subcontrol-origin: margin;

                    }

                    /* Barre de défilement horizontale */
                    QScrollBar:horizontal {
                        border: 0px solid #555555;
                        background: #6DA2D2;
                        width: 12px;

                    }
                    QScrollBar::handle:horizontal {
                        background: #6DA2D2;

                    }
                    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                        background: #555555;
                        width: 10px;
                        subcontrol-position: bottom;
                        subcontrol-origin: margin;

                    }

                """)
        self.text_edit.setItemAlignment(Qt.AlignmentFlag.AlignCenter)
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
        self.widget_button.setStyleSheet("background-color: #9fc5e8;")  # c4dcd9

        # Ajoutez le widget parent au layout principal
        self.layout.addWidget(self.widget_button)

        button_emoji_theme = """
                    QPushButton {

                        border: none; 
                        border-radius: 4;

                        font-size: 22px;
                    }
                    QPushButton:pressed {
                        background-color: #6a6a6a; 
                    }
                    QPushButton:hover {
                        background-color: #6a6a6a; 
                    }
                """

        # Bouton 1
        button1 = QPushButton()
        icon = QIcon("img/emoji1.png")
        button1.setIcon(icon)

        button1.setStyleSheet(button_emoji_theme)
        button1.setIconSize(QSize(20, 20))
        button1.setMaximumSize(20, 20)
        button1.clicked.connect(
            lambda: self.insert_smiley("U+1F600"))
        self.button_layout.addWidget(button1, alignment=Qt.AlignmentFlag.AlignLeft)

        button2 = QPushButton()
        button2.setIcon(QIcon("img/emoji2.png"))
        button2.setIconSize(QSize(20, 20))
        button2.setMaximumSize(20, 20)
        button2.setStyleSheet(button_emoji_theme)
        button2.clicked.connect(
            lambda: self.insert_smiley("U+1F604"))

        self.button_layout.addWidget(button2, alignment=Qt.AlignmentFlag.AlignLeft)

        button3 = QPushButton()
        button3.setStyleSheet(button_emoji_theme)
        button3.setIcon(QIcon("img/emoji3.png"))
        button3.clicked.connect(
            lambda: self.insert_smiley("U+1F602"))
        button3.setIconSize(QSize(20, 20))
        button3.setMaximumSize(20, 20)
        self.button_layout.addWidget(button3, alignment=Qt.AlignmentFlag.AlignLeft)

        button4 = QPushButton()
        button4.setStyleSheet(button_emoji_theme)
        button4.clicked.connect(
            lambda: self.insert_smiley("U+1F605"))
        button4.setIcon(QIcon("img/emoji4.png"))
        button4.setIconSize(QSize(20, 20))
        button4.setMaximumSize(20, 20)
        self.button_layout.addWidget(button4, alignment=Qt.AlignmentFlag.AlignLeft)

        button5 = QPushButton()
        button5.setStyleSheet(button_emoji_theme)
        button5.clicked.connect(
            lambda: self.insert_smiley("U+1F60D"))
        button5.setIcon(QIcon("img/emoji5.png"))
        button5.setIconSize(QSize(20, 20))
        button5.setMaximumSize(20, 20)
        self.button_layout.addWidget(button5, alignment=Qt.AlignmentFlag.AlignLeft)

        button6 = QPushButton()
        button6.setStyleSheet(button_emoji_theme)
        button6.clicked.connect(
            lambda: self.insert_smiley("U+1F618 "))
        button6.setIcon(QIcon("img/emoji6.png"))
        button6.setIconSize(QSize(20, 20))
        button6.setMaximumSize(20, 20)
        self.button_layout.addWidget(button6, alignment=Qt.AlignmentFlag.AlignLeft)

        button7 = QPushButton()
        button7.setStyleSheet(button_emoji_theme)
        button7.clicked.connect(
            lambda: self.insert_smiley("U+1F610"))
        button7.setIcon(QIcon("img/emoji7.png"))
        button7.setIconSize(QSize(20, 20))
        button7.setMaximumSize(20, 20)
        self.button_layout.addWidget(button7, alignment=Qt.AlignmentFlag.AlignLeft)

        button8 = QPushButton()
        button8.setStyleSheet(button_emoji_theme)
        button8.clicked.connect(
            lambda: self.insert_smiley("U+1F60E	"))
        button8.setIcon(QIcon("img/emoji8.png"))
        button8.setIconSize(QSize(20, 20))
        button8.setMaximumSize(20, 20)
        self.button_layout.addWidget(button8, alignment=Qt.AlignmentFlag.AlignLeft)

        spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.button_layout.addItem(spacer)

        button_file_img_theme = """
                    QPushButton {
                        background-color: white;
                        border: none; 
                        border-radius: 3;


                    }
                    QPushButton:pressed {
                        background-color: #4f4f4f; 
                    }
                    QPushButton:hover {
                        background-color: #bababa; 
                    }
                """

        button_file = QPushButton()
        button_file.setStyleSheet(button_file_img_theme)
        button_file.setIcon(QIcon("img/add_file.png"))
        button_file.setToolTip("Send a file\n(Not working yet im on it)")
        button_file.setIconSize(QSize(16, 16))
        button_file.setMaximumSize(20, 20)
        # button1.clicked.connect(self.button1_clicked)
        self.button_layout.addWidget(button_file, alignment=Qt.AlignmentFlag.AlignRight)

        button_img = QPushButton()
        button_img.setStyleSheet(button_file_img_theme)
        button_img.setIcon(QIcon("img/add_img.png"))
        button_img.setToolTip("Send an image")
        button_img.setIconSize(QSize(20, 20))
        button_img.setMaximumSize(20, 20)
        button_img.clicked.connect(self.openFileNameDialog)
        self.button_layout.addWidget(button_img, alignment=Qt.AlignmentFlag.AlignRight)

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
        self.champ_message.setMaximumWidth(600)
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
                                                            alignment=Qt.AlignmentFlag.AlignLeft)

        # self.space_for_send_button = QSpacerItem(QSizePolicy.Expanding, QSizePolicy.Minimum)
        # self.space_for_send_button.setStyleSheet("background-color: white;")

        self.button_smiley = QPushButton("+")
        self.button_smiley.setToolTip("for sending images files or emojis")
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
        self.button_smiley.clicked.connect(self.show_emoji_funct)
        self.button_smiley.setFixedSize(20, 20)
        # self.layout_plus_button.addWidget(self.button_smiley, alignment=Qt.AlignmentFlag.AlignRight)

        self.layout.addLayout(self.layout_send_button_and_champ_message)

        self.layout_for_plus_and_send_button = QVBoxLayout()
        self.layout_for_plus_and_send_button.setContentsMargins(0, 0, 5, 0)
        self.layout_for_plus_and_send_button.setSpacing(0)

        self.widget_send_button_and_champ_message.setContentsMargins(0, 0, 0, 0)
        self.widget_send_button_and_champ_message.setLayout(self.layout_for_plus_and_send_button)

        self.layout_for_plus_and_send_button.addWidget(self.button_smiley, alignment=Qt.AlignmentFlag.AlignLeft)

        # self.send_button = QPushButton(" Send")
        self.send_button = QPushButton()
        icone = QIcon("img/send.png")
        self.send_button.setIcon(icone)
        self.send_button.setIconSize(QSize(24, 24))
        self.send_button.setToolTip("Send a message")

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

        # self.widget_send_button_and_champ_message.addWidget(self.send_button, alignment=Qt.AlignmentFlag.AlignLeft)
        # self.layout_send_button_and_champ_message.addItem(self.space_for_send_button)

        self.layout_for_plus_and_send_button.addWidget(self.send_button, alignment=Qt.AlignmentFlag.AlignLeft)

        self.start_contenu = ""

        self.label_contacts = QLabel(f" Contacts: ")
        self.label_contacts.setFont(QFont("arial", 11))
        self.label_contacts.setStyleSheet("background-color:#4285c2;"

                                          "color: white;")  # "border-radius: 3px;"
        self.label_contacts.setContentsMargins(0, 5, 0, 5)
        self.layout.addWidget(self.label_contacts)

        self.list_contacts = QListView()
        self.list_contacts.setMaximumWidth(600)
        self.list_contacts.setStyleSheet("background: white;"
                                         "font-size: 16px;")

        self.layout.addWidget(self.list_contacts)


        theme_blue_button = """
                QPushButton {
                    background-color: #4285c2;
                    color: #fafafa;
                    border: 1px solid #2f3235;
                    padding: 2px 5px;
                    margin: 1px;

                }
                QPushButton:hover {
                    background-color: #437db1;
                }
                QPushButton:pressed {
                    background-color: #a8a8a8;
                }
                QPushButton:disabled {
                    background-color: #f0f0f0;
                    color: #a9a9a9;
                    border-color: #dcdcdc;
                }
                """

        self.button_add_contact = QPushButton("Add contact")
        self.button_add_contact.clicked.connect(self.show_contact_windows)
        self.layout.addWidget(self.button_add_contact)
        self.button_add_contact.setToolTip("add a contact to your contact list")
        self.button_add_contact.setStyleSheet("""
                QPushButton {
                    background-color: #4285c2;
                    color: #fafafa;

                    border: 1px solid #2f3235;
                    padding: 5px 5px;
                    margin: 1px;

                }
                QPushButton:hover {
                    background-color: #437db1;
                }
                QPushButton:pressed {
                    background-color: #a8a8a8;
                }
                QPushButton:disabled {
                    background-color: #f0f0f0;
                    color: #a9a9a9;
                    border-color: #dcdcdc;
                }
                """)

        self.layout_button_modif_delete = QHBoxLayout()
        self.layout.addLayout(self.layout_button_modif_delete)

        # Largeur fixe pour les labels
        label_width = 80

        # Layout pour le nom
        self.layout_name = QHBoxLayout()
        self.layout.addLayout(self.layout_name)
        self.layout_name.setContentsMargins(3, 3, 3, 3)

        self.label_nom = QLabel("<b>Name:</b>")
        self.label_nom.setFixedWidth(label_width)
        self.layout_name.addWidget(self.label_nom)

        self.champ_nom = QLineEdit()
        self.champ_nom.setStyleSheet("background-color: white;")
        self.layout_name.addWidget(self.champ_nom)

        # Layout pour la clé privée
        self.layout_private_key = QHBoxLayout()
        self.layout.addLayout(self.layout_private_key)
        self.layout_private_key.setContentsMargins(3, 3, 3, 3)

        self.label_privee = QLabel("<b>Private key: </b>")
        self.label_privee.setFixedWidth(label_width)
        self.layout_private_key.addWidget(self.label_privee)

        self.champ_private_key = QLineEdit()
        self.champ_private_key.setStyleSheet("background-color: white;")
        self.champ_private_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.see = True
        self.layout_private_key.addWidget(self.champ_private_key)

        icon_eye = QIcon(QPixmap("img/oeil.png"))

        self.see_private_key = QPushButton()
        self.see_private_key.setIcon(icon_eye)
        self.see_private_key.setToolTip(
            "Show/hide Private key\nthis is the key you keep secret, it is for you and only you")
        self.see_private_key.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)

        self.see_private_key.setStyleSheet(theme_blue_button)
        self.see_private_key.clicked.connect(self.see_private)
        self.layout_private_key.addWidget(self.see_private_key, alignment=Qt.AlignmentFlag.AlignCenter)

        # Layout pour la clé publique
        self.layout_public_key = QHBoxLayout()
        self.layout.addLayout(self.layout_public_key)
        self.layout_public_key.setContentsMargins(3, 3, 3, 3)

        self.label_public = QLabel("<b>Public key: </b>")
        self.label_public.setFixedWidth(label_width)
        self.layout_public_key.addWidget(self.label_public)

        self.champ_public_key = QLineEdit()
        self.champ_public_key.setStyleSheet("background-color: white;")
        self.layout_public_key.addWidget(self.champ_public_key)

        self.button_copy = QPushButton("Copy")
        self.button_copy.clicked.connect(self.copy_pub_key)
        self.button_copy.setStyleSheet(theme_blue_button)
        self.layout_public_key.addWidget(self.button_copy)
        self.button_copy.setToolTip("This is the key you need to share\n to the people you want to talk with")

        self.layout_manage_button = QVBoxLayout()
        self.layout.addLayout(self.layout_manage_button)
        # self.layout_manage_button.setContentsMargins(10, 10, 10, 10)

        self.generate_key_button = QPushButton("generate a new key pair")
        self.generate_key_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        self.generate_key_button.setStyleSheet(theme_blue_button)
        self.generate_key_button.setToolTip("This is basically deleting your account and recreate an other")

        self.generate_key_button.clicked.connect(self.generate_keys)
        self.generate_key_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        self.layout_manage_button.addWidget(self.generate_key_button, alignment=Qt.AlignmentFlag.AlignCenter)

        # self.save_key_button = QPushButton("Save keys")
        # self.save_key_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        # self.save_key_button.setStyleSheet(theme_blue_button)

        # self.save_key_button.clicked.connect(self.show_password_windows_save)
        # self.layout_manage_button.addWidget(self.save_key_button, alignment=Qt.AlignmentFlag.AlignCenter)

        """
        self.get_key_button = QPushButton("Acess keys")
        self.get_key_button.setStyleSheet(theme_blue_button)

        self.get_key_button.clicked.connect(self.show_password_windows_access)
        self.layout_manage_button.addWidget(self.get_key_button, alignment=Qt.AlignmentFlag.AlignCenter)
        """

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

        model = QStandardItemModel()
        self.list_contacts.setModel(model)

        self.list_contacts.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        self.list_contacts.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_contacts.customContextMenuRequested.connect(self.show_context_menu)

        self.list_contacts.doubleClicked.connect(self.fill_info_contact)

        self.counter = 0

        self.create_all_files()

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

        with open("./parameters.json", "rb") as _file:
            data = _file.read().strip()
            if data:
                data = json.loads(data)
                self.show_emoji = int(data['parameters']['show_emoji'])

        self.show_chat()




    def show_context_menu(self, pos: QPoint):
        index = self.list_contacts.indexAt(pos)
        if not index.isValid():
            return

        row = index.row()
        contact_name = index.data()

        menu = QMenu(self)

        action_info = QAction("Show info", self)
        action_supprimer = QAction("Delete", self)
        #action_cancel = QAction("Cancel", self)

        action_info.triggered.connect(lambda: self.show_modify_contact_windows(contact_name))
        action_supprimer.triggered.connect(lambda: self.delete_contact(contact_name))
        #action_cancel.triggered.connect(lambda: None)

        menu.addAction(action_info)
        menu.addAction(action_supprimer)
        #menu.addSeparator()
        #menu.addAction(action_cancel)

        # Affiche le menu à l'endroit du clic
        menu.exec(self.list_contacts.viewport().mapToGlobal(pos))

    def delete_contact(self, contact_name):
        try:

            yes_or_no = QMessageBox.question(self,
                                             'Confirmation',
                                             f'Do you really want to delete {contact_name} contact? ',
                                             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                             QMessageBox.StandardButton.No)

            if yes_or_no == QMessageBox.StandardButton.Yes:
                print("in yes or no")

                with open("./contacts.json", "r", encoding='utf-8') as file:
                    data = json.loads(scrro.decrypt(self.password, file.read()))

                for contact in data["contacts"]:
                    if contact["name"] == contact_name:
                        data["contacts"].remove(contact)
                        break

                with open("./contacts.json", "wb") as file:
                    data = scrro.encrypt(self.password, json.dumps(data).encode())
                    file.write(data)

                try:
                    shutil.rmtree(f"./chat_data/{contact_name}")
                    print(f"Dossier './chat_data/{contact_name}' et tout son contenu ont été supprimés avec succès.")
                except FileNotFoundError:
                    print(f"Le dossier './chat_data/{contact_name}' n'existe pas.")
                except PermissionError:
                    print(f"Permission refusée pour supprimer le dossier './chat_data/{contact_name}'.")
                except OSError as e:
                    print(f"Erreur : {e}")

                self.refresh_contact_list()

        except Exception as e:
            print(e)

    def copy_pub_key(self):
        pub = self.champ_public_key.text()

        clipboard = QApplication.clipboard()

        clipboard.setText(pub)

    def create_all_files(self):
        defaults = {
            "contacts.json": None,
            "key_pair.txt": None,
            "parameters.json": {
                "parameters": {
                    "show_emoji": 1,
                    "last_contact": None
                }
            }
        }

        for filename, default_content in defaults.items():
            if not os.path.exists(filename):
                with open(filename, "w") as f:
                    if filename.endswith(".json") and default_content is not None:
                        json.dump(default_content, f, indent=4)


    def openFileNameDialog(self):
        options = QFileDialog.Options()
        # options |= QFileDialog.DontUseNativeDialog
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

            image_encrypt = crro.encrypt(public_key, reduced_quality_bytes)

            image_encrypt_for_sender = crro.encrypt(public_key_sender, reduced_quality_bytes)

            image_signed = "__IMAGE__" + "\n" + image_encrypt + "__IMAGE__" + "\n" + image_encrypt_for_sender

            image_signed = crro.sign(private_key, image_signed.encode())

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


            self.url_send = f"{self.champ_server.text()}/CrroChat/send_message.php"

            data = {
                "file_name": file_name,
                "msg": image_signed
            }

            thread_send = threading.Thread(target=lambda: self.send_message_thread(data), daemon=True)
            thread_send.start()


    def insert_smiley(self, smiley):
        unicode_code = smiley
        emoji = chr(int(unicode_code[2:], 16))
        # print(smiley, "U+1F600".decode())
        self.champ_message.insertPlainText(emoji)

    
    def show_emoji_funct(self):


        if self.show_emoji == 1:
            self.widget_button.hide()
            self.show_emoji = 2
        else:
            self.widget_button.show()
            self.show_emoji = 1
        with open("./parameters.json", "r") as file:
            data = file.read().strip()
            if data:
                data = json.loads(data)
                data['parameters']['show_emoji'] = self.show_emoji

        with open("./parameters.json", "w") as file:
            json.dump(data, file, indent=4)


    
    def refresh_contact_list(self):
        with open("./contacts.json", "rb") as file:
            data = file.read()
            if not data:
                return
            data = json.loads(scrro.decrypt(self.password, data))


        list_names = []

        for contact in data["contacts"]:
            list_names.append(contact["name"])

        self.only_contacts_name = []

        for name in list_names:
            self.only_contacts_name.append(name)

        model = QStandardItemModel()
        image_path = "img/contacts.png"

        for i in self.only_contacts_name:
            item = QStandardItem(i)
            icon = QIcon(QPixmap(image_path))
            item.setIcon(icon)
            model.appendRow(item)

        self.list_contacts.setModel(model)

    def see_private(self):

        if self.see == True:
            self.see = False
            self.champ_private_key.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.see = True
            self.champ_private_key.setEchoMode(QLineEdit.EchoMode.Password)

    
    def fill_info_contact(self, index, start=False):
        if not start:
            contact_index = index.row()
            with open("contacts.json", "rb") as file:
                data = file.read()
            if data:
                data = scrro.decrypt(self.password, data)
                contacts = json.loads(data)
                contact = contacts["contacts"][contact_index]

                self.current_contact_name = contact["name"]
                server_contact = contact["server"]
                public_key = contact["public_key"]
                self.champ_public_key2.setText(public_key)
                self.champ_server.setText(server_contact)
                self.model.clear()
                self.start_contenu = ""
                self.champ_name_contact.setText(self.current_contact_name)
                self.label_name_current.setText(f" Chat with: {self.current_contact_name}")
                self.show_chat()
                self.fill_server_info()
                self.counter = 1
                self.model.clear()

                temp_data = json.dumps({"contact_name": self.current_contact_name, "server": server_contact, "public_key": public_key}).encode()

                encrypted_data = scrro.encrypt(self.password, temp_data).decode('utf-8')

                with open("parameters.json", "r") as file:
                    content = file.read().strip()

                    if content:
                        file.seek(0)
                        data = json.load(file)
                        data['parameters']['last_contact'] = encrypted_data


                with open("parameters.json", "w") as file:
                    json.dump(data, file, indent=4)



                self.change_contact()
                self.show_messages_from_client_data_chat()
        else:

            with open("parameters.json", "r") as file:
                content = file.read().strip()
                if content:
                    file.seek(0)
                    data = json.load(file)
                    decrypted_data = scrro.decrypt(self.password, data['parameters']['last_contact'])
                    last_contact = json.loads(decrypted_data)

            self.current_contact_name = last_contact['contact_name']
            server_contact = last_contact['server']
            public_key = last_contact['public_key']
            self.champ_public_key2.setText(public_key)
            self.champ_server.setText(server_contact)
            self.model.clear()
            self.start_contenu = ""
            self.champ_name_contact.setText(self.current_contact_name)
            self.label_name_current.setText(f" Chat with: {self.current_contact_name}")
            self.show_chat()
            self.fill_server_info()



    """
    def closeEvent(self, event):
        with open("./parameters.txt", "r") as file:
            data = file.read()

        lines = data.split("\n")
        for line in lines:
            if line.startswith("show_emoji_at:"):
                print("find lines")

                new_data = data.replace(line, "show_emoji_at:" + str(self.show_emoji))

                with open("./parameters.txt", "w") as file:
                    file.write(new_data)
        print("The close is clean")"""

    def closeEvent(self, event):
        self.process.terminate()
        print("The close is clean")

    
    def send_message(self, another=None):
        try:
            print("another lolol", another)
        except Exception as e:
            print(e)



        #self.text_edit.scrollToBottom()
        message_plaintext = str(self.champ_message.toPlainText())

        if not message_plaintext.strip():
            return

        self.champ_message.clear()

        self.play_sound_send_signal.emit()

        public_key = str(self.champ_public_key.text())
        public_key_sender = str(self.champ_public_key2.text())
        private_key = self.champ_private_key.text()
        private_key_int = int.from_bytes(base64.urlsafe_b64decode(private_key), byteorder='big')
        # identifier = hashlib.sha256(public_key.encode()).hexdigest()

        try:
            public_key = eval(public_key)
            public_key_sender = eval(public_key_sender)
            name = str(self.champ_nom.text())
            time = datetime.now()
            time = time.strftime("%Y-%m-%d %H:%M")

            message_plaintext = f"              {time}" + "\n" + name + ":\n" + message_plaintext
            message = crro.encrypt(public_key_sender, message_plaintext.encode())
            message_for_sender = crro.encrypt(public_key, message_plaintext.encode())
            message = message + "\n" + message_for_sender
            message_signed = crro.sign(private_key_int, message.encode())

            if not message.strip():
                return

            public_key_for_x = self.champ_public_key.text().replace("(", "").split(",")
            public_key_sender_for_x = self.champ_public_key2.text().replace("(", "").split(",")
            public_key_for_file_name = str(self.champ_public_key.text()).encode()
            public_key_sender_for_file_name = str(self.champ_public_key2.text()).encode()
            x = int(public_key_for_x[0])
            x_sender = int(public_key_sender_for_x[0])

            if x_sender < x:
                file_name = hashlib.sha256(public_key_for_file_name + public_key_sender_for_file_name).hexdigest()
            else:
                file_name = hashlib.sha256(public_key_sender_for_file_name + public_key_for_file_name).hexdigest()

            self.url_send = f"{self.champ_server.text()}/CrroChat/send_message.php"

            data = {
                "file_name": file_name,
                "msg": message_signed.encode('utf-8') + b"\n\n"
            }

            self.url_send = f"{self.champ_server.text()}/CrroChat/send_message.php"

            thread_send = threading.Thread(target=lambda: self.send_message_thread(data), daemon=True)
            thread_send.start()
            #QTimer.singleShot(0, self.text_edit.scrollToBottom)


        except Exception as e:
            print(e)

    
    def send_message_thread(self, data):
        response_send = requests.post(self.url_send, data=data)
        print("response_send", response_send.json())
        if response_send.status_code == 200:
            self.fill_server_info()
            print("Contenu ajouté avec succès.")
        else:
            print("Error", response_send.status_code)

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

            file_name = "crrochat_conversations" + "/" + file_name + ".txt"

            self.url_contenu = self.champ_server.text() + f"/{file_name}"
        except Exception as e:
            print(e)



    
    def change_contact(self):
        if hasattr(self, "process") and self.process is not None:
            if self.process.is_alive():
                self.process.terminate()
                self.process.join()
            self.process = None

        self.stop_event.set()
        public_key_for_x = self.champ_public_key.text().replace("(", "").split(",")
        public_key_sender_for_x = self.champ_public_key2.text().replace("(", "").split(",")
        public_key_for_file_name = str(self.champ_public_key.text()).encode()
        public_key_sender_for_file_name = str(self.champ_public_key2.text()).encode()
        url = self.champ_server.text()
        x = int(public_key_for_x[0])
        x_sender = int(public_key_sender_for_x[0])
        if x_sender < x:
            file_name = hashlib.sha256(public_key_for_file_name + public_key_sender_for_file_name).hexdigest()
        else:
            file_name = hashlib.sha256(public_key_sender_for_file_name + public_key_for_file_name).hexdigest()

        self.stop_event.clear()

        print("file_name", file_name)

        self.process = Process(target=long_poll, args=(file_name, url, self.queue))
        self.process.start()

    def get_message(self):
        last_timestamp = 0
        if self.current_contact_name:
            dir_path = f"./chat_data/{self.current_contact_name}"
            with open(f"{dir_path}/last_message", "r", encoding="utf-8") as file:
                content = file.read().strip()
                if content:
                    last_message = json.loads(content)
                    last_timestamp = last_message['timestamp']

        while True:
            msg = self.queue.get()
            timestamp = msg['timestamp']
            print("timestamp > last_timestamp", timestamp, last_timestamp)
            if timestamp > last_timestamp:
                # self.play_sound_signal.emit() # if you want to always have notif sound when getting a message
                self.decrypt_show_and_save_message(msg['msg'], f"./chat_data/{self.current_contact_name}/client_chat_data")
                with open(f"./chat_data/{self.current_contact_name}/last_message", "w", encoding="utf-8") as file:
                    json.dump(msg, file)
                last_timestamp = timestamp

            # self.text_edit.scrollToBottom()

    def add_message_to_client_chat_data(self, new_message, file_path):

        with open(file_path, "r", encoding='utf-8') as file:
            data = file.read()
            if data:
                data = scrro.decrypt(self.password, data)
                client_chat_data = json.loads(data)
            else:
                client_chat_data = {
                    "messages": []
                }

        #with open(file_path, "r", encoding="utf-8") as file:
            #client_chat_data = json.load(file)
        client_chat_data["messages"].append(new_message)

        # we only keep the 512 last messages to keep the file size resonalbe
        client_chat_data["messages"] = client_chat_data["messages"][-512:]

        #with open(file_path, "w", encoding="utf-8") as file:
            #json.dump(client_chat_data, file, ensure_ascii=False, indent=4)

        with open(file_path, "wb") as file:
            data = scrro.encrypt(self.password, json.dumps(client_chat_data).encode())
            file.write(data)

    def show_messages_from_client_data_chat(self):
        if not self.current_contact_name:
            return

        with open(f"./chat_data/{self.current_contact_name}/client_chat_data", "r", encoding='utf-8') as file:
            try:
                decrypted = scrro.decrypt(self.password, file.read())
                chat_data = json.loads(decrypted)
            except (ValueError, JSONDecodeError):
                return

        self.text_edit.setMaximumWidth(450)  # avoid bad resizing

        # reduit le nombre de lookup a faire ?
        add = self.model.add_message
        b64decode = base64.urlsafe_b64decode

        for message in chat_data['messages']:
            if message['to'] == 'me_img':
                add(USER_ME, image_bytes=b64decode(message["msg"]))
            elif message['to'] == "them_img":
                add(USER_THEM, image_bytes=b64decode(message["msg"]))
            elif message['to'] == "me":
                add(USER_ME, message["msg"])
            elif message['to'] == "them":
                add(USER_THEM, message["msg"])

        self.text_edit.setMaximumWidth(600)
        self.scroll_to_bottom()

    def decrypt_show_and_save_message(self, message, file_path):
        private_key = int.from_bytes(base64.urlsafe_b64decode(self.champ_private_key.text()), byteorder="big")
        public_key = eval(str(self.champ_public_key2.text()))
        personal_public_key = self.champ_public_key.text().replace("(", "").replace(")", "")
        personal_public_key = personal_public_key.split(",")
        int_x = int(personal_public_key[0])
        int_y = int(personal_public_key[1])
        personal_public_key = int_x, int_y

        sign_true, message_only = crro.check_signature(personal_public_key, message)
        message_list = message_only.split("---BEGIN CRRO MESSAGE---")

        if sign_true:

            encrypted_message = "---BEGIN CRRO MESSAGE---" + message_list[2]

            #if "__IMAGE__" in encrypted_message:
            if message_list[0].strip() == "__IMAGE__":
                print("an image was found")
                message = crro.decrypt(private_key, encrypted_message)
                print(message)
                b64_message = base64.urlsafe_b64encode(
                    message).decode()
                self.all_data = self.all_data + "---Them_Image---" + b64_message + "---End_Message---"
                self.model.add_message(USER_ME, image_bytes=message)
                new_message = {"to": "me_img", "msg": b64_message}
                #self.play_sound_send_signal.emit() # play when button press
                self.add_message_to_client_chat_data(new_message, file_path)
                self.scroll_to_bottom()

            else:
                message = crro.decrypt(private_key, encrypted_message).decode()
                message = str(message)
                self.all_data = self.all_data + "---Them_Message---" + message + "---End_Message---"
                self.model.add_message(USER_ME, message)
                new_message = {"to": "me", "msg": message}
                #self.play_sound_send_signal.emit() # play when button press
                self.add_message_to_client_chat_data(new_message, file_path)
                self.scroll_to_bottom()




        else:
            sign_true, message_only = crro.check_signature(public_key, message)
            if sign_true:
                if message_list[0].strip() == "__IMAGE__":
                    print("an image was found")
                    message = crro.decrypt(private_key, message_only)
                    b64_message = base64.urlsafe_b64encode(
                        message).decode()
                    self.all_data = self.all_data + "---Them_Image---" + b64_message + "---End_Message---"
                    self.model.add_message(USER_THEM, image_bytes=message)
                    new_message = {"to": "them_img", "msg": b64_message}
                    self.play_sound_get_signal.emit()
                    self.add_message_to_client_chat_data(new_message, file_path)
                    self.scroll_to_bottom()
                else:
                    message = crro.decrypt(private_key, message_only).decode()
                    self.all_data = self.all_data + "---Them_Message---" + message + "---End_Message---"
                    self.model.add_message(USER_THEM, message)
                    new_message = {"to": "them", "msg": message}
                    self.play_sound_get_signal.emit()
                    self.add_message_to_client_chat_data(new_message, file_path)

                    self.scroll_to_bottom()



    def scroll_to_bottom(self):
        model = self.text_edit.model()

        row_count = model.rowCount(QModelIndex())
        if row_count > 0:
            last_index = model.index(row_count - 1, 0)

            self.text_edit.scrollTo(last_index, QAbstractItemView.ScrollHint.PositionAtTop)

            # Normalement pas besoin de sélectionner cet élément a voir sur linux
            #selection_model = self.text_edit.selectionModel()
            #selection_model.select(last_index, QItemSelectionModel.SelectionFlag.ClearAndSelect)

            self.text_edit.setCurrentIndex(last_index)

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
                encrypted_key = scrro.encrypt(key, private_key).decode()
                encrypted_name = scrro.encrypt(key, name).decode()
                print("key_", key)

            encrypted_name_and_keys = encrypted_key + "\n" + encrypted_name + "\n" + public_key
            file.write(encrypted_name_and_keys)

    
    def first_time(self, password, name):
        self.champ_nom.setText(name)
        self.generate_keys_first_time()
        self.champ_server.setText("Error during connexion to: ")

        # mon_thread = threading.Thread(target=self.get_contenu_in_thread())

        # Lancer le thread
        # mon_thread.start()

        self.save_keys(password)
        self.password = password
        self.access_key(password, start=True)

    def show_elg256_windows(self, action=None):
        elg256 = By_Elg256(self)
        elg256.exec()

    def show_about_windows(self, action=None):
        about = About(self)
        about.exec()

    
    def show_donation_bitcoin_windows(self, action=None):
        bitcoin = Bitcoin_donation(self)
        bitcoin.exec()

    def show_fisrt_time_password_windows(self, start):
        for_what = "first_time"
        get_password = Get_Passord(self, for_what, start=False)
        get_password.exec()

    def show_password_windows_access(self, start):
        for_what = "access"
        get_password = Get_Passord(self, for_what, start=True)
        get_password.exec()

    def show_contact_windows(self, start):
        get_contact = Get_Contact(self, self.password)
        get_contact.exec()

    def show_password_windows_save(self, action=None):
        for_what = "save"
        get_password = Get_Passord(self, for_what)
        get_password.exec()

    def show_modify_contact_windows(self, contact_name):
        mod_contact = Mod_Contact(self, contact_name, self.password)
        mod_contact.exec()

    def get_contenu_in_thread(self):
        self.fill_server_info()
        # self.timer.start(700)

    def access_key(self, key, start=False, password=True):

        self.password = key
        self.refresh_contact_list()
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

            decrypted_private_key = scrro.decrypt(key, encrypted_key)

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

            with open("parameters.json", "r") as file:
                content = file.read().strip()
                if content:
                    file.seek(0)
                    data = json.load(file)

                    if data['parameters']['last_contact'].strip():

                        try:
                            # self.champ_name_contact.setText(data[0])
                            # self.champ_server.setText(data[1])
                            # self.champ_public_key2.setText(data[2])
                            # self.label_name_current.setText(f" Chat with: {data[0]}")
                            # self.get_contenu(start=True)
                            self.fill_info_contact(index=0, start=True)

                        except Exception as e:
                            print("last contact seems None", e)

                        # self.get_contenu(start=True)  # initialy with a start = True
                        self.change_contact()

            self.thread = threading.Thread(target=self.get_message, daemon=True)
            print("The search thread is now start and only one of this message should be print")
            self.thread.start()

        else:

            self.show_messages_from_client_data_chat()
            print("self.show_messages_from_client_data_chat()")

    
    def generate_keys(self, action=None):

        yes_or_no = QMessageBox.question(self,
                                         'Confirmation',
                                         'By generating new key you will delete your current key pair, are you sure you '
                                         'want to generate a new key pair?',
                                         QMessageBox.Yes | QMessageBox.No,
                                         QMessageBox.No)

        # Vérifier la réponse de l'utilisateur
        if yes_or_no == QMessageBox.Yes:
            self.private_key = crro.generate_private_key()

            self.public_key = crro.generate_public_key(self.private_key)

            self.private_key = self.private_key.to_bytes((self.private_key.bit_length() + 7) // 8, byteorder='big')

            self.champ_private_key.setText(base64.urlsafe_b64encode(self.private_key).decode())
            self.champ_public_key.setText(str(self.public_key))

            self.show_password_windows_save()
        else:
            return

    
    def generate_keys_first_time(self, action=None):

        self.private_key = crro.generate_private_key()

        self.public_key = crro.generate_public_key(self.private_key)

        self.private_key = self.private_key.to_bytes((self.private_key.bit_length() + 7) // 8, byteorder='big')

        self.champ_private_key.setText(base64.urlsafe_b64encode(self.private_key).decode())
        self.champ_public_key.setText(str(self.public_key))

    
    def show_chat(self, action=None):

        self.text_edit.show()
        self.champ_message.show()
        self.send_button.show()
        self.label_name_current.show()
        self.button_smiley.show()

        if self.show_emoji == 1:
            self.widget_button.show()
        # self.show_emoji = 2

        self.champ_private_key.hide()
        self.champ_public_key.hide()
        self.generate_key_button.hide()
        self.label_privee.hide()
        self.label_public.hide()
        self.champ_server.hide()
        self.label_server.hide()
        # self.get_key_button.hide()
        # self.save_key_button.hide()
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
        self.button_copy.hide()


        self.center_widget.setContentsMargins(0, 0, 0, 0)

        self.layout_private_key.setContentsMargins(0, 0, 0, 0)
        self.layout_name.setContentsMargins(0, 0, 0, 0)
        self.layout_public_key.setContentsMargins(0, 0, 0, 0)

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
        # self.get_key_button.hide()
        # self.save_key_button.hide()
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
        self.button_copy.hide()

        self.label_contacts.show()
        self.list_contacts.show()
        self.button_add_contact.show()

        self.center_widget.setContentsMargins(0, 0, 0, 0)

        self.layout_private_key.setContentsMargins(0, 0, 0, 0)
        self.layout_name.setContentsMargins(0, 0, 0, 0)
        self.layout_public_key.setContentsMargins(0, 0, 0, 0)

    def show_server(self):
        self.champ_private_key.hide()
        self.champ_public_key.hide()
        self.generate_key_button.hide()
        self.label_privee.hide()
        self.label_public.hide()
        self.text_edit.hide()
        self.champ_message.hide()
        self.send_button.hide()
        # self.get_key_button.hide()
        # self.save_key_button.hide()
        self.champ_nom.hide()
        self.label_nom.hide()
        self.label_contacts.hide()
        self.list_contacts.hide()
        self.button_add_contact.hide()
        self.see_private_key.hide()
        self.label_name_current.hide()
        self.widget_button.hide()
        self.button_smiley.hide()
        self.button_copy.hide()
        self.button_delete_contact.hide()
        self.button_modify_contact.hide()

        self.champ_server.show()
        self.label_server.show()
        self.champ_public_key2.show()
        self.label_public_key2.show()
        self.label_name_contact.show()
        self.champ_name_contact.show()

        self.center_widget.setContentsMargins(5, 5, 5, 5)

        self.layout_private_key.setContentsMargins(0, 0, 0, 0)
        self.layout_name.setContentsMargins(0, 0, 0, 0)
        self.layout_public_key.setContentsMargins(0, 0, 0, 0)

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
        self.label_nom.hide()
        self.label_name_current.hide()

        self.champ_private_key.show()
        self.champ_public_key.show()
        self.generate_key_button.show()
        self.label_privee.show()
        self.label_public.show()
        # self.get_key_button.show()
        # self.save_key_button.show()
        self.champ_nom.show()
        self.label_nom.show()
        self.see_private_key.show()
        self.button_copy.show()

        self.layout_private_key.setContentsMargins(3, 3, 3, 3)
        self.layout_name.setContentsMargins(3, 3, 3, 3)
        self.layout_public_key.setContentsMargins(3, 3, 3, 3)

        self.center_widget.setContentsMargins(5, 5, 5, 5)


if __name__ == '__main__':
    start_time = time.time()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
