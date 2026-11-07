from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from time_utils import zambia_now


db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(
        db.String(80),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(255),
        nullable=False
    )

    password_change_required = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    role = db.Column(
        db.String(20),
        nullable=False
    )

    department = db.Column(
        db.String(50),
        nullable=True
    )

    student_id = db.Column(
        db.String(20),
        nullable=True
    )

class Staff(db.Model):
    __tablename__ = "staff"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    staff_id = db.Column(
        db.String(30),
        unique=True,
        nullable=False
    )

    name = db.Column(
        db.String(150),
        nullable=False
    )

    department = db.Column(
        db.String(100),
        nullable=False
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        unique=True,
        nullable=False
    )

    active = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=zambia_now
    )


    user = db.relationship(
        "User",
        backref="staff_profile",
        uselist=False
    )


class Student(db.Model):
    __tablename__ = "students"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    student_id = db.Column(
        db.String(20),
        unique=True,
        nullable=False
    )

    name = db.Column(
        db.String(150),
        nullable=False
    )

    program = db.Column(
        db.String(150),
        nullable=False
    )

    gender = db.Column(
        db.String(20),
        nullable=True
    )

    date_of_birth = db.Column(db.Date, nullable=True)

    nationality = db.Column(db.String(80), nullable=True)

    residential_address = db.Column(db.Text, nullable=True)

    phone_number = db.Column(db.String(30), nullable=True)

    alternative_phone = db.Column(db.String(30), nullable=True)

    email = db.Column(db.String(120), nullable=True)

    next_of_kin_name = db.Column(db.String(150), nullable=True)

    next_of_kin_relationship = db.Column(db.String(80), nullable=True)

    next_of_kin_phone = db.Column(db.String(30), nullable=True)

    next_of_kin_alternative_phone = db.Column(db.String(30), nullable=True)

    next_of_kin_address = db.Column(db.Text, nullable=True)

    year = db.Column(
        db.Integer,
        nullable=True
    )

    term = db.Column(
        db.Integer,
        nullable=True
    )

    funding = db.Column(
        db.String(50),
        nullable=True
    )

    profile_pic = db.Column(
        db.String(255),
        nullable=True
    )

    accommodation = db.Column(
        db.String(50),
        nullable=True
    )

    hostel = db.Column(
        db.String(100),
        nullable=True
    )

    room = db.Column(
        db.String(50),
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        default=zambia_now
    )


class ProgramFeeSchool(db.Model):
    __tablename__ = "program_fee_schools"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(150),
        unique=True,
        nullable=False
    )

    sections = db.relationship(
        "ProgramFeeSection",
        backref="school",
        cascade="all, delete-orphan",
        lazy=True
    )

    programmes = db.relationship(
        "ProgramFee",
        backref="school",
        lazy=True
    )


class ProgramFeeSection(db.Model):
    __tablename__ = "program_fee_sections"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    school_id = db.Column(
        db.Integer,
        db.ForeignKey("program_fee_schools.id"),
        nullable=False
    )

    name = db.Column(
        db.String(150),
        nullable=False
    )

    programmes = db.relationship(
        "ProgramFee",
        backref="section",
        lazy=True
    )


class ProgramFeeCategory(db.Model):
    __tablename__ = "program_fee_categories"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(150),
        unique=True,
        nullable=False
    )

class ProgramFee(db.Model):
    __tablename__ = "program_fees"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    # --------------------------------------------------------
    # LEGACY CATEGORY FIELD
    #
    # The existing SQLite table still requires category_id.
    # It is retained only for database compatibility.
    # Programme hierarchy is now controlled by school_id
    # and section_id.
    # --------------------------------------------------------
    category_id = db.Column(
        db.Integer,
        db.ForeignKey("program_fee_categories.id"),
        nullable=False
    )

    school_id = db.Column(
        db.Integer,
        db.ForeignKey("program_fee_schools.id"),
        nullable=False
    )

    section_id = db.Column(
        db.Integer,
        db.ForeignKey("program_fee_sections.id"),
        nullable=True
    )

    program = db.Column(
        db.String(150),
        unique=True,
        nullable=False
    )

    total_fee = db.Column(
        db.Float,
        nullable=False,
        default=0
    )


