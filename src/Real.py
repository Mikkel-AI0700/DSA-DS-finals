import sys
from datetime import date

from PySide6.QtCore import QDate, QTime, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QStackedWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QFormLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QComboBox,
    QDateEdit,
    QTimeEdit,
    QTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QScrollArea,
    QSizePolicy,
)

import reservation_service
from models import Status


# ---------------------------------------------------------
# LOGIN DETAILS
# ---------------------------------------------------------

StudentDetails = {
    "Student 1": {"Username": "1", "Password": "1", "RefNum": 101},
    "Student 2": {"Username": "Kyle", "Password": "Password2", "RefNum": 102},
    "Student 3": {"Username": "Seb", "Password": "Password3", "RefNum": 103},
}

AdminDetails = {
    "Admin 1": {"Username": "Admin", "Password": "SuperCoolPassword", "RefNum": 999},
}


# ---------------------------------------------------------
# BUILDING AND ROOM DATA
# ---------------------------------------------------------

RoomDictionary = {
    "Meeting Rooms": {
        "Cabuco": ["Cabuco - Room 1", "Cabuco - Room 2"],
        "Conchu": ["Conchu - Room 1"],
    },

    "Viewing Room": {
        1: ["Cabezas Viewing Room"],
    },

    "LibSpaces": {
        1: ["LibSpace 1 - Room 1", "LibSpace 1 - Room 2", "LibSpace 1 - Room 3", "LibSpace 1 - Room 4"],
        2: ["LibSpace 2 - Room 5", "LibSpace 2 - Room 6", "LibSpace 2 - Room 7", "LibSpace 2 - Room 8"],
    },

    "Discussion Rooms": {
        1: ["Discussion Room 1", "Discussion Room 2", "Discussion Room 3", "Discussion Room 4"],
    },
}


# ---------------------------------------------------------
# HELPER FUNCTION: CLEAR A LAYOUT
# ---------------------------------------------------------

def ClearLayout(layout):

    while layout.count():

        item = layout.takeAt(0)

        widget = item.widget()

        if widget:
            widget.deleteLater()

        elif item.layout():
            ClearLayout(item.layout())


# ---------------------------------------------------------
# LOGIN PAGE
# ---------------------------------------------------------

class LogInPage(QWidget):

    def __init__(self, stacked_widget, logout_button, main_window):

        super().__init__()

        self.stacked_widget = stacked_widget
        self.logout_button = logout_button
        self.main_window = main_window

        main_layout = QVBoxLayout(self)

        form_layout = QFormLayout()

        self.Username = QLineEdit()
        self.Password = QLineEdit()

        self.Password.setEchoMode(
            QLineEdit.EchoMode.Password
        )

        self.Checker = QComboBox()
        self.Checker.addItems(["Student", "Admin"])

        enter_button = QPushButton("Log In")
        enter_button.clicked.connect(self.LOGGINGIN)

        form_layout.addRow("Enter Username", self.Username)
        form_layout.addRow("Enter Password", self.Password)
        form_layout.addRow("Account Type", self.Checker)
        form_layout.addRow(enter_button)

        center_layout = QHBoxLayout()

        center_layout.addStretch()
        center_layout.addLayout(form_layout)
        center_layout.addStretch()

        main_layout.addStretch()
        main_layout.addLayout(center_layout)
        main_layout.addStretch()

    def LOGGINGIN(self):

        username = self.Username.text()
        password = self.Password.text()

        if self.Checker.currentText() == "Student":

            accounts = StudentDetails
            destination_index = 2

        else:

            accounts = AdminDetails
            destination_index = 1

        for name, account in accounts.items():

            if (
                username == account["Username"]
                and password == account["Password"]
            ):

                self.main_window.current_user_name = name
                self.main_window.current_ref_num = account["RefNum"]
                self.stacked_widget.setCurrentIndex(destination_index)

                self.logout_button.show()

                return

        QMessageBox.warning(
            self,
            "Login Failed",
            "Incorrect username or password."
        )

    def ClearLogin(self):

        self.Username.clear()
        self.Password.clear()


# ---------------------------------------------------------
# ADMIN PAGE
# ---------------------------------------------------------

