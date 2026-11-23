import re
import sys
from datetime import date

from PySide6.QtCore import QDate, QTime, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QDialog,
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
    QSpinBox,
    QInputDialog,
)

import reservation_service
from models import Status


# ---------------------------------------------------------
# LOGIN DETAILS
# ---------------------------------------------------------

# Starts empty: only Admins can register student accounts.
StudentDetails: dict[str, dict[str, str | int]] = {}

AdminDetails: dict[str, dict[str, str | int]] = {
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
# WELCOME / AUTH ENTRY PAGE
# ---------------------------------------------------------

class WelcomePage(QWidget):

    def __init__(self, stacked_widget, main_window):

        super().__init__()

        self.stacked_widget = stacked_widget
        self.main_window = main_window

        main_layout = QVBoxLayout(self)

        title = QLabel("AEA-IRC Smart Room Reservation System")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: bold;")

        subtitle = QLabel(
            "Log in as an Admin or Student, or create a new Admin account.\n"
            "Students cannot self-register and must be added by an Admin."
        )
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        login_button = QPushButton("Log In (Admin / Student)")
        login_button.setMinimumWidth(240)
        login_button.clicked.connect(self.GoToLogin)

        signup_button = QPushButton("Admin Sign Up")
        signup_button.setMinimumWidth(240)
        signup_button.clicked.connect(self.GoToAdminSignUp)

        button_col = QVBoxLayout()
        button_col.addWidget(login_button)
        button_col.addWidget(signup_button)

        center_layout = QHBoxLayout()
        center_layout.addStretch()
        center_layout.addLayout(button_col)
        center_layout.addStretch()

        main_layout.addStretch()
        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)
        main_layout.addSpacing(20)
        main_layout.addLayout(center_layout)
        main_layout.addStretch()

    def GoToLogin(self):
        self.main_window.Login.ClearLogin()
        self.stacked_widget.setCurrentWidget(self.main_window.Login)

    def GoToAdminSignUp(self):
        self.main_window.AdminSignUp.ClearForm()
        self.stacked_widget.setCurrentWidget(self.main_window.AdminSignUp)


# ---------------------------------------------------------
# ADMIN SIGN-UP PAGE
# ---------------------------------------------------------