class DepartmentClearance(db.Model):
    __tablename__ = "department_clearances"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    student_id = db.Column(
        db.String(20),
        db.ForeignKey("students.student_id"),
        nullable=False
    )

    department = db.Column(
        db.String(50),
        nullable=False
    )

    status = db.Column(
        db.String(30),
        default="Pending"
    )

    reason = db.Column(
        db.Text,
        nullable=True
    )

    remarks = db.Column(
        db.Text,
        nullable=True
    )


class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    student_id = db.Column(
        db.String(20),
        db.ForeignKey("students.student_id"),
        nullable=False
    )

    amount = db.Column(
        db.Float,
        nullable=False
    )

    file = db.Column(
        db.String(255),
        nullable=True
    )

    status = db.Column(
        db.String(30),
        default="Pending"
    )

    reason = db.Column(
        db.Text,
        nullable=True
    )

    remarks = db.Column(
        db.Text,
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        default=zambia_now
    )



class Hostel(db.Model):
    __tablename__ = "hostels"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(
        db.String(100),
        nullable=False,
        unique=True
    )

    # General hostel policy.
    # "both" means the hostel accommodates both genders,
    # NOT that males and females share rooms.
    gender_policy = db.Column(
        db.String(20),
        nullable=False,
        default="both"
    )

    active = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )

    sections = db.relationship(
        "HostelSection",
        backref="hostel",
        lazy=True,
        cascade="all, delete-orphan"
    )

    blocks = db.relationship(
        "HostelBlock",
        backref="hostel",
        lazy=True,
        cascade="all, delete-orphan"
    )

    rooms = db.relationship(
        "HostelRoom",
        backref="hostel",
        lazy=True
    )


class HostelSection(db.Model):
    __tablename__ = "hostel_sections"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    hostel_id = db.Column(
        db.Integer,
        db.ForeignKey("hostels.id"),
        nullable=False
    )

    # Examples:
    # Girls Side
    # Boys Side
    # Female Wing
    # Male Wing
    name = db.Column(
        db.String(100),
        nullable=False
    )

    # male, female, or both
    #
    # "both" means this section may be used by either gender
    # when configured that way. It does NOT permit a mixed
    # gender room.
    gender_policy = db.Column(
        db.String(20),
        nullable=False,
        default="both"
    )

    active = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )

    display_order = db.Column(
        db.Integer,
        nullable=False,
        default=0
    )

    blocks = db.relationship(
        "HostelBlock",
        backref="section",
        lazy=True
    )

    rooms = db.relationship(
        "HostelRoom",
        backref="section",
        lazy=True
    )


class HostelBlock(db.Model):
    __tablename__ = "hostel_blocks"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    hostel_id = db.Column(
        db.Integer,
        db.ForeignKey("hostels.id"),
        nullable=False
    )

    section_id = db.Column(
        db.Integer,
        db.ForeignKey("hostel_sections.id"),
        nullable=True
    )

    name = db.Column(
        db.String(100),
        nullable=False
    )

    # "block" for China Jianxi
    # "cube" for Katilungu
    # Can be extended later if needed.
    group_type = db.Column(
        db.String(20),
        nullable=False,
        default="block"
    )

    # male, female, or both
    gender_policy = db.Column(
        db.String(20),
        nullable=False,
        default="both",
        server_default="both"
    )

    active = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )

    rooms = db.relationship(
        "HostelRoom",
        backref="block",
        lazy=True
    )