class HomeAdmin(QWidget):

    def __init__(self):

        super().__init__()

        self.SelectedRoom = None

        main_layout = QHBoxLayout(self)

        # LEFT SIDE: BUILDINGS

        building_layout = QVBoxLayout()

        building_label = QLabel("Select Category")
        building_layout.addWidget(building_label)

        for building_name in RoomDictionary:

            button = QPushButton(building_name)

            button.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Expanding
            )

            button.clicked.connect(
                lambda checked=False, b=building_name:
                    self.ShowFloors(b)
            )

            building_layout.addWidget(button, 1)

        # MIDDLE: FLOORS AND ROOMS

        content_layout = QVBoxLayout()

        content_layout.addWidget(QLabel("Select Section / Floor"))

        self.Floorlayer = QHBoxLayout()
        content_layout.addLayout(self.Floorlayer)

        content_layout.addWidget(QLabel("Select Room"))

        self.Roomlayer = QGridLayout()
        content_layout.addLayout(self.Roomlayer)

        content_layout.addStretch()

        # RIGHT SIDE: APPROVAL PANEL

        approval_layout = QVBoxLayout()

        approval_title = QLabel("Reservation Approval")
        approval_title.setStyleSheet(
            "font-size: 18px; font-weight: bold;"
        )

        self.SelectedRoomLabel = QLabel("Selected Room: None")

        self.ReservationCountLabel = QLabel("Reservations: 0")

        approval_layout.addWidget(approval_title)
        approval_layout.addWidget(self.SelectedRoomLabel)
        approval_layout.addWidget(self.ReservationCountLabel)

        # Scroll area for reservation cards.

        self.ScrollArea = QScrollArea()
        self.ScrollArea.setWidgetResizable(True)

        self.ApprovalContainer = QWidget()

        self.ApprovalList = QVBoxLayout(
            self.ApprovalContainer
        )

        self.ScrollArea.setWidget(self.ApprovalContainer)

        approval_layout.addWidget(self.ScrollArea)

        # COMBINE THREE SIDES

        main_layout.addLayout(building_layout, 1)
        main_layout.addLayout(content_layout, 3)
        main_layout.addLayout(approval_layout, 2)

    def ClearFloors(self):

        ClearLayout(self.Floorlayer)

    def ClearRooms(self):

        ClearLayout(self.Roomlayer)

    def ShowFloors(self, building):

        self.ClearFloors()
        self.ClearRooms()

        self.SelectedRoom = None

        self.SelectedRoomLabel.setText("Selected Room: None")

        self.ShowReservations()

        for floor in sorted(RoomDictionary[building].keys(), key=lambda x: str(x)):

            floor_label = f"Floor {floor}" if isinstance(floor, int) else str(floor)
            new_button = QPushButton(floor_label)

            new_button.clicked.connect(
                lambda checked=False, b=building, f=floor:
                    self.ShowRooms(b, f)
            )

            self.Floorlayer.addWidget(new_button)

    def ShowRooms(self, building, floor):

        self.ClearRooms()

        rooms = RoomDictionary[building][floor]

        for index, room in enumerate(rooms):

            new_button = QPushButton(room)

            new_button.clicked.connect(
                lambda checked=False, r=room:
                    self.SelectRoom(r)
            )

            row = index // 3
            column = index % 3

            self.Roomlayer.addWidget(
                new_button,
                row,
                column
            )

    def SelectRoom(self, room):

        self.SelectedRoom = room

        self.SelectedRoomLabel.setText(
            f"Selected Room: {room}"
        )

        self.ShowReservations()

    def ShowReservations(self):

        ClearLayout(self.ApprovalList)

        if self.SelectedRoom is None:

            self.ReservationCountLabel.setText(
                "Reservations: 0"
            )

            self.ApprovalList.addWidget(
                QLabel("Select a room to view its reservations.")
            )

            return

        room_requests = [
            req for req in reservation_service.all_requests.values()
            if req.room_number == self.SelectedRoom
        ]

        self.ReservationCountLabel.setText(
            f"Reservations: {len(room_requests)}"
        )

        if not room_requests:

            self.ApprovalList.addWidget(
                QLabel("No reservations for this room.")
            )

            return

        for reservation in room_requests:

            card = QWidget()

            card_layout = QVBoxLayout(card)

            name_label = QLabel(
                f"Name: {reservation.s_name}"
            )

            date_label = QLabel(
                f"Date: {reservation.date_requested}"
            )

            start_t = reservation_service.slot_to_time(reservation.time_slot_start, reservation_service.rtg_config)
            end_t = reservation_service.slot_to_time(reservation.time_slot_end, reservation_service.rtg_config)
            time_label = QLabel(
                f"Time: {start_t} - {end_t}"
            )

            status_str = reservation.status.name.title()
            status_label = QLabel(
                f"Status: {status_str}"
            )

            card_layout.addWidget(name_label)
            card_layout.addWidget(date_label)
            card_layout.addWidget(time_label)
            card_layout.addWidget(status_label)

            if reservation.status == Status.PENDING:

                button_layout = QHBoxLayout()

                approve_button = QPushButton("Approve")
                reject_button = QPushButton("Reject")

                approve_button.clicked.connect(
                    lambda checked=False, r_id=reservation.request_id:
                        self.ApproveReservation(r_id)
                )

                reject_button.clicked.connect(
                    lambda checked=False, r_id=reservation.request_id:
                        self.RejectReservation(r_id)
                )

                button_layout.addWidget(approve_button)
                button_layout.addWidget(reject_button)

                card_layout.addLayout(button_layout)

            card.setStyleSheet("""
                QWidget {
                    border: 1px solid gray;
                    border-radius: 5px;
                    padding: 5px;
                }
            """)

            self.ApprovalList.addWidget(card)

        self.ApprovalList.addStretch()

    def ApproveReservation(self, request_id):

        try:
            reservation_service.approve_request(request_id)
            QMessageBox.information(
                self,
                "Reservation Approved",
                "The reservation has been approved."
            )
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

        self.ShowReservations()

    def RejectReservation(self, request_id):

        answer = QMessageBox.question(
            self,
            "Reject Reservation",
            "Are you sure you want to reject this reservation?"
        )

        if answer == QMessageBox.StandardButton.Yes:

            try:
                reservation_service.admin_cancel_request(request_id, 0)
                QMessageBox.information(
                    self,
                    "Reservation Rejected",
                    "The reservation has been rejected."
                )
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))

            self.ShowReservations()