class AdminSignUpPage(QWidget):

    def __init__(self, stacked_widget, main_window):

        super().__init__()

        self.stacked_widget = stacked_widget
        self.main_window = main_window

        main_layout = QVBoxLayout(self)

        title = QLabel("Admin Sign Up")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold;")

        form_layout = QFormLayout()

        self.FullName = QLineEdit()
        self.Username = QLineEdit()
        self.Password = QLineEdit()
        self.Password.setEchoMode(QLineEdit.EchoMode.Password)
        self.ConfirmPassword = QLineEdit()
        self.ConfirmPassword.setEchoMode(QLineEdit.EchoMode.Password)

        create_button = QPushButton("Create Admin Account")
        create_button.clicked.connect(self.RegisterAdmin)

        back_button = QPushButton("Back")
        back_button.clicked.connect(self.GoBack)

        form_layout.addRow("Full Name", self.FullName)
        form_layout.addRow("Username", self.Username)
        form_layout.addRow("Password", self.Password)
        form_layout.addRow("Confirm Password", self.ConfirmPassword)
        form_layout.addRow(create_button)
        form_layout.addRow(back_button)

        center_layout = QHBoxLayout()
        center_layout.addStretch()
        center_layout.addLayout(form_layout)
        center_layout.addStretch()

        main_layout.addStretch()
        main_layout.addWidget(title)
        main_layout.addSpacing(12)
        main_layout.addLayout(center_layout)
        main_layout.addStretch()

    def RegisterAdmin(self):

        full_name = self.FullName.text().strip()
        username = self.Username.text().strip()
        password = self.Password.text()
        confirm = self.ConfirmPassword.text()

        if not full_name or not username or not password:
            QMessageBox.warning(
                self,
                "Incomplete Form",
                "Please fill in all fields."
            )
            return

        if password != confirm:
            QMessageBox.warning(
                self,
                "Password Mismatch",
                "Passwords do not match."
            )
            return

        existing_usernames = {acc["Username"] for acc in AdminDetails.values()}
        if username in existing_usernames:
            QMessageBox.warning(
                self,
                "Duplicate Username",
                "That admin username is already taken."
            )
            return

        if full_name in AdminDetails:
            QMessageBox.warning(
                self,
                "Duplicate Name",
                "An admin with that name already exists."
            )
            return

        next_ref = max((int(acc["RefNum"]) for acc in AdminDetails.values()), default=998) + 1
        AdminDetails[full_name] = {
            "Username": username,
            "Password": password,
            "RefNum": next_ref,
        }

        QMessageBox.information(
            self,
            "Admin Registered",
            f"Admin account '{username}' created. You can now log in."
        )
        self.ClearForm()
        self.main_window.Login.ClearLogin()
        self.main_window.Login.Checker.setCurrentText("Admin")
        self.stacked_widget.setCurrentWidget(self.main_window.Login)

    def GoBack(self):
        self.ClearForm()
        self.stacked_widget.setCurrentWidget(self.main_window.Welcome)

    def ClearForm(self):
        self.FullName.clear()
        self.Username.clear()
        self.Password.clear()
        self.ConfirmPassword.clear()


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

        back_button = QPushButton("Back")
        back_button.clicked.connect(self.GoBack)

        form_layout.addRow("Enter Username", self.Username)
        form_layout.addRow("Enter Password", self.Password)
        form_layout.addRow("Account Type", self.Checker)
        form_layout.addRow(enter_button)
        form_layout.addRow(back_button)

        center_layout = QHBoxLayout()

        center_layout.addStretch()
        center_layout.addLayout(form_layout)
        center_layout.addStretch()

        main_layout.addStretch()
        main_layout.addLayout(center_layout)
        main_layout.addStretch()

    def LOGGINGIN(self):

        username = self.Username.text().strip()
        password = self.Password.text()
        role = self.Checker.currentText()

        if role == "Student":
            if not StudentDetails:
                QMessageBox.warning(
                    self,
                    "No Students Registered",
                    "No student accounts exist yet. Please ask an Admin to add your account."
                )
                return
            accounts = StudentDetails
            destination_widget = self.main_window.SHome
        else:
            accounts = AdminDetails
            destination_widget = self.main_window.AHome

        for name, account in accounts.items():

            if (
                username == account["Username"]
                and password == account["Password"]
            ):

                self.main_window.current_user_name = name
                self.main_window.current_ref_num = int(account["RefNum"])
                self.stacked_widget.setCurrentWidget(destination_widget)

                if role == "Student":
                    self.main_window.SHome.RefreshMyRequests()
                    self.main_window.SHome.UpdateSchedule()
                else:
                    self.main_window.AHome.UpdateStudentCount()
                    self.main_window.AHome.ShowReservations()

                self.logout_button.show()

                return

        QMessageBox.warning(
            self,
            "Login Failed",
            "Incorrect username or password."
        )

    def GoBack(self):
        self.ClearLogin()
        self.stacked_widget.setCurrentWidget(self.main_window.Welcome)

    def ClearLogin(self):

        self.Username.clear()
        self.Password.clear()


# ---------------------------------------------------------
# ADMIN-ONLY ADD STUDENT DIALOG
# ---------------------------------------------------------

class AddStudentDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Student Account (Admin Only)")

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.FullName = QLineEdit()
        self.RefNum = QLineEdit()
        self.RefNum.setPlaceholderText("Numeric ID (e.g. 20240001)")
        self.Username = QLineEdit()
        self.Password = QLineEdit()
        self.Password.setEchoMode(QLineEdit.EchoMode.Password)

        form.addRow("Student Full Name", self.FullName)
        form.addRow("Reference Number", self.RefNum)
        form.addRow("Username", self.Username)
        form.addRow("Password", self.Password)

        layout.addLayout(form)

        btn_row = QHBoxLayout()
        save_btn = QPushButton("Register Student")
        cancel_btn = QPushButton("Cancel")
        save_btn.clicked.connect(self.ValidateAndAccept)
        cancel_btn.clicked.connect(self.reject)

        btn_row.addWidget(save_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

    def ValidateAndAccept(self):
        full_name = self.FullName.text().strip()
        ref_str = self.RefNum.text().strip()
        username = self.Username.text().strip()
        password = self.Password.text()

        if not full_name or not ref_str or not username or not password:
            QMessageBox.warning(self, "Incomplete Form", "Please fill in all fields.")
            return

        try:
            ref_num = int(ref_str)
        except ValueError:
            QMessageBox.warning(self, "Invalid ID", "Reference Number must be numeric.")
            return

        policy_config = reservation_service.get_policy_config()
        if re.search(policy_config.STUDENT_ID_PATTERN, str(ref_num)) is None:
            QMessageBox.warning(
                self,
                "Invalid ID Pattern",
                f"Reference Number must match pattern: {policy_config.STUDENT_ID_PATTERN}"
            )
            return

        if full_name in StudentDetails:
            QMessageBox.warning(self, "Duplicate Name", "A student with that name is already registered.")
            return

        if any(acc["Username"] == username for acc in StudentDetails.values()):
            QMessageBox.warning(self, "Duplicate Username", "That student username is already taken.")
            return

        if any(int(acc["RefNum"]) == ref_num for acc in StudentDetails.values()):
            QMessageBox.warning(self, "Duplicate ID", "That Reference Number is already registered.")
            return

        StudentDetails[full_name] = {
            "Username": username,
            "Password": password,
            "RefNum": ref_num,
        }
        self.accept()


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

        self.StudentCountLabel = QLabel(f"Registered Students: {len(StudentDetails)}")

        self.AddStudentButton = QPushButton("Add Student")
        self.AddStudentButton.clicked.connect(self.OpenAddStudentDialog)

        self.SuggestButton = QPushButton("Suggest Max Approvals (Conflict Graph)")
        self.SuggestButton.clicked.connect(self.SuggestOptimalApprovals)

        approval_layout.addWidget(approval_title)
        approval_layout.addWidget(self.StudentCountLabel)
        approval_layout.addWidget(self.AddStudentButton)
        approval_layout.addWidget(self.SelectedRoomLabel)
        approval_layout.addWidget(self.ReservationCountLabel)
        approval_layout.addWidget(self.SuggestButton)

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

    def UpdateStudentCount(self):
        self.StudentCountLabel.setText(f"Registered Students: {len(StudentDetails)}")

    def OpenAddStudentDialog(self):
        dialog = AddStudentDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.UpdateStudentCount()
            QMessageBox.information(
                self,
                "Student Added",
                f"Student '{dialog.FullName.text().strip()}' can now log in."
            )

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

        room_requests = reservation_service.get_room_requests(self.SelectedRoom)
        conflict_graph = reservation_service.build_pending_conflict_graph(self.SelectedRoom)
        rtg_config = reservation_service.get_time_grid_config()

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
                f"Req #{reservation.request_id} | Name: {reservation.s_name}"
            )

            date_label = QLabel(
                f"Date: {reservation.date_requested}"
            )

            start_t = reservation_service.slot_to_time(reservation.time_slot_start, rtg_config)
            end_t = reservation_service.slot_to_time(reservation.time_slot_end, rtg_config)
            time_label = QLabel(
                f"Time: {start_t} - {end_t} | Group Size: {reservation.group_size}"
            )

            status_str = reservation.status.name.title()
            status_label = QLabel(
                f"Status: {status_str}"
            )

            card_layout.addWidget(name_label)
            card_layout.addWidget(date_label)
            card_layout.addWidget(time_label)

            if reservation.purpose:
                purpose_label = QLabel(f"Purpose: {reservation.purpose}")
                purpose_label.setWordWrap(True)
                card_layout.addWidget(purpose_label)

            card_layout.addWidget(status_label)

            if reservation.status == Status.PENDING:
                neighbors = sorted(conflict_graph.get(reservation.request_id, set()))
                if neighbors:
                    neighbor_str = ", ".join(f"#{nid}" for nid in neighbors)
                    conflict_label = QLabel(
                        f"Conflict Graph Degree: {len(neighbors)} (Overlaps: {neighbor_str})"
                    )
                    conflict_label.setStyleSheet("color: #C62828; font-weight: bold;")
                else:
                    conflict_label = QLabel("Conflict Graph Degree: 0 (No pending overlaps)")
                    conflict_label.setStyleSheet("color: #2E7D32;")
                card_layout.addWidget(conflict_label)

                button_layout = QHBoxLayout()

                approve_button = QPushButton("Approve")
                reject_button = QPushButton("Cancel / Reject")

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

            elif reservation.status == Status.APPROVED:
                cancel_button = QPushButton("Cancel Approved Booking")
                cancel_button.clicked.connect(
                    lambda checked=False, r_id=reservation.request_id:
                        self.RejectReservation(r_id)
                )
                card_layout.addWidget(cancel_button)

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
            result = reservation_service.approve_request(request_id)
            if result.status == Status.APPROVED:
                QMessageBox.information(
                    self,
                    "Reservation Approved",
                    "The reservation has been approved. Any overlapping pending requests were auto-rejected."
                )
            else:
                QMessageBox.warning(
                    self,
                    "Reservation Rejected",
                    result.reason or "The reservation could not be approved due to a conflict."
                )
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

        self.ShowReservations()

    def RejectReservation(self, request_id):

        reason_templates = reservation_service.get_cancel_reasons()
        room_label = self.SelectedRoom or ""
        reason_choices = [template.format(room_label) for template in reason_templates]

        selected_reason, ok = QInputDialog.getItem(
            self,
            "Select Cancellation Reason",
            "Choose a reason for cancelling this reservation:",
            reason_choices,
            0,
            False,
        )

        if ok and selected_reason:
            reason_index = reason_choices.index(selected_reason)
            try:
                reservation_service.admin_cancel_request(request_id, reason_index)
                QMessageBox.information(
                    self,
                    "Reservation Cancelled",
                    f"The reservation has been cancelled.\nReason: {selected_reason}"
                )
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))

            self.ShowReservations()

    def SuggestOptimalApprovals(self):

        if self.SelectedRoom is None:
            QMessageBox.warning(
                self,
                "No Room Selected",
                "Please select a room first to analyze its pending conflict graph."
            )
            return

        suggested = reservation_service.suggest_max_non_conflicting_approvals(self.SelectedRoom)
        if not suggested:
            QMessageBox.information(
                self,
                "No Pending Requests",
                "There are no pending requests for this room to schedule."
            )
            return

        rtg_config = reservation_service.get_time_grid_config()
        lines = []
        for req in suggested:
            start_t = reservation_service.slot_to_time(req.time_slot_start, rtg_config)
            end_t = reservation_service.slot_to_time(req.time_slot_end, rtg_config)
            lines.append(
                f"• Req #{req.request_id} — {req.s_name} ({req.date_requested}, {start_t}-{end_t})"
            )

        summary = (
            "Maximum Independent Set (Interval Conflict Graph)\n"
            f"Optimal conflict-free approvals ({len(suggested)} request(s)):\n\n"
            + "\n".join(lines)
            + "\n\nApprove all suggested requests now? (Overlapping pending requests will be auto-rejected.)"
        )

        answer = QMessageBox.question(
            self,
            "Conflict Graph Suggestion",
            summary,
        )

        if answer == QMessageBox.StandardButton.Yes:
            approved = reservation_service.approve_suggested_requests(self.SelectedRoom)
            QMessageBox.information(
                self,
                "Suggested Requests Approved",
                f"Approved {len(approved)} non-conflicting reservation(s)."
            )
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

        rtg_config = reservation_service.get_time_grid_config()
        policy_config = reservation_service.get_policy_config()

        self.ScheduleTable = QTableWidget()

        self.ScheduleTable.setRowCount(rtg_config.SLOTS_PER_DAY)
        self.ScheduleTable.setColumnCount(5)

        self.ScheduleTable.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )

        self.ScheduleTable.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

        self.AvailabilityLabel = QLabel("Available Slots (U \\ B): Select a room")
        self.AvailabilityLabel.setWordWrap(True)

        self.Schedlayer.addWidget(
            QLabel("Weekly Schedule")
        )

        self.Schedlayer.addWidget(self.WeekPicker)
        self.Schedlayer.addWidget(self.AvailabilityLabel)
        self.Schedlayer.addWidget(self.ScheduleTable)

        content_layout.addLayout(self.Schedlayer, 1)

        self.WeekPicker.dateChanged.connect(
            lambda date: self.UpdateSchedule()
        )

        # RIGHT SIDE: RESERVATION FORM & MY REQUESTS

        reservation_layout = QVBoxLayout()

        reserve_form = QFormLayout()

        self.NameAnswer = QLineEdit()
        self.NameAnswer.setPlaceholderText("Name/Organization name")

        self.RoomAnswer = QLineEdit()
        self.RoomAnswer.setPlaceholderText("Select a room")
        self.RoomAnswer.setReadOnly(True)

        self.GroupSizeAnswer = QSpinBox()
        self.GroupSizeAnswer.setRange(1, 20)
        self.GroupSizeAnswer.setValue(policy_config.MIN_GROUP_SIZE)

        self.DateAnswer = QDateEdit()
        self.DateAnswer.setCalendarPopup(True)
        self.DateAnswer.setDate(QDate.currentDate())
        self.DateAnswer.setDisplayFormat("MMMM d, yyyy")
        self.DateAnswer.dateChanged.connect(
            lambda _date: self.UpdateAvailabilityLabel()
        )

        open_hour, open_min = divmod(rtg_config.OPEN_MINUTES, 60)
        self.TimeInAnswer = QTimeEdit()
        self.TimeInAnswer.setTime(QTime(open_hour, open_min))
        self.TimeInAnswer.setDisplayFormat("h:mm AP")

        self.TimeOutAnswer = QTimeEdit()
        self.TimeOutAnswer.setTime(QTime(open_hour, open_min).addSecs(policy_config.MIN_SLOTS * rtg_config.SLOT_LENGTH_MINUTES * 60))
        self.TimeOutAnswer.setDisplayFormat("h:mm AP")

        self.PurposeAnswer = QTextEdit()
        self.PurposeAnswer.setPlaceholderText(
            "Enter purpose of reservation"
        )

        self.PurposeAnswer.setMaximumHeight(100)

        reserve_button = QPushButton("Submit Reservation")
        reserve_button.clicked.connect(self.ReserveRoom)

        reserve_form.addRow("Name", self.NameAnswer)
        reserve_form.addRow("Selected Room", self.RoomAnswer)
        reserve_form.addRow("Group Size", self.GroupSizeAnswer)
        reserve_form.addRow("Date", self.DateAnswer)
        reserve_form.addRow("Time Start", self.TimeInAnswer)
        reserve_form.addRow("Time End", self.TimeOutAnswer)
        reserve_form.addRow("Purpose", self.PurposeAnswer)
        reserve_form.addRow(reserve_button)

        reservation_layout.addLayout(reserve_form)

        my_req_title = QLabel("My Requests")
        my_req_title.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 8px;")
        reservation_layout.addWidget(my_req_title)

        self.MyRequestsScroll = QScrollArea()
        self.MyRequestsScroll.setWidgetResizable(True)
        self.MyRequestsContainer = QWidget()
        self.MyRequestsList = QVBoxLayout(self.MyRequestsContainer)
        self.MyRequestsScroll.setWidget(self.MyRequestsContainer)
        reservation_layout.addWidget(self.MyRequestsScroll, 1)

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

    def UpdateAvailabilityLabel(self):

        if self.SelectedRoom is None:
            self.AvailabilityLabel.setText("Available Slots (U \\ B): Select a room")
            return

        day_str = self.DateAnswer.date().toString("yyyy-MM-dd")
        try:
            free_ranges = reservation_service.get_available_time_ranges(self.SelectedRoom, day_str)
            if free_ranges:
                formatted = ", ".join(f"{s}-{e}" for s, e in free_ranges)
                self.AvailabilityLabel.setText(f"Available Slots on {day_str} (U \\ B): {formatted}")
            else:
                self.AvailabilityLabel.setText(f"Available Slots on {day_str} (U \\ B): Fully Booked")
        except Exception:
            self.AvailabilityLabel.setText(f"Available Slots on {day_str} (U \\ B): Unavailable")

    def UpdateSchedule(self):

        if self.SelectedRoom is None:
            return

        self.UpdateAvailabilityLabel()

        rtg_config = reservation_service.get_time_grid_config()
        open_hour, open_min = divmod(rtg_config.OPEN_MINUTES, 60)
        slot_secs = rtg_config.SLOT_LENGTH_MINUTES * 60

        selected_date = self.WeekPicker.date()

        monday = selected_date.addDays(
            1 - selected_date.dayOfWeek()
        )

        days = [monday.addDays(i) for i in range(5)]

        headers = [
            day.toString("ddd, MMM d")
            for day in days
        ]

        self.ScheduleTable.setRowCount(rtg_config.SLOTS_PER_DAY)
        self.ScheduleTable.setHorizontalHeaderLabels(headers)

        # Pre-fetch active requests per day (APPROVED, COMPLETED, and PENDING)
        day_requests: list[list] = []
        for day in days:
            day_str = day.toString("yyyy-MM-dd")
            try:
                reqs = [
                    r for r in reservation_service.get_room_requests(self.SelectedRoom, day_str)
                    if r.status not in (Status.REJECTED, Status.CANCELLED)
                ]
            except Exception:
                reqs = []
            day_requests.append(reqs)

        status_priority = {
            Status.APPROVED: 3,
            Status.COMPLETED: 2,
            Status.PENDING: 1,
        }

        for row in range(rtg_config.SLOTS_PER_DAY):

            slot_start = QTime(open_hour, open_min).addSecs(row * slot_secs)
            slot_end = slot_start.addSecs(slot_secs)

            time_label = (
                f"{slot_start.toString('h:mm AP')} - "
                f"{slot_end.toString('h:mm AP')}"
            )

            self.ScheduleTable.setVerticalHeaderItem(
                row,
                QTableWidgetItem(time_label)
            )

            for column, reqs in enumerate(day_requests):

                cell = QTableWidgetItem("Free")
                cell.setBackground(QColor("#C8E6C9"))

                matched_status = None
                for req in reqs:
                    if req.time_slot_start <= row < req.time_slot_end:
                        if (
                            matched_status is None
                            or status_priority.get(req.status, 0) > status_priority.get(matched_status, 0)
                        ):
                            matched_status = req.status

                if matched_status is not None:
                    status_text = matched_status.name.title()
                    cell.setText(status_text)

                    if matched_status == Status.PENDING:
                        cell.setBackground(QColor("#FFE0B2"))
                    elif matched_status == Status.APPROVED:
                        cell.setBackground(QColor("#EF9A9A"))
                    elif matched_status == Status.COMPLETED:
                        cell.setBackground(QColor("#B0BEC5"))

                self.ScheduleTable.setItem(
                    row,
                    column,
                    cell
                )

    def RefreshMyRequests(self):

        ClearLayout(self.MyRequestsList)
        rtg_config = reservation_service.get_time_grid_config()
        my_reqs = reservation_service.get_student_requests(self.main_window.current_ref_num)

        if not my_reqs:
            self.MyRequestsList.addWidget(QLabel("No active requests yet."))
            self.MyRequestsList.addStretch()
            return

        for req in my_reqs:
            card = QWidget()
            card_layout = QVBoxLayout(card)

            start_t = reservation_service.slot_to_time(req.time_slot_start, rtg_config)
            end_t = reservation_service.slot_to_time(req.time_slot_end, rtg_config)
            card_layout.addWidget(QLabel(f"#{req.request_id} | {req.room_number}"))
            card_layout.addWidget(QLabel(f"{req.date_requested} ({start_t} - {end_t})"))
            card_layout.addWidget(QLabel(f"Status: {req.status.name.title()}"))

            if req.status == Status.REJECTED and req.reason:
                reason_lbl = QLabel(req.reason.strip())
                reason_lbl.setWordWrap(True)
                reason_lbl.setStyleSheet("color: #C62828;")
                card_layout.addWidget(reason_lbl)

            if req.status == Status.PENDING:
                cancel_btn = QPushButton("Cancel Request")
                cancel_btn.clicked.connect(
                    lambda checked=False, r_id=req.request_id:
                        self.CancelOwnReservation(r_id)
                )
                card_layout.addWidget(cancel_btn)

            card.setStyleSheet("""
                QWidget {
                    border: 1px solid #BDBDBD;
                    border-radius: 4px;
                    padding: 4px;
                }
            """)
            self.MyRequestsList.addWidget(card)

        self.MyRequestsList.addStretch()

    def CancelOwnReservation(self, request_id):

        try:
            reservation_service.cancel_own_request(
                request_id,
                self.main_window.current_ref_num,
            )
            QMessageBox.information(
                self,
                "Request Cancelled",
                f"Request #{request_id} has been cancelled."
            )
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

        self.RefreshMyRequests()
        self.UpdateSchedule()

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
        group_size = self.GroupSizeAnswer.value()
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
            req = reservation_service.submit_request(
                student_name=name,
                student_ref_num=self.main_window.current_ref_num,
                room_number=self.SelectedRoom,
                date_str=date_val.toString("yyyy-MM-dd"),
                start_str=start.toString("HH:mm"),
                end_str=end.toString("HH:mm"),
                group_size=group_size,
                purpose=purpose,
            )

            if req.status == Status.REJECTED:
                QMessageBox.warning(
                    self,
                    "Reservation Rejected",
                    req.reason or "The selected time slot is already booked."
                )
            else:
                QMessageBox.information(
                    self,
                    "Reservation Submitted",
                    f"Request #{req.request_id} has been submitted for approval."
                )
                self.NameAnswer.clear()
                self.PurposeAnswer.clear()

            self.UpdateSchedule()
            self.RefreshMyRequests()

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

        self.Welcome = WelcomePage(
            self.stacked_widget,
            self
        )

        self.AdminSignUp = AdminSignUpPage(
            self.stacked_widget,
            self
        )

        self.Login = LogInPage(
            self.stacked_widget,
            self.LogoutButton,
            self
        )

        self.AHome = HomeAdmin()
        self.SHome = HomeStudent(self)

        self.stacked_widget.addWidget(self.Welcome)
        self.stacked_widget.addWidget(self.Login)
        self.stacked_widget.addWidget(self.AdminSignUp)
        self.stacked_widget.addWidget(self.AHome)
        self.stacked_widget.addWidget(self.SHome)

        self.stacked_widget.setCurrentWidget(self.Welcome)

        main_layout.addWidget(self.stacked_widget)

        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.LogoutButton)
        main_layout.addLayout(bottom_layout)

    def Logout(self):

        self.stacked_widget.setCurrentWidget(self.Welcome)

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