class HostelRoom(db.Model):
    __tablename__ = "hostel_rooms"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    hostel_id = db.Column(
        db.Integer,
        db.ForeignKey("hostels.id"),
        nullable=False
    )

    section_id = db.Column(
        db.Integer,
        db.ForeignKey("hostel_sections.id"),
        nullable=True
    )

    block_id = db.Column(
        db.Integer,
        db.ForeignKey("hostel_blocks.id"),
        nullable=True
    )

    room_number = db.Column(
        db.String(50),
        nullable=False
    )

    capacity = db.Column(
        db.Integer,
        nullable=False,
        default=1
    )

    # Kept for compatibility with the existing SQLite table.
    # This system does NOT allow mixed-gender rooms.
    mixed_gender_allowed = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        server_default="0"
    )

    # male, female, or both
    #
    # "both" means the room can be assigned to either gender
    # according to the section/hostel configuration. It does
    # NOT mean males and females may share the room.
    gender_policy = db.Column(
        db.String(20),
        nullable=False,
        default="both"
    )

    # normal = ordinary sleeping room
    # common = common room
    room_type = db.Column(
        db.String(20),
        nullable=False,
        default="normal"
    )

    active = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )

    # NOTE:
    # mixed_gender_allowed has intentionally been removed from
    # the SQLAlchemy model. The old SQLite column may still exist
    # physically for migration safety, but the application no
    # longer uses it.

    assignments = db.relationship(
        "AccommodationAssignment",
        backref="room",
        lazy=True
    )


class AccommodationAssignment(db.Model):
    __tablename__ = "accommodation_assignments"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    student_id = db.Column(
        db.String(20),
        db.ForeignKey("students.student_id"),
        nullable=False
    )

    room_id = db.Column(
        db.Integer,
        db.ForeignKey("hostel_rooms.id"),
        nullable=False
    )

    status = db.Column(
        db.String(30),
        nullable=False,
        default="Occupying"
    )

    assigned_at = db.Column(
        db.DateTime,
        nullable=False,
        default=zambia_now
    )

    vacated_at = db.Column(
        db.DateTime,
        nullable=True
    )


class HostelItem(db.Model):
    __tablename__ = "hostel_items"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    student_id = db.Column(
        db.String(20),
        db.ForeignKey("students.student_id"),
        nullable=False
    )

    item = db.Column(
        db.String(100),
        nullable=False
    )

    status = db.Column(
        db.String(30),
        nullable=False
    )

    reference = db.Column(
        db.String(150),
        nullable=True
    )

    remarks = db.Column(
        db.Text,
        nullable=True
    )


class LibraryBook(db.Model):
    __tablename__ = "library_books"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    student_id = db.Column(
        db.String(20),
        db.ForeignKey("students.student_id"),
        nullable=False
    )

    name = db.Column(
        db.String(200),
        nullable=False
    )

    borrowed_at = db.Column(
        db.String(100),
        nullable=True
    )

    returned = db.Column(
        db.Boolean,
        default=False
    )

    returned_at = db.Column(
        db.String(100),
        nullable=True
    )


class SportsItem(db.Model):
    __tablename__ = "sports_items"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    student_id = db.Column(
        db.String(20),
        db.ForeignKey("students.student_id"),
        nullable=False
    )

    sport = db.Column(
        db.String(50),
        nullable=False
    )

    item = db.Column(
        db.String(150),
        nullable=True
    )

    status = db.Column(
        db.String(30),
        nullable=True
    )

    remarks = db.Column(
        db.Text,
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        nullable=True,
        default=zambia_now
    )

    responded_at = db.Column(
        db.DateTime,
        nullable=True
    )

    returned_at = db.Column(
        db.DateTime,
        nullable=True
    )


class MathematicsProperty(db.Model):
    __tablename__ = "mathematics_properties"

    id = db.Column(db.Integer, primary_key=True)

    request_id = db.Column(
        db.Integer,
        db.ForeignKey("item_requests.id"),
        nullable=True
    )

    student_id = db.Column(
        db.String(20),
        db.ForeignKey("students.student_id"),
        nullable=False
    )

    name = db.Column(
        db.String(150),
        nullable=False
    )

    status = db.Column(
        db.String(30),
        nullable=True
    )

    remarks = db.Column(
        db.Text,
        nullable=True
    )

    issued_by = db.Column(
        db.String(100),
        nullable=True
    )

    issued_at = db.Column(
        db.DateTime,
        nullable=True
    )

    returned_by = db.Column(
        db.String(100),
        nullable=True
    )

    returned_at = db.Column(
        db.DateTime,
        nullable=True
    )