# ---------------------------------------------------------
# STUDENT PAGE
# ---------------------------------------------------------

class HomeStudent(QWidget):

    def __init__(self, main_window):

        super().__init__()

        self.main_window = main_window
        self.SelectedRoom = None

        main_layout = QHBoxLayout(self)

        # LEFT SIDE: BUILDINGS

        building_layout = QVBoxLayout()

        building_layout.addWidget(
            QLabel("Select Category")
        )

        for building_name in RoomDictionary:

            button = QPushButton(building_name)

            button.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Expanding
            )

            button.clicked.connect(
                lambda checked=False, b=building_name:
                    self.ShowFloors(b)
            )

            building_layout.addWidget(button, 1)

        # MIDDLE: FLOORS, ROOMS, AND SCHEDULE

        content_layout = QVBoxLayout()

        content_layout.addWidget(
            QLabel("Select Section / Floor")
        )

        self.Floorlayer = QHBoxLayout()
        content_layout.addLayout(self.Floorlayer)

        content_layout.addWidget(
            QLabel("Select Room")
        )

        self.Roomlayer = QGridLayout()
        content_layout.addLayout(self.Roomlayer)

        # WEEKLY SCHEDULE

        self.Schedlayer = QVBoxLayout()

        self.WeekPicker = QDateEdit()

        self.WeekPicker.setCalendarPopup(True)
        self.WeekPicker.setDate(QDate.currentDate())
        self.WeekPicker.setDisplayFormat("MMMM d, yyyy")

        self.ScheduleTable = QTableWidget()

        self.ScheduleTable.setRowCount(28)
        self.ScheduleTable.setColumnCount(5)

        self.ScheduleTable.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )

        self.ScheduleTable.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

        self.Schedlayer.addWidget(
            QLabel("Weekly Schedule")
        )

        self.Schedlayer.addWidget(self.WeekPicker)
        self.Schedlayer.addWidget(self.ScheduleTable)

        content_layout.addLayout(self.Schedlayer, 1)

        self.WeekPicker.dateChanged.connect(
            lambda date: self.UpdateSchedule()
        )

        # RIGHT SIDE: RESERVATION FORM

        reservation_layout = QVBoxLayout()

        reserve_form = QFormLayout()

        self.NameAnswer = QLineEdit()
        self.NameAnswer.setPlaceholderText("Name/Organization name")

        self.RoomAnswer = QLineEdit()
        self.RoomAnswer.setPlaceholderText("Select a room")
        self.RoomAnswer.setReadOnly(True)

        self.DateAnswer = QDateEdit()
        self.DateAnswer.setCalendarPopup(True)
        self.DateAnswer.setDate(QDate.currentDate())
        self.DateAnswer.setDisplayFormat("MMMM d, yyyy")

        self.TimeInAnswer = QTimeEdit()
        self.TimeInAnswer.setTime(QTime(7, 0))
        self.TimeInAnswer.setDisplayFormat("h:mm AP")

        self.TimeOutAnswer = QTimeEdit()
        self.TimeOutAnswer.setTime(QTime(8, 0))
        self.TimeOutAnswer.setDisplayFormat("h:mm AP")

        self.PurposeAnswer = QTextEdit()
        self.PurposeAnswer.setPlaceholderText(
            "Enter purpose of reservation"
        )

        self.PurposeAnswer.setMaximumHeight(150)

        reserve_button = QPushButton("Submit Reservation")
        reserve_button.clicked.connect(self.ReserveRoom)

        reserve_form.addRow("Name", self.NameAnswer)
        reserve_form.addRow("Selected Room", self.RoomAnswer)
        reserve_form.addRow("Date", self.DateAnswer)
        reserve_form.addRow("Time Start", self.TimeInAnswer)
        reserve_form.addRow("Time End", self.TimeOutAnswer)
        reserve_form.addRow("Purpose", self.PurposeAnswer)
        reserve_form.addRow(reserve_button)

        reservation_layout.addLayout(reserve_form)
        reservation_layout.addStretch()

        # COMBINE THREE SIDES

        main_layout.addLayout(building_layout, 1)
        main_layout.addLayout(content_layout, 3)
        main_layout.addLayout(reservation_layout, 1)

    def ClearFloors(self):

        ClearLayout(self.Floorlayer)

    def ClearRooms(self):

        ClearLayout(self.Roomlayer)

    def ShowFloors(self, building):

        self.ClearFloors()
        self.ClearRooms()

        self.SelectedRoom = None

        self.RoomAnswer.clear()

        self.ScheduleTable.clear()
        self.ScheduleTable.setHorizontalHeaderLabels(
            ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        )

        for floor in sorted(RoomDictionary[building].keys(), key=lambda x: str(x)):

            floor_label = f"Floor {floor}" if isinstance(floor, int) else str(floor)
            new_button = QPushButton(floor_label)

            new_button.clicked.connect(
                lambda checked=False, b=building, f=floor:
                    self.ShowRooms(b, f)
            )

            self.Floorlayer.addWidget(new_button)

    def ShowRooms(self, building, floor):

        self.ClearRooms()

        rooms = RoomDictionary[building][floor]

        for index, room in enumerate(rooms):

            new_button = QPushButton(room)

            new_button.clicked.connect(
                lambda checked=False, r=room:
                    self.ShowSchedule(r)
            )

            row = index // 3
            column = index % 3

            self.Roomlayer.addWidget(
                new_button,
                row,
                column
            )

    def ShowSchedule(self, room):

        self.SelectedRoom = room

        self.RoomAnswer.setText(room)

        self.UpdateSchedule()

    def UpdateSchedule(self):

        if self.SelectedRoom is None:
            return

        selected_date = self.WeekPicker.date()

        monday = selected_date.addDays(
            1 - selected_date.dayOfWeek()
        )

        days = [monday.addDays(i) for i in range(5)]

        headers = [
            day.toString("ddd, MMM d")
            for day in days
        ]

        self.ScheduleTable.setHorizontalHeaderLabels(headers)

        for row in range(28):

            slot_start = QTime(7, 0).addSecs(row * 30 * 60)
            slot_end = slot_start.addSecs(30 * 60)

            time_label = (
                f"{slot_start.toString('h:mm AP')} - "
                f"{slot_end.toString('h:mm AP')}"
            )

            self.ScheduleTable.setVerticalHeaderItem(
                row,
                QTableWidgetItem(time_label)
            )

            for column, day in enumerate(days):

                cell = QTableWidgetItem("Free")

                cell.setBackground(QColor("#C8E6C9"))

                day_str = day.toString("yyyy-MM-dd")
                try:
                    bookings = reservation_service.get_day_schedule(self.SelectedRoom, day_str)
                    for start_str, end_str, req in bookings:
                        if req.status == Status.REJECTED or req.status == Status.CANCELLED:
                            continue

                        r_start = QTime.fromString(start_str, "HH:mm")
                        r_end = QTime.fromString(end_str, "HH:mm")

                        if slot_start < r_end and slot_end > r_start:

                            status = req.status.name.title()

                            cell.setText(status)

                            if status == "Pending":
                                cell.setBackground(QColor("#FFE0B2"))

                            elif status == "Approved":
                                cell.setBackground(QColor("#EF9A9A"))

                            elif status == "Completed":
                                cell.setBackground(QColor("#B0BEC5"))

                            break
                except Exception:
                    pass

                self.ScheduleTable.setItem(
                    row,
                    column,
                    cell
                )

    def ReserveRoom(self, checked=False):

        if self.SelectedRoom is None:

            QMessageBox.warning(
                self,
                "No Room Selected",
                "Please select a room first."
            )

            return

        name = self.NameAnswer.text().strip()
        purpose = self.PurposeAnswer.toPlainText().strip()
        date_val = self.DateAnswer.date()
        start = self.TimeInAnswer.time()
        end = self.TimeOutAnswer.time()

        if not name or not purpose:

            QMessageBox.warning(
                self,
                "Incomplete Form",
                "Please enter your name and purpose."
            )

            return

        try:
            reservation_service.submit_request(
                student_name=name,
                student_ref_num=self.main_window.current_ref_num,
                room_number=self.SelectedRoom,
                date_str=date_val.toString("yyyy-MM-dd"),
                start_str=start.toString("HH:mm"),
                end_str=end.toString("HH:mm")
            )

            QMessageBox.information(
                self,
                "Reservation Submitted",
                "Your reservation has been submitted for approval."
            )

            self.NameAnswer.clear()
            self.PurposeAnswer.clear()
            self.UpdateSchedule()

        except Exception as e:
            QMessageBox.warning(
                self,
                "Reservation Error",
                str(e)
            )