class TrainingSectionProperty(db.Model):
    __tablename__ = "training_section_properties"

    id = db.Column(db.Integer, primary_key=True)

    request_id = db.Column(
        db.Integer,
        db.ForeignKey("item_requests.id"),
        nullable=True
    )

    student_id = db.Column(
        db.String(20),
        db.ForeignKey("students.student_id"),
        nullable=False
    )

    name = db.Column(
        db.String(150),
        nullable=False
    )

    status = db.Column(
        db.String(30),
        nullable=True
    )

    remarks = db.Column(
        db.Text,
        nullable=True
    )

    issued_by = db.Column(
        db.String(100),
        nullable=True
    )

    issued_at = db.Column(
        db.DateTime,
        nullable=True
    )

    returned_by = db.Column(
        db.String(100),
        nullable=True
    )

    returned_at = db.Column(
        db.DateTime,
        nullable=True
    )


class CommunicationProperty(db.Model):
    __tablename__ = "communication_properties"

    id = db.Column(db.Integer, primary_key=True)

    request_id = db.Column(
        db.Integer,
        db.ForeignKey("item_requests.id"),
        nullable=True
    )

    student_id = db.Column(
        db.String(20),
        db.ForeignKey("students.student_id"),
        nullable=False
    )

    name = db.Column(
        db.String(150),
        nullable=False
    )

    status = db.Column(
        db.String(30),
        nullable=True
    )

    remarks = db.Column(
        db.Text,
        nullable=True
    )

    issued_by = db.Column(
        db.String(100),
        nullable=True
    )

    issued_at = db.Column(
        db.DateTime,
        nullable=True
    )

    returned_by = db.Column(
        db.String(100),
        nullable=True
    )

    returned_at = db.Column(
        db.DateTime,
        nullable=True
    )


class AMETool(db.Model):
    __tablename__ = "ame_tools"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    student_id = db.Column(
        db.String(20),
        db.ForeignKey("students.student_id"),
        nullable=False
    )

    name = db.Column(
        db.String(150),
        nullable=False
    )

    issued_at = db.Column(
        db.String(100),
        nullable=True
    )

    issued_by = db.Column(
        db.String(150),
        nullable=True
    )

    returned = db.Column(
        db.Boolean,
        default=False
    )

    returned_at = db.Column(
        db.String(100),
        nullable=True
    )

    returned_by = db.Column(
        db.String(150),
        nullable=True
    )

    remarks = db.Column(
        db.Text,
        nullable=True
    )


class StoreProperty(db.Model):
    __tablename__ = "store_properties"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    request_id = db.Column(
        db.Integer,
        db.ForeignKey("item_requests.id"),
        nullable=True
    )

    student_id = db.Column(
        db.String(20),
        db.ForeignKey("students.student_id"),
        nullable=False
    )

    name = db.Column(
        db.String(150),
        nullable=False
    )

    status = db.Column(
        db.String(30),
        nullable=True
    )

    remarks = db.Column(
        db.Text,
        nullable=True
    )

    issued_by = db.Column(
        db.String(100),
        nullable=True
    )

    issued_at = db.Column(
        db.DateTime,
        nullable=True
    )

    returned_by = db.Column(
        db.String(100),
        nullable=True
    )

    returned_at = db.Column(
        db.DateTime,
        nullable=True
    )


class Account(db.Model):
    __tablename__ = "accounts"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    student_id = db.Column(
        db.String(20),
        db.ForeignKey("students.student_id"),
        unique=True,
        nullable=False
    )

    total_fee = db.Column(
        db.Float,
        default=0
    )

    paid = db.Column(
        db.Float,
        default=0
    )

    minimum_required = db.Column(
        db.Float,
        default=0
    )

    status = db.Column(
        db.String(30),
        default="Pending"
    )

    reason = db.Column(
        db.Text,
        nullable=True
    )

    remarks = db.Column(
        db.Text,
        nullable=True
    )


class AccountHistory(db.Model):
    __tablename__ = "account_history"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    student_id = db.Column(
        db.String(20),
        db.ForeignKey("students.student_id"),
        nullable=False
    )

    amount = db.Column(
        db.Float,
        nullable=False
    )

    status = db.Column(
        db.String(30),
        nullable=True
    )

    reason = db.Column(
        db.Text,
        nullable=True
    )

    remarks = db.Column(
        db.Text,
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        default=zambia_now
    )




class TSOInspection(db.Model):
    __tablename__ = "tso_inspections"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    student_id = db.Column(
        db.String(20),
        db.ForeignKey("students.student_id"),
        nullable=False
    )

    accommodation_assignment_id = db.Column(
        db.Integer,
        db.ForeignKey("accommodation_assignments.id"),
        nullable=False
    )

    room_id = db.Column(
        db.Integer,
        db.ForeignKey("hostel_rooms.id"),
        nullable=False
    )

    # Physical / technical inspection checklist
    electrical_outlets = db.Column(
        db.String(30),
        nullable=True
    )

    lights = db.Column(
        db.String(30),
        nullable=True
    )

    switches = db.Column(
        db.String(30),
        nullable=True
    )

    wiring = db.Column(
        db.String(30),
        nullable=True
    )

    ventilation = db.Column(
        db.String(30),
        nullable=True
    )

    door_lock = db.Column(
        db.String(30),
        nullable=True
    )

    windows = db.Column(
        db.String(30),
        nullable=True
    )

    plumbing = db.Column(
        db.String(30),
        nullable=True
    )

    furniture = db.Column(
        db.String(30),
        nullable=True
    )

    general_condition = db.Column(
        db.String(30),
        nullable=True
    )

    other = db.Column(
        db.Text,
        nullable=True
    )

    remarks = db.Column(
        db.Text,
        nullable=True
    )

    # Key collection
    key_collected = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        server_default="0"
    )

    key_name = db.Column(
        db.String(200),
        nullable=True
    )

    inspected_by = db.Column(
        db.String(150),
        nullable=True
    )

    inspected_at = db.Column(
        db.DateTime,
        nullable=True
    )

    status = db.Column(
        db.String(30),
        nullable=False,
        default="Pending"
    )



class HostelInspection(db.Model):
    __tablename__ = "hostel_inspections"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    student_id = db.Column(
        db.String(20),
        db.ForeignKey("students.student_id"),
        nullable=False
    )

    accommodation_assignment_id = db.Column(
        db.Integer,
        db.ForeignKey("accommodation_assignments.id"),
        nullable=False
    )

    room_id = db.Column(
        db.Integer,
        db.ForeignKey("hostel_rooms.id"),
        nullable=False
    )

    # General room-condition checklist
    walls = db.Column(
        db.String(30),
        nullable=True
    )

    paint = db.Column(
        db.String(30),
        nullable=True
    )

    floor = db.Column(
        db.String(30),
        nullable=True
    )

    ceiling = db.Column(
        db.String(30),
        nullable=True
    )

    windows = db.Column(
        db.String(30),
        nullable=True
    )

    door = db.Column(
        db.String(30),
        nullable=True
    )

    bed = db.Column(
        db.String(30),
        nullable=True
    )

    mattress = db.Column(
        db.String(30),
        nullable=True
    )

    wardrobe = db.Column(
        db.String(30),
        nullable=True
    )

    desk_table = db.Column(
        db.String(30),
        nullable=True
    )

    chair = db.Column(
        db.String(30),
        nullable=True
    )

    electrical_condition = db.Column(
        db.String(30),
        nullable=True
    )

    other = db.Column(
        db.Text,
        nullable=True
    )

    remarks = db.Column(
        db.Text,
        nullable=True
    )

    inspected_by = db.Column(
        db.String(150),
        nullable=True
    )

    inspected_at = db.Column(
        db.DateTime,
        nullable=True
    )

    status = db.Column(
        db.String(30),
        nullable=False,
        default="Pending"
    )


class ClearanceHistory(db.Model):
    __tablename__ = "clearance_history"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    student_id = db.Column(
        db.String(20),
        db.ForeignKey("students.student_id"),
        nullable=False
    )

    document_id = db.Column(
        db.String(100),
        nullable=False
    )

    generated_time = db.Column(
        db.String(100),
        nullable=True
    )

    status = db.Column(
        db.String(100),
        nullable=True
    )