# ---------------------------------------------------------
# MAIN APPLICATION WINDOW
# ---------------------------------------------------------

class MainWindow(QWidget):

    def __init__(self):
        super().__init__()
        self.current_user_name = ""
        self.current_ref_num = 101

        self.setWindowTitle("Smart Room Reservation")
        self.showMaximized()

        main_layout = QVBoxLayout(self)

        self.stacked_widget = QStackedWidget()

        self.LogoutButton = QPushButton("Log Out")
        self.LogoutButton.hide()
        self.LogoutButton.clicked.connect(self.Logout)

        self.Login = LogInPage(
            self.stacked_widget,
            self.LogoutButton,
            self
        )

        self.AHome = HomeAdmin()
        self.SHome = HomeStudent(self)

        self.stacked_widget.addWidget(self.Login)
        self.stacked_widget.addWidget(self.AHome)
        self.stacked_widget.addWidget(self.SHome)

        self.stacked_widget.setCurrentWidget(self.Login)

        main_layout.addWidget(self.stacked_widget)

        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.LogoutButton)
        main_layout.addLayout(bottom_layout)

    def Logout(self):

        self.stacked_widget.setCurrentWidget(self.Login)

        self.Login.ClearLogin()

        self.LogoutButton.hide()


# ---------------------------------------------------------
# RUN APPLICATION
# ---------------------------------------------------------

if __name__ == "__main__":
    reservation_service.start_service()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    exit_code = app.exec()
    reservation_service.stop_service()
    sys.exit(exit_code)