class ItemRequest(db.Model):
    __tablename__ = "item_requests"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    student_id = db.Column(
        db.String(20),
        db.ForeignKey("students.student_id"),
        nullable=False
    )

    department = db.Column(
        db.String(50),
        nullable=False
    )

    item = db.Column(
        db.String(50),
        nullable=False
    )

    item_type = db.Column(
        db.String(150),
   nullable=False
    )
    status = db.Column(
        db.String(30),
        default="Pending",
        nullable=False
    )

    assigned_by = db.Column(
        db.String(100),
        nullable=True
    )

    assigned_at = db.Column(
        db.DateTime,
        default=zambia_now,
        nullable=False
    )

    responded_at = db.Column(
        db.DateTime,
        nullable=True
    )

    remarks = db.Column(
        db.Text,
        nullable=True
    )


class DepartmentHistory(db.Model):
    __tablename__ = "department_history"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    student_id = db.Column(
        db.String(20),
        db.ForeignKey("students.student_id"),
        nullable=False
    )

    department = db.Column(
        db.String(100),
        nullable=False
    )

    status = db.Column(
        db.String(50),
        nullable=False,
        default="Pending"
    )

    remarks = db.Column(
        db.Text,
        nullable=True
    )

    action = db.Column(
        db.String(100),
        nullable=True
    )

    performed_by = db.Column(
        db.String(100),
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        default=zambia_now,
        nullable=False
    )

# --------------------------------------------------
# ANNOUNCEMENTS
# --------------------------------------------------

class Announcement(db.Model):
    __tablename__ = "announcements"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    title = db.Column(
        db.String(200),
        nullable=False
    )

    message = db.Column(
        db.Text,
        nullable=False
    )

    audience = db.Column(
        db.String(30),
        nullable=False,
        default="all"
    )

    created_by = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        default=zambia_now
    )

    active = db.Column(
        db.Boolean,
        default=True
    )


class DisciplinaryCase(db.Model):
    __tablename__ = "disciplinary_cases"

    id = db.Column(db.Integer, primary_key=True)

    # Student involved in the disciplinary case
    student_id = db.Column(
        db.String(20),
        db.ForeignKey("students.student_id"),
        nullable=False
    )

    # Basic offence information
    offence = db.Column(
        db.String(200),
        nullable=False
    )

    offence_date = db.Column(
        db.DateTime,
        nullable=True
    )

    location = db.Column(
        db.String(200),
        nullable=True
    )

    description = db.Column(
        db.Text,
        nullable=False
    )

    reported_by = db.Column(
        db.String(150),
        nullable=True
    )

    reported_at = db.Column(
        db.DateTime,
        default=zambia_now,
        nullable=False
    )

    # Case lifecycle
    status = db.Column(
        db.String(50),
        default="Reported",
        nullable=False
    )

    # Student's explanation/response
    student_response = db.Column(
        db.Text,
        nullable=True
    )

    response_at = db.Column(
        db.DateTime,
        nullable=True
    )

    # Committee decision
    committee_decision = db.Column(
        db.Text,
        nullable=True
    )

    decision_date = db.Column(
        db.DateTime,
        nullable=True
    )

    decided_by = db.Column(
        db.String(150),
        nullable=True
    )

    # Disciplinary action/sanction
    sanction = db.Column(
        db.String(100),
        nullable=True
    )

    sanction_details = db.Column(
        db.Text,
        nullable=True
    )

    sanction_start = db.Column(
        db.DateTime,
        nullable=True
    )

    sanction_end = db.Column(
        db.DateTime,
        nullable=True
    )

    sanction_status = db.Column(
        db.String(50),
        nullable=True
    )

    # Final resolution
    resolution = db.Column(
        db.Text,
        nullable=True
    )

    resolved_at = db.Column(
        db.DateTime,
        nullable=True
    )

    resolved_by = db.Column(
        db.String(150),
        nullable=True
    )

    remarks = db.Column(
        db.Text,
        nullable=True
    )

    student = db.relationship(
        "Student",
        backref=db.backref(
            "disciplinary_cases",
            lazy=True
        ),
        foreign_keys=[student_id]
    )

