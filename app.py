import re
import os
import sqlite3

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    send_from_directory,
)

from werkzeug.security import check_password_hash, generate_password_hash, generate_password_hash

from models import (
    HostelSection,
    db,
    User,
    Staff,
    Announcement,
    Student,
    DepartmentClearance,
    Payment,
    HostelItem,
    Hostel,
    HostelBlock,
    HostelRoom,
    AccommodationAssignment,
    TSOInspection,
    HostelInspection,
    LibraryBook,
    SportsItem,
    AMETool,
    StoreProperty,
    CommunicationProperty,
    MathematicsProperty,
    TrainingSectionProperty,
    DisciplinaryCase,
    Account,
    AccountHistory,
    ClearanceHistory,
    ItemRequest,
    DepartmentHistory,
    ProgramFeeCategory,
    ProgramFeeSchool,
    ProgramFeeSection,
    ProgramFee
)
from config import DATABASE_URL
from datetime import datetime, timedelta
from time_utils import zambia_now
from config import PROFILE_PICS_FOLDER
from werkzeug.utils import secure_filename


app = Flask(
    __name__,
    static_folder="clearance_static",
    template_folder="templates"
)


# ============================================================
# GLOBAL KWACHA MONEY FORMATTER
# ============================================================

@app.template_filter("money")
def money_filter(value):
    try:
        amount = float(value or 0)
        return f"K{amount:,.2f}"
    except (TypeError, ValueError):
        return "K0.00"

app.config["SECRET_KEY"] = (
    "clearance-system-secret-key"
)

app.config["SQLALCHEMY_DATABASE_URI"] = (
    "sqlite:///" + DATABASE_URL
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)


# ============================================================
# PROGRAMME FEE LOOKUP
# ============================================================
def get_programme_fee(programme):
    """Return the configured fee for a programme."""
    if not programme:
        return 7860.0

    programme_name = str(programme).strip()

    fee_record = ProgramFee.query.filter(
        db.func.lower(ProgramFee.program)
        == programme_name.lower()
    ).first()

    if fee_record and fee_record.total_fee is not None:
        return float(fee_record.total_fee)

    # Legacy fallback when no programme fee is configured.
    return 7860.0




# -----------------------------------------------
# --------------------------------------------------
# STAFF DEPARTMENT NAVIGATION
# --------------------------------------------------

def dept_nav(title='Department'):
    return (
        '<header style="background:#ffffff;border-bottom:1px solid #e2e8f0;padding:20px 30px;">'
        '<div style="max-width:1200px;margin:0 auto;display:flex;justify-content:space-between;align-items:center;gap:20px;flex-wrap:wrap;">'
        '<div><div style="color:#14532d;font-size:22px;font-weight:800;">ZASTI</div>'
        '<div style="color:#64748b;font-size:13px;margin-top:3px;">Digital Student Clearance System</div></div>'
        '<div style="color:#14532d;font-size:18px;font-weight:700;">' + str(title) + '</div>'
        '<div style="display:flex;gap:10px;align-items:center;">'
        ''
        '<a href="/logout" style="text-decoration:none;padding:9px 15px;border-radius:10px;background:#14532d;color:white;font-weight:700;font-size:14px;">Logout</a>'
        '</div></div></header>'
        '<main style="min-height:calc(100vh - 150px);background:#f8fafc;">'
    )


# HOME
# -----------------------------------------------

# ============================================================
# RETURN PROPERTY
# ============================================================


# ============================================================
# STAFF NAME DISPLAY HELPER
# ============================================================

def get_staff_display_name(value):
    """
    Convert a stored staff username into the registered
    Staff.name.

    Example:
        staff_training
        -> Jane Doe

    If no Staff profile can be found, the original value
    is returned safely.
    """

    if not value:
        return "Staff"

    value = str(value).strip()

    # Try username -> User -> Staff profile
    user = User.query.filter_by(
        username=value
    ).first()

    if user:
        staff_member = Staff.query.filter_by(
            user_id=user.id
        ).first()

        if staff_member and staff_member.name:
            return staff_member.name

    # Also allow a staff ID to be supplied
    staff_member = Staff.query.filter_by(
        staff_id=value
    ).first()

    if staff_member and staff_member.name:
        return staff_member.name

    # If it is already a staff name or an old value,
    # leave it unchanged.
    return value



# ============================================================
# HOSTEL STAFF — ACCOMMODATION DASHBOARD
# ============================================================


# ============================================================
# HOSTEL STAFF — ACCOMMODATION DASHBOARD
# ============================================================


# ============================================================
# HOSTEL STAFF — ACCOMMODATION DASHBOARD
# ============================================================


# ============================================================
# STAFF ROOMS — SIMPLE ROOM ASSIGNMENT
# ============================================================

# ============================================================
# STAFF — ASSIGN ROOM
# ============================================================

@app.route("/new-staff/rooms", methods=["GET", "POST"])
def staff_rooms_assignment():

    if not _hostel_staff_allowed():
        return redirect("/login")

    active_statuses = [
        "Occupying",
        "occupying",
        "Active",
        "active",
    ]

    if request.method == "POST":

        student_id = request.form.get(
            "student_id", ""
        ).strip()

        hostel_id_raw = request.form.get(
            "hostel_id", ""
        ).strip()

        block_id_raw = request.form.get(
            "block_id", ""
        ).strip()

        room_number = request.form.get(
            "room_number", ""
        ).strip()

        if not student_id:
            return redirect(
                url_for("staff_rooms_assignment")
            )

        if not hostel_id_raw:
            return redirect(
                url_for("staff_rooms_assignment")
            )

        if not room_number:
            return redirect(
                url_for("staff_rooms_assignment")
            )

        student = Student.query.filter_by(
            student_id=student_id
        ).first()

        if not student:
            return redirect(
                url_for("staff_rooms_assignment")
            )

        # Day scholars do not receive rooms.
        accommodation = (
            student.accommodation or ""
        ).strip().lower()

        if accommodation in {
            "day scholar",
            "day",
            "daystudent",
            "day student",
        }:
            return redirect(
                url_for("staff_rooms_assignment")
            )

        try:
            hostel_id = int(hostel_id_raw)
        except (TypeError, ValueError):
            return redirect(
                url_for("staff_rooms_assignment")
            )

        hostel = Hostel.query.filter_by(
            id=hostel_id,
            active=True
        ).first()

        if not hostel:
            return redirect(
                url_for("staff_rooms_assignment")
            )

        # --------------------------------------------------------
        # Optional Block / Cube
        # --------------------------------------------------------

        block = None

        if block_id_raw:
            try:
                block_id = int(block_id_raw)
            except (TypeError, ValueError):
                block_id = None

            if block_id:
                block = HostelBlock.query.filter_by(
                    id=block_id,
                    hostel_id=hostel.id,
                    active=True
                ).first()

                if not block:
                    return redirect(
                        url_for("staff_rooms_assignment")
                    )

        # --------------------------------------------------------
        # Do not allow a student to have two active rooms.
        # --------------------------------------------------------

        existing_assignment = (
            AccommodationAssignment.query
            .filter(
                AccommodationAssignment.student_id
                == student.student_id,
                AccommodationAssignment.status.in_(
                    active_statuses
                )
            )
            .first()
        )

        if existing_assignment:
            return redirect(
                url_for("staff_rooms_assignment")
            )

        # --------------------------------------------------------
        # Find the room.
        #
        # If it already exists, use it.
        # If it does not exist, CREATE IT automatically.
        # --------------------------------------------------------

        room_query = HostelRoom.query.filter_by(
            hostel_id=hostel.id,
            room_number=room_number,
            active=True
        )

        if block:
            room_query = room_query.filter_by(
                block_id=block.id
            )
        else:
            room_query = room_query.filter(
                HostelRoom.block_id.is_(None)
            )

        room = room_query.first()
        # --------------------------------------------------------
        # GENDER COMPATIBILITY
        # --------------------------------------------------------

        student_gender = (
            student.gender or ""
        ).strip().lower()

        if student_gender not in {"male", "female"}:
            flash(
                "Room allocation stopped: this student needs a valid gender record first.",
                "error"
            )
            return redirect(url_for("staff_rooms_assignment"))

        section_id = (
            room.section_id
            if room is not None
            else (block.section_id if block else None)
        )

        section = (
            db.session.get(HostelSection, section_id)
            if section_id
            else None
        )

        if section and not section.active:
            flash(
                "Room allocation stopped: the selected section is inactive.",
                "error"
            )
            return redirect(url_for("staff_rooms_assignment"))

        hostel_policy = (
            hostel.gender_policy or "both"
        ).strip().lower()

        section_policy = (
            (section.gender_policy or "both").strip().lower()
            if section
            else "both"
        )

        block_policy = (
            (block.gender_policy or "both").strip().lower()
            if block
            else "both"
        )

        room_policy = (
            (room.gender_policy or "both").strip().lower()
            if room is not None
            else (
                block_policy
                if block
                else (
                    section_policy
                    if section
                    else hostel_policy
                )
            )
        )

        for policy_name, policy in (
            ("hostel", hostel_policy),
            ("section", section_policy),
            ("block/cube", block_policy),
            ("room", room_policy),
        ):
            if policy not in {"male", "female", "both"}:
                flash(
                    f"Room allocation stopped: invalid {policy_name} gender policy.",
                    "error"
                )
                return redirect(url_for("staff_rooms_assignment"))

            if policy != "both" and policy != student_gender:
                flash(
                    f"Room allocation stopped: the student's gender does not match the {policy_name} policy.",
                    "error"
                )
                return redirect(url_for("staff_rooms_assignment"))

        # Existing occupants must have known, matching genders.
        if room is not None:
            current_room_assignments = (
                AccommodationAssignment.query
                .filter(
                    AccommodationAssignment.room_id == room.id,
                    AccommodationAssignment.status.in_(active_statuses)
                )
                .all()
            )

            for current_assignment in current_room_assignments:
                occupant = Student.query.filter_by(
                    student_id=current_assignment.student_id
                ).first()

                occupant_gender = (
                    (occupant.gender or "").strip().lower()
                    if occupant
                    else ""
                )

                if occupant_gender not in {"male", "female"}:
                    flash(
                        "Room allocation stopped: an existing occupant has no valid gender record.",
                        "error"
                    )
                    return redirect(url_for("staff_rooms_assignment"))

                if occupant_gender != student_gender:
                    flash(
                        "Room allocation stopped: male and female students cannot share a room.",
                        "error"
                    )
                    return redirect(url_for("staff_rooms_assignment"))


        if room is None:

            # New rooms default to two occupants.
            room_capacity = 2

            room = HostelRoom(
                hostel_id=hostel.id,
                section_id=(
                    block.section_id
                    if block
                    else None
                ),
                block_id=(
                    block.id
                    if block
                    else None
                ),
                room_number=room_number,
                capacity=room_capacity,
                gender_policy=room_policy,
                room_type="normal",
                active=True
            )

            db.session.add(room)
            db.session.flush()

        # --------------------------------------------------------
        # Check room capacity.
        # --------------------------------------------------------

        occupied = (
            AccommodationAssignment.query
            .filter(
                AccommodationAssignment.room_id
                == room.id,
                AccommodationAssignment.status.in_(
                    active_statuses
                )
            )
            .count()
        )

        capacity = max(
            room.capacity or 2,
            1
        )

        if occupied >= capacity:
            db.session.rollback()
            return redirect(
                url_for("staff_rooms_assignment")
            )

        # --------------------------------------------------------
        # Create assignment.
        # --------------------------------------------------------

        assignment = AccommodationAssignment(
            student_id=student.student_id,
            room_id=room.id,
            status="Occupying",
            assigned_at=zambia_now()
        )

        # Keep Student record synchronized.
        student.hostel = hostel.name

        if block:
            student.room = (
                f"{block.name} - {room_number}"
            )
        else:
            student.room = room_number

        db.session.add(assignment)
        db.session.commit()

        return redirect(
            url_for("staff_rooms_assignment")
        )

    # ============================================================
    # GET
    # ============================================================

    students = (
        Student.query
        .order_by(Student.student_id.asc())
        .all()
    )

    # Day scholars are never assigned rooms.
    students = [
        student
        for student in students
        if (
            student.accommodation or ""
        ).strip().lower()
        not in {
            "day scholar",
            "day",
            "daystudent",
            "day student",
        }
    ]

    hostels = (
        Hostel.query
        .filter_by(active=True)
        .order_by(Hostel.name.asc())
        .all()
    )

    blocks = (
        HostelBlock.query
        .filter_by(active=True)
        .order_by(
            HostelBlock.hostel_id.asc(),
            HostelBlock.name.asc()
        )
        .all()
    )

    active_assignments = (
        AccommodationAssignment.query
        .filter(
            AccommodationAssignment.status.in_(
                active_statuses
            )
        )
        .all()
    )

    assigned_student_ids = {
        assignment.student_id
        for assignment in active_assignments
    }

    available_students = [
        student
        for student in students
        if student.student_id
        not in assigned_student_ids
    ]

    occupied_by_room = {}

    for assignment in active_assignments:
        occupied_by_room[assignment.room_id] = (
            occupied_by_room.get(
                assignment.room_id,
                0
            ) + 1
        )

    return render_template(
        "new_staff/hostel/rooms.html",
        students=available_students,
        hostels=hostels,
        blocks=blocks,
        occupied_by_room=occupied_by_room,
    )


@app.route("/hostel/dashboard")
def hostel_dashboard():
    if not _hostel_staff_allowed():
        return redirect("/login")

    students = Student.query.order_by(
        Student.name.asc()
    ).all()

    boarders = [
        student
        for student in students
        if (student.accommodation or "").strip().lower()
        in {
            "boarding",
            "boarder",
            "boarding student",
        }
    ]

    day_scholars = [
        student
        for student in students
        if (student.accommodation or "").strip().lower()
        in {
            "day scholar",
            "day",
            "daystudent",
            "day student",
        }
    ]

    active_assignments = (
        AccommodationAssignment.query
        .filter(
            db.func.lower(
                db.func.trim(
                    db.func.coalesce(
                        AccommodationAssignment.status,
                        ""
                    )
                )
            ).in_(["occupying", "active"])
        )
        .order_by(
            AccommodationAssignment.assigned_at.desc(),
            AccommodationAssignment.id.desc()
        )
        .all()
    )

    vacated_assignments = (
        AccommodationAssignment.query
        .filter(
            db.func.lower(
                db.func.trim(
                    db.func.coalesce(
                        AccommodationAssignment.status,
                        ""
                    )
                )
            ) == "vacated"
        )
        .order_by(
            AccommodationAssignment.vacated_at.desc(),
            AccommodationAssignment.id.desc()
        )
        .limit(10)
        .all()
    )

    hostels = (
        Hostel.query
        .filter_by(active=True)
        .order_by(Hostel.name.asc())
        .all()
    )

    sections = (
        HostelSection.query
        .filter_by(active=True)
        .order_by(
            HostelSection.display_order.asc(),
            HostelSection.name.asc()
        )
        .all()
    )

    blocks = (
        HostelBlock.query
        .filter_by(active=True)
        .order_by(
            HostelBlock.name.asc()
        )
        .all()
    )

    rooms = (
        HostelRoom.query
        .filter_by(active=True)
        .order_by(
            HostelRoom.room_number.asc()
        )
        .all()
    )

    students_by_id = {
        student.student_id: student
        for student in students
    }

    rooms_by_id = {
        room.id: room
        for room in rooms
    }

    recent_assignments = (
        AccommodationAssignment.query
        .order_by(
            AccommodationAssignment.assigned_at.desc(),
            AccommodationAssignment.id.desc()
        )
        .limit(10)
        .all()
    )

    recent_inspections = (
        HostelInspection.query
        .order_by(
            HostelInspection.inspected_at.desc(),
            HostelInspection.id.desc()
        )
        .limit(10)
        .all()
    )

    recent_announcements = (
        Announcement.query
        .filter(
            Announcement.active == True,
            Announcement.audience.in_(["staff", "all"])
        )
        .order_by(
            Announcement.created_at.desc()
        )
        .limit(5)
        .all()
    )

    # --------------------------------------------------
    # DASHBOARD SETTINGS
    # Existing staff mini academic calendar/clock uses
    # these values from system_settings.
    # --------------------------------------------------
    import sqlite3

    calendar_conn = sqlite3.connect(DATABASE_URL)
    calendar_cursor = calendar_conn.cursor()

    calendar_cursor.execute("""
        SELECT setting_key, setting_value
        FROM system_settings
    """)

    settings = dict(calendar_cursor.fetchall())

    calendar_conn.close()

    return render_template(
        "new_staff/hostel/dashboard.html",
        staff_name=(
            session.get("staff_name")
            or session.get("user")
            or "Hostel Staff"
        ),

        students=students,
        students_by_id=students_by_id,
        rooms_by_id=rooms_by_id,

        total_students=len(students),
        boarders=len(boarders),
        day_scholars=len(day_scholars),

        active_assignments=active_assignments,
        active_assignment_count=len(active_assignments),
        vacated_assignments=vacated_assignments,

        hostels=hostels,
        sections=sections,
        blocks=blocks,
        rooms=rooms,

        total_hostels=len(hostels),
        total_sections=len(sections),
        total_blocks=len(blocks),
        total_rooms=len(rooms),

        recent_assignments=recent_assignments,
        recent_inspections=recent_inspections,
        recent_announcements=recent_announcements,
        settings=settings,
    )


@app.route("/student/item/<int:item_id>/accept", methods=["POST"])
def accept_item(item_id):

    if session.get("role") != "student":
        return redirect(
            url_for("student_login")
        )

    student_id = session.get("student_id")

    item_request = ItemRequest.query.filter_by(
        id=item_id,
        student_id=student_id
    ).first()

    if not item_request:
        flash(
            "Item request not found.",
            "error"
        )

        return redirect(
            url_for("student_dashboard")
        )

    if item_request.status != "Pending":
        flash(
            "This item request has already been responded to.",
            "error"
        )

        return redirect(
            url_for("student_dashboard")
        )

    # --------------------------------------------------------
    # RECORD STUDENT RESPONSE
    # --------------------------------------------------------

    response_time = zambia_now()

    item_request.status = "Accepted"
    item_request.responded_at = response_time

    # --------------------------------------------------------
    # CREATE ACTUAL PROPERTY ONLY AFTER ACCEPTANCE
    # --------------------------------------------------------

    if item_request.item_type == "Institutional Property":

        # --------------------------------------------------------
        # CREATE THE ACTUAL PROPERTY RECORD AFTER STUDENT
        # CONFIRMATION.
        #
        # The property table is determined by the department
        # that created the ItemRequest.
        #
        # Communication Skills -> CommunicationProperty
        # Stores Officer       -> StoreProperty
        # --------------------------------------------------------

        request_department = (
            item_request.department or ""
        ).strip().lower()

        if request_department in {
            "communication skills (rel/sc)",
            "communication skills (rel sc)",
            "communication skills",
        }:

            existing_property = CommunicationProperty.query.filter_by(
                request_id=item_request.id
            ).first()

            if not existing_property:

                property_record = CommunicationProperty(
                    request_id=item_request.id,
                    student_id=student_id,
                    name=item_request.item,
                    status="Issued",
                    issued_by=item_request.assigned_by or "Communication Skills Staff",
                    issued_at=response_time,
                    returned_by=None,
                    returned_at=None,
                    remarks=(
                        f"Confirmed by student. "
                        f"Requested by "
                        f"{item_request.assigned_by or 'Staff'} "
                        f"from {item_request.department}."
                    )
                )

                db.session.add(property_record)

        elif request_department in {
            "mathematics",
            "mathematics department",
        }:
            existing_property = MathematicsProperty.query.filter_by(
                request_id=item_request.id
            ).first()

            if not existing_property:
                property_record = MathematicsProperty(
                    request_id=item_request.id,
                    student_id=student_id,
                    name=item_request.item,
                    status="Issued",
                    issued_by=item_request.assigned_by or "Mathematics Staff",
                    issued_at=response_time,
                    returned_by=None,
                    returned_at=None,
                    remarks=(
                        f"Confirmed by student. "
                        f"Requested by "
                        f"{item_request.assigned_by or 'Staff'} "
                        f"from {item_request.department}."
                    )
                )

                db.session.add(property_record)

        elif request_department in {
            "stores officer",
            "stores",
            "stores office",
            "stores department",
        }:

            existing_property = StoreProperty.query.filter_by(
                request_id=item_request.id
            ).first()

            if not existing_property:

                property_record = StoreProperty(
                    request_id=item_request.id,
                    student_id=student_id,
                    name=item_request.item,
                    status="Issued",
                    issued_by=item_request.assigned_by or "Stores Staff",
                    issued_at=response_time,
                    returned_by=None,
                    returned_at=None,
                    remarks=(
                        f"Confirmed by student. "
                        f"Requested by "
                        f"{item_request.assigned_by or 'Staff'} "
                        f"from {item_request.department}."
                    )
                )

                db.session.add(property_record)

    # --------------------------------------------------------

        elif request_department in {
            "ame stores",
            "ame stores department",
            "ame",
        }:

            # AME tools do not have a request_id column.
            # The ItemRequest itself is the pending/response record.
            # Only create the actual AMETool after acceptance.

            existing_tool = AMETool.query.filter_by(
                student_id=student_id,
                name=item_request.item,
                returned=False
            ).first()

            if not existing_tool:

                tool_record = AMETool(
                    student_id=student_id,
                    name=item_request.item,
                    issued_at=response_time.strftime(
                        "%d %b %Y %H:%M:%S"
                    ),
                    issued_by=(
                        item_request.assigned_by
                        or "AME Stores Staff"
                    ),
                    returned=False,
                    returned_at=None,
                    returned_by=None,
                    remarks=(
                        f"Confirmed by student. "
                        f"Requested by "
                        f"{item_request.assigned_by or 'AME Stores Staff'} "
                        f"from AME Stores. "
                        f"Request ID: {item_request.id}."
                        + (
                            f" Notes: {item_request.remarks}"
                            if item_request.remarks
                            else ""
                        )
                    )
                )

                db.session.add(tool_record)

        elif request_department == "training section":

            existing_property = TrainingSectionProperty.query.filter_by(
                request_id=item_request.id
            ).first()

            if not existing_property:

                property_record = TrainingSectionProperty(
                    request_id=item_request.id,
                    student_id=student_id,
                    name=item_request.item,
                    status="Issued",
                    issued_by=(
                        item_request.assigned_by
                        or "Training Section Staff"
                    ),
                    issued_at=response_time,
                    returned_by=None,
                    returned_at=None,
                    remarks=(
                        f"Confirmed by student. "
                        f"Requested by "
                        f"{item_request.assigned_by or 'Staff'} "
                        f"from Training Section."
                    )
                )

                db.session.add(property_record)

    # UNIVERSAL DEPARTMENT HISTORY
    # --------------------------------------------------------
    # IMPORTANT:
    # This uses the department stored on the request.
    #
    # Therefore:
    # Training Section -> Training Section history
    # Library          -> Library history
    # AME Stores       -> AME Stores history
    # Sports           -> Sports history
    # etc.
    # --------------------------------------------------------

    # --------------------------------------------------------
    # PERMANENT DEPARTMENT HISTORY
    # --------------------------------------------------------
    # Record the student's response against the department
    # that originally created the request.
    #
    # created_at on DepartmentHistory records the actual
    # response time automatically.
    # --------------------------------------------------------

    history = DepartmentHistory(
        student_id=student_id,
        department=item_request.department,
        status="Accepted",
        remarks=(
            f"Item: {item_request.item} | "
            f"Student accepted this request. | "
            f"Requested by: "
            f"{item_request.assigned_by or 'Staff'} | "
            f"Request created: "
            f"{item_request.assigned_at.strftime('%d %b %Y %H:%M:%S')}"
            if item_request.assigned_at
            else (
                f"Item: {item_request.item} | "
                f"Student accepted this request. | "
                f"Requested by: "
                f"{item_request.assigned_by or 'Staff'}"
            )
        ),
        action="Item Request Accepted",
        performed_by=(
            item_request.assigned_by or "Staff"
        )
    )

    db.session.add(history)

    db.session.commit()

    flash(
        f"{item_request.item} accepted successfully.",
        "success"
    )

    return redirect(
        url_for("student_dashboard")
    )










@app.route(
    "/admin",
    methods=["GET", "POST"]
)
def admin_login():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        user = User.query.filter_by(
            username=username,
            role="admin"
        ).first()

        if user and check_password_hash(
            user.password,
            password
        ):

            session.clear()

            session["user_id"] = user.id
            session["username"] = user.username
            session["role"] = user.role

            return redirect(
                url_for("admin_dashboard")
            )

        flash(
            "Invalid administrator username or password.",
            "error"
        )

    return render_template(
        "admin/login.html"
    )

# --------------------------------------------------
# STUDENT DASHBOARD
# --------------------------------------------------



# --------------------------------------------------
# STAFF LOGIN
# --------------------------------------------------

@app.route("/")
def home():
    return render_template("student/login.html")

# --------------------------------------------------
# STUDENT LOGIN
# --------------------------------------------------

@app.route(
    "/student-login",
    methods=["GET", "POST"]
)
def student_login():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        user = User.query.filter_by(
            username=username,
            role="student"
        ).first()

        # ------------------------------------------
        # VALID LOGIN
        # ------------------------------------------

        if user and check_password_hash(
            user.password,
            password
        ):

            session.clear()

            session["user_id"] = user.id
            session["username"] = user.username
            session["role"] = user.role
            session["student_id"] = user.student_id

            # Newly registered students must change temporary password first.
            if user.password_change_required:
                return redirect(url_for("reset_password"))

            # Student must read T&C after login
            return redirect(
                url_for("terms")
            )

        # ------------------------------------------
        # INVALID LOGIN
        # ------------------------------------------

        flash(
            "Invalid student ID or password.",
            "error"
        )

    return render_template(
        "student/login.html"
    )













@app.route("/student/upload-proof", methods=["GET", "POST"])
def upload_proof():

    if session.get("role") != "student":
        return redirect(
            url_for("student_login")
        )

    student = Student.query.filter_by(
        student_id=session.get("student_id")
    ).first()

    if not student:
        return "Student record not found.", 404

    if request.method == "POST":

        amount = request.form.get(
            "amount",
            ""
        ).strip()

        proof = request.files.get("proof")

        if not amount:
            flash(
                "Please enter the payment amount.",
                "error"
            )

            return redirect(
                url_for("upload_proof")
            )

        if not proof or not proof.filename:
            flash(
                "Please select your proof of payment.",
                "error"
            )

            return redirect(
                url_for("upload_proof")
            )

        try:
            amount = float(amount)

        except ValueError:

            flash(
                "Please enter a valid payment amount.",
                "error"
            )

            return redirect(
                url_for("upload_proof")
            )

        filename = proof.filename

        extension = filename.rsplit(
            ".",
            1
        )[-1].lower()

        allowed_extensions = {
            "png",
            "jpg",
            "jpeg",
            "pdf"
        }

        if extension not in allowed_extensions:

            flash(
                "Only PNG, JPG, JPEG and PDF files are allowed.",
                "error"
            )

            return redirect(
                url_for("upload_proof")
            )

        import os
        from werkzeug.utils import secure_filename
        from config import DOCUMENTS_FOLDER

        os.makedirs(
            DOCUMENTS_FOLDER,
            exist_ok=True
        )

        safe_filename = secure_filename(
            proof.filename
        )

        final_filename = (
            student.student_id
            + "_"
            + str(int(zambia_now().timestamp()))
            + "_"
            + safe_filename
        )

        proof.save(
            os.path.join(
                DOCUMENTS_FOLDER,
                final_filename
            )
        )

        payment = Payment(
            student_id=student.student_id,
            amount=amount,
            file=final_filename,
            status="Pending"
        )

        db.session.add(payment)

        db.session.commit()

        flash(
            "Proof of payment submitted successfully.",
            "success"
        )

        return redirect(
            url_for("upload_proof")
        )

    payments = Payment.query.filter_by(
        student_id=student.student_id
    ).order_by(
        Payment.created_at.desc()
    ).all()

    return render_template(
        "student/upload_proof.html",
        student=student,
        payments=payments,
        show_sidebar=True
    )


# --------------------------------------------------
# STUDENT CLEARANCE REPORT
# --------------------------------------------------

# --------------------------------------------------
# STUDENT CLEARANCE REPORT
# --------------------------------------------------



# =========================================================
# STUDENT ACCOMMODATION
# =========================================================


@app.route("/profile-pics/<filename>")
def serve_profile_picture(filename):

    if not filename:
        return "", 404

    from config import PROFILE_PICS_FOLDER

    return send_from_directory(
        PROFILE_PICS_FOLDER,
        filename
    )


# --------------------------------------------------

# STUDENT PROOF OF PAYMENT
# --------------------------------------------------

@app.route("/student/profile", methods=["GET", "POST"])
def student_profile():

    if session.get("role") != "student":
        return redirect(
            url_for("student_login")
        )

    student = Student.query.filter_by(
        student_id=session.get("student_id")
    ).first()

    if not student:
        return "Student record not found.", 404

    if request.method == "POST":

        profile_file = request.files.get("profile_pic")

        if profile_file and profile_file.filename:

            from werkzeug.utils import secure_filename
            from config import PROFILE_PICS_FOLDER
            import os

            os.makedirs(
                PROFILE_PICS_FOLDER,
                exist_ok=True
            )

            filename = secure_filename(
                profile_file.filename
            )

            extension = ""

            if "." in filename:
                extension = "." + filename.rsplit(
                    ".", 1
                )[1].lower()

            allowed_extensions = {
                ".png",
                ".jpg",
                ".jpeg"
            }

            if extension not in allowed_extensions:

                flash(
                    "Please upload a PNG, JPG or JPEG image.",
                    "error"
                )

                return redirect(
                    url_for("student_profile")
                )

            final_filename = (
                student.student_id
                + "_profile"
                + extension
            )

            filepath = os.path.join(
                PROFILE_PICS_FOLDER,
                final_filename
            )

            profile_file.save(filepath)

            student.profile_pic = (
                "profile_pics/"
                + final_filename
            )

            db.session.commit()

            flash(
                "Profile picture updated successfully.",
                "success"
            )

            return redirect(
                url_for("student_profile")
            )

    return render_template(
        "student/profile.html",
        student=student,
        show_sidebar=True
    )


# --------------------------------------------------
# SERVE STUDENT PROFILE PICTURES
# --------------------------------------------------



# ============================================================
# STUDENT — CONFIRM SPORTS ITEM
# ============================================================

@app.route(
    "/student/sports/confirm/<int:item_id>",
    methods=["POST"]
)
def student_confirm_sports_item(item_id):

    if session.get("role") != "student":
        return redirect(
            url_for("student_login")
        )

    student_id = (
        session.get("student_id") or ""
    ).strip()

    if not student_id:
        return redirect(
            url_for("student_login")
        )

    item = SportsItem.query.filter_by(
        id=item_id,
        student_id=student_id
    ).first()

    if not item:

        flash(
            "Sports assignment not found.",
            "error"
        )

        return redirect(
            url_for("student_dashboard")
        )

    if (
        (item.status or "").strip().lower()
        != "pending"
    ):

        flash(
            "This sports assignment is no longer awaiting confirmation.",
            "error"
        )

        return redirect(
            url_for("student_dashboard")
        )

    item.status = "confirmed"

    item.remarks = "Confirmed by student."

    db.session.commit()

    flash(
        f"{item.item} has been confirmed.",
        "success"
    )

    return redirect(
        url_for("student_dashboard")
    )



@app.route(
    "/student/sports/accept/<int:item_id>",
    methods=["POST"]
)
def student_accept_sports_item(item_id):

    if session.get("role") != "student":
        return redirect(
            url_for("student_login")
        )

    student_id = (
        session.get("student_id") or ""
    ).strip()

    if not student_id:
        return redirect(
            url_for("student_login")
        )

    item = SportsItem.query.filter_by(
        id=item_id,
        student_id=student_id
    ).first()

    if not item:
        flash(
            "Sports assignment not found.",
            "error"
        )
        return redirect(
            url_for("student_dashboard")
        )

    if (
        (item.status or "").strip().lower()
        != "pending"
    ):
        flash(
            "This sports assignment is no longer awaiting a response.",
            "error"
        )
        return redirect(
            url_for("student_dashboard")
        )

    item.status = "confirmed"
    item.remarks = "Accepted by student."

    from datetime import datetime
    item.responded_at = zambia_now()

    db.session.commit()

    flash(
        f"{item.item} was accepted successfully.",
        "success"
    )

    return redirect(
        url_for("student_dashboard")
    )


@app.route(
    "/student/sports/decline/<int:item_id>",
    methods=["POST"]
)
def student_decline_sports_item(item_id):

    if session.get("role") != "student":
        return redirect(
            url_for("student_login")
        )

    student_id = (
        session.get("student_id") or ""
    ).strip()

    if not student_id:
        return redirect(
            url_for("student_login")
        )

    item = SportsItem.query.filter_by(
        id=item_id,
        student_id=student_id
    ).first()

    if not item:
        flash(
            "Sports assignment not found.",
            "error"
        )
        return redirect(
            url_for("student_dashboard")
        )

    if (
        (item.status or "").strip().lower()
        != "pending"
    ):
        flash(
            "This sports assignment is no longer awaiting a response.",
            "error"
        )
        return redirect(
            url_for("student_dashboard")
        )

    item.status = "declined"
    item.remarks = "Declined by student."

    from datetime import datetime
    item.responded_at = zambia_now()

    db.session.commit()

    flash(
        f"{item.item} was declined.",
        "error"
    )

    return redirect(
        url_for("student_dashboard")
    )


@app.route("/student/dashboard")
def student_dashboard():

    if session.get("role") != "student":
        return redirect(
            url_for("student_login")
        )

    student = Student.query.filter_by(
        student_id=session.get("student_id")
    ).first()


    # --------------------------------------------------
    # PENDING ITEM REQUESTS
    # --------------------------------------------------
    # Staff may offer/assign an item to a student, but
    # the item is NOT actually allocated until the student
    # accepts it.
    #
    # Pending requests therefore appear on the dashboard
    # and allow the student to Accept or Decline.
    # --------------------------------------------------

    pending_item_requests = (
        ItemRequest.query
        .filter(
            ItemRequest.student_id == student.student_id,
            db.func.lower(ItemRequest.status) == "pending"
        )
        .order_by(ItemRequest.id.desc())
        .all()
    )

    if not student:
        return "Student record not found.", 404

    # --------------------------------------------------
    # DEPARTMENT CLEARANCE
    # --------------------------------------------------

    clearances = DepartmentClearance.query.filter_by(
        student_id=student.student_id
    ).all()

    clearance_map = {
        c.department: c
        for c in clearances
    }

    # --------------------------------------------------
    # LIBRARY
    # --------------------------------------------------

    library_books = LibraryBook.query.filter_by(
        student_id=student.student_id,
        returned=False
    ).all()

    # --------------------------------------------------
    # LIBRARY BOOKS AWAITING STUDENT CONFIRMATION
    # --------------------------------------------------

    import sqlite3

    con = sqlite3.connect("database.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    pending_library_books = cur.execute(
        """
        SELECT
            id,
            name,
            borrowed_at,
            status
        FROM library_books
        WHERE student_id = ?
          AND COALESCE(status, '') = 'pending'
        ORDER BY id DESC
        """,
        (student.student_id,)
    ).fetchall()

    con.close()

    library_status = (
        "Pending"
        if library_books
        else "Cleared"
    )

    # --------------------------------------------------
    # SPORTS
    # --------------------------------------------------

    sports_items = SportsItem.query.filter_by(
        student_id=student.student_id
    ).order_by(
        SportsItem.id.desc()
    ).all()

    # --------------------------------------------------
    # SPORTS ITEMS AWAITING STUDENT CONFIRMATION
    # --------------------------------------------------

    pending_sports_items = [
        item
        for item in sports_items
        if (item.status or "").strip().lower() == "pending"
    ]

    sports_pending = any(
        (item.status or "").strip().lower() != "returned"
        for item in sports_items
    )

    sports_status = (
        "Pending"
        if sports_pending
        else "Cleared"
    )

    # --------------------------------------------------
    # AME STORES
    # --------------------------------------------------

    ame_tools = AMETool.query.filter_by(
        student_id=student.student_id,
        returned=False
    ).all()

    ame_status = (
        "Pending"
        if ame_tools
        else "Cleared"
    )

    # --------------------------------------------------
    # STORES
    # --------------------------------------------------

    store_items = StoreProperty.query.filter_by(
        student_id=student.student_id
    ).all()

    hostel_items = HostelItem.query.filter_by(
        student_id=student.student_id
    ).all()

    unreturned_store_items = [
        item
        for item in store_items
        if item.status != "Returned"
    ]

    unreturned_hostel_items = [
        item
        for item in hostel_items
        if item.status != "Returned"
    ]

    is_day_scholar = (
        student.accommodation == "Day Scholar"
    )

    if is_day_scholar:

        stores_status = "Cleared"

    elif (
        unreturned_store_items
        or unreturned_hostel_items
    ):

        stores_status = "Pending"

    else:

        stores_status = "Cleared"

    # --------------------------------------------------
    # ACCOUNTS
    # --------------------------------------------------

    account = Account.query.filter_by(
        student_id=student.student_id
    ).first()

    if account:

        outstanding = (
            (account.total_fee or 0)
            - (account.paid or 0)
        )

        minimum_required = (
            account.minimum_required or 0
        )

        accounts_status = (
            "Cleared"
            if (
                outstanding <= 0
                or account.paid >= minimum_required
            )
            else "Pending"
        )

    else:

        accounts_status = "Pending"

    # --------------------------------------------------
    # OTHER DEPARTMENTS
    # --------------------------------------------------

    def department_status(name):

        clearance = clearance_map.get(name)

        if clearance:

            return clearance.status or "Pending"

        return "Pending"

    communication_status = department_status(
        "communication"
    )

    mathematics_status = department_status(
        "mathematics"
    )

    hr_status = department_status(
        "hr"
    )

    training_status = department_status(
        "training"
    )

    # --------------------------------------------------
    # DIGITAL CLEARANCE SUMMARY
    # --------------------------------------------------

    departments = [

        ("Library", library_status),

        ("Sports", sports_status),

        ("Accounts", accounts_status),

        ("Stores Office", stores_status),

        (
            "Communication Skills (REL/SC)",
            communication_status
        ),

        (
            "Mathematics",
            mathematics_status
        ),

        (
            "Human Resource/Admin Office",
            hr_status
        ),

        (
            "Training Section",
            training_status
        ),

        (
            "AME Stores",
            ame_status
        )
    ]

    # --------------------------------------------------
    # DAY SCHOLAR RULE
    # --------------------------------------------------

    if is_day_scholar:

        departments = [
            item
            for item in departments
            if item[0] != "Stores"
        ]

    # --------------------------------------------------
    # CLEARANCE CALCULATION
    # --------------------------------------------------

    cleared = sum(
        1
        for name, status in departments
        if status == "Cleared"
    )

    total = len(departments)

    percentage = (
        int((cleared / total) * 100)
        if total
        else 0
    )

    pending_departments = [
        name
        for name, status in departments
        if status != "Cleared"
    ]

    # --------------------------------------------------
    # PHYSICAL CLEARANCE
    # --------------------------------------------------

    physical_required = not is_day_scholar

    # --------------------------------------------------
    # GREETING
    # --------------------------------------------------

    from datetime import datetime

    hour = zambia_now().hour

    if hour < 12:

        greeting = "Good Morning"

    elif hour < 17:

        greeting = "Good Afternoon"

    else:

        greeting = "Good Evening"

    today = zambia_now().strftime(
        "%A, %d %B %Y"
    )

    # --------------------------------------------------
    # ANNOUNCEMENTS
    # --------------------------------------------------
    #
    # Students should see:
    #   1. announcements specifically sent to students
    #   2. announcements sent to everyone
    #
    # Only active announcements are displayed.
    # --------------------------------------------------

    announcements = (
        Announcement.query
        .filter(
            Announcement.active == True,
            Announcement.audience.in_(["students", "all"])
        )
        .order_by(
            Announcement.created_at.desc()
        )
        .all()
    )

    # --------------------------------------------------
    # ACCOUNT HISTORY / LATEST TRANSACTIONS
    # --------------------------------------------------

    account_history = (
        AccountHistory.query
        .filter_by(
            student_id=student.student_id
        )
        .order_by(
            AccountHistory.created_at.desc(),
            AccountHistory.id.desc()
        )
        .limit(10)
        .all()
    )

    # --------------------------------------------------
    # RETURN DASHBOARD
    # --------------------------------------------------

    # The detailed clearance report is the single source of truth.
    report_snapshot = student_clearance(_return_snapshot=True)

    if not isinstance(report_snapshot, dict):
        raise RuntimeError(
            "Could not obtain the finalized clearance report snapshot."
        )

    report_rows = report_snapshot.get("clearance_rows")
    if not isinstance(report_rows, list) or len(report_rows) != 11:
        raise RuntimeError(
            "Expected exactly 11 finalized clearance rows; "
            f"received {len(report_rows) if isinstance(report_rows, list) else 'invalid data'}."
        )

    # Use the finalized report rows for every dashboard status.
    status_by_department = {
        str(row.get("department", "")).strip().casefold():
            str(row.get("status", "Pending")).strip()
        for row in report_rows
    }

    def report_status(department, fallback="Pending"):
        return status_by_department.get(
            department.casefold(),
            fallback
        )

    library_status = report_status("Library", library_status)
    sports_status = report_status("Sports", sports_status)
    accounts_status = report_status("Accounts", accounts_status)
    stores_status = report_status("Stores", stores_status)
    communication_status = report_status(
        "Communication Skills", communication_status
    )
    mathematics_status = report_status("Mathematics", mathematics_status)
    hr_status = report_status("Human Resource", hr_status)
    training_status = report_status(
        "Head Of Training Section", training_status
    )
    ame_status = report_status("AME Stores", ame_status)
    tso_status = report_status("TSO", "Pending")
    hostel_status = report_status("Hostel", "Pending")

    departments = [
        (
            str(row.get("department", "")).strip(),
            str(row.get("status", "Pending")).strip()
        )
        for row in report_rows
    ]

    cleared = sum(
        1 for _, status in departments
        if status.lower() == "cleared"
    )
    total = len(departments)
    percentage = int(cleared * 100 / total) if total else 0
    pending_departments = [
        name for name, status in departments
        if status.lower() != "cleared"
    ]

    return render_template(
        "student/dashboard.html",

        student=student,

        announcements=announcements,

        account=account,

        account_history=account_history,

        greeting=greeting,

        today=today,

        percentage=percentage,

        cleared=cleared,

        total=total,

        pending_departments=pending_departments,

        physical_required=physical_required,

        pending_library_books=pending_library_books,

        library_status=library_status,

        sports_status=sports_status,
        pending_sports_items=pending_sports_items,

        accounts_status=accounts_status,

        stores_status=stores_status,

        communication_status=communication_status,

        mathematics_status=mathematics_status,

        hr_status=hr_status,

        training_status=training_status,

        ame_status=ame_status,
        tso_status=tso_status,
        hostel_status=hostel_status,
        show_sidebar=True,
        pending_item_requests=pending_item_requests,

    )


# --------------------------------------------------
# SERVE STUDENT PROFILE PICTURES
# --------------------------------------------------

@app.route("/student/accommodation")
def student_accommodation():

    if session.get("role") != "student":
        return redirect(url_for("student_login"))

    sid = session.get("student_id")

    if not sid:
        sid = session.get("user")

    if not sid:
        return "<h2>No student ID found in session.</h2>", 404

    student = Student.query.filter_by(
        student_id=str(sid)
    ).first()

    if not student:
        return f"""
        <h2>Student not found</h2>
        <p>Student ID: {sid}</p>
        """, 404

    # -----------------------------------------------------
    # HOSTEL ITEMS
    # -----------------------------------------------------

    hostel_items = HostelItem.query.filter_by(
        student_id=student.student_id
    ).all()

    return render_template(
        "student/accommodation.html",
        student=student,
        hostel_items=hostel_items
    )

@app.route("/student/clearance")
def student_clearance(_return_snapshot=False):

    if session.get("role") != "student":
        return redirect(
            url_for("student_login")
        )

    student = Student.query.filter_by(
        student_id=session.get("student_id")
    ).first()

    if not student:
        return "Student record not found.", 404

    # --------------------------------------------------
    # DEPARTMENT CLEARANCE
    # --------------------------------------------------

    clearances = DepartmentClearance.query.filter_by(
        student_id=student.student_id
    ).all()

    clearance_map = {
        c.department: c
        for c in clearances
    }

    # --------------------------------------------------
    # LIBRARY
    # --------------------------------------------------

    library_books = LibraryBook.query.filter_by(
        student_id=student.student_id,
        returned=False
    ).all()

    library_status = (
        "Pending"
        if library_books
        else "Cleared"
    )

    library_Remarks = (
        "Books pending return"
        if library_books
        else "No library books outstanding"
    )

    # --------------------------------------------------
    # SPORTS
    # --------------------------------------------------

    sports_items = SportsItem.query.filter_by(
        student_id=student.student_id
    ).all()

    sports_pending = any(
        item.status != "Returned"
        for item in sports_items
    )

    sports_status = (
        "Pending"
        if sports_pending
        else "Cleared"
    )

    # --------------------------------------------------
    # AME STORES
    # --------------------------------------------------

    ame_tools = AMETool.query.filter_by(
        student_id=student.student_id,
        returned=False
    ).all()

    ame_status = (
        "Pending"
        if ame_tools
        else "Cleared"
    )

    # --------------------------------------------------
    # STORES
    # --------------------------------------------------

    store_items = StoreProperty.query.filter_by(
        student_id=student.student_id
    ).all()

    hostel_items = HostelItem.query.filter_by(
        student_id=student.student_id
    ).all()

    unreturned_store_items = [
        item
        for item in store_items
        if item.status != "Returned"
    ]

    unreturned_hostel_items = [
        item
        for item in hostel_items
        if item.status != "Returned"
    ]

    is_day_scholar = (
        student.accommodation == "Day Scholar"
    )

    if is_day_scholar:

        stores_status = "Cleared"

    elif (
        unreturned_store_items
        or unreturned_hostel_items
    ):

        stores_status = "Pending"

    else:

        stores_status = "Cleared"

    # --------------------------------------------------
    # ACCOUNTS
    # --------------------------------------------------

    account = Account.query.filter_by(
        student_id=student.student_id
    ).first()

    if account:

        outstanding = (
            (account.total_fee or 0)
            - (account.paid or 0)
        )

        minimum_required = (
            account.minimum_required or 0
        )

        accounts_status = (
            "Cleared"
            if (
                outstanding <= 0
                or account.paid >= minimum_required
            )
            else "Pending"
        )

    else:

        accounts_status = "Pending"

    # --------------------------------------------------
    # OTHER DEPARTMENTS
    # --------------------------------------------------

    def department_status(name):

        clearance = clearance_map.get(name)

        if clearance:

            return clearance.status or "Pending"

        return "Pending"

    communication_status = department_status(
        "communication"
    )

    mathematics_status = department_status(
        "mathematics"
    )

    hr_status = department_status(
        "hr"
    )
    # --------------------------------------------------
    # TRAINING SECTION CLEARANCE STATUS
    # --------------------------------------------------
    #
    # Training Section uses TrainingSectionProperty.
    #
    # No current property:
    #       -> Cleared
    #
    # Pending request:
    #       -> preserve existing clearance status
    #
    # Accepted + issued/assigned property:
    #       -> Pending
    #
    # Accepted + returned property:
    #       -> Cleared
    #
    # Declined:
    #       -> Cleared
    #
    # ACCEPTED does not mean CLEARED.
    # An issued property remains outstanding until returned.
    # --------------------------------------------------

    training_clearance = clearance_map.get("training section")

    training_requests = (
        ItemRequest.query
        .filter(
            ItemRequest.student_id == student.student_id,
            db.func.lower(
                db.func.trim(
                    db.func.coalesce(
                        ItemRequest.department,
                        ""
                    )
                )
            ) == "training section"
        )
        .order_by(
            ItemRequest.id.desc()
        )
        .all()
    )

    training_properties = (
        TrainingSectionProperty.query
        .filter_by(
            student_id=student.student_id
        )
        .order_by(
            TrainingSectionProperty.id.desc()
        )
        .all()
    )

    training_outstanding = [
        property_record
        for property_record in training_properties
        if (
            property_record.returned_at is None
            and (property_record.status or "").strip().lower()
            in {"issued", "assigned"}
        )
    ]

    training_issued = bool(training_outstanding)

    latest_training_request = (
        training_requests[0]
        if training_requests
        else None
    )

    if training_issued:

        training_status = "Pending"

    elif latest_training_request:

        request_status = (
            latest_training_request.status or ""
        ).strip().lower()

        if request_status == "pending":

            if training_clearance:
                training_status = (
                    training_clearance.status
                    or "Cleared"
                )
            else:
                training_status = "Cleared"

        elif request_status == "accepted":

            # No current issued property means the property
            # has already been returned, or there is no
            # outstanding physical property.
            training_status = "Cleared"

        elif request_status == "declined":

            training_status = "Cleared"

        else:

            training_status = (
                training_clearance.status
                if (
                    training_clearance
                    and training_clearance.status
                )
                else "Cleared"
            )

    else:

        training_status = "Cleared"

    # SPORTS
    # --------------------------------------------------

    sports_items = SportsItem.query.filter_by(
        student_id=student.student_id
    ).all()

    unreturned_items = []

    for item in sports_items:

        if item.status != "Returned":

            if item.item:
                unreturned_items.append(item.item)

    sports_status = (
        "Cleared"
        if not unreturned_items
        else "Pending"
    )

    sports_Remarks = (
        "No sports items pending"
        if not unreturned_items
        else "Items pending: " +
             ", ".join(unreturned_items)
    )

    # --------------------------------------------------
    # STORES
    # --------------------------------------------------

    store_properties = StoreProperty.query.filter_by(
        student_id=student.student_id
    ).all()

    hostel_items = HostelItem.query.filter_by(
        student_id=student.student_id
    ).all()

    store_items = []

    for item in store_properties:

        if item.status != "Returned":

            store_items.append(item.name)

    if is_day_scholar:

        stores_status = "Cleared"
        stores_Remarks = "Day Scholar"

    elif not store_items:

        stores_status = "Cleared"
        stores_Remarks = "No items assigned"

    else:

        stores_status = "Pending"

        stores_Remarks = (
            "Items assigned: " +
            ", ".join(store_items)
        )

    # --------------------------------------------------
    # TSO + HOSTEL
    # --------------------------------------------------
    # Use the actual inspection records. There is no
    # hardcoded "Physical Clearance Required" status.

    # Find the student's CURRENT accommodation assignment
    # before looking for its TSO inspection.
    current_accommodation_for_tso = (
        AccommodationAssignment.query
        .filter_by(student_id=student.student_id)
        .filter(
            db.func.lower(
                db.func.trim(
                    db.func.coalesce(
                        AccommodationAssignment.status,
                        ""
                    )
                )
            ).in_(["occupying", "active"])
        )
        .order_by(
            AccommodationAssignment.assigned_at.desc(),
            AccommodationAssignment.id.desc()
        )
        .first()
    )

    tso_inspection = None

    if current_accommodation_for_tso:
        tso_inspection = (
            TSOInspection.query
            .filter_by(
                accommodation_assignment_id=
                current_accommodation_for_tso.id
            )
            .order_by(TSOInspection.id.desc())
            .first()
        )

    if tso_inspection:
        tso_status = tso_inspection.status or "Pending"

        tso_remarks_parts = []

        if tso_inspection.remarks:
            tso_remarks_parts.append(
                str(tso_inspection.remarks)
            )

        if tso_inspection.key_collected:
            key_text = "Key collected"
            if tso_inspection.key_name:
                key_text += f": {tso_inspection.key_name}"
            tso_remarks_parts.append(key_text)

        if tso_inspection.other:
            tso_remarks_parts.append(
                f"Other: {tso_inspection.other}"
            )

        tso_Remarks = (
            " | ".join(tso_remarks_parts)
            if tso_remarks_parts
            else "No remarks available."
        )
    else:
        # No inspection exists for the CURRENT accommodation.
        # Therefore the current TSO clearance is Pending.
        # Do not fall back to an older/student-wide TSO record.
        tso_status = "Pending"
        tso_Remarks = "No current TSO clearance record available."

    hostel_inspection = (
        HostelInspection.query
        .filter_by(student_id=student.student_id)
        .order_by(HostelInspection.id.desc())
        .first()
    )

    if hostel_inspection:
        hostel_status = hostel_inspection.status or "Pending"

        hostel_remarks_parts = []

        if hostel_inspection.remarks:
            hostel_remarks_parts.append(
                str(hostel_inspection.remarks)
            )

        if hostel_inspection.other:
            hostel_remarks_parts.append(
                f"Other: {hostel_inspection.other}"
            )

        hostel_Remarks = (
            " | ".join(hostel_remarks_parts)
            if hostel_remarks_parts
            else "No remarks available."
        )
    else:
        # No Hostel inspection record exists; keep clearance pending.
        hostel_status = "Pending"
        hostel_Remarks = "No Hostel clearance record available."
    # --------------------------------------------------

    # --------------------------------------------------

    tools = AMETool.query.filter_by(
        student_id=student.student_id
    ).all()

    pending_tools = [
        tool.name
        for tool in tools
        if not tool.returned
    ]

    ame_status = (
        "Cleared"
        if not pending_tools
        else "Pending"
    )

    ame_Remarks = (
        "All AME tools returned"
        if not pending_tools
        else "Items pending: " +
             ", ".join(pending_tools)
    )

    # --------------------------------------------------
    # ACCOUNTS
    # --------------------------------------------------

    account = Account.query.filter_by(
        student_id=student.student_id
    ).first()

    if account:

        total_fee = account.total_fee or 0
        paid = account.paid or 0
        minimum_required = (
            account.minimum_required or 4000
        )

    else:

        total_fee = 0
        paid = 0
        minimum_required = 4000

    outstanding = float(total_fee) - float(paid)

    if outstanding <= 0:

        accounts_status = "Cleared"

        accounts_Remarks = (
            "Fees fully paid. Balance: K0"
        )

    elif paid >= minimum_required:

        accounts_status = "Cleared"

        accounts_Remarks = (
            "Meets minimum payment requirement. "
            f"Outstanding Balance: K{outstanding:g}"
        )

    else:

        accounts_status = "Pending"

        accounts_Remarks = (
            f"Outstanding Balance: K{outstanding:g}"
        )


    # --------------------------------------------------
    # DEPARTMENT CLEARANCE RECORDS
    # --------------------------------------------------
    #
    # Build a lookup dictionary before department_status()
    # and department_remarks() are used below.
    # --------------------------------------------------

    clearance_records = DepartmentClearance.query.filter_by(
        student_id=student.student_id
    ).all()

    departments = {}

    for record in clearance_records:

        departments[record.department] = {
            "status": record.status or "Pending",
            "remarks": (
                getattr(record, "remarks", None)
                or getattr(record, "reason", None)
                or "No remarks available."
            )
        }

    # --------------------------------------------------
    # NORMALIZED DEPARTMENT LOOKUP
    # --------------------------------------------------
    #
    # Department names in the database are not necessarily
    # identical to the short keys used by the dashboard.
    # Create aliases so the dashboard can reliably find them.
    # --------------------------------------------------

    def find_department(*names):

        for name in names:

            if name in departments:
                return departments[name]

        normalized = {
            str(name).strip().lower(): value
            for name, value in departments.items()
        }

        for name in names:

            key = str(name).strip().lower()

            if key in normalized:
                return normalized[key]

        return {}

    departments = {
        "communication": find_department(
            "Communication Skills",
            "Communication Skills (REL SC)"
        ),
        "mathematics": find_department(
            "Mathematics"
        ),
        "hr": find_department(
            "HR",
            "Human Resource",
            "Human Resource / Admin Officer"
        ),
        "training": find_department(
            "Training Section",
            "Head of Training Section"
        ),
        "ame": find_department(
            "AME Stores"
        ),
        "tso": find_department(
            "TSO",
            "Technical Services Office"
        ),
        "stores": find_department(
            "Stores",
            "Stores Office"
        ),
        "hostel": find_department(
            "Hostel"
        ),
    }

    # --------------------------------------------------
    # DEPARTMENT HELPERS
    # --------------------------------------------------

    def department_status(key):

        data = departments.get(key, {})

        if not isinstance(data, dict):
            return "Pending"

        return data.get(
            "status",
            "Pending"
        )

    def department_remarks(key):

        data = departments.get(key, {})

        if not isinstance(data, dict):
            return "No information available"

        return (
            data.get("remarks")
            or data.get("Remarks")
            or "No outstanding requirements"
        )

    # --------------------------------------------------
    # OVERALL CLEARANCE
    # --------------------------------------------------

    statuses = [
        library_status,
        sports_status,
        accounts_status,
        department_status("communication"),
        department_status("mathematics"),
        department_status("hr"),
        department_status("training"),
        ame_status,
        stores_status,
        tso_status,
        hostel_status
    ]

    # The detailed current clearance table is the source of truth.
    # The summary must count the same 11 department rows that
    # the student actually sees in the table.
    #
    # This calculation is intentionally finalized again after
    # clearance_rows is built below.

    cleared = 0
    total = 11
    overall = "0/11 Cleared • PENDING"

    generated_time = zambia_now().strftime(
        "%d %B %Y | %I:%M %p"
    )

    # --------------------------------------------------
    # DETAILED CURRENT CLEARANCE TABLE
    # --------------------------------------------------
    # CURRENT CLEARANCE SNAPSHOT
    #
    # Exactly ONE row per department.
    # Multiple current outstanding items are aggregated
    # into the Item / Requirement cell.
    #
    # Returned/resolved items disappear from this table.
    # Declined requests are never treated as outstanding.
    # Historical transactions belong in History.
    # --------------------------------------------------

    clearance_rows = []

    def table_value(value):
        if value is None:
            return "NIL"
        value = str(value).strip()
        return value if value else "NIL"

    def table_date(value):
        if not value:
            return "NIL"

        if hasattr(value, "strftime"):
            return value.strftime("%d %b %Y %H:%M")

        value = str(value).strip()
        return value if value else "NIL"

    def unique_join(values):
        result = []
        seen = set()

        for value in values:
            value = table_value(value)
            if value == "NIL":
                continue

            key = value.casefold()

            if key not in seen:
                seen.add(key)
                result.append(value)

        return "; ".join(result) if result else "NIL"

    def add_department_row(
        department,
        items=None,
        issued_at=None,
        issued_by=None,
        resolved_at=None,
        resolved_by=None,
        remarks=None,
        status="Cleared"
    ):
        if items is None:
            items = []

        if isinstance(items, str):
            items = [items]

        # --------------------------------------------------
        # DEPARTMENT STAFF
        # --------------------------------------------------
        # If no transaction-specific staff member was supplied,
        # resolve the designated staff member for this department.
        # --------------------------------------------------

        department_staff_map = {
            "Accounts": "Accounts",
            "Library": "Library",
            "Communication Skills": "Communication Skills (REL SC)",
            "Mathematics": "Mathematics",
            "Human Resource": "Human Resource / Admin Officer",
            "Sports": "Sports",
            "AME Stores": "AME Stores",
            "Stores": "Stores Officer",
            "Head Of Training Section": "Training Section",
            "TSO": "Technical Services Office (TSO)",
            "Hostel": "Hostels (HOS)"
        }

        staff_department = department_staff_map.get(
            department
        )

        # --------------------------------------------------
        # RESOLVE DESIGNATED DEPARTMENT STAFF
        # --------------------------------------------------
        department_staff = None

        if staff_department:
            department_staff = (
                Staff.query
                .filter(
                    db.func.lower(
                        db.func.trim(
                            Staff.department
                        )
                    )
                    == staff_department.lower()
                )
                .order_by(Staff.id.desc())
                .first()
            )

        # Assigned By fallback
        if not issued_by and department_staff:
            issued_by = getattr(
                department_staff,
                "name",
                None
            )

        # --------------------------------------------------
        # RESOLVED BY
        # --------------------------------------------------
        # Use the shared authoritative resolver.
        # Print Clearance uses this same resolver.
        # --------------------------------------------------
        resolved_by = _resolve_clearance_officer(
            student.student_id,
            department,
            resolved_by=resolved_by
        )

        clearance_rows.append({
            "department": department,
            "item": unique_join(items),
            "issued_at": unique_join(
                [table_date(v) for v in (
                    issued_at if isinstance(issued_at, list)
                    else [issued_at]
                )]
            ),
            "issued_by": unique_join(
                issued_by if isinstance(issued_by, list)
                else [issued_by]
            ),
            "resolved_at": unique_join(
                [table_date(v) for v in (
                    resolved_at if isinstance(resolved_at, list)
                    else [resolved_at]
                )]
            ),
            "resolved_by": unique_join(
                resolved_by if isinstance(resolved_by, list)
                else [resolved_by]
            ),
            "remarks": unique_join(
                remarks if isinstance(remarks, list)
                else [remarks]
            ),
            "status": table_value(status)
        })

    def current_property_items(model, student_id):
        """
        Return ONLY currently outstanding property.

        Returned/Resolved:
            excluded.

        Declined/Rejected/Cancelled:
            excluded.

        Issued/Assigned/Pending:
            included.

        The newest active record for the same item name wins.
        """
        records = (
            model.query
            .filter_by(student_id=student_id)
            .order_by(model.id.desc())
            .all()
        )

        grouped = {}

        for record in records:
            name = str(
                getattr(record, "name", None) or ""
            ).strip()

            if not name:
                continue

            status = str(
                getattr(record, "status", "") or ""
            ).strip().lower()

            if status in {
                "declined",
                "rejected",
                "cancelled",
                "returned",
                "resolved",
                "cleared",
                "complete",
                "completed"
            }:
                continue

            if getattr(record, "returned_at", None) is not None:
                continue

            if status not in {
                "issued",
                "assigned",
                "pending",
                "accepted"
            }:
                continue

            key = name.casefold()

            if key not in grouped:
                grouped[key] = record

        return list(grouped.values())

    def current_library_items(student_id):
        books = (
            LibraryBook.query
            .filter_by(student_id=student_id)
            .order_by(LibraryBook.id.desc())
            .all()
        )

        current = []

        for book in books:
            if bool(getattr(book, "returned", False)):
                continue

            if not getattr(book, "borrowed_at", None):
                continue

            current.append(book)

        return current

    def current_sports_items(student_id):
        records = (
            SportsItem.query
            .filter_by(student_id=student_id)
            .order_by(SportsItem.id.desc())
            .all()
        )

        grouped = {}

        for record in records:
            status = str(
                getattr(record, "status", "") or ""
            ).strip().lower()

            if status in {
                "returned",
                "resolved",
                "cleared",
                "declined",
                "rejected",
                "cancelled",
                "complete",
                "completed"
            }:
                continue

            if getattr(record, "returned_at", None) is not None:
                continue

            name = (
                getattr(record, "item", None)
                or getattr(record, "sport", None)
                or ""
            )

            name = str(name).strip()

            if not name:
                continue

            key = name.casefold()

            if key not in grouped:
                grouped[key] = record

        return list(grouped.values())

    def current_ame_items(student_id):
        records = (
            AMETool.query
            .filter_by(student_id=student_id)
            .order_by(AMETool.id.desc())
            .all()
        )

        grouped = {}

        for record in records:
            if bool(getattr(record, "returned", False)):
                continue

            if getattr(record, "returned_at", None):
                continue

            name = str(
                getattr(record, "name", None) or ""
            ).strip()

            if not name:
                continue

            key = name.casefold()

            if key not in grouped:
                grouped[key] = record

        return list(grouped.values())

    def add_property_department(
        department,
        model,
        student_id
    ):
        # --------------------------------------------------
        # CURRENT PROPERTY SNAPSHOT
        # --------------------------------------------------
        # Only unresolved/current items belong in the
        # current clearance table.
        #
        # Returned/resolved items remain in History, but
        # their actual return metadata is preserved here
        # when the department becomes Cleared.
        # --------------------------------------------------

        records = (
            model.query
            .filter_by(student_id=student_id)
            .order_by(model.id.desc())
            .all()
        )

        current_records = []
        resolved_records = []

        for record in records:

            status = str(
                getattr(record, "status", "") or ""
            ).strip().lower()

            returned_at = getattr(
                record,
                "returned_at",
                None
            )

            if (
                returned_at is not None
                or status in {
                    "returned",
                    "resolved",
                    "cleared",
                    "declined",
                    "rejected",
                    "cancelled",
                    "complete",
                    "completed"
                }
            ):
                resolved_records.append(record)
                continue

            if status in {
                "",
                "pending",
                "issued",
                "assigned",
                "accepted"
            }:
                current_records.append(record)

        # --------------------------------------------------
        # CURRENT OUTSTANDING ITEMS
        # --------------------------------------------------

        if current_records:

            items = []
            issued_dates = []
            issued_staff = []
            remarks = []

            for record in current_records:

                name = getattr(
                    record,
                    "name",
                    None
                )

                if name:
                    items.append(name)

                # --------------------------------------------------
                # ASSIGNMENT METADATA
                # --------------------------------------------------
                # The property record's issued_at is the time the
                # student confirmed/accepted the item.
                #
                # For the clearance table, "Issued / Assigned" and
                # "Assigned By" must represent the actual staff
                # assignment stored on ItemRequest.
                #
                # Fall back to the property record for older records
                # that do not have a linked request.
                # --------------------------------------------------

                issued_at = None
                issued_by = None

                request_id = getattr(
                    record,
                    "request_id",
                    None
                )

                if request_id:
                    item_request = db.session.get(
                        ItemRequest,
                        request_id
                    )

                    if item_request:
                        issued_at = getattr(
                            item_request,
                            "assigned_at",
                            None
                        )

                        assigned_by_username = getattr(
                            item_request,
                            "assigned_by",
                            None
                        )

                        # Resolve the username stored on ItemRequest
                        # to the actual Staff member's display name.
                        if assigned_by_username:
                            assigned_user = User.query.filter_by(
                                username=assigned_by_username
                            ).first()

                            if assigned_user:
                                assigned_staff = Staff.query.filter_by(
                                    user_id=assigned_user.id
                                ).first()

                                if assigned_staff:
                                    issued_by = getattr(
                                        assigned_staff,
                                        "name",
                                        None
                                    )

                        # Fallback for records where the User/Staff
                        # relationship cannot be resolved.
                        if issued_by is None:
                            issued_by = assigned_by_username

                if issued_at is None:
                    issued_at = getattr(
                        record,
                        "issued_at",
                        None
                    )

                if issued_by is None:
                    issued_by = getattr(
                        record,
                        "returned_by",
                        None
                    )

                record_remarks = getattr(
                    record,
                    "remarks",
                    None
                )

                if issued_at:
                    issued_dates.append(issued_at)

                if issued_by:
                    issued_staff.append(issued_by)

                if record_remarks:
                    remarks.append(record_remarks)

            add_department_row(
                department,
                items=items or ["NIL"],
                issued_at=issued_dates,
                issued_by=issued_staff,
                resolved_at=None,
                resolved_by=None,
                remarks=remarks or ["NIL"],
                status="Pending"
            )

            return

        # --------------------------------------------------
        # NO CURRENT ITEMS
        # --------------------------------------------------
        # Department stays visible as Cleared, but preserve
        # the latest real transaction metadata.
        # --------------------------------------------------

        latest = None

        if resolved_records:
            latest = resolved_records[0]

            for candidate in resolved_records[1:]:

                latest_time = (
                    getattr(
                        latest,
                        "returned_at",
                        None
                    )
                    or getattr(
                        latest,
                        "issued_at",
                        None
                    )
                )

                candidate_time = (
                    getattr(
                        candidate,
                        "returned_at",
                        None
                    )
                    or getattr(
                        candidate,
                        "issued_at",
                        None
                    )
                )

                if latest_time is None:
                    latest = candidate
                    continue

                if candidate_time is None:
                    continue

                if candidate_time > latest_time:
                    latest = candidate

        if latest:

            returned_at = getattr(
                latest,
                "returned_at",
                None
            )

            returned_by = getattr(
                latest,
                "returned_by",
                None
            )

            # Use the original staff assignment transaction when
            # available. The property's issued_at/issued_by represent
            # confirmation/issue, not necessarily the staff assignment.
            issued_at = None
            issued_by = None

            request_id = getattr(
                latest,
                "request_id",
                None
            )

            if request_id:
                item_request = db.session.get(
                    ItemRequest,
                    request_id
                )

                if item_request:
                    issued_at = getattr(
                        item_request,
                        "assigned_at",
                        None
                    )

                    assigned_by_username = getattr(
                        item_request,
                        "assigned_by",
                        None
                    )

                    # Resolve ItemRequest username to the actual
                    # Staff member belonging to that department.
                    if assigned_by_username:
                        assigned_user = User.query.filter_by(
                            username=assigned_by_username
                        ).first()

                        if assigned_user:
                            assigned_staff = Staff.query.filter_by(
                                user_id=assigned_user.id
                            ).first()

                            if assigned_staff:
                                issued_by = getattr(
                                    assigned_staff,
                                    "name",
                                    None
                                )

                    # Safe fallback if no Staff record is linked.
                    if issued_by is None:
                        issued_by = assigned_by_username

            if issued_at is None:
                issued_at = getattr(
                    latest,
                    "issued_at",
                    None
                )

            if issued_by is None:
                issued_by = getattr(
                    latest,
                    "returned_by",
                    None
                )

            latest_remarks = getattr(
                latest,
                "remarks",
                None
            )

            add_department_row(
                department,
                items=["NIL"],
                issued_at=issued_at,
                issued_by=issued_by,
                resolved_at=returned_at,
                resolved_by=returned_by,
                remarks=latest_remarks or "NIL",
                status="Cleared"
            )

        else:

            add_department_row(
                department,
                items=["NIL"],
                issued_at=None,
                issued_by=None,
                resolved_at=None,
                resolved_by=None,
                remarks="NIL",
                status="Cleared"
            )

    # --------------------------------------------------
    # ACCOUNTS
    # --------------------------------------------------

    add_department_row(
        "Accounts",
        items=["NIL"],
        remarks=accounts_Remarks,
        status=accounts_status
    )

    # --------------------------------------------------
    # LIBRARY
    # --------------------------------------------------

    library_items = current_library_items(
        student.student_id
    )

    if library_items:
        library_names = []
        library_dates = []

        for book in library_items:
            library_names.append(book.name)

            if book.borrowed_at:
                library_dates.append(book.borrowed_at)

        add_department_row(
            "Library",
            items=library_names,
            issued_at=library_dates,
            issued_by=None,
            remarks=library_Remarks,
            status="Pending"
        )
    else:
        # No outstanding books. Keep the current row as NIL/Cleared,
        # while showing dates from the latest actual returned book.
        library_history = (
            LibraryBook.query
            .filter_by(student_id=student.student_id)
            .order_by(LibraryBook.id.desc())
            .all()
        )

        returned_books = [
            book for book in library_history
            if (
                bool(getattr(book, "returned", False))
                or getattr(book, "returned_at", None)
            )
        ]

        if returned_books:
            latest_book = returned_books[0]

            add_department_row(
                "Library",
                items=["NIL"],
                issued_at=getattr(
                    latest_book, "borrowed_at", None
                ),
                issued_by=None,
                resolved_at=getattr(
                    latest_book, "returned_at", None
                ),
                resolved_by=None,
                remarks=library_Remarks or "No library books outstanding",
                status="Cleared"
            )
        else:
            add_department_row(
                "Library",
                items=["NIL"],
                remarks=library_Remarks or "No library books outstanding",
                status="Cleared"
            )

    # --------------------------------------------------
    # COMMUNICATION SKILLS
    # --------------------------------------------------

    add_property_department(
        "Communication Skills",
        CommunicationProperty,
        student.student_id
    )

    # --------------------------------------------------
    # MATHEMATICS
    # --------------------------------------------------

    add_property_department(
        "Mathematics",
        MathematicsProperty,
        student.student_id
    )

    # --------------------------------------------------
    # HUMAN RESOURCE
    # --------------------------------------------------

    hr_status = "Cleared"
    hr_remarks = None

    try:
        if isinstance(department_status, dict):
            hr_status = (
                department_status.get(
                    "Human Resource"
                )
                or department_status.get(
                    "Human Resources"
                )
                or department_status.get(
                    "hr"
                )
                or "Cleared"
            )

        if isinstance(department_remarks, dict):
            hr_remarks = (
                department_remarks.get(
                    "Human Resource"
                )
                or department_remarks.get(
                    "Human Resources"
                )
                or department_remarks.get(
                    "hr"
                )
            )
    except Exception:
        pass

    add_department_row(
        "Human Resource",
        items=["NIL"],
        remarks=hr_remarks,
        status=hr_status
    )

    # --------------------------------------------------
    # SPORTS
    # --------------------------------------------------

    sports_items = current_sports_items(
        student.student_id
    )

    if sports_items:
        sports_names = []
        sports_dates = []
        sports_remarks = []

        for record in sports_items:
            name = (
                getattr(record, "item", None)
                or getattr(record, "sport", None)
            )

            if name:
                sports_names.append(name)

            created_at = getattr(
                record,
                "created_at",
                None
            )

            if created_at:
                sports_dates.append(created_at)

            record_remarks = getattr(
                record,
                "remarks",
                None
            )

            if record_remarks:
                sports_remarks.append(record_remarks)

        add_department_row(
            "Sports",
            items=sports_names,
            issued_at=sports_dates,
            issued_by=None,
            remarks=sports_remarks or "NIL",
            status="Pending"
        )
    else:
        add_department_row(
            "Sports",
            items=["NIL"],
            issued_at=None,
            issued_by=None,
            resolved_at=None,
            resolved_by=None,
            remarks="No sports items pending",
            status="Cleared"
        )

    # --------------------------------------------------
    # AME STORES
    # --------------------------------------------------

    ame_items = current_ame_items(
        student.student_id
    )

    if ame_items:
        ame_names = []
        ame_dates = []
        ame_staff = []
        ame_remarks = []

        for tool in ame_items:
            ame_names.append(tool.name)

            if tool.issued_at:
                ame_dates.append(tool.issued_at)

            if tool.issued_by:
                ame_staff.append(tool.issued_by)

            if tool.remarks:
                ame_remarks.append(tool.remarks)

        add_department_row(
            "AME Stores",
            items=ame_names,
            issued_at=ame_dates,
            issued_by=ame_staff,
            remarks=ame_remarks or ame_Remarks,
            status="Pending"
        )
    else:
        # No current AME tools are outstanding.
        # Keep the department row as NIL/Cleared, but preserve
        # the latest real resolved transaction metadata.
        ame_history = (
            AMETool.query
            .filter_by(student_id=student.student_id)
            .order_by(AMETool.id.desc())
            .all()
        )

        resolved_ame = []

        for tool in ame_history:
            returned = bool(
                getattr(tool, "returned", False)
            )

            returned_at = getattr(
                tool,
                "returned_at",
                None
            )

            if returned or returned_at:
                resolved_ame.append(tool)

        if resolved_ame:
            latest_ame = resolved_ame[0]

            add_department_row(
                "AME Stores",
                items=["NIL"],
                issued_at=getattr(
                    latest_ame,
                    "issued_at",
                    None
                ),
                issued_by=getattr(
                    latest_ame,
                    "returned_by",
                    None
                ),
                resolved_at=getattr(
                    latest_ame,
                    "returned_at",
                    None
                ),
                resolved_by=getattr(
                    latest_ame,
                    "returned_by",
                    None
                ),
                remarks=(
                    getattr(
                        latest_ame,
                        "remarks",
                        None
                    )
                    or ame_Remarks
                    or "NIL"
                ),
                status="Cleared"
            )
        else:
            add_department_row(
                "AME Stores",
                items=["NIL"],
                remarks=ame_Remarks,
                status="Cleared"
            )

    # --------------------------------------------------
    # STORES
    # --------------------------------------------------

    if is_day_scholar:
        add_department_row(
            "Stores",
            items=["NIL"],
            issued_at=None,
            issued_by=None,
            resolved_at=None,
            resolved_by=None,
            remarks="Day Scholar",
            status="Cleared"
        )
    else:
        add_property_department(
            "Stores",
            StoreProperty,
            student.student_id
        )

    # --------------------------------------------------
    # HEAD OF TRAINING SECTION
    # --------------------------------------------------

    add_property_department(
        "Head Of Training Section",
        TrainingSectionProperty,
        student.student_id
    )



    current_accommodation = (
        AccommodationAssignment.query
        .filter_by(
            student_id=student.student_id
        )
        .filter(
            db.func.lower(
                db.func.trim(
                    db.func.coalesce(
                        AccommodationAssignment.status,
                        ""
                    )
                )
            ).in_([
                "occupying",
                "active"
            ])
        )
        .order_by(
            AccommodationAssignment.assigned_at.desc(),
            AccommodationAssignment.id.desc()
        )
        .first()
    )

    # --------------------------------------------------
    # TSO
    # --------------------------------------------------
    # TSO is responsible for the hostel key.
    #
    # An active hostel assignment automatically creates
    # the current TSO key requirement.
    #
    # TSO becomes Cleared only after an actual TSO
    # inspection has been completed.
    #
    # Returned/old transactions remain in History.

    tso_current_items = []

    if current_accommodation:
        tso_key_name = None

        try:
            tso_accommodation = _tso_accommodation_details(
                current_accommodation
            )
            if tso_accommodation:
                tso_key_name = (
                    tso_accommodation.get("key_name")
                    or ""
                ).strip()
        except Exception:
            tso_key_name = None

        if not tso_key_name:
            room_obj = db.session.get(
                HostelRoom,
                current_accommodation.room_id
            )

            hostel_obj = (
                db.session.get(
                    Hostel,
                    room_obj.hostel_id
                )
                if room_obj
                else None
            )

            hostel_name = (
                getattr(
                    hostel_obj,
                    "name",
                    None
                )
                or ""
            ).strip()

            block_name = ""

            if (
                room_obj
                and getattr(
                    room_obj,
                    "block_id",
                    None
                )
            ):
                block_obj = db.session.get(
                    HostelBlock,
                    room_obj.block_id
                )

                block_name = (
                    getattr(
                        block_obj,
                        "name",
                        None
                    )
                    or ""
                ).strip()

            room_number = (
                getattr(
                    room_obj,
                    "room_number",
                    None
                )
                or ""
            ).strip()

            key_parts = [hostel_name]

            if block_name:
                key_parts.append(block_name)

            if room_number:
                key_parts.append(
                    f"Room {room_number}"
                )

            tso_key_name = " — ".join(
                part
                for part in key_parts
                if part
            )

        if (
            tso_inspection
            and str(
                getattr(
                    tso_inspection,
                    "status",
                    ""
                )
                or ""
            ).strip().lower()
            == "cleared"
        ):
            add_department_row(
                "TSO",
                items=[
                    tso_key_name or "NIL"
                ],
                issued_at=getattr(
                    current_accommodation,
                    "assigned_at",
                    None
                ),
                issued_by=None,
                resolved_at=getattr(
                    tso_inspection,
                    "inspected_at",
                    None
                ),
                resolved_by=getattr(
                    tso_inspection,
                    "inspected_by",
                    None
                ),
                remarks=(
                    getattr(
                        tso_inspection,
                        "remarks",
                        None
                    )
                    or tso_Remarks
                    or "NIL"
                ),
                status="Cleared"
            )
        else:
            add_department_row(
                "TSO",
                items=[
                    tso_key_name or "NIL"
                ],
                issued_at=getattr(
                    current_accommodation,
                    "assigned_at",
                    None
                ),
                issued_by=None,
                remarks=(
                    getattr(
                        tso_inspection,
                        "remarks",
                        None
                    )
                    or "NIL"
                ),
                status="Pending"
            )
    else:
        add_department_row(
            "TSO",
            items=["NIL"],
            remarks="NIL",
            status="Cleared"
        )

    # --------------------------------------------------
    # HOSTEL
    # --------------------------------------------------
    # Current accommodation snapshot.
    #
    # Show the complete current accommodation:
    # Hostel + Cube/Block where applicable + Room.
    #
    # Previous/returned accommodation belongs in History,
    # not in the current clearance snapshot.

    if current_accommodation:

        accommodation = _tso_accommodation_details(
            current_accommodation
        )

        accommodation_item = (
            accommodation.get("key_name")
            or "Accommodation assigned"
        )

        add_department_row(
            "Hostel",
            items=[accommodation_item],
            issued_at=getattr(
                current_accommodation,
                "assigned_at",
                None
            ),
            issued_by=None,
            resolved_at=None,
            resolved_by=None,
            remarks=(
                hostel_Remarks
                or "NIL"
            ),
            status="Pending"
        )

    else:

        add_department_row(
            "Hostel",
            items=["NIL"],
            issued_at=None,
            issued_by=None,
            resolved_at=None,
            resolved_by=None,
            remarks="NIL",
            status="Cleared"
        )

    # --------------------------------------------------
    # SAFETY CHECK:
    # EXACTLY 11 DEPARTMENTS
    # --------------------------------------------------

    required_departments = [
        "Accounts",
        "Library",
        "Communication Skills",
        "Mathematics",
        "Human Resource",
        "Sports",
        "AME Stores",
        "Stores",
        "Head Of Training Section",
        "TSO",
        "Hostel"
    ]

    row_by_department = {
        row["department"]: row
        for row in clearance_rows
    }

    clearance_rows = []

    for department in required_departments:
        row = row_by_department.get(department)

        if row is None:
            row = {
                "department": department,
                "item": "NIL",
                "issued_at": "NIL",
                "issued_by": "NIL",
                "resolved_at": "NIL",
                "resolved_by": "NIL",
                "remarks": "NIL",
                "status": "Cleared"
            }

        clearance_rows.append(row)

    # --------------------------------------------------
    # --------------------------------------------------
    # NORMALIZE STATUS VALUES
    # --------------------------------------------------

    for row in clearance_rows:

        normalized_status = (
            str(row["status"]).strip().lower()
        )

        if normalized_status in {
            "returned",
            "resolved",
            "cleared",
            "complete",
            "completed"
        }:
            row["status"] = "Cleared"

        elif normalized_status in {
            "accepted",
            "issued",
            "assigned",
            "pending",
            "pending confirmation"
        }:
            row["status"] = "Pending"

        else:
            row["status"] = (
                "Cleared"
                if normalized_status == "cleared"
                else "Pending"
            )

    # --------------------------------------------------
    # END DETAILED CURRENT CLEARANCE TABLE
    # --------------------------------------------------

    # --------------------------------------------------
    # OVERALL SUMMARY FROM CURRENT 11-ROW SNAPSHOT
    # --------------------------------------------------

    total = 11

    cleared = sum(
        1
        for row in clearance_rows
        if str(row.get("status", "")).strip().lower()
        == "cleared"
    )

    overall = f"{cleared}/{total} Cleared"

    if cleared == total:
        overall += " • FULLY CLEARED"
    else:
        overall += " • PENDING"

    # --------------------------------------------------
    # RENDER THE ACTUAL TEMPLATE
    # --------------------------------------------------

    if _return_snapshot:
        return {
            "clearance_rows": clearance_rows,
            "cleared": cleared,
            "total": total,
            "overall": overall,
        }

    return render_template(
        "student/clearance.html",

        student=student,

        departments=departments,

        library_status=library_status,
        library_Remarks=library_Remarks,

        sports_status=sports_status,
        sports_Remarks=sports_Remarks,

        accounts_status=accounts_status,
        accounts_Remarks=accounts_Remarks,

        ame_status=ame_status,
        ame_Remarks=ame_Remarks,

        stores_status=stores_status,
        stores_Remarks=stores_Remarks,

        tso_status=tso_status,
        tso_Remarks=tso_Remarks,

        hostel_status=hostel_status,
        hostel_Remarks=hostel_Remarks,

        is_day_scholar=is_day_scholar,

        cleared=cleared,
        total=total,
        overall=overall,

        generated_time=generated_time,

        clearance_rows=clearance_rows,

        department_status=department_status,
        department_remarks=department_remarks,

        show_sidebar=True
    )



# --------------------------------------------------
# PRINT / EXPORT CLEARANCE
# --------------------------------------------------


def _real_clearance_person_name(value):
    """
    Accept only a real person's name.
    Shared by Student Clearance and Print Clearance.
    """
    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    generic = {
        "nil",
        "n/a",
        "na",
        "none",
        "staff",
        "staff member",
        "staff officer",
        "stores staff",
        "sports staff",
        "sports staff member",
        "library staff",
        "accounts staff",
        "accounts staff member",
        "ame stores staff",
        "ame stores staff member",
        "hostels staff",
        "hostel staff",
        "hr staff",
        "hr staff member",
        "human resource staff",
        "mathematics staff",
        "math staff",
        "math staff member",
        "training staff",
        "training staff member",
        "training section staff",
        "communication skills staff",
        "communication skills staff member",
        "technical services office",
        "technical services office (tso)",
        "tso staff",
        "tso staff member",
        "stores officer",
        "training section",
        "hostels (hos)",
        "human resource / admin officer",
        "communication skills (rel sc)",
        "communication skills (rel/sc)",
    }

    if value.casefold() in generic:
        return None

    lowered = value.casefold()

    generic_fragments = (
        " staff member",
        " staff officer",
        " staff",
        " officer",
        " admin officer",
        " technical services office",
    )

    # Reject generic department labels, not real people's names.
    if lowered.startswith(generic_fragments):
        return None

    generic_exact = {
        "stores staff",
        "stores staff member",
        "stores officer",
        "sports staff",
        "sports staff member",
        "library staff",
        "library staff member",
        "accounts staff",
        "accounts staff member",
        "ame stores staff",
        "ame stores staff member",
        "hostels staff",
        "hostels staff member",
        "hr staff",
        "human resource staff",
        "human resources staff",
        "tso staff",
        "technical services office staff",
        "technical services office (tso)",
        "mathematics staff",
        "mathematics staff member",
        "training section staff",
        "training section officer",
        "communication skills staff",
        "communication skills (rel sc)",
        "communication skills (rel/sc)",
    }

    if lowered in generic_exact:
        return None

    generic_suffixes = (
        " staff",
        " staff member",
        " staff officer",
        " officer",
    )

    if lowered.endswith(generic_suffixes):
        return None

    return value


def _resolve_clearance_officer(
    student_id,
    department,
    resolved_by=None
):
    """
    AUTHORITATIVE clearance officer resolver.

    Student Clearance and Print Clearance both use this
    function.

    Resolution order:
    1. Explicit transaction-specific resolved_by.
    2. Latest valid DepartmentHistory.performed_by.
    3. Latest TSOInspection.inspected_by for TSO.
    4. Designated department staff, only when it is a real
       person's name.
    """

    department_staff_map = {
        "Accounts": "Accounts",
        "Library": "Library",
        "Communication Skills": "Communication Skills (REL SC)",
        "Mathematics": "Mathematics",
        "Human Resource": "Human Resource / Admin Officer",
        "Sports": "Sports",
        "AME Stores": "AME Stores",
        "Stores": "Stores Officer",
        "Head Of Training Section": "Training Section",
        "TSO": "Technical Services Office (TSO)",
        "Hostel": "Hostels (HOS)"
    }

    staff_department = department_staff_map.get(department)
    department_staff = None

    if staff_department:
        try:
            department_staff = (
                Staff.query
                .filter(
                    db.func.lower(
                        db.func.trim(
                            Staff.department
                        )
                    ) == staff_department.lower()
                )
                .order_by(Staff.id.desc())
                .first()
            )
        except Exception:
            department_staff = None

    resolved_by = _real_clearance_person_name(
        resolved_by
    )

    # --------------------------------------------------------
    # DepartmentHistory is the main transaction source.
    # --------------------------------------------------------
    if not resolved_by:
        try:
            history_department_aliases = {
                "Communication Skills": [
                    "Communication Skills",
                    "Communication Skills (REL/SC)",
                    "Communication Skills (REL SC)"
                ],
                "Head Of Training Section": [
                    "Head Of Training Section",
                    "Training Section"
                ],
                "Human Resource": [
                    "Human Resource",
                    "Human Resources",
                    "Human Resource / Admin Officer"
                ],
                "TSO": [
                    "TSO",
                    "Technical Services Office",
                    "Technical Services Office (TSO)"
                ],
                "Hostel": [
                    "Hostel",
                    "Hostels",
                    "Hostels (HOS)"
                ],
                "Stores": [
                    "Stores",
                    "Stores Officer"
                ],
                "AME Stores": [
                    "AME Stores"
                ],
                "Accounts": [
                    "Accounts"
                ],
                "Library": [
                    "Library"
                ],
                "Sports": [
                    "Sports"
                ],
                "Mathematics": [
                    "Mathematics"
                ]
            }

            history_names = history_department_aliases.get(
                department,
                [department]
            )

            history_rows = (
                DepartmentHistory.query
                .filter(
                    DepartmentHistory.student_id == student_id,
                    db.func.lower(
                        db.func.trim(
                            DepartmentHistory.department
                        )
                    ).in_([
                        name.lower()
                        for name in history_names
                    ])
                )
                .order_by(
                    DepartmentHistory.created_at.desc(),
                    DepartmentHistory.id.desc()
                )
                .all()
            )

            for history_row in history_rows:
                history_officer = (
                    _real_clearance_person_name(
                        getattr(
                            history_row,
                            "performed_by",
                            None
                        )
                    )
                )

                if history_officer:
                    resolved_by = history_officer
                    break

        except Exception:
            resolved_by = None

    # --------------------------------------------------------
    # TSO has its own inspection record.
    # --------------------------------------------------------
    if not resolved_by and department == "TSO":
        try:
            tso_record = (
                TSOInspection.query
                .filter_by(
                    student_id=student_id
                )
                .order_by(
                    TSOInspection.inspected_at.desc(),
                    TSOInspection.id.desc()
                )
                .first()
            )

            if tso_record:
                resolved_by = (
                    _real_clearance_person_name(
                        getattr(
                            tso_record,
                            "inspected_by",
                            None
                        )
                    )
                )

        except Exception:
            resolved_by = None

    # --------------------------------------------------------
    # Final designated-staff fallback.
    # --------------------------------------------------------
    if not resolved_by and department_staff:
        resolved_by = (
            _real_clearance_person_name(
                getattr(
                    department_staff,
                    "name",
                    None
                )
            )
        )

    return resolved_by




@app.route("/hostel/clearance")
def hostel_clearance():

    if not _hostel_staff_allowed():
        return redirect(url_for("student_login"))

    # Only students whose official clearance document
    # has actually been generated appear here.
    generated_ids = (
        db.session.query(
            ClearanceHistory.student_id
        )
        .filter_by(
            status="Official Clearance Form Generated"
        )
        .distinct()
        .subquery()
    )

    students = (
        Student.query
        .filter(
            Student.student_id.in_(generated_ids)
        )
        .order_by(
            Student.name.asc()
        )
        .all()
    )

    export_info = {}

    histories = (
        ClearanceHistory.query
        .filter_by(
            status="Official Clearance Form Generated"
        )
        .order_by(
            ClearanceHistory.generated_time.desc()
        )
        .all()
    )

    for history in histories:
        if history.student_id not in export_info:
            export_info[history.student_id] = {
                "document_id": history.document_id,
                "generated_time": history.generated_time,
            }

    return render_template(
        "new_staff/hostel/clearance.html",
        students=students,
        export_info=export_info
    )


@app.route("/print-clearance")
def print_clearance():

    role = session.get("role")

    # Normal student access remains unchanged.
    if role == "student":

        sid = session.get("student_id")

        if not sid:
            sid = session.get("user")

    # Hostel staff may open an existing student's clearance.
    elif role == "staff" and _hostel_staff_allowed():

        sid = request.args.get("student_id", "").strip()

    else:
        return redirect(url_for("student_login"))


    if not sid:
        return "<h3>No student ID found in session.</h3>", 404

    s = Student.query.filter_by(
        student_id=str(sid)
    ).first()

    if not s:
        return f"""
        <h3>Student not found</h3>
        <p>Student ID: {sid}</p>
        """, 404

    generated_time = zambia_now().strftime(
        "%d %B %Y | %I:%M %p"
    )

    document_id = (
        f"CLR-{s.student_id}-"
        f"{zambia_now().strftime('%Y%m%d%H%M%S')}"
    )

    # --------------------------------------------------
    # ============================================================
    # CURRENT CLEARANCE REPORT DATA
    # One current row per department/item/requirement.
    # Historical transactions are deliberately excluded.
    # ============================================================

    from markupsafe import escape

    def _display(value):
        if value is None:
            return "—"
        value = str(value).strip()
        return escape(value) if value else "—"

    def _remark(value):
        if value is None:
            return "NIL"
        value = str(value).strip()
        return escape(value) if value else "NIL"

    def _date(value):
        if not value:
            return "—"
        try:
            if hasattr(value, "strftime"):
                return value.strftime("%d %b %Y")
            return str(value).strip()
        except Exception:
            return str(value).strip()

    def _status(value, default="Pending"):
        if not value:
            return default
        value = str(value).strip().lower()

        if value in ("cleared", "clear", "returned", "resolved", "complete", "completed"):
            return "Cleared"

        return "Pending"

    def _row(
        department,
        item_requirement,
        issued_at=None,
        assigned_by=None,
        returned_at=None,
        returned_by=None,
        remarks=None,
        status="Pending"
    ):
        return {
            "department": department,
            "item_requirement": item_requirement,
            "issued_at": _date(issued_at),
            "assigned_by": _display(assigned_by),
            "returned_at": _date(returned_at),
            "returned_by": _display(returned_by),
            "remarks": _remark(remarks),
            "status": status
        }

    # The report must always contain every clearance department.
    report_departments = [
        ("Library", "library"),
        ("Sports", "sports"),
        ("Accounts", "accounts"),
        ("Communication Skills", "communication"),
        ("Mathematics", "mathematics"),
        ("Human Resource", "human_resource"),
        ("Head Of Training Section", "training_section"),
        ("AME Stores", "ame"),
        ("Stores", "stores"),
        ("Technical Services Office", "tso"),
        ("Hostel", "hostel"),
    ]

    report_rows = []

    # ------------------------------------------------------------
    # Department-level records helper
    # ------------------------------------------------------------
    def _department_record(department_key):
        try:
            return (
                DepartmentClearance.query
                .filter_by(
                    student_id=s.student_id,
                    department=department_key
                )
                .order_by(DepartmentClearance.id.desc())
                .first()
            )
        except Exception:
            return None

    # ------------------------------------------------------------
    # LIBRARY
    # Only current/unreturned books are outstanding.
    # Returned books are retained only when they are the current
    # transaction context; historical books are not dumped.
    # ------------------------------------------------------------
    library_books = (
        LibraryBook.query
        .filter_by(student_id=s.student_id)
        .order_by(LibraryBook.id.desc())
        .all()
    )

    active_library_books = [
        book for book in library_books
        if not bool(book.returned)
    ]

    if active_library_books:
        for book in active_library_books:
            report_rows.append(
                _row(
                    "Library",
                    book.name or "Book",
                    book.borrowed_at,
                    None,
                    None,
                    None,
                    None,
                    "Pending"
                )
            )
    else:
        rec = _department_record("library")
        report_rows.append(
            _row(
                "Library",
                "Library Clearance",
                None,
                None,
                None,
                None,
                rec.remarks if rec else None,
                _status(rec.status if rec else "Cleared", "Cleared")
            )
        )

    # ------------------------------------------------------------
    # SPORTS
    # Show current outstanding sports items only.
    # Do not concatenate historical items into Remarks.
    # ------------------------------------------------------------
    sports_records = (
        SportsItem.query
        .filter_by(student_id=s.student_id)
        .order_by(SportsItem.id.desc())
        .all()
    )

    current_sports = [
        item for item in sports_records
        if str(item.status or "").strip().lower() not in
        ("returned", "cleared", "resolved", "complete", "completed")
    ]

    if current_sports:
        for item in current_sports:
            item_name = item.item or item.sport or "Sports Item"
            report_rows.append(
                _row(
                    "Sports",
                    item_name,
                    item.created_at,
                    None,
                    None,
                    None,
                    item.remarks,
                    "Pending"
                )
            )
    else:
        rec = _department_record("sports")
        report_rows.append(
            _row(
                "Sports",
                "Sports Clearance",
                None,
                None,
                None,
                None,
                rec.remarks if rec else None,
                _status(rec.status if rec else "Cleared", "Cleared")
            )
        )

    # ------------------------------------------------------------
    # ACCOUNTS
    # Financial information belongs in Item / Requirement.
    # Remarks remains remarks only.
    # ------------------------------------------------------------
    account = (
        Account.query
        .filter_by(student_id=s.student_id)
        .first()
    )

    if account:
        balance = max(
            0,
            float(account.total_fee or 0) - float(account.paid or 0)
        )

        if str(account.status or "").strip().lower() == "cleared":
            account_status = "Cleared"
        elif float(account.paid or 0) >= float(account.minimum_required or 0):
            account_status = "Cleared"
        elif balance <= 0:
            account_status = "Cleared"
        else:
            account_status = "Pending"

        requirement = (
            f"Fees — Total: K{float(account.total_fee or 0):,.2f}; "
            f"Paid: K{float(account.paid or 0):,.2f}; "
            f"Balance: K{balance:,.2f}"
        )

        report_rows.append(
            _row(
                "Accounts",
                requirement,
                None,
                None,
                None,
                None,
                account.remarks,
                account_status
            )
        )
    else:
        rec = _department_record("accounts")
        report_rows.append(
            _row(
                "Accounts",
                "Fees",
                None,
                None,
                None,
                None,
                rec.remarks if rec else None,
                _status(rec.status if rec else "Pending")
            )
        )

    # ------------------------------------------------------------
    # COMMUNICATION SKILLS
    # Current property record only.
    # ------------------------------------------------------------
    communication_properties = (
        CommunicationProperty.query
        .filter_by(student_id=s.student_id)
        .order_by(CommunicationProperty.id.desc())
        .all()
    )

    active_communication = [
        p for p in communication_properties
        if str(p.status or "").strip().lower() not in
        ("returned", "cleared", "resolved", "complete", "completed")
    ]

    if active_communication:
        communication_items = []
        communication_issued = []
        communication_staff = []
        communication_returned = []
        communication_returned_by = []
        communication_remarks = []
        communication_statuses = []

        for prop in active_communication:
            if prop.name:
                communication_items.append(prop.name)
            if prop.issued_at:
                communication_issued.append(prop.issued_at)
            if prop.issued_by:
                communication_staff.append(prop.issued_by)
            if prop.returned_at:
                communication_returned.append(prop.returned_at)
            if prop.returned_by:
                communication_returned_by.append(prop.returned_by)
            if prop.remarks:
                communication_remarks.append(prop.remarks)
            communication_statuses.append(_status(prop.status))

        report_rows.append(
            _row(
                "Communication Skills",
                "; ".join(dict.fromkeys(communication_items))
                or "Departmental Requirement",
                communication_issued,
                communication_staff,
                communication_returned,
                communication_returned_by,
                communication_remarks,
                "Cleared"
                if all(
                    status == "Cleared"
                    for status in communication_statuses
                )
                else "Pending"
            )
        )
    else:
        rec = _department_record("communication")
        report_rows.append(
            _row(
                "Communication Skills",
                "Departmental Clearance",
                None,
                None,
                None,
                None,
                rec.remarks if rec else None,
                _status(rec.status if rec else "Pending")
            )
        )

    # ------------------------------------------------------------
    # MATHEMATICS
    # ------------------------------------------------------------
    mathematics_properties = (
        MathematicsProperty.query
        .filter_by(student_id=s.student_id)
        .order_by(MathematicsProperty.id.desc())
        .all()
    )

    active_mathematics = [
        p for p in mathematics_properties
        if str(p.status or "").strip().lower() not in
        ("returned", "cleared", "resolved", "complete", "completed")
    ]

    if active_mathematics:
        for prop in active_mathematics:
            report_rows.append(
                _row(
                    "Mathematics",
                    prop.name or "Departmental Requirement",
                    prop.issued_at,
                    prop.issued_by,
                    prop.returned_at,
                    prop.returned_by,
                    prop.remarks,
                    _status(prop.status)
                )
            )
    else:
        rec = _department_record("mathematics")
        report_rows.append(
            _row(
                "Mathematics",
                "Departmental Clearance",
                None,
                None,
                None,
                None,
                rec.remarks if rec else None,
                _status(rec.status if rec else "Pending")
            )
        )

    # ------------------------------------------------------------
    # HUMAN RESOURCE
    # ------------------------------------------------------------
    rec = _department_record("human resource") or _department_record("hr")
    report_rows.append(
        _row(
            "Human Resource",
            "Departmental Clearance",
            None,
            None,
            None,
            None,
            rec.remarks if rec else None,
            _status(rec.status if rec else "Pending")
        )
    )

    # ------------------------------------------------------------
    # HEAD OF TRAINING SECTION
    # ------------------------------------------------------------
    training_properties = (
        TrainingSectionProperty.query
        .filter_by(student_id=s.student_id)
        .order_by(TrainingSectionProperty.id.desc())
        .all()
    )

    active_training = [
        p for p in training_properties
        if str(p.status or "").strip().lower() not in
        ("returned", "cleared", "resolved", "complete", "completed")
    ]

    if active_training:
        for prop in active_training:
            report_rows.append(
                _row(
                    "Head Of Training Section",
                    prop.name or "Training Requirement",
                    prop.issued_at,
                    prop.issued_by,
                    prop.returned_at,
                    prop.returned_by,
                    prop.remarks,
                    _status(prop.status)
                )
            )
    else:
        rec = (
            _department_record("training section")
            or _department_record("head of training section")
            or _department_record("training")
        )
        report_rows.append(
            _row(
                "Head Of Training Section",
                "Departmental Clearance",
                None,
                None,
                None,
                None,
                rec.remarks if rec else None,
                _status(rec.status if rec else "Pending")
            )
        )

    # ------------------------------------------------------------
    # AME STORES
    # Only currently unreturned tools are pending.
    # ------------------------------------------------------------
    ame_tools = (
        AMETool.query
        .filter_by(student_id=s.student_id)
        .order_by(AMETool.id.desc())
        .all()
    )

    active_ame = [
        tool for tool in ame_tools
        if not bool(tool.returned)
    ]

    if active_ame:
        for tool in active_ame:
            report_rows.append(
                _row(
                    "AME Stores",
                    tool.name or "AME Tool",
                    tool.issued_at,
                    tool.issued_by,
                    None,
                    None,
                    tool.remarks,
                    "Pending"
                )
            )
    else:
        rec = _department_record("ame stores") or _department_record("ame")
        report_rows.append(
            _row(
                "AME Stores",
                "AME Tools",
                None,
                None,
                None,
                None,
                rec.remarks if rec else None,
                _status(rec.status if rec else "Cleared", "Cleared")
            )
        )

    # ------------------------------------------------------------
    # STORES
    # Use current StoreProperty records and pending ItemRequests.
    # ------------------------------------------------------------
    store_properties = (
        StoreProperty.query
        .filter_by(student_id=s.student_id)
        .order_by(StoreProperty.id.desc())
        .all()
    )

    active_store_properties = [
        p for p in store_properties
        if str(p.status or "").strip().lower() not in
        ("returned", "cleared", "resolved", "complete", "completed")
    ]

    if active_store_properties:
        for prop in active_store_properties:
            report_rows.append(
                _row(
                    "Stores",
                    prop.name or "Store Property",
                    prop.issued_at,
                    prop.issued_by,
                    None,
                    None,
                    prop.remarks,
                    _status(prop.status)
                )
            )
    else:
        # If a current accepted/requested item has not yet been issued,
        # represent that actual request instead of inventing a record.
        pending_requests = (
            ItemRequest.query
            .filter_by(
                student_id=s.student_id,
                department="stores"
            )
            .order_by(ItemRequest.id.desc())
            .all()
        )

        current_pending_requests = [
            req for req in pending_requests
            if str(req.status or "").strip().lower()
            not in ("returned", "cleared", "resolved", "complete", "completed")
        ]

        if current_pending_requests:
            for req in current_pending_requests:
                report_rows.append(
                    _row(
                        "Stores",
                        req.item or req.item_type or "Store Property",
                        req.assigned_at,
                        req.assigned_by,
                        None,
                        None,
                        req.remarks,
                        "Pending"
                    )
                )
        else:
            rec = _department_record("stores")
            report_rows.append(
                _row(
                    "Stores",
                    "Stores Clearance",
                    None,
                    None,
                    None,
                    None,
                    rec.remarks if rec else None,
                    _status(rec.status if rec else "Pending")
                )
            )

    # ------------------------------------------------------------
    # TECHNICAL SERVICES OFFICE
    # TSO is a normal clearance department.
    # ------------------------------------------------------------

    student_accommodation = (
        AccommodationAssignment.query
        .filter(
            AccommodationAssignment.student_id
            == s.student_id,
            AccommodationAssignment.status.in_([
                "Occupying",
                "occupying",
                "Active",
                "active",
            ])
        )
        .order_by(
            AccommodationAssignment.id.desc()
        )
        .first()
    )

    tso = None

    if student_accommodation:
        tso = (
            TSOInspection.query
            .filter_by(
                accommodation_assignment_id=student_accommodation.id
            )
            .order_by(TSOInspection.id.desc())
            .first()
        )

    if tso:
        tso_status = _status(tso.status)

        if tso_status == "Cleared":
            returned_at = tso.inspected_at
            returned_by = tso.inspected_by
        else:
            returned_at = None
            returned_by = None

        tso_requirement = (
            f"Room / Key — {tso.key_name}"
            if tso.key_name
            else "Technical Services Inspection"
        )

        report_rows.append(
            _row(
                "Technical Services Office",
                tso_requirement,
                tso.inspected_at,
                tso.inspected_by,
                returned_at,
                returned_by,
                tso.remarks,
                tso_status
            )
        )
    else:
        rec = _department_record("technical services office") or _department_record("tso")
        report_rows.append(
            _row(
                "Technical Services Office",
                "Technical Services Clearance",
                None,
                None,
                None,
                None,
                rec.remarks if rec else None,
                _status(rec.status if rec else "Pending")
            )
        )

    # ------------------------------------------------------------
    # HOSTEL
    # Hostel remains a normal digital clearance department.
    # ------------------------------------------------------------
    hostel = (
        HostelInspection.query
        .filter_by(student_id=s.student_id)
        .order_by(HostelInspection.id.desc())
        .first()
    )

    if hostel:
        hostel_status = _status(hostel.status)

        if hostel_status == "Cleared":
            returned_at = hostel.inspected_at
            returned_by = hostel.inspected_by
        else:
            returned_at = None
            returned_by = None

        report_rows.append(
            _row(
                "Hostel",
                "Hostel Room Inspection",
                hostel.inspected_at,
                hostel.inspected_by,
                returned_at,
                returned_by,
                hostel.remarks,
                hostel_status
            )
        )
    else:
        rec = _department_record("hostel")
        report_rows.append(
            _row(
                "Hostel",
                "Hostel Clearance",
                None,
                None,
                None,
                None,
                rec.remarks if rec else None,
                _status(rec.status if rec else "Pending")
            )
        )

    # ------------------------------------------------------------
    # AUTHORITATIVE EXPORT GATE
    # ------------------------------------------------------------
    # The student Current Clearance table is the source of truth.
    # Recalculate ONLY the 11 department statuses here using the
    # same current-state rules as /student/clearance.
    #
    # This gate runs before ClearanceHistory is created.
    # ------------------------------------------------------------

    export_statuses = {}

    # Accounts
    account_gate = Account.query.filter_by(
        student_id=s.student_id
    ).first()

    if account_gate:
        account_outstanding = (
            (account_gate.total_fee or 0)
            - (account_gate.paid or 0)
        )
        account_minimum = account_gate.minimum_required or 0

        export_statuses["Accounts"] = (
            "Cleared"
            if (
                account_outstanding <= 0
                or (account_gate.paid or 0) >= account_minimum
            )
            else "Pending"
        )
    else:
        export_statuses["Accounts"] = "Pending"

    # Library
    library_gate = LibraryBook.query.filter_by(
        student_id=s.student_id,
        returned=False
    ).all()

    export_statuses["Library"] = (
        "Pending" if library_gate else "Cleared"
    )

    # Communication Skills
    communication_gate = (
        CommunicationProperty.query
        .filter_by(student_id=s.student_id)
        .order_by(CommunicationProperty.id.desc())
        .all()
    )

    communication_current = [
        record
        for record in communication_gate
        if (
            getattr(record, "returned_at", None) is None
            and str(
                getattr(record, "status", "") or ""
            ).strip().lower()
            in {
                "",
                "pending",
                "issued",
                "assigned",
                "accepted"
            }
        )
    ]

    if communication_current:
        export_statuses["Communication Skills"] = "Pending"
    else:
        communication_clearance = (
            DepartmentClearance.query
            .filter_by(
                student_id=s.student_id,
                department="communication"
            )
            .order_by(DepartmentClearance.id.desc())
            .first()
        )

        export_statuses["Communication Skills"] = (
            "Pending"
            if (
                communication_clearance
                and str(
                    communication_clearance.status or ""
                ).strip().lower()
                not in {
                    "returned",
                    "resolved",
                    "cleared",
                    "complete",
                    "completed"
                }
            )
            else "Cleared"
        )

    # Mathematics
    mathematics_gate = (
        MathematicsProperty.query
        .filter_by(student_id=s.student_id)
        .order_by(MathematicsProperty.id.desc())
        .all()
    )

    mathematics_current = [
        record
        for record in mathematics_gate
        if (
            getattr(record, "returned_at", None) is None
            and str(
                getattr(record, "status", "") or ""
            ).strip().lower()
            in {
                "",
                "pending",
                "issued",
                "assigned",
                "accepted"
            }
        )
    ]

    if mathematics_current:
        export_statuses["Mathematics"] = "Pending"
    else:
        mathematics_clearance = (
            DepartmentClearance.query
            .filter_by(
                student_id=s.student_id,
                department="mathematics"
            )
            .order_by(DepartmentClearance.id.desc())
            .first()
        )

        export_statuses["Mathematics"] = (
            "Pending"
            if (
                mathematics_clearance
                and str(
                    mathematics_clearance.status or ""
                ).strip().lower()
                not in {
                    "returned",
                    "resolved",
                    "cleared",
                    "complete",
                    "completed"
                }
            )
            else "Cleared"
        )

    # Human Resource
    hr_gate = (
        DepartmentClearance.query
        .filter(
            DepartmentClearance.student_id == s.student_id,
            db.func.lower(
                db.func.trim(DepartmentClearance.department)
            ).in_([
                "hr",
                "human resource",
                "human resources"
            ])
        )
        .order_by(DepartmentClearance.id.desc())
        .first()
    )

    export_statuses["Human Resource"] = (
        _status(hr_gate.status, "Cleared")
        if hr_gate
        else "Cleared"
    )

    # Sports
    sports_gate = (
        SportsItem.query
        .filter_by(student_id=s.student_id)
        .order_by(SportsItem.id.desc())
        .all()
    )

    sports_current = []

    for record in sports_gate:
        status = str(
            getattr(record, "status", "") or ""
        ).strip().lower()

        if status in {
            "returned",
            "resolved",
            "cleared",
            "declined",
            "rejected",
            "cancelled",
            "complete",
            "completed"
        }:
            continue

        if getattr(record, "returned_at", None) is not None:
            continue

        name = (
            getattr(record, "item", None)
            or getattr(record, "sport", None)
            or ""
        )

        if str(name).strip():
            sports_current.append(record)

    export_statuses["Sports"] = (
        "Pending" if sports_current else "Cleared"
    )

    # AME Stores
    ame_gate = (
        AMETool.query
        .filter_by(student_id=s.student_id)
        .order_by(AMETool.id.desc())
        .all()
    )

    ame_current = []

    for record in ame_gate:
        if bool(getattr(record, "returned", False)):
            continue

        if getattr(record, "returned_at", None) is not None:
            continue

        if not str(
            getattr(record, "name", None) or ""
        ).strip():
            continue

        ame_current.append(record)

    export_statuses["AME Stores"] = (
        "Pending" if ame_current else "Cleared"
    )

    # Stores
    if s.accommodation == "Day Scholar":
        export_statuses["Stores"] = "Cleared"
    else:
        stores_gate = (
            StoreProperty.query
            .filter_by(student_id=s.student_id)
            .all()
        )

        store_current = [
            record
            for record in stores_gate
            if str(
                getattr(record, "status", "") or ""
            ).strip().lower() != "returned"
        ]

        export_statuses["Stores"] = (
            "Pending" if store_current else "Cleared"
        )

    # Head Of Training Section
    training_requests_gate = (
        ItemRequest.query
        .filter(
            ItemRequest.student_id == s.student_id,
            db.func.lower(
                db.func.trim(
                    db.func.coalesce(
                        ItemRequest.department,
                        ""
                    )
                )
            ) == "training section"
        )
        .order_by(ItemRequest.id.desc())
        .all()
    )

    training_properties_gate = (
        TrainingSectionProperty.query
        .filter_by(student_id=s.student_id)
        .order_by(TrainingSectionProperty.id.desc())
        .all()
    )

    training_current = [
        record
        for record in training_properties_gate
        if (
            getattr(record, "returned_at", None) is None
            and str(
                getattr(record, "status", "") or ""
            ).strip().lower()
            in {"issued", "assigned"}
        )
    ]

    latest_training_gate = (
        training_requests_gate[0]
        if training_requests_gate
        else None
    )

    if training_current:
        export_statuses["Head Of Training Section"] = "Pending"
    elif latest_training_gate:
        request_status = str(
            getattr(latest_training_gate, "status", "") or ""
        ).strip().lower()

        if request_status in {"accepted", "declined"}:
            export_statuses["Head Of Training Section"] = "Cleared"
        elif request_status == "pending":
            training_clearance_gate = (
                DepartmentClearance.query
                .filter(
                    DepartmentClearance.student_id == s.student_id,
                    db.func.lower(
                        db.func.trim(
                            DepartmentClearance.department
                        )
                    ) == "training section"
                )
                .order_by(DepartmentClearance.id.desc())
                .first()
            )

            export_statuses["Head Of Training Section"] = (
                _status(
                    training_clearance_gate.status,
                    "Cleared"
                )
                if training_clearance_gate
                else "Cleared"
            )
        else:
            export_statuses["Head Of Training Section"] = "Cleared"
    else:
        export_statuses["Head Of Training Section"] = "Cleared"

    # TSO
    accommodation_gate = (
        AccommodationAssignment.query
        .filter(
            AccommodationAssignment.student_id == s.student_id,
            AccommodationAssignment.status.in_([
                "Occupying",
                "occupying",
                "Active",
                "active"
            ])
        )
        .order_by(AccommodationAssignment.id.desc())
        .first()
    )

    # TSO clearance is based on the actual TSO inspection
    # transaction, not only on whether the student currently
    # occupies a room. A student may have completed TSO
    # inspection and later vacated the accommodation.

    tso_gate = (
        TSOInspection.query
        .filter_by(student_id=s.student_id)
        .order_by(
            TSOInspection.inspected_at.desc(),
            TSOInspection.id.desc()
        )
        .first()
    )

    if tso_gate:
        export_statuses["TSO"] = (
            "Cleared"
            if str(
                tso_gate.status or ""
            ).strip().lower() == "cleared"
            else "Pending"
        )
    else:
        export_statuses["TSO"] = "Cleared"

    # Hostel
    # Current Clearance treats an active accommodation assignment
    # as a current Hostel requirement.
    export_statuses["Hostel"] = (
        "Pending"
        if accommodation_gate
        else "Cleared"
    )

    # ------------------------------------------------------------
    # EXACT 11-DEPARTMENT EXPORT CHECK
    # ------------------------------------------------------------

    export_departments = [
        "Accounts",
        "Library",
        "Communication Skills",
        "Mathematics",
        "Human Resource",
        "Sports",
        "AME Stores",
        "Stores",
        "Head Of Training Section",
        "TSO",
        "Hostel"
    ]

    # ------------------------------------------------------------
    # SYNCHRONIZE PRINTED OFFICER WITH STUDENT CLEARANCE
    # RESOLVED-BY / RETURNED-BY LOGIC
    # ------------------------------------------------------------

    def print_real_person_name(value):
        if value is None:
            return None

        value = str(value).strip()

        if not value:
            return None

        generic = {
            "nil", "n/a", "na", "none",
            "staff", "staff member", "staff officer",
            "stores staff", "sports staff",
            "sports staff member", "library staff",
            "accounts staff", "accounts staff member",
            "ame stores staff", "ame stores staff member",
            "hostels staff", "hostel staff",
            "hr staff", "hr staff member",
            "human resource staff",
            "mathematics staff", "math staff",
            "math staff member",
            "training staff", "training staff member",
            "training section staff",
            "communication skills staff",
            "communication skills staff member",
            "technical services office",
            "technical services office (tso)",
            "tso staff", "tso staff member",
            "stores officer", "training section",
            "hostels (hos)",
            "human resource / admin officer",
            "communication skills (rel sc)",
            "communication skills (rel/sc)"
        }

        lowered = value.casefold()

        if lowered in generic:
            return None

        if (
            lowered.endswith(" staff")
            or lowered.endswith(" staff member")
            or lowered.endswith(" staff officer")
        ):
            return None

        return value


    print_history_aliases = {
        "Communication Skills": [
            "Communication Skills",
            "Communication Skills (REL/SC)",
            "Communication Skills (REL SC)"
        ],
        "Head Of Training Section": [
            "Head Of Training Section",
            "Training Section"
        ],
        "Human Resource": [
            "Human Resource",
            "Human Resources"
        ],
        "TSO": [
            "TSO",
            "Technical Services Office",
            "Technical Services Office (TSO)"
        ],
        "Hostel": [
            "Hostel",
            "Hostels",
            "Hostels (HOS)"
        ],
        "Stores": ["Stores"],
        "AME Stores": ["AME Stores"],
        "Accounts": ["Accounts"],
        "Library": ["Library"],
        "Sports": ["Sports"],
        "Mathematics": ["Mathematics"]
    }


    for record in report_rows:
        department = str(
            record.get("department", "")
        ).strip()

        lookup_department = (
            "TSO"
            if department == "Technical Services Office"
            else department
        )

        resolved_officer = None

        try:
            aliases = print_history_aliases.get(
                lookup_department,
                [lookup_department]
            )

            history_rows = (
                DepartmentHistory.query
                .filter(
                    DepartmentHistory.student_id
                    == student.student_id,
                    db.func.lower(
                        db.func.trim(
                            DepartmentHistory.department
                        )
                    ).in_([
                        name.lower() for name in aliases
                    ])
                )
                .order_by(
                    DepartmentHistory.created_at.desc(),
                    DepartmentHistory.id.desc()
                )
                .all()
            )

            for history_row in history_rows:
                candidate = print_real_person_name(
                    getattr(
                        history_row,
                        "performed_by",
                        None
                    )
                )

                if candidate:
                    resolved_officer = candidate
                    break

        except Exception:
            resolved_officer = None

        if not resolved_officer and lookup_department == "TSO":
            try:
                tso_record = (
                    TSOInspection.query
                    .filter_by(
                        student_id=student.student_id
                    )
                    .order_by(
                        TSOInspection.inspected_at.desc(),
                        TSOInspection.id.desc()
                    )
                    .first()
                )

                if tso_record:
                    resolved_officer = print_real_person_name(
                        getattr(
                            tso_record,
                            "inspected_by",
                            None
                        )
                    )

            except Exception:
                resolved_officer = None

        if not resolved_officer:
            resolved_officer = print_real_person_name(
                record.get("officer")
            )

        if resolved_officer:
            record["officer"] = resolved_officer

            if isinstance(
                record.get("details"),
                dict
            ):
                record["details"]["officer"] = resolved_officer

    export_pending_departments = [
        department
        for department in export_departments
        if export_statuses.get(department) != "Cleared"
    ]

    # Keep the existing report rows synchronized with the same
    # authoritative department statuses.
    for record in report_rows:
        department = record.get("department")

        if department == "Technical Services Office":
            department = "TSO"

        if department in export_statuses:
            record["status"] = export_statuses[department]

    # ------------------------------------------------------------
    # BLOCK OFFICIAL EXPORT IF ANY DEPARTMENT IS PENDING
    # ------------------------------------------------------------

    if export_pending_departments:
        pending_departments = "".join(
            f"<li>{department}</li>"
            for department in export_pending_departments
        )

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta
                name="viewport"
                content="width=device-width, initial-scale=1.0"
            >
            <title>Clearance Export Unavailable</title>
            <style>

        @page {{
            size: A4 landscape;
            margin: 12mm;
        }}

                body {{
                    margin: 0;
                    padding: 30px 15px;
                    font-family: Arial, sans-serif;
                    background: #f5f7f9;
                    color: #1f2937;
                }}

                .container {{
                    max-width: 600px;
                    margin: 40px auto;
                    background: white;
                    padding: 30px;
                    border-radius: 12px;
                    box-shadow: 0 4px 18px rgba(0,0,0,0.08);
                }}

                h1 {{
                    color: #b91c1c;
                    margin-top: 0;
                }}

                .message {{
                    line-height: 1.6;
                    margin-bottom: 20px;
                }}

                ul {{
                    line-height: 1.8;
                    padding-left: 25px;
                }}

                .back {{
                    display: inline-block;
                    margin-top: 20px;
                    padding: 11px 18px;
                    background: #166534;
                    color: white;
                    text-decoration: none;
                    border-radius: 7px;
                }}
            </style>
        </head>

        <body>
            <div class="container">
                <h1>Clearance Export Unavailable</h1>

                <div class="message">
                    Your official clearance document cannot be generated
                    because the following department(s) are not yet cleared:
                </div>

                <ul>
                    {pending_departments}
                </ul>

                <a
                    class="back"
                    href="{"/hostel/clearance" if session.get("role") == "staff" and _hostel_staff_allowed() else "/student/clearance"}"
                >
                    {"Back to Hostel Clearance" if session.get("role") == "staff" and _hostel_staff_allowed() else "Back to Current Clearance"}
                </a>
            </div>
        </body>
        </html>
        """

    # ------------------------------------------------------------
    # BUILD CURRENT REPORT TABLE
    # ------------------------------------------------------------
    # EXPORT TRANSACTION DETAILS
    #
    # The official document is generated only after every
    # department is cleared. The Date/Time column therefore
    # represents the most recent transaction that actually
    # completed/cleared the department.
    # ------------------------------------------------------------

    completed_statuses = {
        "cleared",
        "returned",
        "resolved",
        "complete",
        "completed",
    }

    def completed(value):
        return (
            str(value or "").strip().lower()
            in completed_statuses
        )

    def transaction_date(value):
        if not value:
            return "—"

        try:
            if hasattr(value, "strftime"):
                return value.strftime("%d %b %Y %I:%M %p")

            value = str(value).strip()

            for fmt in (
                "%Y-%m-%d %H:%M:%S.%f",
                "%Y-%m-%d %H:%M:%S",
                "%d %b %Y %H:%M",
                "%d %b %Y %I:%M %p",
            ):
                try:
                    parsed = datetime.strptime(value, fmt)
                    return parsed.strftime("%d %b %Y %I:%M %p")
                except Exception:
                    pass

            return value

        except Exception:
            return str(value).strip() or "—"

    def transaction_details(record, officer_field=None,
                             date_field=None, remarks_field=None):

        if not record:
            return {
                "officer": "NIL",
                "remarks": "NIL",
                "datetime": "—",
            }

        # The export must show the officer who ASSIGNED/ISSUED
        # the item, not the officer who later returned it.
        officer = None

        officer_fields = []

        if officer_field:
            officer_fields.append(officer_field)

        officer_fields.extend([
            "returned_by",
            "assigned_by",
            "performed_by",
        ])

        for field in officer_fields:
            candidate = getattr(record, field, None)

            if candidate and str(candidate).strip():
                officer = candidate
                break

        date_value = (
            getattr(record, date_field, None)
            if date_field
            else getattr(record, "created_at", None)
        )

        remarks = (
            getattr(record, remarks_field, None)
            if remarks_field
            else getattr(record, "remarks", None)
        )

        return {
            "officer": _display(officer) if officer else "NIL",
            "remarks": _remark(remarks),
            "datetime": transaction_date(date_value),
        }

    def history_transaction(*department_names):
        names = {
            str(name or "").strip().lower()
            for name in department_names
        }

        try:
            records = (
                DepartmentHistory.query
                .filter_by(student_id=s.student_id)
                .order_by(DepartmentHistory.created_at.desc())
                .all()
            )

            for record in records:
                department_name = str(
                    record.department or ""
                ).strip().lower()

                if (
                    department_name in names
                    and completed(record.status)
                ):
                    return record

        except Exception:
            pass

        return None

    def latest_completed_property(model):
        try:
            records = (
                model.query
                .filter_by(student_id=s.student_id)
                .order_by(model.id.desc())
                .all()
            )

            for record in records:
                if completed(record.status):
                    return record

        except Exception:
            pass

        return None

    export_transactions = {}

    # ------------------------------------------------------------
    # LIBRARY
    # ------------------------------------------------------------

    try:
        library_books = (
            LibraryBook.query
            .filter_by(student_id=s.student_id)
            .all()
        )

        returned_books = [
            book for book in library_books
            if getattr(book, "returned", False)
            and getattr(book, "returned_at", None)
        ]

        if returned_books:
            latest = max(
                returned_books,
                key=lambda x: str(x.returned_at or "")
            )

            export_transactions["Library"] = {
                "officer": "NIL",
                "remarks": "NIL",
                "datetime": transaction_date(latest.returned_at),
            }

    except Exception:
        pass

    # ------------------------------------------------------------
    # STAFF NAME FALLBACK
    # ------------------------------------------------------------
    # Some older clearance records do not store the officer who
    # performed the clearance. In those cases, use the current
    # departmental staff account as the display name.
    def staff_officer_for_department(*department_names):
        users = (
            User.query
            .filter_by(role="staff")
            .order_by(User.id.desc())
            .all()
        )

        wanted = {
            str(name).strip().lower()
            for name in department_names
            if name
        }

        for user in users:
            department_name = str(
                getattr(user, "department", "") or ""
            ).strip().lower()

            if department_name in wanted:
                username = (
                    getattr(user, "username", None)
                    or getattr(user, "name", None)
                )

                if username and str(username).strip():
                    return _display(username)

        return "NIL"

    # ------------------------------------------------------------
    # SPORTS
    # ------------------------------------------------------------

    try:
        sports_records = (
            SportsItem.query
            .filter_by(student_id=s.student_id)
            .all()
        )

        completed_sports = [
            item for item in sports_records
            if completed(item.status)
            and getattr(item, "returned_at", None)
        ]

        if completed_sports:
            latest = max(
                completed_sports,
                key=lambda x: x.returned_at
            )

            export_transactions["Sports"] = transaction_details(
                latest,
                "returned_by",
                "returned_at",
                "remarks",
            )

    except Exception:
        pass

    if "Sports" not in export_transactions:
        export_transactions["Sports"] = {
            "officer": staff_officer_for_department(
                "Sports"
            ),
            "remarks": "NIL",
            "datetime": "—",
        }

    # ------------------------------------------------------------
    # ACCOUNTS
    # ------------------------------------------------------------

    try:
        account_history = (
            AccountHistory.query
            .filter_by(student_id=s.student_id)
            .order_by(AccountHistory.created_at.desc())
            .all()
        )

        completed_accounts = [
            record for record in account_history
            if completed(record.status)
        ]

        if completed_accounts:
            export_transactions["Accounts"] = transaction_details(
                completed_accounts[0],
                None,
                "created_at",
                "remarks",
            )

    except Exception:
        pass

    # ------------------------------------------------------------
    # COMMUNICATION SKILLS — REL/SC
    # ------------------------------------------------------------

    communication = latest_completed_property(
        CommunicationProperty
    )

    if communication:
        export_transactions["Communication Skills"] = (
            transaction_details(
                communication,
                "returned_by",
                "returned_at",
                "remarks",
            )
        )
    else:
        communication_history = history_transaction(
            "Communication Skills (REL/SC)"
        )

        if communication_history:
            export_transactions["Communication Skills"] = (
                transaction_details(communication_history)
            )

    # ------------------------------------------------------------
    # MATHEMATICS
    # ------------------------------------------------------------

    mathematics = latest_completed_property(
        MathematicsProperty
    )

    if mathematics:
        export_transactions["Mathematics"] = (
            transaction_details(
                mathematics,
                "returned_by",
                "returned_at",
                "remarks",
            )
        )
    else:
        mathematics_history = history_transaction(
            "Mathematics"
        )

        if mathematics_history:
            export_transactions["Mathematics"] = (
                transaction_details(mathematics_history)
            )

    # ------------------------------------------------------------
    # HUMAN RESOURCE
    # ------------------------------------------------------------

    hr_history = history_transaction(
        "Human Resource",
        "hr",
    )

    if hr_history:
        export_transactions["Human Resource"] = (
            transaction_details(hr_history)
        )
    else:
        export_transactions["Human Resource"] = {
            "officer": staff_officer_for_department(
                "Human Resources/Admin Officer",
                "Human Resource / Admin Officer",
            ),
            "remarks": "NIL",
            "datetime": "—",
        }

    # ------------------------------------------------------------
    # HEAD OF TRAINING SECTION
    # ------------------------------------------------------------

    training = latest_completed_property(
        TrainingSectionProperty
    )

    if training:
        export_transactions["Head Of Training Section"] = (
            transaction_details(
                training,
                "returned_by",
                "returned_at",
                "remarks",
            )
        )
    else:
        training_history = history_transaction(
            "Training Section",
            "Head Of Training Section",
            "Head of Training Section",
            "Training",
        )

        if training_history:
            export_transactions["Head Of Training Section"] = (
                transaction_details(training_history)
            )

    # ------------------------------------------------------------
    # AME STORES
    # ------------------------------------------------------------

    try:
        ame_tools = (
            AMETool.query
            .filter_by(student_id=s.student_id)
            .all()
        )

        returned_tools = [
            tool for tool in ame_tools
            if getattr(tool, "returned", False)
            and getattr(tool, "returned_at", None)
        ]

        if returned_tools:
            latest = max(
                returned_tools,
                key=lambda x: str(x.returned_at or "")
            )

            export_transactions["AME Stores"] = (
                transaction_details(
                    latest,
                    "returned_by",
                    "returned_at",
                    "remarks",
                )
            )

    except Exception:
        pass

    # ------------------------------------------------------------
    # STORES
    # ------------------------------------------------------------

    stores = latest_completed_property(
        StoreProperty
    )

    stores_history = history_transaction(
        "Stores",
        "Stores Officer",
        "stores",
    )

    if stores_history:
        export_transactions["Stores"] = (
            transaction_details(stores_history)
        )
    elif stores:
        export_transactions["Stores"] = (
            transaction_details(
                stores,
                "returned_by",
                "returned_at",
                "remarks",
            )
        )

    # ------------------------------------------------------------
    # TSO
    # ------------------------------------------------------------

    try:
        tso_records = (
            TSOInspection.query
            .filter_by(student_id=s.student_id)
            .order_by(TSOInspection.id.desc())
            .all()
        )

        cleared_tso = [
            inspection for inspection in tso_records
            if completed(inspection.status)
        ]

        if cleared_tso:
            latest = cleared_tso[0]

            export_transactions["TSO"] = {
                "officer": _display(
                    getattr(latest, "inspected_by", None)
                ),
                "remarks": _remark(
                    getattr(latest, "remarks", None)
                ),
                "datetime": transaction_date(
                    getattr(latest, "inspected_at", None)
                ),
            }

    except Exception:
        pass

    # ------------------------------------------------------------
    # HOSTEL
    # ------------------------------------------------------------

    hostel_history = history_transaction("Hostel")

    if hostel_history:
        export_transactions["Hostel"] = (
            transaction_details(hostel_history)
        )
    else:
        try:
            vacated = (
                AccommodationAssignment.query
                .filter_by(student_id=s.student_id)
                .order_by(AccommodationAssignment.id.desc())
                .all()
            )

            completed_assignments = [
                assignment
                for assignment in vacated
                if str(
                    assignment.status or ""
                ).strip().lower() == "vacated"
                and assignment.vacated_at
            ]

            if completed_assignments:
                latest = completed_assignments[0]

                export_transactions["Hostel"] = {
                    "officer": "NIL",
                    "remarks": "NIL",
                    "datetime": transaction_date(
                        latest.vacated_at
                    ),
                }

        except Exception:
            pass

    # ------------------------------------------------------------
    # AUTHORITATIVE OFFICER NAMES
    #
    # The final export table reads from export_transactions["officer"].
    # Student Clearance already resolves the real officer through
    # _resolve_clearance_officer(). Use that SAME resolver here.
    #
    # This deliberately happens immediately before the final rows
    # are built, so no older export logic can replace the names.
    # ------------------------------------------------------------

    _export_officer_map = {
        "Accounts": "Accounts",
        "Library": "Library",
        "Communication Skills": "Communication Skills",
        "Mathematics": "Mathematics",
        "Human Resource": "Human Resource",
        "Sports": "Sports",
        "AME Stores": "AME Stores",
        "Stores": "Stores",
        "Head Of Training Section": "Head Of Training Section",
        "Technical Services Office": "TSO",
        "TSO": "TSO",
        "Hostel": "Hostel",
    }

    for _department, _lookup_department in _export_officer_map.items():

        _authoritative_officer = _resolve_clearance_officer(
            s.student_id,
            _lookup_department
        )

        if isinstance(_authoritative_officer, list):
            _authoritative_officer = ", ".join(
                str(_name).strip()
                for _name in _authoritative_officer
                if _name and str(_name).strip()
            )

        _authoritative_officer = (
            str(_authoritative_officer).strip()
            if _authoritative_officer
            else "NIL"
        )

        if _department == "Technical Services Office":
            _export_key = "Technical Services Office"
        else:
            _export_key = _department

        if _export_key not in export_transactions:
            export_transactions[_export_key] = {
                "officer": _authoritative_officer,
                "remarks": "NIL",
                "datetime": "—",
            }
        else:
            export_transactions[_export_key]["officer"] = (
                _authoritative_officer
            )

    # ------------------------------------------------------------
    # BUILD OFFICIAL FIVE-COLUMN EXPORT
    # ------------------------------------------------------------

    rows = []

    for department, _ in report_departments:

        details = export_transactions.get(
            department,
            {
                "officer": "NIL",
                "remarks": "NIL",
                "datetime": "—",
            }
        )

        status_key = (
            "TSO"
            if department == "Technical Services Office"
            else department
        )

        clearance_status = export_statuses.get(
            status_key,
            "Pending"
        )

        status_class = (
            "status-cleared"
            if clearance_status == "Cleared"
            else "status-pending"
        )

        rows.append(
            f"""
            <tr>

                <td>{_display(department)}</td>

                <td>{details["officer"]}</td>

                <td>{details["remarks"]}</td>

                <td class="{status_class}">
                    {clearance_status}
                </td>

                <td>{details["datetime"]}</td>

            </tr>
            """
        )

    # ------------------------------------------------------------
    # CURRENT REPORT SUMMARY
    # ------------------------------------------------------------

    not_cleared = []

    for row in report_rows:
        department = str(row.get("department", "")).strip()
        status = str(row.get("status", "")).strip().lower()

        if status not in {"cleared", "clear", "returned", "resolved", "complete", "completed"}:
            not_cleared.append(department)

    not_cleared = list(dict.fromkeys(not_cleared))

    # --------------------------------------------------
    # BLOCK OFFICIAL EXPORT IF ANY DEPARTMENT IS PENDING
    # --------------------------------------------------

    if not_cleared:

        pending_departments = "".join(
            f"<li>{department}</li>"
            for department in not_cleared
        )

        return f"""
        <!DOCTYPE html>

        <html>

        <head>

            <meta charset="UTF-8">

            <meta
                name="viewport"
                content="width=device-width, initial-scale=1.0"
            >

            <title>Clearance Export Unavailable</title>

            <style>

                body {{
                    margin: 0;
                    padding: 30px 15px;
                    font-family: Arial, sans-serif;
                    background: #f5f7f9;
                    color: #1f2937;
                }}

                .container {{
                    max-width: 600px;
                    margin: 40px auto;
                    background: white;
                    padding: 30px;
                    border-radius: 12px;
                    box-shadow: 0 4px 18px rgba(0,0,0,0.08);
                }}

                h1 {{
                    color: #b91c1c;
                    margin-top: 0;
                }}

                .message {{
                    line-height: 1.6;
                    margin-bottom: 20px;
                }}

                .pending {{
                    background: #fef2f2;
                    border: 1px solid #fecaca;
                    border-radius: 8px;
                    padding: 15px 20px;
                }}

                .pending li {{
                    margin: 8px 0;
                }}

                .back {{
                    display: inline-block;
                    margin-top: 25px;
                    padding: 11px 18px;
                    background: #15803d;
                    color: white;
                    text-decoration: none;
                    border-radius: 7px;
                }}

            </style>

        </head>

        <body>

            <div class="container">

                <h1>Clearance Export Unavailable</h1>

                <div class="message">

                    Your official clearance document cannot be
                    exported yet.

                    <br><br>

                    All departments must be cleared before an
                    official clearance document can be generated.

                </div>

                <strong>Pending Departments:</strong>

                <div class="pending">

                    <ul>
                        {pending_departments}
                    </ul>

                </div>

                <a
                    class="back"
                    href="{"/hostel/clearance" if session.get("role") == "staff" and _hostel_staff_allowed() else "/student/clearance"}"
                >
                    {"Back to Hostel Clearance" if session.get("role") == "staff" and _hostel_staff_allowed() else "Back to Clearance"}
                </a>

            </div>

        </body>

        </html>
        """

    # --------------------------------------------------
    # SAVE CLEARANCE HISTORY
    # --------------------------------------------------

    history = ClearanceHistory(
        student_id=s.student_id,
        document_id=document_id,
        generated_time=generated_time,
        status="Official Clearance Form Generated"
    )

    db.session.add(history)
    db.session.commit()

    # --------------------------------------------------
    # FINAL REPORT
    # --------------------------------------------------


    # Hostel staff navigation for the existing clearance export.
    hostel_staff_view = (
        role == "staff"
        and _hostel_staff_allowed()
    )

    hostel_sidebar_html = (
        render_template("new_staff/hostel/_sidebar.html")
        if hostel_staff_view
        else ""
    )

    hostel_mobile_ui = """
        <div
            class="hostel-mobile-ui"
        >
            <div
                class="hostel-sidebar-overlay"
                id="sidebarOverlay"
                onclick="toggleSidebar()"
            ></div>

            <header class="mobile-top-header">
                <button
                    class="menu-button"
                    onclick="toggleSidebar()"
                    type="button"
                    aria-label="Open menu"
                >
                    <i class="fa-solid fa-bars"></i>
                </button>

                <div class="mobile-title">
                    Hostel Department
                </div>
            </header>

            <script>
            function toggleSidebar() {
                const sidebar =
                    document.getElementById("sidebar");

                const overlay =
                    document.getElementById("sidebarOverlay");

                if (!sidebar || !overlay) {
                    return;
                }

                sidebar.classList.toggle("open");
                overlay.classList.toggle("open");
            }
            </script>
        </div>
    """

    report_html = f"""
    <!DOCTYPE html>

    <html>

    <head>

        <meta charset="UTF-8">

        <meta
            name="viewport"
            content="width=device-width, initial-scale=1.0"
        >

        <title>Clearance Report</title>

        <style>

        /* HOSTEL STAFF MOBILE NAVIGATION */

        .hostel-mobile-ui {{
            display: block;
        }}

        .hostel-sidebar-overlay {{
            display: none;
        }}

        .mobile-top-header {{
            display: flex;
            position: sticky;
            top: 0;
            align-items: center;
            gap: 12px;
            padding: 13px 16px;
            background: white;
            border-bottom: 1px solid #e5e7eb;
            z-index: 1200;
            box-sizing: border-box;
        }}

        .menu-button {{
            width: 38px;
            height: 38px;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            background: white;
            color: #1e293b;
            font-size: 18px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        .mobile-title {{
            color: #166534;
            font-size: 16px;
            font-weight: 800;
        }}

        /* Hide the mobile header on genuine desktop widths. */
        @media (min-width: 901px) {{

            .hostel-mobile-ui {{
                display: none;
            }}

        }}

        @media (max-width: 900px) {{

            .hostel-mobile-ui {{
                display: block;
            }}

            .hostel-sidebar-overlay.open {{
                display: block;
                position: fixed;
                inset: 0;
                background: rgba(15, 23, 42, .35);
                z-index: 1050;
            }}

            .sidebar {{
                display: flex !important;
                z-index: 1100;
            }}

            .report {{
                max-width: none;
                width: 100%;
                box-sizing: border-box;
                padding: 22px 16px;
            }}
        }}

        @media print {{

            .hostel-mobile-ui,
            .hostel-sidebar-overlay,
            .sidebar {{
                display: none !important;
            }}
        }}


        body {{
            font-family:Arial, Helvetica, sans-serif;
            padding:35px;
            background:white;
            color:#1e293b;
        }}

        .report {{
            max-width:900px;
            margin:auto;
        }}

        h1 {{
            text-align:center;
            color:#166534;
        }}

        .generated {{
            text-align:center;
            color:#64748b;
        }}

        .document {{
            text-align:center;
            color:#2563eb;
            margin:12px 0 35px;
            font-weight:bold;
        }}

        table {{
            width:100%;
            border-collapse:collapse;
            font-size:13px;
            table-layout:fixed;
        }}

        th, td {{
            word-wrap:break-word;
            overflow-wrap:anywhere;
        }}

        th {{
            font-size:12px;
        }}

        td {{
            font-size:13px;
        }}

        @media print {{
            table {{
                font-size:10px;
            }}

            th, td {{
                padding:7px;
            }}

            th {{
                font-size:10px;
            }}

            td {{
                font-size:10px;
            }}
        }}

        th {{
            background:#166534;
            color:white;
            padding:12px;
            text-align:left;
        }}

        td {{
            padding:12px;
            border:1px solid #dbe3ea;
            vertical-align:top;
        }}

        .student-info {{
            margin-bottom:25px;
            line-height:1.8;
        }}

        .footer {{
            text-align:center;
            margin-top:40px;
            padding-top:20px;
            border-top:1px solid #e2e8f0;
            color:#64748b;
            font-size:13px;
        }}

        @media print {{

            body {{
                padding:0;
            }}

            .report {{
                max-width:none;
                width:100%;
            }}

            table {{
                width:100%;
            }}

            .no-print {{
                display:none;
            }}

        }}

        </style>

    </head>

    <body>

        {hostel_mobile_ui if hostel_staff_view else ""}
        {hostel_sidebar_html if hostel_staff_view else ""}


    <div class="report">

        <h1>
            STUDENT CLEARANCE REPORT
        </h1>

        <div class="generated">
            Generated: {generated_time}
        </div>

        <div class="document">
            Document ID: {document_id}
        </div>

        <div class="student-info">

            <strong>Student Name:</strong>
            {s.name}

            <br>

            <strong>Student ID:</strong>
            {s.student_id}

            <br>

            <strong>Program:</strong>
            {s.program}

            <br>

            <strong>Year:</strong>
            {s.year or "N/A"}

        </div>

        <table>

            <tr>

                <th>
                    Department
                </th>

                <th>
                    Name of officer
                </th>

                <th>
                    Remarks
                </th>

                <th>
                    Clearance Status
                </th>

                <th>
                    Date of last cleared transaction
                </th>

            </tr>

            {''.join(rows)}

        </table>

        <div class="footer">

            © 2026 Zambia Air Services Training Institute

            <br>

            All Rights Reserved

        </div>

    </div>

    <script>
        window.print();
    </script>

    </body>

    </html>
    """

    # --------------------------------------------------
    # HOSTEL STAFF NAVIGATION
    # --------------------------------------------------
    if role == "staff" and _hostel_staff_allowed():

        hostel_sidebar_html = render_template(
            "new_staff/hostel/_sidebar.html"
        )

        hostel_mobile_header = """
        <style>
            .hostel-print-mobile-ui {
                display: none;
            }

            @media (max-width: 900px) {

                .hostel-print-mobile-ui {
                    display: block;
                }

                .hostel-print-mobile-header {
                    display: flex;
                    position: sticky;
                    top: 0;
                    align-items: center;
                    gap: 12px;
                    padding: 13px 16px;
                    background: white;
                    border-bottom: 1px solid #e5e7eb;
                    z-index: 1200;
                    box-sizing: border-box;
                }

                .hostel-print-menu-button {
                    width: 38px;
                    height: 38px;
                    border: 1px solid #e5e7eb;
                    border-radius: 8px;
                    background: white;
                    color: #1e293b;
                    font-size: 18px;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }

                .hostel-print-mobile-title {
                    color: #166534;
                    font-size: 16px;
                    font-weight: 800;
                }

                .hostel-print-sidebar-wrap .sidebar {
                    display: flex !important;
                    z-index: 1100 !important;
                }

                .hostel-print-sidebar-wrap .sidebar-overlay {
                    display: block;
                }

                .hostel-print-sidebar-wrap .sidebar-overlay.open {
                    display: block;
                }
            }

            @media (min-width: 901px) {

                .hostel-print-sidebar-wrap .sidebar {
                    display: none !important;
                }

                .hostel-print-mobile-header {
                    display: none !important;
                }
            }

            @media print {

                .hostel-print-mobile-ui,
                .hostel-print-sidebar-wrap {
                    display: none !important;
                }
            }
        </style>

        <div class="hostel-print-mobile-ui">

            <header class="hostel-print-mobile-header">

                <button
                    class="hostel-print-menu-button"
                    onclick="toggleSidebar()"
                    type="button"
                    aria-label="Open menu"
                >
                    <i class="fa-solid fa-bars"></i>
                </button>

                <div class="hostel-print-mobile-title">
                    Hostel Department
                </div>

            </header>

            <script>
            function toggleSidebar() {

                const sidebar =
                    document.getElementById("sidebar");

                if (!sidebar) {
                    return;
                }

                sidebar.classList.toggle("open");

                const overlay =
                    document.getElementById("sidebarOverlay");

                if (overlay) {
                    overlay.classList.toggle("open");
                }
            }
            </script>

        </div>
        """

        sidebar_wrapper = """
        <div class="hostel-print-sidebar-wrap">
        """ + hostel_sidebar_html + """
        </div>
        """

        report_html = report_html.replace(
            "<body>",
            "<body>" + hostel_mobile_header + sidebar_wrapper,
            1
        )

    return report_html



# --------------------------------------------------
# STUDENT CLEARANCE HISTORY
# --------------------------------------------------

# --------------------------------------------------




# --------------------------------------------------
@app.route("/clearance_history")
def clearance_history():

    if session.get("role") != "student":
        return redirect(url_for("student_login"))

    sid = session.get("student_id")

    if not sid:
        return "<h2>No student ID found in session.</h2>", 404

    history = ClearanceHistory.query.filter_by(
        student_id=str(sid)
    ).order_by(
        ClearanceHistory.id.desc()
    ).all()

    return render_template(
        "student/clearance_history.html",
        history=history,
        student_id=sid,
        show_sidebar=True
    )




# ------------------------------------------------------------
# STUDENT DOCUMENT HISTORY
# ------------------------------------------------------------

# ------------------------------------------------------------
# CLEARANCE FORMS — ALL GENERATED FORMS
# ------------------------------------------------------------

@app.route("/clearance_forms")
def clearance_forms():

    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))

    forms = (
        ClearanceHistory.query
        .order_by(ClearanceHistory.id.desc())
        .all()
    )

    students = {}

    for form in forms:

        student = Student.query.filter_by(
            student_id=str(form.student_id)
        ).first()

        students[form.student_id] = student

    return render_template(
        "admin/clearance_forms.html",
        forms=forms,
        students=students
    )
@app.route("/document_history")
def document_history():

    if session.get("role") != "student":
        return redirect(url_for("student_login"))

    sid = session.get("student_id")

    if not sid:
        sid = session.get("user")

    if not sid:
        return "<h2>No student ID found in session.</h2>", 404

    sid = str(sid)

    # --------------------------------------------------
    # CLEARANCE HISTORY
    # --------------------------------------------------

    clearance_history = (
        ClearanceHistory.query
        .filter_by(student_id=sid)
        .order_by(ClearanceHistory.id.desc())
        .all()
    )

    # --------------------------------------------------
    # PAYMENT / ACCOUNTS DOCUMENTS
    # --------------------------------------------------

    payments = (
        Payment.query
        .filter_by(student_id=sid)
        .order_by(Payment.created_at.desc())
        .all()
    )

    # --------------------------------------------------
    # ACCOUNT HISTORY
    # --------------------------------------------------

    account_history = (
        AccountHistory.query
        .filter_by(student_id=sid)
        .order_by(AccountHistory.created_at.desc())
        .all()
    )

    # --------------------------------------------------
    # AGREEMENT HISTORY
    # --------------------------------------------------

    agreement_records = []

    try:
        conn = sqlite3.connect(DATABASE_URL)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agreement_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id VARCHAR(20) NOT NULL,
                agreement_type VARCHAR(100) NOT NULL,
                agreement_version VARCHAR(50),
                accepted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR(30) DEFAULT 'Accepted'
            )
        """)

        cursor.execute("""
            SELECT
                id,
                student_id,
                agreement_type,
                agreement_version,
                accepted_at,
                status
            FROM agreement_history
            WHERE student_id = ?
            ORDER BY accepted_at DESC, id DESC
        """, (sid,))

        agreement_records = cursor.fetchall()

        conn.close()

    except Exception:
        agreement_records = []

    # --------------------------------------------------
    # OTHER DOCUMENTS
    # --------------------------------------------------

    other_documents = []

    try:
        conn = sqlite3.connect(DATABASE_URL)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_archive (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id VARCHAR(20) NOT NULL,
                document_type VARCHAR(50) NOT NULL,
                title VARCHAR(200) NOT NULL,
                filename VARCHAR(255),
                description TEXT,
                uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                source VARCHAR(100)
            )
        """)

        cursor.execute("""
            SELECT
                id,
                student_id,
                document_type,
                title,
                filename,
                description,
                uploaded_at,
                source
            FROM document_archive
            WHERE student_id = ?
            ORDER BY uploaded_at DESC, id DESC
        """, (sid,))

        other_documents = cursor.fetchall()

        conn.close()

    except Exception:
        other_documents = []

    # --------------------------------------------------
    # PAYMENT FILES THAT ARE NOT LINKED TO ARCHIVE
    # ARE STILL SHOWN THROUGH THE ACCOUNTS SECTION.
    # --------------------------------------------------

    return render_template(
        "student/document_history.html",
        history=clearance_history,
        clearance_history=clearance_history,
        payments=payments,
        account_history=account_history,
        agreement_records=agreement_records,
        other_documents=other_documents,
        student_id=sid
    )





# ============================================================
# STUDENT ACCOUNTS DOCUMENTS
# ============================================================


@app.route("/student/other_documents")
def student_other_documents():

    if session.get("role") != "student":
        return redirect(url_for("student_login"))

    sid = session.get("student_id")

    if not sid:
        return redirect(url_for("student_login"))

    other_documents = []

    try:
        conn = sqlite3.connect(DATABASE_URL)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                id,
                student_id,
                document_type,
                title,
                filename,
                description,
                uploaded_at,
                source
            FROM document_archive
            WHERE student_id = ?
            ORDER BY uploaded_at DESC, id DESC
        """, (sid,))

        other_documents = cursor.fetchall()

        conn.close()

    except Exception:
        other_documents = []

    return render_template(
        "student/other_documents.html",
        other_documents=other_documents,
        student_id=sid
    )


@app.route("/student/other_documents/<int:document_id>")
def student_other_document(document_id):

    if session.get("role") != "student":
        return redirect(url_for("student_login"))

    sid = session.get("student_id")

    if not sid:
        return redirect(url_for("student_login"))

    try:
        conn = sqlite3.connect(DATABASE_URL)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                id,
                student_id,
                document_type,
                title,
                filename
            FROM document_archive
            WHERE id = ?
              AND student_id = ?
        """, (document_id, sid))

        document = cursor.fetchone()

        conn.close()

    except Exception:
        document = None

    if not document:
        return "DOCUMENT_UNAVAILABLE", 404

    filename = document["filename"]

    if not filename:
        return "DOCUMENT_UNAVAILABLE", 404

    return redirect(
        url_for(
            "static",
            filename=filename
        )
    )


@app.route("/student/accounts_documents")
def student_accounts_documents():

    if session.get("role") != "student":
        return redirect(url_for("student_login"))

    sid = session.get("student_id")

    if not sid:
        sid = session.get("user")

    if not sid:
        return "<h3>No student ID found in session.</h3>", 404

    student = Student.query.filter_by(
        student_id=str(sid)
    ).first()

    if not student:
        return f"""
        <h3>Student not found</h3>
        <p>Student ID: {sid}</p>
        """, 404

    payments = Payment.query.filter_by(
        student_id=student.student_id
    ).order_by(
        Payment.id.desc()
    ).all()

    return render_template(
        "student/accounts_documents.html",
        student=student,
        payments=payments
    )


@app.route("/student/payment/<int:payment_id>/document")
def student_payment_document(payment_id):

    # --------------------------------------------------
    # ACCESS CONTROL
    #
    # 1. The student who owns the payment may view it.
    # 2. Accounts staff may view payment proofs for
    #    verification.
    # 3. Everyone else is denied.
    # --------------------------------------------------

    role = session.get("role")

    if role not in {"student", "staff"}:
        return redirect(url_for("student_login"))

    # --------------------------------------------------
    # GET PAYMENT RECORD
    # --------------------------------------------------

    payment = Payment.query.get(payment_id)

    if not payment:
        return "Payment document not found or access denied.", 404

    # --------------------------------------------------
    # STUDENT ACCESS
    #
    # Students may ONLY view their own payment document.
    # --------------------------------------------------

    if role == "student":

        sid = session.get("student_id")

        if not sid:
            sid = session.get("user")

        if not sid:
            return "No student ID found in session.", 404

        sid = str(sid)

        if str(payment.student_id) != sid:
            return "Payment document not found or access denied.", 404

    # --------------------------------------------------
    # STAFF ACCESS
    #
    # Only Accounts staff may view payment proofs.
    # --------------------------------------------------

    elif role == "staff":

        department = (
            session.get("department") or ""
        ).strip().lower()

        if department not in {
            "accounts",
            "accounts department"
        }:
            return "Payment document not found or access denied.", 404

    # --------------------------------------------------
    # DOCUMENT CHECK
    # --------------------------------------------------

    if not payment.file:
        return "No payment document is attached to this record.", 404

    from flask import send_from_directory
    from config import DOCUMENTS_FOLDER

    filepath = os.path.join(
        DOCUMENTS_FOLDER,
        payment.file
    )

    if not os.path.isfile(filepath):
        return """
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >

    <title>Document Unavailable</title>

    <style>

        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
            font-family: Arial, Helvetica, sans-serif;
            background: #f8fafc;
            color: #1e293b;
        }

        .notice-card {
            width: 100%;
            max-width: 520px;
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 16px;
            padding: 32px 26px;
            text-align: center;
            box-shadow: 0 4px 18px rgba(0,0,0,.07);
        }

        .notice-icon {
            width: 58px;
            height: 58px;
            margin: 0 auto 18px;
            border-radius: 50%;
            background: #fff7ed;
            color: #c2410c;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .notice-icon svg {
            width: 28px;
            height: 28px;
        }

        h1 {
            margin: 0 0 10px;
            color: #166534;
            font-size: 23px;
        }

        .message {
            margin: 0 auto;
            max-width: 430px;
            color: #64748b;
            font-size: 15px;
            line-height: 1.7;
        }

        .assistance {
            margin-top: 20px;
            padding: 14px 16px;
            background: #eff6ff;
            border: 1px solid #bfdbfe;
            border-radius: 10px;
            color: #1e40af;
            font-size: 14px;
            line-height: 1.6;
        }

        .back-button {
            display: inline-block;
            margin-top: 22px;
            padding: 11px 18px;
            border-radius: 9px;
            background: #166534;
            color: white;
            text-decoration: none;
            font-size: 14px;
            font-weight: 700;
        }

        .back-button:hover {
            background: #14532d;
        }

    </style>
</head>

<body>

    <div class="notice-card">

        <div class="notice-icon">

            <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
            >
                <circle cx="12" cy="12" r="9"></circle>
                <path d="M12 8v4"></path>
                <path d="M12 16h.01"></path>
            </svg>

        </div>

        <h1>Document Unavailable</h1>

        <p class="message">
            This document is currently unavailable.
            Some account documents may not be accessible
            at the moment.
        </p>

        <div class="assistance">
            Please visit the <strong>Accounts Department</strong>
            for assistance or verification of your document.
        </div>

        <a
            href="/document_history"
            class="back-button"
        >
            Back to Document History
        </a>

    </div>

</body>

</html>
""", 404

    return send_from_directory(
        DOCUMENTS_FOLDER,
        payment.file
    )


@app.route("/student/document/<path:filename>")
def serve_student_document(filename):

    if session.get("role") != "student":
        return redirect(url_for("student_login"))

    sid = session.get("student_id")

    if not sid:
        sid = session.get("user")

    if not sid:
        return "No student ID found in session.", 404

    sid = str(sid)

    # --------------------------------------------------
    # ONLY ALLOW DOCUMENTS BELONGING TO THIS STUDENT
    # --------------------------------------------------

    conn = sqlite3.connect(DATABASE_URL)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT filename
        FROM document_archive
        WHERE student_id = ?
        AND filename = ?
        LIMIT 1
    """, (sid, filename))

    row = cursor.fetchone()

    conn.close()

    if not row:
        return "Document not found or access denied.", 404

    from flask import send_from_directory
    from config import DOCUMENTS_FOLDER

    return send_from_directory(
        DOCUMENTS_FOLDER,
        filename
    )


@app.route("/department_history")
def department_history():

    if session.get("role") != "student":
        return redirect(url_for("student_login"))

    sid = session.get("student_id")

    if not sid:
        return "<h2>No student ID found in session.</h2>", 404

    # ------------------------------------------------------------
    # DEPARTMENT HISTORY NAME NORMALIZATION
    # ------------------------------------------------------------
    # The sidebar uses the official/display department names,
    # while DepartmentHistory stores some internal names.
    #
    # In particular:
    #
    # Sidebar:
    #     Head of Training Section
    #
    # Database:
    #     training
    #
    # Convert the display name to the value actually stored
    # in DepartmentHistory before querying.
    # ------------------------------------------------------------

    requested_department = request.args.get("department", "").strip()

    department_aliases = {
        "Head of Training Section": "Training Section",
        "Training Section": "Training Section",
        "Training": "Training Section",
        "training_section": "Training Section",
        "training": "Training Section",
    }

    department = department_aliases.get(
        requested_department,
        requested_department
    )

    # ------------------------------------------------------------
    # LOAD THE STUDENT'S HISTORY FOR THIS DEPARTMENT
    # ------------------------------------------------------------

    history = (
        DepartmentHistory.query
        .filter_by(
            student_id=sid,
            department=department
        )
        .order_by(
            DepartmentHistory.id.desc()
        )
        .all()
    )

    # ------------------------------------------------------------
    # DISPLAY NAME
    # ------------------------------------------------------------
    # Keep the database value unchanged, but show the proper
    # department name on the page.
    # ------------------------------------------------------------

    display_department = requested_department or department

    if department == "Training Section":
        display_department = "Training Section"

    return render_template(
        "student/department_history.html",
        history=history,
        department=display_department,
        student_id=sid,
        show_sidebar=True
    )




# ============================================================
# STUDENT DEPARTMENT HISTORIES — SINGLE UNIFIED ROUTE
# ============================================================

@app.route(
    "/student/history/<department_slug>",
    endpoint="student_department_history_page"
)
@app.route(
    "/student/history/<department>",
    endpoint="student_department_history"
)
def student_department_history_page(department_slug=None, department=None):
    if session.get("role") != "student":
        return redirect(url_for("student_login"))

    sid = str(
        session.get("student_id") or session.get("user") or ""
    ).strip()

    if not sid:
        return redirect(url_for("student_login"))

    slug = str(department_slug or department or "")
    slug = slug.strip().lower().replace("_", "-")

    departments = {
        "library": (
            "Library",
            ["Library"],
        ),
        "sports": (
            "Sports",
            ["Sports"],
        ),
        "ame-stores": (
            "AME Stores",
            ["AME Stores", "AME Store", "AME Stores Office"],
        ),
        "stores": (
            "Stores",
            ["Stores", "Stores Officer", "Stores Office"],
        ),
        "hostel": (
            "Hostel",
            ["Hostel"],
        ),
        "accounts": (
            "Accounts",
            ["Accounts", "Account"],
        ),
        "communication-skills": (
            "Communication Skills",
            [
                "Communication Skills",
                "Communication Skills (REL/SC)",
                "Communication Skills (REL SC)",
            ],
        ),
        "mathematics": (
            "Mathematics",
            ["Mathematics", "Maths"],
        ),
        "human-resource": (
            "Human Resource",
            [
                "Human Resource",
                "Human Resources",
                "Human Resources/Admin Officer",
                "Human Resource / Admin Officer",
            ],
        ),
        "training-section": (
            "Training Section",
            [
                "Training",
                "Training Section",
                "Head of Training Section",
            ],
        ),
        "tso": (
            "TSO",
            [
                "TSO",
                "Technical Services Office",
                "Technical Services Office (TSO)",
            ],
        ),
    }

    if slug not in departments:
        return "History department not found.", 404

    display_name, aliases = departments[slug]

    def normalize(value):
        return re.sub(
            r"[^a-z0-9]+",
            " ",
            str(value or "").strip().lower(),
        ).strip()

    accepted_names = {normalize(name) for name in aliases}
    history = []

    def add_record(
        when=None,
        status="",
        action="",
        remarks="",
        performed_by="",
        item="",
        record_department=None,
    ):
        history.append({
            "created_at": when,
            "status": status or "Recorded",
            "action": action or "",
            "remarks": remarks or "",
            "performed_by": performed_by or "",
            "item": item or "",
            "department": record_department or display_name,
        })

    # 1. Load the shared department decision/audit history.
    try:
        records = DepartmentHistory.query.filter_by(
            student_id=sid
        ).all()

        for record in records:
            if normalize(getattr(record, "department", "")) not in accepted_names:
                continue

            add_record(
                when=getattr(record, "created_at", None),
                status=getattr(record, "status", ""),
                action=getattr(record, "action", ""),
                remarks=getattr(record, "remarks", ""),
                performed_by=getattr(record, "performed_by", ""),
                item=getattr(record, "item", ""),
                record_department=getattr(
                    record, "department", display_name
                ),
            )
    except Exception:
        app.logger.exception(
            "Could not load DepartmentHistory for student %s, department %s",
            sid, slug
        )

    # 2. Load each department's own records.
    # Separate error handling ensures one table cannot block another source.
    try:
        if slug == "library":
            records = LibraryBook.query.filter_by(student_id=sid).all()

            for r in records:
                returned = bool(getattr(r, "returned", False))
                book_name = getattr(r, "name", "") or "Library book"

                expected_action = "book returned" if returned else "book assigned"
                audit_records = DepartmentHistory.query.filter_by(
                    student_id=sid
                ).all()

                staff_name = next(
                    (
                        getattr(a, "performed_by", "")
                        for a in reversed(audit_records)
                        if normalize(getattr(a, "department", "")) == "library"
                        and normalize(getattr(a, "action", "")) == normalize(expected_action)
                        and book_name.lower() in str(
                            getattr(a, "remarks", "") or ""
                        ).lower()
                        and getattr(a, "performed_by", "")
                    ),
                    "",
                )

                add_record(
                    when=getattr(r, "returned_at", None)
                         or getattr(r, "borrowed_at", None)
                         or getattr(r, "created_at", None),
                    status="Returned" if returned else "Borrowed",
                    action="Book returned" if returned else "Book borrowed",
                    item=book_name,
                    remarks=getattr(r, "remarks", "") or
                            ("Book: " + str(book_name)),
                    performed_by=staff_name,
                )

        elif slug == "sports":
            records = SportsItem.query.filter_by(student_id=sid).all()

            for r in records:
                add_record(
                    when=getattr(r, "responded_at", None)
                         or getattr(r, "created_at", None),
                    status=getattr(r, "status", ""),
                    action=getattr(r, "sport", "") or "Sports item",
                    item=getattr(r, "item", ""),
                    remarks=getattr(r, "remarks", ""),
                    performed_by=(
                        getattr(r, "responded_by", "")
                        or (
                            str(getattr(r, "remarks", "")).split(" by ", 1)[1].rstrip(".")
                            if " by " in str(getattr(r, "remarks", "")).lower()
                            and " by " in str(getattr(r, "remarks", ""))
                            else ""
                        )
                    ),
                )

        elif slug == "ame-stores":
            records = AMETool.query.filter_by(student_id=sid).all()

            for r in records:
                returned = bool(getattr(r, "returned", False))

                add_record(
                    when=getattr(r, "returned_at", None)
                         or getattr(r, "issued_at", None)
                         or getattr(r, "created_at", None),
                    status="Returned" if returned else "Issued",
                    action="Tool returned" if returned else "Tool issued",
                    item=getattr(r, "name", "") or "AME tool",
                    remarks=getattr(r, "remarks", ""),
                    performed_by=getattr(r, "returned_by", "")
                                  or getattr(r, "issued_by", ""),
                )

        elif slug == "stores":
            records = StoreProperty.query.filter_by(
                student_id=sid
            ).all()

            for r in records:
                add_record(
                    when=getattr(r, "returned_at", None)
                         or getattr(r, "issued_at", None)
                         or getattr(r, "created_at", None),
                    status=getattr(r, "status", ""),
                    action=getattr(r, "name", "") or "Store property",
                    item=getattr(r, "name", ""),
                    remarks=getattr(r, "remarks", ""),
                    performed_by=getattr(r, "returned_by", "")
                                  or getattr(r, "issued_by", ""),
                )

        elif slug == "hostel":
            assignments = (
                AccommodationAssignment.query
                .filter_by(student_id=sid)
                .order_by(
                    AccommodationAssignment.assigned_at.desc(),
                    AccommodationAssignment.id.desc()
                )
                .all()
            )

            for assignment in assignments:
                room = db.session.get(HostelRoom, assignment.room_id)
                if not room:
                    continue

                hostel = db.session.get(Hostel, room.hostel_id)
                parts = [
                    getattr(hostel, "name", None) or "Hostel"
                ]

                if getattr(room, "block_id", None):
                    block = db.session.get(HostelBlock, room.block_id)
                    if block and getattr(block, "name", None):
                        parts.append(block.name)

                if getattr(room, "section_id", None):
                    section = db.session.get(HostelSection, room.section_id)
                    if section and getattr(section, "name", None):
                        parts.append(section.name)

                room_number = getattr(room, "room_number", None) or "Not recorded"
                parts.append(f"Room {room_number}")
                location = " - ".join(str(p) for p in parts if p)

                add_record(
                    when=assignment.assigned_at,
                    status="Assigned",
                    action="Room assigned",
                    item=location,
                    remarks="Accommodation assigned",
                    performed_by=getattr(assignment, "assigned_by", None) or "",
                )

                if assignment.vacated_at:
                    add_record(
                        when=assignment.vacated_at,
                        status="Vacated",
                        action="Room vacated",
                        item=location,
                        remarks="Accommodation vacated",
                        performed_by=getattr(assignment, "vacated_by", None) or "",
                    )

        elif slug == "tso":
            inspection_model = globals().get("TSOInspection")
            room_model = globals().get("HostelRoom")

            if inspection_model is None:
                raise RuntimeError("TSOInspection model is not available")

            records = inspection_model.query.filter_by(
                student_id=sid
            ).all()

            for r in records:
                room_label = "Room not recorded"
                room_id = getattr(r, "room_id", None)

                if room_id and room_model is not None:
                    room = room_model.query.get(room_id)
                    if room:
                        room_label = "Room " + str(
                            getattr(room, "room_number", room_id)
                        )
                elif room_id:
                    room_label = "Room ID " + str(room_id)

                key_name = getattr(r, "key_name", "")
                if getattr(r, "key_collected", False):
                    item_label = room_label + " - Key collected"
                    if key_name:
                        item_label += ": " + str(key_name)
                else:
                    item_label = room_label

                checklist = []
                for field, label in [
                    ("electrical_outlets", "Electrical outlets"),
                    ("lights", "Lights"),
                    ("switches", "Switches"),
                    ("wiring", "Wiring"),
                    ("ventilation", "Ventilation"),
                    ("door_lock", "Door lock"),
                    ("windows", "Windows"),
                    ("plumbing", "Plumbing"),
                    ("furniture", "Furniture"),
                    ("general_condition", "General condition"),
                    ("other", "Other"),
                ]:
                    value = getattr(r, field, None)
                    if value:
                        checklist.append(label + ": " + str(value))

                remarks = checklist
                extra_remarks = getattr(r, "remarks", "")
                if extra_remarks:
                    remarks.append("Remarks: " + str(extra_remarks))

                add_record(
                    when=getattr(r, "inspected_at", None),
                    status=getattr(r, "status", ""),
                    action="Accommodation inspection",
                    item=item_label,
                    remarks="; ".join(remarks),
                    performed_by=getattr(r, "inspected_by", ""),
                )

        elif slug == "human-resource":
            case_model = globals().get("DisciplinaryCase")

            if case_model is None:
                raise RuntimeError("DisciplinaryCase model is not available")

            records = case_model.query.filter_by(
                student_id=sid
            ).all()

            for case in records:
                offence = getattr(case, "offence", "") or "Disciplinary case"
                offence_details = []

                offence_date = getattr(case, "offence_date", None)
                location = getattr(case, "location", "")
                description = getattr(case, "description", "")

                if offence_date:
                    offence_details.append("Offence date: " + str(offence_date))
                if location:
                    offence_details.append("Location: " + str(location))
                if description:
                    offence_details.append(str(description))

                current_status = getattr(case, "status", "")
                if current_status:
                    offence_details.append("Current case status: " + str(current_status))

                add_record(
                    when=getattr(case, "reported_at", None),
                    status="Reported",
                    action="Disciplinary case reported",
                    item=offence,
                    remarks="; ".join(offence_details),
                    performed_by=getattr(case, "reported_by", ""),
                )

                response = getattr(case, "student_response", "")
                if response:
                    add_record(
                        when=getattr(case, "response_at", None),
                        status="Response recorded",
                        action="Student response recorded",
                        item=offence,
                        remarks=response,
                    )

                decision = getattr(case, "committee_decision", "")
                if decision:
                    add_record(
                        when=getattr(case, "decision_date", None),
                        status="Decision recorded",
                        action="Committee decision",
                        item=offence,
                        remarks=decision,
                        performed_by=getattr(case, "decided_by", ""),
                    )

                sanction = getattr(case, "sanction", "")
                if sanction:
                    sanction_details = [
                        str(sanction),
                        str(getattr(case, "sanction_details", "") or ""),
                        "Sanction status: " + str(
                            getattr(case, "sanction_status", "") or "Not specified"
                        ),
                    ]

                    sanction_start = getattr(case, "sanction_start", None)
                    sanction_end = getattr(case, "sanction_end", None)

                    if sanction_start:
                        sanction_details.append("Start: " + str(sanction_start))
                    if sanction_end:
                        sanction_details.append("End: " + str(sanction_end))

                    add_record(
                        when=getattr(case, "decision_date", None),
                        status=getattr(case, "sanction_status", "") or "Recorded",
                        action="Disciplinary sanction",
                        item=offence,
                        remarks="; ".join(v for v in sanction_details if v),
                        performed_by=getattr(case, "decided_by", ""),
                    )

                resolution = getattr(case, "resolution", "")
                if resolution:
                    resolution_details = [str(resolution)]
                    final_remarks = getattr(case, "remarks", "")
                    if final_remarks:
                        resolution_details.append(str(final_remarks))

                    add_record(
                        when=getattr(case, "resolved_at", None),
                        status="Resolved",
                        action="Case resolution",
                        item=offence,
                        remarks="; ".join(resolution_details),
                        performed_by=getattr(case, "resolved_by", ""),
                    )

        # MISSING_DEPARTMENT_HISTORY_LOADERS
        elif slug in (
            "communication-skills",
            "mathematics",
            "training-section",
            "head-of-training-section",
        ):
            model_name = {
                "communication-skills": "CommunicationProperty",
                "mathematics": "MathematicsProperty",
                "training-section": "TrainingSectionProperty",
                "head-of-training-section": "TrainingSectionProperty",
            }.get(slug)

            model = globals().get(model_name) if model_name else None

            if model:
                records = model.query.filter_by(student_id=sid).all()

                for r in records:
                    returned_at = getattr(r, "returned_at", None)
                    issued_at = getattr(r, "issued_at", None)
                    current_status = getattr(r, "status", "") or ""

                    is_returned = bool(returned_at) or str(
                        current_status
                    ).strip().lower() == "returned"

                    add_record(
                        when=returned_at or issued_at or getattr(r, "created_at", None),
                        status="Returned" if is_returned else current_status or "Issued",
                        action="Property returned" if is_returned else "Property issued",
                        item=getattr(r, "name", "") or "Department property",
                        remarks=getattr(r, "remarks", ""),
                        performed_by=(
                            getattr(r, "returned_by", "")
                            or getattr(r, "issued_by", "")
                        ),
                    )

        elif slug == "accounts":
            records = AccountHistory.query.filter_by(
                student_id=sid
            ).all()

            for r in records:
                details = [
                    getattr(r, "reason", ""),
                    getattr(r, "remarks", ""),
                ]

                amount = getattr(r, "amount", None)
                if amount is not None:
                    details.append("Amount: " + str(amount))

                add_record(
                    when=getattr(r, "created_at", None),
                    status=getattr(r, "status", ""),
                    action=getattr(r, "action", "") or "Account update",
                    remarks="; ".join(str(v) for v in details if v),
                    performed_by=getattr(r, "performed_by", ""),
                )

    except Exception:
        app.logger.exception(
            "Could not load department-specific history for student %s, department %s",
            sid, slug
        )

    # 3. Remove duplicate records, preserving staff attribution.
    unique = {}

    for row in history:
        key = (
            str(row.get("created_at") or ""),
            normalize(row.get("status")),
            normalize(row.get("action")),
            normalize(row.get("item")),
            normalize(row.get("remarks")),
        )

        existing = unique.get(key)

        if existing is None:
            unique[key] = row
        elif not existing.get("performed_by") and row.get("performed_by"):
            existing["performed_by"] = row["performed_by"]

    history = list(unique.values())

    history.sort(
        key=lambda row: str(row.get("created_at") or ""),
        reverse=True,
    )

    return render_template(
        "student/department_history.html",
        history=history,
        department_name=display_name,
    )


@app.route("/terms", methods=["GET", "POST"])
def terms():

    if session.get("role") != "student":
        return redirect(url_for("student_login"))

    current_user = User.query.get(session.get("user_id"))
    if current_user and current_user.password_change_required:
        return redirect(url_for("reset_password"))

    # --------------------------------------------------
    # IDENTIFY STUDENT
    # --------------------------------------------------

    sid = session.get("student_id")

    if not sid:
        sid = session.get("user")

    if not sid:
        return "<h3>No student ID found in session.</h3>", 404

    # --------------------------------------------------
    # POST = ACCEPT TERMS
    # --------------------------------------------------

    if request.method == "POST":

        if request.form.get("agree") != "yes":
            flash(
                "You must agree to the Terms & Conditions before continuing.",
                "warning"
            )
            return redirect(url_for("terms"))

        # --------------------------------------------------
        # SESSION RECORD
        # --------------------------------------------------

        session["accepted_terms"] = True
        session.modified = True

        # --------------------------------------------------
        # PERMANENT AGREEMENT HISTORY
        # --------------------------------------------------

        try:

            conn = sqlite3.connect(DATABASE_URL)
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agreement_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id VARCHAR(20) NOT NULL,
                    agreement_type VARCHAR(100) NOT NULL,
                    agreement_version VARCHAR(50),
                    accepted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    status VARCHAR(30) DEFAULT 'Accepted'
                )
            """)

            cursor.execute("""
                INSERT INTO agreement_history
                (
                    student_id,
                    agreement_type,
                    agreement_version,
                    accepted_at,
                    status
                )
                VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?)
            """, (
                str(sid),
                "Terms & Conditions",
                "1.0",
                "Accepted"
            ))

            conn.commit()
            conn.close()

        except Exception as e:

            print("=" * 80)
            print("AGREEMENT HISTORY ERROR")
            print("=" * 80)
            print(e)
            print("=" * 80)

        # --------------------------------------------------
        # FIND STUDENT DASHBOARD AUTOMATICALLY
        # --------------------------------------------------

        dashboard_endpoint = None

        preferred_endpoints = [
            "student_dashboard",
            "student_home",
            "student_dashboard_home",
            "dashboard"
        ]

        for endpoint in preferred_endpoints:

            if endpoint in app.view_functions:
                dashboard_endpoint = endpoint
                break

        # --------------------------------------------------
        # FALLBACK:
        # LOOK FOR ANY STUDENT/DASHBOARD ENDPOINT
        # --------------------------------------------------

        if dashboard_endpoint is None:

            for endpoint in app.view_functions:

                name = endpoint.lower()

                if (
                    "student" in name
                    and "dashboard" in name
                ):
                    dashboard_endpoint = endpoint
                    break

        # --------------------------------------------------
        # REDIRECT TO DASHBOARD
        # --------------------------------------------------

        if dashboard_endpoint:

            print()
            print("=" * 80)
            print("TERMS ACCEPTED")
            print("STUDENT:", sid)
            print("REDIRECTING TO:", dashboard_endpoint)
            print("=" * 80)

            return redirect(
                url_for(dashboard_endpoint)
            )

        # --------------------------------------------------
        # SAFETY FALLBACK
        # --------------------------------------------------

        print()
        print("=" * 80)
        print("WARNING: STUDENT DASHBOARD ENDPOINT NOT FOUND")
        print("AVAILABLE ENDPOINTS:")
        print(list(app.view_functions.keys()))
        print("=" * 80)

        return redirect(url_for("home"))

    # --------------------------------------------------
    # GET = SHOW TERMS PAGE
    # --------------------------------------------------

    # Load current penalty fee from system settings
    penalty_fee = 0
    try:
        conn = sqlite3.connect(DATABASE_URL)
        conn.row_factory = sqlite3.Row

        row = conn.execute(
            "SELECT setting_value FROM system_settings WHERE setting_key = ?",
            ("penalty_fee",)
        ).fetchone()

        if row and row["setting_value"] is not None:
            penalty_fee = row["setting_value"]

        conn.close()
    except Exception:
        penalty_fee = 0

    return render_template(
        "student/terms.html",
        penalty_fee=penalty_fee
    )



# ============================================================
# LIBRARY BOOK CONFIRMATION
# ============================================================

@app.route("/student/library/book/<int:book_id>/confirm", methods=["POST"])
def confirm_library_book(book_id):

    if session.get("role") != "student":
        return redirect(url_for("student_login"))

    student_id = session.get("student_id")

    if not student_id:
        return redirect(url_for("student_login"))

    import sqlite3
    from datetime import datetime

    con = sqlite3.connect("database.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    book = cur.execute(
        """
        SELECT *
        FROM library_books
        WHERE id = ?
          AND student_id = ?
        LIMIT 1
        """,
        (book_id, student_id)
    ).fetchone()

    if not book:
        con.close()

        flash(
            "Library book request not found.",
            "error"
        )

        return redirect(url_for("student_dashboard"))

    if (book["status"] or "").lower() != "pending":
        con.close()

        flash(
            "This library book request has already been processed.",
            "error"
        )

        return redirect(url_for("student_dashboard"))

    active_count = cur.execute(
        """
        SELECT COUNT(*)
        FROM library_books
        WHERE student_id = ?
          AND COALESCE(status, '') = 'borrowed'
          AND COALESCE(returned, 0) = 0
        """,
        (student_id,)
    ).fetchone()[0]

    if active_count >= 2:
        con.close()

        flash(
            "You already have the maximum of 2 borrowed books.",
            "error"
        )

        return redirect(url_for("student_dashboard"))

    borrowed_at = zambia_now().strftime(
        "%d %B %Y | %I:%M %p"
    )

    cur.execute(
        """
        UPDATE library_books
        SET
            status = 'borrowed',
            borrowed_at = ?,
            returned = 0,
            returned_at = NULL
        WHERE id = ?
          AND student_id = ?
          AND COALESCE(status, '') = 'pending'
        """,
        (
            borrowed_at,
            book_id,
            student_id
        )
    )

    con.commit()
    con.close()

    flash(
        f"You confirmed '{book['name']}'. "
        "The book is now recorded as borrowed.",
        "success"
    )

    return redirect(url_for("student_dashboard"))


# ============================================================
# DECLINE LIBRARY BOOK ASSIGNMENT
# ============================================================

@app.route("/student/library/book/<int:book_id>/decline", methods=["POST"])
def decline_library_book(book_id):

    if session.get("role") != "student":
        return redirect(url_for("student_login"))

    student_id = session.get("student_id")

    if not student_id:
        return redirect(url_for("student_login"))

    import sqlite3

    con = sqlite3.connect("database.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    book = cur.execute(
        """
        SELECT *
        FROM library_books
        WHERE id = ?
          AND student_id = ?
        LIMIT 1
        """,
        (book_id, student_id)
    ).fetchone()

    if not book:
        con.close()

        flash(
            "Library book request not found.",
            "error"
        )

        return redirect(url_for("student_dashboard"))

    if (book["status"] or "").lower() != "pending":
        con.close()

        flash(
            "This library book request has already been processed.",
            "error"
        )

        return redirect(url_for("student_dashboard"))

    cur.execute(
        """
        UPDATE library_books
        SET
            status = 'declined',
            returned = 1
        WHERE id = ?
          AND student_id = ?
          AND COALESCE(status, '') = 'pending'
        """,
        (
            book_id,
            student_id
        )
    )

    con.commit()
    con.close()

    flash(
        f"You declined the book assignment '{book['name']}'.",
        "success"
    )

    return redirect(url_for("student_dashboard"))


@app.route("/student/item/<int:item_id>/decline", methods=["POST"])
def decline_item(item_id):

    if session.get("role") != "student":
        return redirect(
            url_for("student_login")
        )

    student_id = session.get("student_id")

    item_request = ItemRequest.query.filter_by(
        id=item_id,
        student_id=student_id
    ).first()

    if not item_request:
        flash(
            "Item request not found.",
            "error"
        )
        return redirect(
            url_for("student_dashboard")
        )

    if item_request.status != "Pending":
        flash(
            "This item request has already been responded to.",
            "error"
        )
        return redirect(
            url_for("student_dashboard")
        )

    # --------------------------------------------------------
    # RECORD STUDENT RESPONSE
    # --------------------------------------------------------

    response_time = zambia_now()

    item_request.status = "Declined"
    item_request.responded_at = response_time

    # --------------------------------------------------------
    # UNIVERSAL DEPARTMENT HISTORY
    # --------------------------------------------------------

    history = DepartmentHistory(
        student_id=student_id,
        department=item_request.department,
        status="Declined",
        remarks=(
            f"Item: {item_request.item} | "
            f"Student declined this request. | "
            f"Requested by: "
            f"{item_request.assigned_by or 'Staff'} | "
            f"Request created: "
            f"{item_request.assigned_at.strftime('%d %b %Y %H:%M:%S')}"
            if item_request.assigned_at
            else (
                f"Item: {item_request.item} | "
                f"Student declined this request. | "
                f"Requested by: "
                f"{item_request.assigned_by or 'Staff'}"
            )
        ),
        action="Item Request Declined",
        performed_by=(
            item_request.assigned_by or "Staff"
        )
    )

    db.session.add(history)

    # --------------------------------------------------------
    # PROPERTY RECORD HISTORY
    #
    # Pending requests are not property records.
    # Accepted requests become Issued property records.
    # Declined requests become Declined property records.
    #
    # Stores and Sports are intentionally excluded.
    # Library uses its own library_books system.
    # --------------------------------------------------------

    if item_request.item_type == "Institutional Property":

        request_department = (
            item_request.department or ""
        ).strip().lower()

        # COMMUNICATION SKILLS
        if request_department in {
            "communication skills (rel/sc)",
            "communication skills (rel sc)",
            "communication skills",
        }:

            existing_property = CommunicationProperty.query.filter_by(
                request_id=item_request.id
            ).first()

            if not existing_property:
                property_record = CommunicationProperty(
                    request_id=item_request.id,
                    student_id=student_id,
                    name=item_request.item,
                    status="Declined",
                    issued_by=(
                        item_request.assigned_by
                        or "Communication Skills Staff"
                    ),
                    issued_at=None,
                    returned_by=None,
                    returned_at=None,
                    remarks=(
                        f"Declined by student. "
                        f"Requested by "
                        f"{item_request.assigned_by or 'Staff'} "
                        f"from {item_request.department}."
                    )
                )

                db.session.add(property_record)

        # MATHEMATICS
        elif request_department in {
            "mathematics",
            "mathematics department",
        }:

            existing_property = MathematicsProperty.query.filter_by(
                request_id=item_request.id
            ).first()

            if not existing_property:
                property_record = MathematicsProperty(
                    request_id=item_request.id,
                    student_id=student_id,
                    name=item_request.item,
                    status="Declined",
                    issued_by=(
                        item_request.assigned_by
                        or "Mathematics Staff"
                    ),
                    issued_at=None,
                    returned_by=None,
                    returned_at=None,
                    remarks=(
                        f"Declined by student. "
                        f"Requested by "
                        f"{item_request.assigned_by or 'Staff'} "
                        f"from {item_request.department}."
                    )
                )

                db.session.add(property_record)

        # TRAINING SECTION
        elif request_department == "training section":

            existing_property = TrainingSectionProperty.query.filter_by(
                request_id=item_request.id
            ).first()

            if not existing_property:
                property_record = TrainingSectionProperty(
                    request_id=item_request.id,
                    student_id=student_id,
                    name=item_request.item,
                    status="Declined",
                    issued_by=(
                        item_request.assigned_by
                        or "Training Section Staff"
                    ),
                    issued_at=None,
                    returned_by=None,
                    returned_at=None,
                    remarks=(
                        f"Declined by student. "
                        f"Requested by "
                        f"{item_request.assigned_by or 'Staff'} "
                        f"from Training Section."
                    )
                )

                db.session.add(property_record)

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    db.session.commit()

    flash(
        f"{item_request.item} declined.",
        "success"
    )

    return redirect(
        url_for("student_dashboard")
    )


@app.route(
    "/admin/staff",
    methods=["GET", "POST"]
)
def admin_staff():

    if session.get("role") != "admin":
        return redirect(
            url_for("admin_login")
        )

    # --------------------------------------------------
    # DEPARTMENTS
    # --------------------------------------------------

    departments = [
        "Library",
        "Sports",
        "Accounts",
        "Communication Skills (REL/SC)",
        "Mathematics",
        "Human Resource / Admin Officer",
        "Training Section",
        "AME Stores",
        "Stores Office",
        "Technical Services Office",
        "Hostel"
    ]

    # --------------------------------------------------
    # REGISTER STAFF
    # --------------------------------------------------

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        requested_staff_id = request.form.get(
            "staff_id",
            ""
        ).strip()

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        department = request.form.get(
            "department",
            ""
        ).strip()

        if not name or not username or not password or not department:

            flash(
                "All required staff fields must be completed.",
                "error"
            )

            return redirect(
                url_for("admin_staff")
            )

        # Check username

        existing_user = User.query.filter_by(
            username=username
        ).first()

        if existing_user:

            flash(
                "That username is already in use.",
                "error"
            )

            return redirect(
                url_for("admin_staff")
            )

        # --------------------------------------------------
        # STAFF ID
        # --------------------------------------------------

        if requested_staff_id:

            existing_staff = Staff.query.filter_by(
                staff_id=requested_staff_id
            ).first()

            if existing_staff:

                flash(
                    "That Staff ID is already in use.",
                    "error"
                )

                return redirect(
                    url_for("admin_staff")
                )

            staff_id = requested_staff_id

        else:

            number = Staff.query.count() + 1

            staff_id = f"ZASTI-STF-{number:04d}"

            # Protect against deleted/reused IDs

            while Staff.query.filter_by(
                staff_id=staff_id
            ).first():

                number += 1

                staff_id = f"ZASTI-STF-{number:04d}"

        # --------------------------------------------------
        # CREATE USER
        # --------------------------------------------------

        from werkzeug.security import generate_password_hash

        user = User(
            username=username,
            password=generate_password_hash(password),
            password_change_required=True,
            role="staff",
            department=department
        )

        db.session.add(user)

        db.session.flush()

        # --------------------------------------------------
        # CREATE STAFF PROFILE
        # --------------------------------------------------

        staff_member = Staff(
            staff_id=staff_id,
            name=name,
            department=department,
            user_id=user.id,
            active=True
        )

        db.session.add(staff_member)

        db.session.commit()

        flash(
            f"Staff account created successfully. Staff ID: {staff_id}",
            "success"
        )

        return redirect(
            url_for("admin_staff")
        )

    # --------------------------------------------------
    # STAFF LIST
    # --------------------------------------------------

    staff_members = Staff.query.order_by(
        Staff.created_at.desc()
    ).all()

    total_staff = len(staff_members)

    active_staff = sum(
        1 for member in staff_members
        if member.active
    )

    inactive_staff = total_staff - active_staff

    # --------------------------------------------------
    # PAGE
    # --------------------------------------------------

    return render_template(
        "admin/staff.html",
        staff_members=staff_members,
        departments=departments,
        total_staff=total_staff,
        active_staff=active_staff,
        inactive_staff=inactive_staff
    )


# --------------------------------------------------
# STAFF TOGGLE
# --------------------------------------------------

@app.route(
    "/admin/staff/<staff_id>/toggle",
    methods=["POST"]
)
def admin_toggle_staff(staff_id):

    if session.get("role") != "admin":
        return redirect(
            url_for("admin_login")
        )

    staff_member = Staff.query.filter_by(
        staff_id=staff_id
    ).first()

    if not staff_member:

        flash(
            "Staff member not found.",
            "error"
        )

        return redirect(
            url_for("admin_staff")
        )

    staff_member.active = not staff_member.active

    db.session.commit()

    if staff_member.active:

        flash(
            f"{staff_member.name} has been activated.",
            "success"
        )

    else:

        flash(
            f"{staff_member.name} has been deactivated.",
            "success"
        )

    return redirect(
        url_for("admin_staff")
    )



# --------------------------------------------------
# STAFF EDIT
# --------------------------------------------------


# --------------------------------------------------
# PERMANENTLY DELETE INACTIVE STAFF
# --------------------------------------------------
@app.route("/admin/staff/<staff_id>/delete", methods=["POST"])
def admin_delete_staff(staff_id):
    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))

    staff_member = Staff.query.filter_by(staff_id=staff_id).first()

    if not staff_member:
        flash("Staff member not found.", "error")
        return redirect(url_for("admin_staff"))

    if staff_member.active:
        flash("Deactivate this staff member before attempting deletion.", "error")
        return redirect(url_for("admin_staff"))

    user = User.query.filter_by(id=staff_member.user_id).first()
    references = set()

    # Check declared foreign keys and common historical user/staff ID fields.
    # If checking fails, do not delete anything.
    try:
        for table in db.metadata.tables.values():
            if table.name in ("staff", "users"):
                continue

            for column in table.columns:
                values = set()

                for foreign_key in column.foreign_keys:
                    parts = foreign_key.target_fullname.split(".")
                    target_table = parts[-2] if len(parts) >= 2 else ""
                    target_column = parts[-1]

                    if target_table == "users" and target_column == "id" and user:
                        values.add(user.id)
                    elif target_table == "staff" and target_column == "id":
                        values.add(staff_member.id)
                    elif target_table == "staff" and target_column == "staff_id":
                        values.add(staff_member.staff_id)

                if column.name in {
                    "user_id", "staff_user_id", "created_by_user_id",
                    "updated_by_user_id", "actor_user_id",
                    "performed_by_user_id"
                } and user:
                    values.add(user.id)

                if column.name == "staff_id":
                    values.add(staff_member.staff_id)

                if column.name == "staff_profile_id":
                    values.add(staff_member.id)

                for value in values:
                    if db.session.query(table).filter(column == value).first():
                        references.add(table.name)
                        break

                if table.name in references:
                    break

    except Exception:
        db.session.rollback()
        app.logger.exception("Could not safely check staff deletion dependencies")
        flash(
            "Deletion was stopped because linked records could not be checked. "
            "The staff account has not been deleted.",
            "error"
        )
        return redirect(url_for("admin_staff"))

    if references:
        table_names = ", ".join(sorted(references))
        flash(
            f"{staff_member.name} cannot be permanently deleted because "
            f"records refer to this account ({table_names}). "
            "The account remains inactive so its history is preserved.",
            "error"
        )
        return redirect(url_for("admin_staff"))

    name = staff_member.name

    try:
        db.session.delete(staff_member)
        if user:
            db.session.delete(user)
        db.session.commit()
    except Exception:
        db.session.rollback()
        app.logger.exception("Staff deletion failed")
        flash(
            "Deletion failed. No changes were committed; check the application log.",
            "error"
        )
        return redirect(url_for("admin_staff"))

    flash(f"{name} was permanently deleted.", "success")
    return redirect(url_for("admin_staff"))

@app.route("/admin/staff/<staff_id>/edit", methods=["GET", "POST"])
def admin_edit_staff(staff_id):

    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))

    staff_member = Staff.query.filter_by(
        staff_id=staff_id
    ).first()

    if not staff_member:
        flash("Staff member not found.", "error")
        return redirect(url_for("admin_staff"))

    user = User.query.filter_by(
        id=staff_member.user_id
    ).first()

    departments = [
        "Library",
        "Communication Skills (REL/SC)",
        "Mathematics",
        "HR",
        "Sports",
        "AME Stores",
        "Training Section",
        "Accounts",
        "TSO",
        "Stores",
        "Hostel"
    ]

    if request.method == "POST":

        name = (request.form.get("name") or "").strip()
        username = (request.form.get("username") or "").strip()
        department = (request.form.get("department") or "").strip()
        password = (request.form.get("password") or "").strip()

        if not name or not username or not department:
            flash(
                "Name, username and department are required.",
                "error"
            )
            return redirect(
                url_for("admin_edit_staff", staff_id=staff_id)
            )

        existing_user = User.query.filter(
            User.username == username,
            User.id != staff_member.user_id
        ).first()

        if existing_user:
            flash(
                "That username is already in use.",
                "error"
            )
            return redirect(
                url_for("admin_edit_staff", staff_id=staff_id)
            )

        staff_member.name = name
        staff_member.department = department

        if user:
            user.username = username
            user.department = department

            if password:
                from werkzeug.security import generate_password_hash
                user.password = generate_password_hash(password)

        db.session.commit()

        flash(
            f"{staff_member.name}'s details were updated successfully.",
            "success"
        )

        return redirect(
            url_for("admin_staff")
        )

    return render_template(
        "admin/edit_staff.html",
        staff_member=staff_member,
        user=user,
        departments=departments
    )

# --------------------------------------------------
# STAFF CHANGE PASSWORD
# --------------------------------------------------

@app.route("/new-staff/change-password", methods=["GET", "POST"])
def staff_change_password():

    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    user_id = session.get("user_id")

    if not user_id:
        session.clear()
        return redirect(url_for("new_staff_login"))

    user = User.query.get(user_id)

    if not user:
        session.clear()
        return redirect(url_for("new_staff_login"))

    first_login_change = bool(
        getattr(user, "password_change_required", False)
    )

    staff_member = Staff.query.filter_by(user_id=user.id).first()
    staff_member_name = (
        staff_member.name
        if staff_member and staff_member.name
        else session.get("staff_name", session.get("name", "Staff Member"))
    )

    if request.method == "POST":

        current_password = request.form.get("current_password") or ""
        new_password = request.form.get("new_password") or ""
        confirm_password = request.form.get("confirm_password") or ""

        if not current_password or not new_password or not confirm_password:
            return render_template(
                "new_staff/change_password.html",
                error="Please fill in all password fields.",
                first_login_change=first_login_change,
                staff_member_name=staff_member_name
            )

        try:
            password_valid = check_password_hash(
                user.password,
                current_password
            )
        except Exception:
            password_valid = str(user.password) == current_password

        if not password_valid:
            return render_template(
                "new_staff/change_password.html",
                error="Current password is incorrect.",
                first_login_change=first_login_change,
                staff_member_name=staff_member_name
            )

        if len(new_password) < 8:
            return render_template(
                "new_staff/change_password.html",
                error="New password must be at least 8 characters.",
                first_login_change=first_login_change,
                staff_member_name=staff_member_name
            )

        if new_password != confirm_password:
            return render_template(
                "new_staff/change_password.html",
                error="New passwords do not match.",
                first_login_change=first_login_change,
                staff_member_name=staff_member_name
            )

        if new_password == current_password:
            return render_template(
                "new_staff/change_password.html",
                error="New password must be different from your current password.",
                first_login_change=first_login_change,
                staff_member_name=staff_member_name
            )

        user.password = generate_password_hash(new_password)
        user.password_change_required = False

        db.session.commit()

        flash(
            "Password changed successfully. You can now access your Staff Dashboard.",
            "success"
        )

        department = (
            session.get("department") or ""
        ).strip().lower()

        if department in {
            "accounts",
            "accounts department"
        }:
            return redirect(
                url_for("new_staff_accounts_dashboard")
            )

        if department in {
            "library",
            "library department"
        }:
            return redirect(
                url_for("new_staff_library_dashboard")
            )

        if department in {
            "human resource / admin officer",
            "human resource/admin officer",
            "human resource",
            "hr"
        }:
            return redirect(
                url_for("new_staff_hr_dashboard")
            )

        if department in {
            "sports",
            "sports department"
        }:
            return redirect(
                url_for("new_staff_sports_dashboard")
            )

        return redirect(
            url_for("new_staff_login")
        )

    return render_template(
        "new_staff/change_password.html",
        first_login_change=first_login_change,
                staff_member_name=staff_member_name
    )



# --------------------------------------------------
# NEW STAFF ACCOUNTS DASHBOARD
# --------------------------------------------------

@app.route("/new-staff/accounts/dashboard")
def new_staff_accounts_dashboard():

    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    department = (session.get("department") or "").strip().lower()

    if department not in {
        "accounts",
        "accounts department"
    }:
        return redirect(url_for("new_staff_login"))


    announcements = Announcement.query.filter(
        Announcement.active == True,
        Announcement.audience.in_(["staff", "all"])
    ).order_by(
        Announcement.created_at.desc()
    ).all()

    search = request.args.get("search", "").strip().lower()

    students = Student.query.order_by(
        Student.student_id.asc()
    ).all()

    accounts = []

    for student in students:

        account = Account.query.filter_by(
            student_id=student.student_id
        ).first()

        if not account:
            programme_fee = get_programme_fee(
                student.program
            )

            account = Account(
                student_id=student.student_id,
                total_fee=programme_fee,
                paid=0,
                minimum_required=4000,
                status="Pending",
                remarks=f"Outstanding balance: K{programme_fee:.2f}"
            )

            db.session.add(account)
            db.session.flush()

        total = account.total_fee or 0
        paid = account.paid or 0
        minimum = account.minimum_required or 4000

        outstanding = total - paid

        if outstanding <= 0:
            status = "Cleared"
            remarks = "Fees fully paid"

        elif paid >= minimum:
            status = "Cleared"
            remarks = "Meets minimum payment requirement"

        else:
            status = "Pending"
            remarks = f"Outstanding balance: K{outstanding:.2f}"

        account.status = status
        account.remarks = remarks

        if search:
            student_id = str(
                student.student_id or ""
            ).lower()

            student_name = str(
                getattr(student, "name", "") or ""
            ).lower()

            if search not in student_id and search not in student_name:
                continue

        accounts.append({
            "student": student,
            "account": account,
            "outstanding": outstanding,
            "status": status,
            "remarks": remarks
        })

    db.session.commit()

    total_students = len(accounts)

    cleared_count = sum(
        1 for item in accounts
        if item["status"] == "Cleared"
    )

    pending_count = sum(
        1 for item in accounts
        if item["status"] == "Pending"
    )

    pending_payments = Payment.query.filter_by(
        status="Pending"
    ).count()

    # ========================================================
    # ACCOUNTS DASHBOARD EXTRA DATA
    # ========================================================

    recent_activity_records = (
        AccountHistory.query
        .order_by(AccountHistory.created_at.desc())
        .limit(8)
        .all()
    )

    # Attach the matching Student object to each activity record.
    # AccountHistory stores student_id, while the dashboard
    # displays the student's name.
    recent_activity = []

    for record in recent_activity_records:
        record.student = Student.query.filter_by(
            student_id=record.student_id
        ).first()

        recent_activity.append(record)

    approved_payments = Payment.query.filter_by(
        status="Approved"
    ).count()

    pending_payment_count = Payment.query.filter_by(
        status="Pending"
    ).count()

    rejected_payments = Payment.query.filter_by(
        status="Rejected"
    ).count()

    total_payment_records = Payment.query.count()

    clearance_percentage = (
        round((cleared_count / total_students) * 100, 1)
        if total_students
        else 0
    )

    from datetime import timedelta

    today = zambia_now().date()

    payment_activity = []

    for i in range(6, -1, -1):

        day = today - timedelta(days=i)

        start = datetime.combine(day, datetime.min.time())
        end = start + timedelta(days=1)

        count = Payment.query.filter(
            Payment.created_at >= start,
            Payment.created_at < end
        ).count()

        payment_activity.append({
            "date": day.strftime("%a"),
            "count": count
        })

    # ========================================================
    # SYSTEM SETTINGS FOR ACADEMIC CALENDAR
    # ========================================================

    import sqlite3

    calendar_conn = sqlite3.connect(DATABASE_URL)
    calendar_cursor = calendar_conn.cursor()

    calendar_cursor.execute("""
        SELECT setting_key, setting_value
        FROM system_settings
    """)

    settings = dict(calendar_cursor.fetchall())
    calendar_conn.close()

    return render_template(
        "new_staff/accounts/dashboard.html",
        accounts=accounts,
        total_students=total_students,
        cleared_count=cleared_count,
        pending_count=pending_count,
        pending_payments=pending_payments,

        recent_activity=recent_activity,
        approved_payments=approved_payments,
        pending_payment_count=pending_payment_count,
        rejected_payments=rejected_payments,
        total_payment_records=total_payment_records,
        clearance_percentage=clearance_percentage,
        payment_activity=payment_activity,
        settings=settings,

        search=search,
        announcements=announcements,
        staff_name=session.get("staff_name")
        or session.get("name")
        or "Accounts Staff"
    )


# --------------------------------------------------
# NEW STAFF ACCOUNTS - STUDENT ACCOUNTS
# --------------------------------------------------

@app.route("/new-staff/accounts/students", methods=["GET", "POST"])
def new_staff_accounts_students():

    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    department = (session.get("department") or "").strip().lower()

    if department not in {
        "accounts",
        "accounts department"
    }:
        return redirect(url_for("new_staff_login"))

    if request.method == "POST":

        student_id = (request.form.get("student_id") or "").strip()

        if not student_id:
            return redirect(url_for("new_staff_accounts_students"))

        student = Student.query.filter_by(
            student_id=student_id
        ).first()

        if not student:
            flash("Student not found.", "error")
            return redirect(url_for("new_staff_accounts_students"))

        account = Account.query.filter_by(
            student_id=student.student_id
        ).first()

        if not account:
            programme_fee = get_programme_fee(
                student.program
            )

            account = Account(
                student_id=student.student_id,
                total_fee=programme_fee,
                paid=0,
                minimum_required=4000,
                status="Pending",
                remarks=f"Outstanding balance: K{programme_fee:.2f}"
            )
            db.session.add(account)

        total_input = (request.form.get("total_fee") or "").strip()
        paid_input = (request.form.get("paid") or "").strip()
        minimum_input = (request.form.get("minimum_required") or "").strip()
        action = request.form.get("action")

        try:
            if total_input:
                account.total_fee = float(total_input)

            if paid_input:
                account.paid = float(paid_input)

            if minimum_input:
                account.minimum_required = float(minimum_input)

        except ValueError:
            flash("Please enter valid amounts.", "error")
            return redirect(url_for("new_staff_accounts_students"))

        total = account.total_fee or 0
        paid = account.paid or 0
        minimum = account.minimum_required or 4000

        outstanding = total - paid

        if action == "clear":
            account.status = "Cleared"
            account.remarks = "Cleared by Accounts Office"

        elif outstanding <= 0:
            account.status = "Cleared"
            account.remarks = "Fees fully paid"

        elif paid >= minimum:
            account.status = "Cleared"
            account.remarks = "Meets minimum payment requirement"

        else:
            account.status = "Pending"
            account.remarks = f"Outstanding balance: K{outstanding:.2f}"

        db.session.commit()

        flash("Student account updated successfully.", "success")

        return redirect(
            url_for("new_staff_accounts_students")
        )

    search = request.args.get(
        "search",
        ""
    ).strip().lower()

    students = Student.query.order_by(
        Student.student_id.asc()
    ).all()

    accounts = []

    for student in students:

        if search:
            student_id = str(
                student.student_id or ""
            ).lower()

            student_name = str(
                getattr(student, "name", "") or ""
            ).lower()

            if search not in student_id and search not in student_name:
                continue

        account = Account.query.filter_by(
            student_id=student.student_id
        ).first()

        if not account:
            programme_fee = get_programme_fee(
                student.program
            )

            account = Account(
                student_id=student.student_id,
                total_fee=programme_fee,
                paid=0,
                minimum_required=4000,
                status="Pending",
                remarks=f"Outstanding balance: K{programme_fee:.2f}"
            )
            db.session.add(account)
            db.session.flush()

        total = account.total_fee or 0
        paid = account.paid or 0
        minimum = account.minimum_required or 4000

        outstanding = total - paid

        if outstanding <= 0:
            status = "Cleared"
            remarks = "Fees fully paid"

        elif paid >= minimum:
            status = "Cleared"
            remarks = "Meets minimum payment requirement"

        else:
            status = "Pending"
            remarks = f"Outstanding balance: K{outstanding:.2f}"

        account.status = status
        account.remarks = remarks

        accounts.append({
            "student": student,
            "account": account,
            "outstanding": outstanding,
            "status": status,
            "remarks": remarks
        })

    db.session.commit()

    return render_template(
        "new_staff/accounts/students.html",
        accounts=accounts,
        search=search,
        staff_name=session.get("staff_name")
        or session.get("name")
        or "Accounts Staff"
    )



# --------------------------------------------------
# NEW STAFF ACCOUNTS - PAYMENTS
# --------------------------------------------------

@app.route("/new-staff/accounts/payments", methods=["GET", "POST"])
def new_staff_accounts_payments():

    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    department = (session.get("department") or "").strip().lower()

    if department not in {
        "accounts",
        "accounts department"
    }:
        return redirect(url_for("new_staff_login"))

    if request.method == "POST":

        payment_id = request.form.get("payment_id")
        action = request.form.get("action")

        payment = None

        if payment_id:
            try:
                payment = Payment.query.get(int(payment_id))
            except (ValueError, TypeError):
                payment = None

        if not payment:
            flash("Payment record not found.", "error")
            return redirect(url_for("new_staff_accounts_payments"))

        # --------------------------------------------------
        # APPROVE PAYMENT
        # --------------------------------------------------

        if action == "approve":

            # Prevent the same payment from being added twice.
            if payment.status == "Approved":
                flash("This payment has already been approved.", "error")
                return redirect(
                    url_for("new_staff_accounts_payments")
                )

            # A payment that was already rejected should not
            # suddenly become approved through a stale form.
            if payment.status != "Pending":
                flash("Only pending payments can be approved.", "error")
                return redirect(
                    url_for("new_staff_accounts_payments")
                )

            account = Account.query.filter_by(
                student_id=payment.student_id
            ).first()

            if not account:
                payment_student = Student.query.filter_by(
                    student_id=payment.student_id
                ).first()

                programme_fee = get_programme_fee(
                    payment_student.program
                    if payment_student
                    else None
                )

                account = Account(
                    student_id=payment.student_id,
                    total_fee=programme_fee,
                    paid=0,
                    minimum_required=4000,
                    status="Pending",
                    remarks=f"Outstanding balance: K{programme_fee:.2f}"
                )

                db.session.add(account)
                db.session.flush()

            # Add this payment exactly once.
            account.paid = (
                (account.paid or 0) +
                (payment.amount or 0)
            )

            total = account.total_fee or 0
            paid = account.paid or 0
            minimum = account.minimum_required or 4000

            outstanding = total - paid

            # Recalculate account clearance status.
            if outstanding <= 0:
                account.status = "Cleared"
                account.remarks = "Fees fully paid"

            elif paid >= minimum:
                account.status = "Cleared"
                account.remarks = "Meets minimum payment requirement"

            else:
                account.status = "Pending"
                account.remarks = (
                    f"Outstanding balance: K{outstanding:.2f}"
                )

            payment.status = "Approved"

            db.session.add(
                AccountHistory(
                    student_id=payment.student_id,
                    amount=payment.amount or 0,
                    status="Approved",
                    reason="Online Payment",
                    remarks="Payment approved by Accounts Office"
                )
            )

            db.session.add(DepartmentHistory(
                student_id=payment.student_id,
                department="accounts",
                status="Approved",
                action="Payment approved",
                remarks="Payment approved by Accounts Office",
                performed_by=(
                    session.get("staff_name")
                    or session.get("name")
                    or session.get("username")
                    or "Accounts Staff"
                ),
                created_at=zambia_now()
            ))

            flash(
                "Payment approved and student account updated.",
                "success"
            )

        # --------------------------------------------------
        # REJECT PAYMENT
        # --------------------------------------------------

        elif action == "reject":

            # Prevent changing an already approved payment.
            if payment.status == "Approved":
                flash(
                    "An approved payment cannot be rejected here.",
                    "error"
                )
                return redirect(
                    url_for("new_staff_accounts_payments")
                )

            if payment.status != "Pending":
                flash(
                    "Only pending payments can be rejected.",
                    "error"
                )
                return redirect(
                    url_for("new_staff_accounts_payments")
                )

            payment.status = "Rejected"

            payment.remarks = (
                request.form.get("remarks")
                or request.form.get("reason")
                or "Payment rejected by Accounts Office."
            ).strip()

            # --------------------------------------------------
            # RECORD REJECTED PAYMENT IN ACCOUNT HISTORY
            # --------------------------------------------------
            # Rejected payments must appear in Account History
            # but MUST NOT be added to the student's paid amount.
            # --------------------------------------------------

            db.session.add(
                AccountHistory(
                    student_id=payment.student_id,
                    amount=payment.amount or 0,
                    status="Rejected",
                    reason="Online Payment",
                    remarks=payment.remarks
                )
            )

            db.session.add(DepartmentHistory(
                student_id=payment.student_id,
                department="accounts",
                status="Rejected",
                action="Payment rejected",
                remarks=payment.remarks,
                performed_by=(
                    session.get("staff_name")
                    or session.get("name")
                    or session.get("username")
                    or "Accounts Staff"
                ),
                created_at=zambia_now()
            ))

            flash(
                "Payment rejected. The student's account was not credited.",
                "success"
            )

        else:

            flash("Invalid payment action.", "error")
            return redirect(
                url_for("new_staff_accounts_payments")
            )

        db.session.commit()

        return redirect(
            url_for("new_staff_accounts_payments")
        )

    status_filter = (
        request.args.get("status") or "Pending"
    ).strip()

    query = Payment.query.order_by(
        Payment.id.desc()
    )

    if status_filter in {
        "Pending",
        "Approved",
        "Rejected"
    }:
        query = query.filter_by(
            status=status_filter
        )

    payments = query.all()

    payment_rows = []

    for payment in payments:

        student = Student.query.filter_by(
            student_id=payment.student_id
        ).first()

        payment_rows.append({
            "payment": payment,
            "student": student
        })

    return render_template(
        "new_staff/accounts/payments.html",
        payments=payment_rows,
        status_filter=status_filter,
        staff_name=session.get("staff_name")
        or session.get("name")
        or "Accounts Staff"
    )


# --------------------------------------------------
# NEW STAFF ACCOUNTS - ACCOUNT HISTORY
# --------------------------------------------------

@app.route("/new-staff/accounts/history")
def new_staff_accounts_history():

    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    department = (
        session.get("department") or ""
    ).strip().lower()

    if department not in {
        "accounts",
        "accounts department"
    }:
        return redirect(url_for("new_staff_login"))

    history = AccountHistory.query.order_by(
        AccountHistory.id.desc()
    ).all()

    history_rows = []

    for record in history:

        student = Student.query.filter_by(
            student_id=record.student_id
        ).first()

        history_rows.append({
            "record": record,
            "student": student
        })

    return render_template(
        "new_staff/accounts/history.html",
        history=history_rows,
        staff_name=session.get("staff_name")
        or session.get("name")
        or "Accounts Staff"
    )


# --------------------------------------------------
# STAFF DASHBOARD
# --------------------------------------------------







# --------------------------------------------------
# ADMIN DEPARTMENTS
# --------------------------------------------------

@app.route("/admin/departments")
def admin_departments():

    if session.get("role") != "admin":
        return redirect(
            url_for("admin_login")
        )

    departments = [
        ("Library", "bi-book-fill"),
        ("Communication Skills (REL SC)", "bi-chat-square-text-fill"),
        ("Mathematics", "bi-calculator-fill"),
        ("Human Resource / Admin Officer", "bi-people-fill"),
        ("Sports", "bi-trophy-fill"),
        ("Head of Training Section", "bi-mortarboard-fill"),
        ("AME Stores", "bi-tools"),
        ("Accounts", "bi-cash-stack"),
        ("Technical Services Office", "bi-pc-display"),
        ("Stores Office", "bi-box-seam-fill"),
        ("Hostel", "bi-house-fill"),
    ]

    def normalize_staff_department(value):
        if not value:
            return ""
        value = str(value).strip().lower()
        value = value.replace("_", " ").replace("-", " ")
        return " ".join(value.split())

    # Recognize existing names and abbreviations without modifying
    # any staff records.
    department_aliases = {
        "Library": ["Library"],
        "Communication Skills (REL SC)": [
            "Communication Skills",
            "Communication Skills (REL SC)",
            "Communication Skills (REL/SC)",
        ],
        "Mathematics": ["Mathematics"],
        "Human Resource / Admin Officer": [
            "Human Resource",
            "Human Resources",
            "Human Resource / Admin Officer",
            "HR",
        ],
        "Sports": ["Sports"],
        "Head of Training Section": [
            "Head of Training Section",
            "Head Of Training Section",
            "Training Section",
        ],
        "AME Stores": ["AME Stores"],
        "Accounts": ["Accounts"],
        "Technical Services Office": [
            "TSO",
            "Technical Services Office",
            "Technical Services Office (TSO)",
        ],
        "Stores Office": [
            "Stores",
            "Stores Office",
            "Stores Officer",
        ],
        "Hostel": [
            "Hostel",
            "Hostels",
            "Hostels (HOS)",
        ],
    }

    all_staff = Staff.query.order_by(Staff.name.asc()).all()
    department_data = []

    for name, icon in departments:
        accepted_names = {
            normalize_staff_department(alias)
            for alias in department_aliases[name]
        }

        staff_members = [
            member for member in all_staff
            if normalize_staff_department(member.department)
            in accepted_names
        ]

        active_count = sum(
            1 for member in staff_members if member.active
        )

        department_data.append({
            "name": name,
            "icon": icon,
            "staff": staff_members,
            "staff_count": len(staff_members),
            "active_count": active_count,
        })

    return render_template(
        "admin/departments.html",
        departments=department_data,
        total_departments=len(department_data),
        total_staff=Staff.query.count(),
        active_staff=Staff.query.filter_by(
            active=True
        ).count()
    )


# --------------------------------------------------
# ADMIN CLEARANCE MANAGEMENT
# --------------------------------------------------


@app.route("/admin/clearance")
def admin_clearance_management():
    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))

    search = request.args.get("search", "").strip()
    query = Student.query

    if search:
        query = query.filter(
            db.or_(
                Student.student_id.ilike(f"%{search}%"),
                Student.name.ilike(f"%{search}%"),
                Student.program.ilike(f"%{search}%"),
            )
        )

    students = query.order_by(Student.name.asc()).all()

    # These keys match the existing admin clearance template.
    display_names = [
        "Library",
        "Communication Skills (REL SC)",
        "Mathematics",
        "Human Resource / Admin Officer",
        "Sports",
        "AME Stores",
        "Head Of Training Section",
        "Accounts",
        "Technical Services Office",
        "Stores Office",
        "Hostel",
    ]

    def normalize_department(value):
        return "".join(
            character
            for character in str(value or "").casefold()
            if character.isalnum()
        )

    # Match the names used in the authoritative student report
    # to the existing display keys in the admin table.
    aliases = {
        "library": "Library",

        "communicationskills": "Communication Skills (REL SC)",
        "communicationskillsrelsc": "Communication Skills (REL SC)",
        "communication": "Communication Skills (REL SC)",

        "mathematics": "Mathematics",
        "humanresource": "Human Resource / Admin Officer",
        "humanresources": "Human Resource / Admin Officer",
        "humanresourcesadminofficer": "Human Resource / Admin Officer",
        "hr": "Human Resource / Admin Officer",

        "sports": "Sports",
        "amestores": "AME Stores",

        "head of training section": "Head Of Training Section",
        "headoftrainingsection": "Head Of Training Section",
        "trainingsection": "Head Of Training Section",
        "training": "Head Of Training Section",

        "accounts": "Accounts",

        "tso": "Technical Services Office",
        "technicalservicesoffice": "Technical Services Office",
        "technicalservicesofficetso": "Technical Services Office",

        "stores": "Stores Office",
        "storesoffice": "Stores Office",
        "storesofficer": "Stores Office",

        "hostel": "Hostel",
        "hostels": "Hostel",
        "hostelshos": "Hostel",
    }

    student_clearances = []

    # Preserve the administrator's session while reusing the
    # exact report logic for each student.
    had_role = "role" in session
    original_role = session.get("role")
    had_student_id = "student_id" in session
    original_student_id = session.get("student_id")

    try:
        for student in students:
            session["role"] = "student"
            session["student_id"] = student.student_id

            snapshot = student_clearance(_return_snapshot=True)

            rows = (
                snapshot.get("clearance_rows", [])
                if isinstance(snapshot, dict)
                else []
            )

            # Default every area to Pending. The report snapshot
            # then supplies the authoritative status for each one.
            status_map = {
                name: "Pending"
                for name in display_names
            }

            matched_departments = set()

            for row in rows:
                if not isinstance(row, dict):
                    continue

                department_key = normalize_department(
                    row.get("department", "")
                )
                display_name = aliases.get(department_key)

                if not display_name:
                    continue

                report_status = str(
                    row.get("status", "Pending")
                ).strip().casefold()

                status_map[display_name] = (
                    "Cleared"
                    if report_status == "cleared"
                    else "Pending"
                )
                matched_departments.add(display_name)

            cleared = sum(
                1 for status in status_map.values()
                if status == "Cleared"
            )
            total = len(display_names)

            # Require all 11 report areas to be present and cleared.
            fully_cleared = (
                len(rows) == total
                and len(matched_departments) == total
                and cleared == total
            )

            student_clearances.append({
                "student": student,
                "statuses": status_map,
                "cleared": cleared,
                "total": total,
                "fully_cleared": fully_cleared,
                "is_day_scholar": (
                    student.accommodation == "Day Scholar"
                ),
            })

    finally:
        if had_role:
            session["role"] = original_role
        else:
            session.pop("role", None)

        if had_student_id:
            session["student_id"] = original_student_id
        else:
            session.pop("student_id", None)

    total_students = Student.query.count()
    fully_cleared_count = sum(
        1 for item in student_clearances
        if item["fully_cleared"]
    )
    pending_count = len(student_clearances) - fully_cleared_count

    return render_template(
        "admin/clearance_management.html",
        student_clearances=student_clearances,
        search=search,
        total_students=total_students,
        fully_cleared_count=fully_cleared_count,
        pending_count=pending_count,
    )

@app.route("/admin/dashboard")
def admin_dashboard():

    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))

    total_students = Student.query.count()

    total_staff = Staff.query.count()

    department_names = [
        ("Library", "bi bi-book-fill", "Library"),
        ("Communication Skills (REL SC)", "bi bi-chat-square-text-fill", "Communication Skills"),
        ("Mathematics", "bi bi-calculator-fill", "Mathematics"),
        ("Human Resource / Admin Officer", "bi bi-people-fill", "Human Resource"),
        ("Sports", "bi bi-trophy-fill", "Sports"),
        ("Head Of Training Section", "bi bi-mortarboard-fill", "Head Of Training Section"),
        ("AME Stores", "bi bi-tools", "AME Stores"),
        ("Stores Office", "bi bi-box-seam-fill", "Stores"),
        ("Technical Services Office", "bi bi-building", "TSO"),
        ("Hostel", "bi bi-house-fill", "Hostel"),
        ("Accounts", "bi bi-cash-stack", "Accounts"),
    ]

    departments = []
    students = Student.query.order_by(Student.name.asc()).all()

    department_counts = {
        report_name: {"total": 0, "cleared": 0, "pending": 0}
        for _, _, report_name in department_names
    }

    pending_students = 0
    cleared_students = 0

    # Preserve the administrator's session while using the existing
    # student clearance report to calculate each student's real statuses.
    had_role = "role" in session
    original_role = session.get("role")
    had_student_id = "student_id" in session
    original_student_id = session.get("student_id")

    try:
        for student in students:
            session["role"] = "student"
            session["student_id"] = student.student_id

            snapshot = student_clearance(_return_snapshot=True)

            rows = (
                snapshot.get("clearance_rows", [])
                if isinstance(snapshot, dict)
                else []
            )

            status_by_department = {
                str(row.get("department", "")).strip().casefold():
                    str(row.get("status", "Pending")).strip().casefold()
                for row in rows
                if isinstance(row, dict)
            }

            student_fully_cleared = (
                len(rows) == 11
                and all(
                    status_by_department.get(report_name.casefold(), "pending")
                    == "cleared"
                    for _, _, report_name in department_names
                )
            )

            if student_fully_cleared:
                cleared_students += 1
            else:
                pending_students += 1

            for _, _, report_name in department_names:
                counts = department_counts[report_name]
                counts["total"] += 1

                status = status_by_department.get(
                    report_name.casefold(), "pending"
                )

                if status == "cleared":
                    counts["cleared"] += 1
                else:
                    counts["pending"] += 1
    finally:
        if had_role:
            session["role"] = original_role
        else:
            session.pop("role", None)

        if had_student_id:
            session["student_id"] = original_student_id
        else:
            session.pop("student_id", None)

    for display_name, icon, report_name in department_names:
        counts = department_counts[report_name]
        departments.append({
            "name": display_name,
            "icon": icon,
            "total": counts["total"],
            "cleared": counts["cleared"],
            "pending": counts["pending"],
        })

    department_total = len(departments)

    recent_activity = []

    history_records = ClearanceHistory.query.order_by(
        ClearanceHistory.id.desc()
    ).limit(8).all()

    for item in history_records:

        description = (
            getattr(item, "status", None)
            or "Clearance activity recorded"
        )

        generated_time = (
            getattr(item, "generated_time", None)
            or "Recent activity"
        )

        recent_activity.append({
            "description": description,
            "time": generated_time
        })

    # ========================================================
    # SYSTEM SETTINGS FOR DASHBOARD CALENDAR
    # ========================================================

    import sqlite3

    conn = sqlite3.connect(DATABASE_URL)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT setting_key, setting_value
        FROM system_settings
    """)

    settings = dict(cursor.fetchall())
    conn.close()

    return render_template(
        "admin/dashboard.html",
        total_students=total_students,
        total_staff=total_staff,
        pending_students=pending_students,
        cleared_students=cleared_students,
        departments=departments,
        department_total=department_total,
        recent_activity=recent_activity,
        settings=settings
    )



# --------------------------------------------------
# LOGOUT
# --------------------------------------------------

@app.route("/logout")
def logout():

    role = session.get("role")

    session.clear()

    if role == "admin":
        return redirect(url_for("admin_login"))

    elif role == "staff":
        return redirect(url_for("new_staff_login"))

    elif role == "student":
        return redirect(url_for("student_login"))

    return redirect(url_for("student_login"))



# ==================================================
# ADMIN STUDENT DETAILS
# ==================================================

@app.route(
    "/admin/students/<student_id>/gender",
    methods=["POST"]
)
def admin_update_student_gender(student_id):
    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))

    from models import (
        Student,
        AccommodationAssignment,
        HostelRoom,
        Hostel,
        HostelSection
    )

    student = Student.query.filter_by(
        student_id=student_id
    ).first()

    if not student:
        flash("Student record not found.", "error")
        return redirect(url_for("admin_students"))

    gender = request.form.get("gender", "").strip().lower()

    if gender not in ("male", "female"):
        flash("Please select Male or Female.", "error")
        return redirect(
            url_for("admin_student_view", student_id=student_id)
        )

    active_statuses = [
        "Occupying", "occupying", "Active", "active"
    ]

    assignments = AccommodationAssignment.query.filter(
        AccommodationAssignment.student_id == student_id,
        AccommodationAssignment.status.in_(active_statuses)
    ).all()

    for assignment in assignments:
        room = HostelRoom.query.filter_by(
            id=assignment.room_id
        ).first()

        if not room:
            flash("Gender not updated: current room is missing.", "error")
            return redirect(url_for(
                "admin_student_view", student_id=student_id
            ))

        hostel = Hostel.query.filter_by(
            id=room.hostel_id
        ).first()

        if not hostel:
            flash("Gender not updated: current hostel is missing.", "error")
            return redirect(url_for(
                "admin_student_view", student_id=student_id
            ))

        section = None
        if room.section_id:
            section = HostelSection.query.filter_by(
                id=room.section_id
            ).first()

            if not section:
                flash("Gender not updated: room section is missing.", "error")
                return redirect(url_for(
                    "admin_student_view", student_id=student_id
                ))

        policies = [
            hostel.gender_policy,
            section.gender_policy if section else "both",
            room.gender_policy
        ]

        for value in policies:
            policy = (value or "").strip().lower()

            if policy not in ("male", "female", "both"):
                flash("Gender not updated: invalid accommodation policy.", "error")
                return redirect(url_for(
                    "admin_student_view", student_id=student_id
                ))

            if policy != "both" and policy != gender:
                flash(
                    "Gender not updated: it conflicts with the current accommodation policy.",
                    "error"
                )
                return redirect(url_for(
                    "admin_student_view", student_id=student_id
                ))

        occupants = AccommodationAssignment.query.filter(
            AccommodationAssignment.room_id == room.id,
            AccommodationAssignment.status.in_(active_statuses)
        ).all()

        for other_assignment in occupants:
            if other_assignment.student_id == student_id:
                continue

            other_student = Student.query.filter_by(
                student_id=other_assignment.student_id
            ).first()

            other_gender = (
                (other_student.gender or "").strip().lower()
                if other_student else ""
            )

            if other_gender not in ("male", "female"):
                flash(
                    "Gender not updated: another room occupant has no valid recorded gender.",
                    "error"
                )
                return redirect(url_for(
                    "admin_student_view", student_id=student_id
                ))

            if other_gender != gender:
                flash(
                    "Gender not updated: this would create mixed-gender room occupancy.",
                    "error"
                )
                return redirect(url_for(
                    "admin_student_view", student_id=student_id
                ))

    student.gender = gender.title()
    db.session.commit()

    flash("Student gender updated successfully.", "success")
    return redirect(url_for(
        "admin_student_view", student_id=student_id
    ))


@app.route("/admin/students/<student_id>")
def admin_student_view(student_id):

    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))

    student = Student.query.filter_by(
        student_id=student_id
    ).first_or_404()

    # ==================================================
    # DEPARTMENT CLEARANCE
    # ==================================================

    department_names = [
        "Library",
        "Communication Skills",
        "Mathematics",
        "HR",
        "Sports",
        "AME Stores",
        "Head Of Training Section",
        "Accounts",
        "TSO",
        "Stores",
        "Hostel",
    ]

    def normalize_department(value):
        if not value:
            return ""
        value = str(value).strip().lower()
        value = value.replace("_", " ").replace("-", " ")
        return " ".join(value.split())

    # Calculate clearance using the same rules as the detailed report.
    original_role = session.get("role")
    had_student_id = "student_id" in session
    original_student_id = session.get("student_id")

    try:
        session["role"] = "student"
        session["student_id"] = student.student_id
        report_snapshot = student_clearance(_return_snapshot=True)
    finally:
        if original_role is None:
            session.pop("role", None)
        else:
            session["role"] = original_role

        if had_student_id:
            session["student_id"] = original_student_id
        else:
            session.pop("student_id", None)

    if not isinstance(report_snapshot, dict):
        raise RuntimeError(
            "Could not calculate clearance for this student."
        )

    report_rows = report_snapshot.get("clearance_rows", [])
    report_map = {
        normalize_department(row.get("department")): row
        for row in report_rows
        if normalize_department(row.get("department"))
    }

    aliases = {
        "HR": "Human Resource",
    }

    departments = []
    for name in department_names:
        report_name = aliases.get(name, name)
        row = report_map.get(normalize_department(report_name))

        if row is None:
            row = report_map.get(normalize_department(name))

        if row is not None:
            departments.append({
                "name": name,
                "status": row.get("status") or "Pending",
                "reason": row.get("reason"),
                "remarks": row.get("remarks"),
                "record_exists": True,
            })
        else:
            departments.append({
                "name": name,
                "status": "No Record",
                "reason": None,
                "remarks": None,
                "record_exists": False,
            })

    # ==================================================
    # ACCOUNT
    # ==================================================
    account = Account.query.filter_by(
        student_id=student.student_id
    ).first()

    # ==================================================
    # ACCOUNT HISTORY
    # ==================================================

    account_history = AccountHistory.query.filter_by(
        student_id=student.student_id
    ).order_by(
        AccountHistory.id.desc()
    ).all()

    # ==================================================
    # LIBRARY
    # ==================================================

    library_books = LibraryBook.query.filter_by(
        student_id=student.student_id
    ).order_by(
        LibraryBook.id.desc()
    ).all()

    # ==================================================
    # SPORTS
    # ==================================================

    sports_items = SportsItem.query.filter_by(
        student_id=student.student_id
    ).order_by(
        SportsItem.id.desc()
    ).all()

    # ==================================================
    # AME TOOLS
    # ==================================================

    ame_tools = AMETool.query.filter_by(
        student_id=student.student_id
    ).order_by(
        AMETool.id.desc()
    ).all()

    # ==================================================
    # STORES
    # ==================================================

    store_properties = StoreProperty.query.filter_by(
        student_id=student.student_id
    ).order_by(
        StoreProperty.id.desc()
    ).all()

    # ==================================================
    # PROFILE PHOTO
    # ==================================================

    profile_photo_url = None

    if student.profile_pic:

        profile_photo_url = url_for(
            "admin_student_photo",
            filename=student.profile_pic
        )

    # ==================================================
    # RENDER
    # ==================================================

    return render_template(
        "admin/student_view.html",

        student=student,

        departments=departments,

        account=account,

        account_history=account_history,

        library_books=library_books,

        sports_items=sports_items,

        ame_tools=ame_tools,

        store_properties=store_properties,

        profile_photo_url=profile_photo_url
    )


# ==================================================
# ADMIN STUDENT PHOTO
# ==================================================

@app.route("/admin/student-photo/<path:filename>")
def admin_student_photo(filename):

    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))

    from flask import send_from_directory
    import os

    possible_directories = [
        os.path.join(app.root_path, "profile_pics"),
        os.path.join(app.root_path, "uploads"),
        os.path.join(app.root_path, "static", "profile_pics"),
        os.path.join(app.root_path, "static", "uploads")
    ]

    for directory in possible_directories:

        full_path = os.path.join(directory, filename)

        if os.path.isfile(full_path):

            return send_from_directory(
                directory,
                filename
            )

    return ("", 404)




# ==================================================
# ADMIN DOCUMENTS & PAYMENTS
# ==================================================

@app.route("/admin/documents-payments")
def admin_documents_payments():

    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))

    payments = Payment.query.order_by(
        Payment.created_at.desc()
    ).all()

    pending_count = Payment.query.filter(
        Payment.status == "Pending"
    ).count()

    approved_count = Payment.query.filter(
        Payment.status == "Approved"
    ).count()

    return render_template(
        "admin/documents_payments.html",
        payments=payments,
        pending_count=pending_count,
        approved_count=approved_count
    )


@app.route("/admin/payment/<int:payment_id>/document")
def admin_payment_document(payment_id):

    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))

    payment = Payment.query.get_or_404(payment_id)

    if not payment.file:
        return "No payment document attached to this submission.", 404

    from config import DOCUMENTS_FOLDER
    from flask import send_from_directory

    filepath = os.path.join(
        DOCUMENTS_FOLDER,
        payment.file
    )

    if not os.path.isfile(filepath):
        return render_template(
            "student/payment_document_unavailable.html"
        ), 404

    return send_from_directory(
        DOCUMENTS_FOLDER,
        payment.file,
        as_attachment=False
    )


@app.route("/admin/payment/<int:payment_id>/review", methods=["GET", "POST"])
def admin_payment_review(payment_id):

    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))

    payment = Payment.query.get_or_404(payment_id)

    student = Student.query.filter_by(
        student_id=payment.student_id
    ).first()

    if request.method == "POST":

        action = request.form.get(
            "action",
            ""
        ).strip()

        remarks = request.form.get(
            "remarks",
            ""
        ).strip()

        if action == "approve":

            payment.status = "Approved"
            payment.reason = None
            payment.remarks = remarks or "Payment proof approved by administrator."

            db.session.commit()

            flash(
                "Payment proof approved successfully.",
                "success"
            )

            return redirect(
                url_for("admin_documents_payments")
            )


        if action == "reject":

            payment.status = "Rejected"
            payment.reason = remarks or "Payment proof rejected by administrator."
            payment.remarks = remarks

            db.session.commit()

            flash(
                "Payment proof rejected.",
                "success"
            )

            return redirect(
                url_for("admin_documents_payments")
            )


        flash(
            "Invalid payment action.",
            "error"
        )


    return render_template(
        "admin/payment_review.html",
        payment=payment,
        student=student
    )




# ==================================================
# ADMIN SYSTEM SETTINGS
# ==================================================



# ==================================================
# ADMIN CHANGE PASSWORD
# ==================================================

@app.route("/admin/change-password", methods=["POST"])
def admin_change_password():

    if session.get("role") != "admin":
        return redirect(
            url_for("admin_login")
        )

    current_password = request.form.get(
        "current_password",
        ""
    )

    new_password = request.form.get(
        "new_password",
        ""
    )

    confirm_password = request.form.get(
        "confirm_password",
        ""
    )

    # --------------------------------------------------
    # VALIDATION
    # --------------------------------------------------

    if not current_password:
        flash(
            "Please enter your current password.",
            "error"
        )

        return redirect(
            url_for("admin_system_settings")
        )

    if not new_password:
        flash(
            "Please enter a new password.",
            "error"
        )

        return redirect(
            url_for("admin_system_settings")
        )

    if not confirm_password:
        flash(
            "Please confirm your new password.",
            "error"
        )

        return redirect(
            url_for("admin_system_settings")
        )

    if len(new_password) < 8:
        flash(
            "New password must contain at least 8 characters.",
            "error"
        )

        return redirect(
            url_for("admin_system_settings")
        )

    if new_password != confirm_password:
        flash(
            "New passwords do not match.",
            "error"
        )

        return redirect(
            url_for("admin_system_settings")
        )

    # --------------------------------------------------
    # FIND LOGGED-IN ADMIN
    # --------------------------------------------------

    username = session.get("user")

    if not username:
        username = session.get("username")

    admin = None

    if username:
        admin = User.query.filter_by(
            username=username
        ).first()

    # Fallback for sessions that store the user differently
    if not admin and session.get("user_id"):

        admin = User.query.get(
            session.get("user_id")
        )

    if not admin or admin.role != "admin":

        flash(
            "Administrator account could not be found.",
            "error"
        )

        return redirect(
            url_for("admin_system_settings")
        )

    # --------------------------------------------------
    # VERIFY CURRENT PASSWORD
    # --------------------------------------------------

    if not check_password_hash(
        admin.password,
        current_password
    ):

        flash(
            "Current password is incorrect.",
            "error"
        )

        return redirect(
            url_for("admin_system_settings")
        )

    # --------------------------------------------------
    # PREVENT SAME PASSWORD
    # --------------------------------------------------

    if check_password_hash(
        admin.password,
        new_password
    ):

        flash(
            "Your new password must be different from your current password.",
            "error"
        )

        return redirect(
            url_for("admin_system_settings")
        )

    # --------------------------------------------------
    # SAVE NEW PASSWORD
    # --------------------------------------------------

    admin.password = generate_password_hash(
        new_password
    )

    db.session.commit()

    flash(
        "Your administrator password has been changed successfully.",
        "success"
    )

    return redirect(
        url_for("admin_system_settings")
    )


@app.route("/admin/system-settings", methods=["GET", "POST"])
def admin_system_settings():

    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))

    import sqlite3

    database_path = DATABASE_URL

    if request.method == "POST":

        institution_name = request.form.get(
            "institution_name",
            ""
        ).strip()

        system_name = request.form.get(
            "system_name",
            ""
        ).strip()

        academic_year = request.form.get(
            "academic_year",
            ""
        ).strip()

        academic_term = request.form.get(
            "academic_term",
            "Term 1"
        ).strip()

        term_start_date = request.form.get(
            "term_start_date",
            ""
        ).strip()

        term_end_date = request.form.get(
            "term_end_date",
            ""
        ).strip()

        minimum_payment = request.form.get(
            "minimum_payment_required",
            "4000"
        ).strip()

        penalty_fee = request.form.get(
            "penalty_fee",
            "200"
        ).strip()

        payment_proof_enabled = (
            "1"
            if request.form.get("payment_proof_enabled")
            else "0"
        )

        try:
            minimum_payment_value = float(
                minimum_payment
            )

            if minimum_payment_value < 0:
                raise ValueError

        except ValueError:

            flash(
                "Minimum payment must be a valid non-negative amount.",
                "error"
            )

            return redirect(
                url_for("admin_system_settings")
            )

        try:
            penalty_fee_value = float(penalty_fee)

            if penalty_fee_value < 0:
                raise ValueError

        except ValueError:
            flash(
                "Penalty fee must be a valid non-negative amount.",
                "error"
            )
            return redirect(
                url_for("admin_system_settings")
            )

        # --------------------------------------------------
        # VALIDATE ACADEMIC TERM DATES
        # --------------------------------------------------

        if term_start_date and term_end_date:
            try:
                start_date = datetime.strptime(
                    term_start_date,
                    "%Y-%m-%d"
                ).date()

                end_date = datetime.strptime(
                    term_end_date,
                    "%Y-%m-%d"
                ).date()

                if end_date < start_date:
                    flash(
                        "Term end date cannot be before the term start date.",
                        "error"
                    )
                    return redirect(
                        url_for("admin_system_settings")
                    )

            except ValueError:
                flash(
                    "Please enter valid term start and end dates.",
                    "error"
                )
                return redirect(
                    url_for("admin_system_settings")
                )

        settings = {
            "institution_name": institution_name,
            "system_name": system_name,
            "academic_year": academic_year,
            "academic_term": academic_term,
            "term_start_date": term_start_date,
            "term_end_date": term_end_date,
            "minimum_payment_required": str(
                int(minimum_payment_value)
                if minimum_payment_value.is_integer()
                else minimum_payment_value
            ),
            "penalty_fee": str(
                int(penalty_fee_value)
                if penalty_fee_value.is_integer()
                else penalty_fee_value
            ),

            "payment_proof_enabled": payment_proof_enabled
        }

        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()

        for key, value in settings.items():

            cursor.execute("""
                INSERT INTO system_settings
                (setting_key, setting_value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)

                ON CONFLICT(setting_key)
                DO UPDATE SET
                    setting_value = excluded.setting_value,
                    updated_at = CURRENT_TIMESTAMP
            """, (key, value))

        conn.commit()
        conn.close()

        flash(
            "System settings saved successfully.",
            "success"
        )

        return redirect(
            url_for("admin_system_settings")
        )

    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT setting_key, setting_value
        FROM system_settings
    """)

    settings = dict(cursor.fetchall())

    conn.close()

    programme_fee_schools = (
        ProgramFeeSchool.query
        .order_by(ProgramFeeSchool.id)
        .all()
    )

    programme_fees = (
        ProgramFee.query
        .order_by(
            ProgramFee.school_id,
            ProgramFee.section_id,
            ProgramFee.program
        )
        .all()
    )

    return render_template(
        "admin/system_settings.html",
        settings=settings,
        programme_fee_schools=programme_fee_schools,
        programme_fees=programme_fees
    )


# ============================================================

# ============================================================
# STUDENT DEPARTMENT HISTORIES
# ============================================================

@app.route(
    "/admin/system-settings/programme-fees/add",
    methods=["POST"]
)
def admin_add_programme_fee():

    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))

    school_id_input = (
        request.form.get("school_id") or ""
    ).strip()

    section_id_input = (
        request.form.get("section_id") or ""
    ).strip()

    programme = (
        request.form.get("programme") or ""
    ).strip()

    total_fee_input = (
        request.form.get("total_fee") or ""
    ).strip()

    if not school_id_input:
        flash(
            "Please select a school.",
            "error"
        )
        return redirect(
            url_for("admin_system_settings")
        )

    if not programme:
        flash(
            "Please enter a programme name.",
            "error"
        )
        return redirect(
            url_for("admin_system_settings")
        )

    try:
        school_id = int(school_id_input)

    except ValueError:
        flash(
            "Invalid school selected.",
            "error"
        )
        return redirect(
            url_for("admin_system_settings")
        )

    school = ProgramFeeSchool.query.get(school_id)

    if not school:
        flash(
            "Selected school was not found.",
            "error"
        )
        return redirect(
            url_for("admin_system_settings")
        )

    section = None

    if section_id_input:
        try:
            section_id = int(section_id_input)

        except ValueError:
            flash(
                "Invalid section selected.",
                "error"
            )
            return redirect(
                url_for("admin_system_settings")
            )

        section = ProgramFeeSection.query.filter_by(
            id=section_id,
            school_id=school.id
        ).first()

        if not section:
            flash(
                "Selected section was not found under that school.",
                "error"
            )
            return redirect(
                url_for("admin_system_settings")
            )

    try:
        total_fee = float(total_fee_input)

        if total_fee < 0:
            raise ValueError

    except ValueError:
        flash(
            "Programme fee must be a valid non-negative amount.",
            "error"
        )
        return redirect(
            url_for("admin_system_settings")
        )

    existing = ProgramFee.query.filter_by(
        program=programme
    ).first()

    if existing:
        flash(
            f"A fee record already exists for {programme}.",
            "error"
        )
        return redirect(
            url_for("admin_system_settings")
        )

    # --------------------------------------------------------
    # The old category_id column is still required by the
    # database. Match the school to the corresponding legacy
    # category automatically.
    # --------------------------------------------------------

    category = ProgramFeeCategory.query.filter_by(
        name=school.name
    ).first()

    if not category:
        flash(
            "The legacy fee category for this school was not found.",
            "error"
        )
        return redirect(
            url_for("admin_system_settings")
        )

    fee = ProgramFee(
        category_id=category.id,
        school_id=school.id,
        section_id=section.id if section else None,
        program=programme,
        total_fee=total_fee
    )

    db.session.add(fee)
    db.session.commit()

    flash(
        f"Programme fee added for {programme}.",
        "success"
    )

    return redirect(
        url_for("admin_system_settings")
    )


@app.route(
    "/admin/system-settings/programme-fees/<int:fee_id>/edit",
    methods=["POST"]
)
def admin_edit_programme_fee(fee_id):

    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))

    fee = ProgramFee.query.get_or_404(fee_id)

    school_id_input = (
        request.form.get("school_id") or ""
    ).strip()

    section_id_input = (
        request.form.get("section_id") or ""
    ).strip()

    programme = (
        request.form.get("programme") or ""
    ).strip()

    total_fee_input = (
        request.form.get("total_fee") or ""
    ).strip()

    if not school_id_input or not programme:
        flash(
            "School and programme are required.",
            "error"
        )
        return redirect(
            url_for("admin_system_settings")
        )

    try:
        school_id = int(school_id_input)

    except ValueError:
        flash(
            "Invalid school selected.",
            "error"
        )
        return redirect(
            url_for("admin_system_settings")
        )

    school = ProgramFeeSchool.query.get(school_id)

    if not school:
        flash(
            "Selected school was not found.",
            "error"
        )
        return redirect(
            url_for("admin_system_settings")
        )

    section = None

    if section_id_input:
        try:
            section_id = int(section_id_input)

        except ValueError:
            flash(
                "Invalid section selected.",
                "error"
            )
            return redirect(
                url_for("admin_system_settings")
            )

        section = ProgramFeeSection.query.filter_by(
            id=section_id,
            school_id=school.id
        ).first()

        if not section:
            flash(
                "Selected section was not found under that school.",
                "error"
            )
            return redirect(
                url_for("admin_system_settings")
            )

    try:
        total_fee = float(total_fee_input)

        if total_fee < 0:
            raise ValueError

    except ValueError:
        flash(
            "Programme fee must be a valid non-negative amount.",
            "error"
        )
        return redirect(
            url_for("admin_system_settings")
        )

    duplicate = ProgramFee.query.filter(
        ProgramFee.program == programme,
        ProgramFee.id != fee.id
    ).first()

    if duplicate:
        flash(
            f"A fee record already exists for {programme}.",
            "error"
        )
        return redirect(
            url_for("admin_system_settings")
        )

    category = ProgramFeeCategory.query.filter_by(
        name=school.name
    ).first()

    if not category:
        flash(
            "The legacy fee category for this school was not found.",
            "error"
        )
        return redirect(
            url_for("admin_system_settings")
        )

    fee.category_id = category.id
    fee.school_id = school.id
    fee.section_id = section.id if section else None
    fee.program = programme
    fee.total_fee = total_fee

    db.session.commit()

    flash(
        f"Programme fee updated for {programme}.",
        "success"
    )

    return redirect(
        url_for("admin_system_settings")
    )


@app.route(
    "/admin/system-settings/programme-fees/<int:fee_id>/delete",
    methods=["POST"]
)
def admin_delete_programme_fee(fee_id):

    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))

    fee = ProgramFee.query.get_or_404(fee_id)

    programme = fee.program

    db.session.delete(fee)
    db.session.commit()

    flash(
        f"Programme fee removed for {programme}.",
        "success"
    )

    return redirect(
        url_for("admin_system_settings")
    )



# ==================================================
# ADMIN ANNOUNCEMENTS
# ==================================================


# ==================================================
# ADMIN STUDENTS
# ==================================================


@app.route("/admin/students/add", methods=["GET", "POST"])
def admin_add_student():

    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))

    if request.method == "GET":
        return render_template("admin/add_student.html")

    form_data = request.form

    student_id = form_data.get("student_id", "").strip()
    name = form_data.get("name", "").strip()
    gender = form_data.get("gender", "").strip().title()
    program = form_data.get("program", "").strip()
    funding = form_data.get("funding", "").strip()
    accommodation = form_data.get("accommodation", "").strip()
    date_text = form_data.get("date_of_birth", "").strip()
    nationality = form_data.get("nationality", "").strip()

    if not all([student_id, name, gender, program, funding,
                accommodation, date_text, nationality]):
        return render_template(
            "admin/add_student.html",
            error="Please complete all required fields.",
            form_data=form_data
        )

    if len(student_id) > 20 or len(name) > 150 or len(program) > 150:
        return render_template(
            "admin/add_student.html",
            error="Student ID, name or programme is too long.",
            form_data=form_data
        )

    if gender not in ("Male", "Female"):
        return render_template(
            "admin/add_student.html",
            error="Please select Male or Female.",
            form_data=form_data
        )

    if funding not in ("Self Sponsored", "CDF", "Bursary", "Other"):
        return render_template(
            "admin/add_student.html",
            error="Please select a valid funding type.",
            form_data=form_data
        )

    if accommodation not in ("Boarder", "Day Scholar"):
        return render_template(
            "admin/add_student.html",
            error="Please select Boarder or Day Scholar.",
            form_data=form_data
        )

    try:
        date_of_birth = datetime.strptime(
            date_text, "%Y-%m-%d"
        ).date()

        if date_of_birth > datetime.now().date():
            raise ValueError("Date of birth cannot be in the future.")

        year = int(form_data.get("year", ""))
        term = int(form_data.get("term", ""))

        if year < 1 or term < 1:
            raise ValueError("Year and term must be positive numbers.")

    except ValueError as exc:
        return render_template(
            "admin/add_student.html",
            error=str(exc) or "Enter a valid date, year and term.",
            form_data=form_data
        )

    if Student.query.filter_by(student_id=student_id).first():
        return render_template(
            "admin/add_student.html",
            error="That Student ID is already registered.",
            form_data=form_data
        )

    if User.query.filter(
        db.or_(
            User.username == student_id,
            User.student_id == student_id
        )
    ).first():
        return render_template(
            "admin/add_student.html",
            error="A login account already exists for that Student ID.",
            form_data=form_data
        )

    import secrets
    temporary_password = secrets.token_urlsafe(10)

    student = Student(
        student_id=student_id,
        name=name,
        gender=gender,
        date_of_birth=date_of_birth,
        nationality=nationality,
        residential_address=form_data.get("residential_address", "").strip() or None,
        phone_number=form_data.get("phone_number", "").strip() or None,
        alternative_phone=form_data.get("alternative_phone", "").strip() or None,
        email=form_data.get("email", "").strip() or None,
        next_of_kin_name=form_data.get("next_of_kin_name", "").strip() or None,
        next_of_kin_relationship=form_data.get("next_of_kin_relationship", "").strip() or None,
        next_of_kin_phone=form_data.get("next_of_kin_phone", "").strip() or None,
        next_of_kin_alternative_phone=form_data.get("next_of_kin_alternative_phone", "").strip() or None,
        next_of_kin_address=form_data.get("next_of_kin_address", "").strip() or None,
        program=program,
        year=year,
        term=term,
        funding=funding,
        accommodation=accommodation,
        hostel=None,
        room=None
    )

    user = User(
        username=student_id,
        password=generate_password_hash(temporary_password),
        role="student",
        student_id=student_id,
        password_change_required=True
    )

    try:
        db.session.add(student)
        db.session.flush()
        db.session.add(user)
        db.session.commit()

    except Exception as exc:
        db.session.rollback()
        print("Student registration failed:", exc)
        return render_template(
            "admin/add_student.html",
            error="Registration could not be completed. No records were saved.",
            form_data=form_data
        )

    return render_template(
        "admin/add_student.html",
        created_student=student,
        temporary_password=temporary_password
    )


@app.route("/admin/students")
def admin_students():

    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))

    search = request.args.get("search", "").strip()
    funding = request.args.get("funding", "").strip()

    query = Student.query

    if search:
        query = query.filter(
            db.or_(
                Student.student_id.ilike(f"%{search}%"),
                Student.name.ilike(f"%{search}%"),
                Student.program.ilike(f"%{search}%")
            )
        )

    if funding:
        query = query.filter(Student.funding == funding)

    students = query.order_by(Student.name.asc()).all()

    return render_template(
        "admin/students.html",
        students=students,
        search=search,
        funding=funding,
        total_students=Student.query.count()
    )



# ==================================================
# ADMIN STUDENT DETAILS
# ==================================================

@app.route("/admin/students/<student_id>")
def admin_student_details(student_id):

    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))

    student = Student.query.filter_by(
        student_id=student_id
    ).first_or_404()

    clearances = DepartmentClearance.query.filter_by(
        student_id=student.student_id
    ).all()

    account = Account.query.filter_by(
        student_id=student.student_id
    ).first()

    payments = Payment.query.filter_by(
        student_id=student.student_id
    ).order_by(
        Payment.id.desc()
    ).all()

    library_books = LibraryBook.query.filter_by(
        student_id=student.student_id
    ).order_by(
        LibraryBook.id.desc()
    ).all()

    sports_items = SportsItem.query.filter_by(
        student_id=student.student_id
    ).order_by(
        SportsItem.id.desc()
    ).all()

    ame_tools = AMETool.query.filter_by(
        student_id=student.student_id
    ).order_by(
        AMETool.id.desc()
    ).all()

    store_properties = StoreProperty.query.filter_by(
        student_id=student.student_id
    ).order_by(
        StoreProperty.id.desc()
    ).all()

    return render_template(
        "admin/student_details.html",
        student=student,
        clearances=clearances,
        account=account,
        payments=payments,
        library_books=library_books,
        sports_items=sports_items,
        ame_tools=ame_tools,
        store_properties=store_properties
    )


@app.route("/new-staff/library/announcements")
def new_staff_library_announcements():

    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    department = (
        session.get("department") or ""
    ).strip().lower()

    if department not in {
        "library",
        "library department"
    }:
        return redirect(url_for("new_staff_login"))

    announcements = Announcement.query.filter(
        Announcement.active == True,
        Announcement.audience.in_(["staff", "all"])
    ).order_by(
        Announcement.created_at.desc()
    ).all()

    return render_template(
        "new_staff/library/announcements.html",
        announcements=announcements
    )


# --------------------------------------------------
# NEW STAFF ACCOUNTS — ANNOUNCEMENTS
# --------------------------------------------------

@app.route("/new-staff/accounts/announcements")
def new_staff_accounts_announcements():

    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    department = (
        session.get("department") or ""
    ).strip().lower()

    if department not in {
        "accounts",
        "accounts department"
    }:
        return redirect(url_for("new_staff_login"))

    announcements = Announcement.query.filter(
        Announcement.active == True,
        Announcement.audience.in_(["staff", "all"])
    ).order_by(
        Announcement.created_at.desc()
    ).all()

    return render_template(
        "new_staff/accounts/announcements.html",
        announcements=announcements,
        staff_name=session.get("staff_name")
        or session.get("name")
        or "Accounts Staff"
    )



# ============================================================
# HR — ANNOUNCEMENTS
# ============================================================

@app.route("/new-staff/hr/announcements")
def new_staff_hr_announcements():

    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    department = (
        session.get("department") or ""
    ).strip().lower()

    allowed_departments = {
        "human resource / admin officer",
        "human resource/admin officer",
        "human resource",
        "hr",
    }

    if department not in allowed_departments:
        return redirect(url_for("new_staff_login"))

    announcements = (
        Announcement.query
        .filter(
            Announcement.active == True,
            Announcement.audience.in_(["staff", "all"])
        )
        .order_by(
            Announcement.created_at.desc()
        )
        .all()
    )

    return render_template(
        "new_staff/hr_announcements.html",
        staff_name=(
            session.get("staff_name")
            or session.get("name")
            or session.get("username")
            or "HR Staff"
        ),
        department=(
            session.get("department")
            or "Human Resource / Admin Officer"
        ),
        announcements=announcements
    )


@app.route("/admin/announcements")
def admin_announcements():

    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))

    announcements = Announcement.query.order_by(
        Announcement.created_at.desc()
    ).all()

    return render_template(
        "admin/announcements.html",
        announcements=announcements
    )


@app.route("/admin/announcements/add", methods=["POST"])
def admin_add_announcement():

    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))

    title = request.form.get("title", "").strip()
    message = request.form.get("message", "").strip()

    send_staff = request.form.get("send_staff")
    send_students = request.form.get("send_students")

    if not title or not message:
        flash("Please enter both a title and message.", "error")
        return redirect(url_for("admin_announcements"))

    if send_staff and send_students:
        audience = "all"
    elif send_staff:
        audience = "staff"
    elif send_students:
        audience = "students"
    else:
        flash("Please select at least one audience.", "error")
        return redirect(url_for("admin_announcements"))

    announcement = Announcement(
        title=title,
        message=message,
        audience=audience,
        created_by=session.get("user_id"),
        active=True
    )

    db.session.add(announcement)
    db.session.commit()

    flash("Announcement published successfully.", "success")

    return redirect(url_for("admin_announcements"))


@app.route(
    "/admin/announcements/<int:announcement_id>/toggle",
    methods=["POST"]
)
def admin_toggle_announcement(announcement_id):

    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))

    announcement = Announcement.query.get_or_404(
        announcement_id
    )

    announcement.active = not announcement.active

    db.session.commit()

    flash("Announcement status updated.", "success")

    return redirect(url_for("admin_announcements"))


@app.route(
    "/admin/announcements/<int:announcement_id>/delete",
    methods=["POST"]
)
def admin_delete_announcement(announcement_id):

    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))

    announcement = Announcement.query.get_or_404(
        announcement_id
    )

    db.session.delete(announcement)
    db.session.commit()

    flash("Announcement deleted.", "success")

    return redirect(url_for("admin_announcements"))



# ------------------------------------------------------------
# STUDENT CLEARANCE FORMS
# ------------------------------------------------------------

@app.route("/student/clearance_forms")
def student_clearance_forms():
    if session.get("role") != "student":
        return redirect(url_for("student_login"))

    sid = session.get("student_id")

    if not sid:
        sid = session.get("user")

    if not sid:
        return "<h3>No student ID found in session.</h3>", 404

    student = Student.query.filter_by(
        student_id=str(sid)
    ).first()

    if not student:
        return f"""
        <h3>Student not found</h3>
        <p>Student ID: {sid}</p>
        """, 404

    forms = ClearanceHistory.query.filter_by(
        student_id=student.student_id
    ).order_by(
        ClearanceHistory.id.desc()
    ).all()

    return render_template(
        "student/clearance_forms.html",
        student=student,
        forms=forms
    )

@app.route("/admin/clearance-history")
def admin_clearance_history():

    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))

    search = request.args.get("search", "").strip()

    query = ClearanceHistory.query

    if search:
        matching_students = Student.query.filter(
            db.or_(
                Student.student_id.ilike(f"%{search}%"),
                Student.name.ilike(f"%{search}%"),
                Student.program.ilike(f"%{search}%")
            )
        ).all()

        matching_ids = [
            student.student_id
            for student in matching_students
        ]

        if matching_ids:
            query = query.filter(
                ClearanceHistory.student_id.in_(matching_ids)
            )
        else:
            query = query.filter(
                ClearanceHistory.student_id == "__NO_MATCH__"
            )

    history = query.order_by(
        ClearanceHistory.id.desc()
    ).all()

    student_map = {}

    if history:
        student_ids = list({
            record.student_id
            for record in history
        })

        students = Student.query.filter(
            Student.student_id.in_(student_ids)
        ).all()

        student_map = {
            student.student_id: student
            for student in students
        }

    return render_template(
        "admin/clearance_history.html",
        history=history,
        student_map=student_map,
        search=search
    )

# ============================================================
# START FLASK APPLICATION
# ============================================================


# ============================================================
# STUDENT RESET PASSWORD
# ============================================================

@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():

    if not session.get("user_id"):
        return redirect(url_for("student_login"))

    user = User.query.get(session.get("user_id"))

    if not user:
        session.clear()
        return redirect(url_for("student_login"))

    if request.method == "POST":

        current_password = request.form.get(
            "current_password",
            ""
        ).strip()

        new_password = request.form.get(
            "new_password",
            ""
        ).strip()

        confirm_password = request.form.get(
            "confirm_password",
            ""
        ).strip()

        if not check_password_hash(
            user.password,
            current_password
        ):
            return render_template(
                "student/reset_password.html",
                error="Current password is incorrect."
            )

        if not new_password:
            return render_template(
                "student/reset_password.html",
                error="Please enter a new password."
            )

        if len(new_password) < 6:
            return render_template(
                "student/reset_password.html",
                error="New password must be at least 6 characters."
            )

        if new_password != confirm_password:
            return render_template(
                "student/reset_password.html",
                error="New passwords do not match."
            )

        if new_password == current_password:
            return render_template(
                "student/reset_password.html",
                error="Your new password must be different from your current password."
            )

        user.password = generate_password_hash(
            new_password
        )
        user.password_change_required = False

        db.session.commit()

        return render_template(
            "student/reset_password.html",
            success="Your password has been changed successfully."
        )

    return render_template(
        "student/reset_password.html"
    )





# ============================================================
# ADMIN — DEPARTMENT ACTIVITY HISTORY
# ============================================================


# ============================================================
# ADMIN — DEPARTMENT ACTIVITY HISTORY
# ============================================================

@app.route("/admin/department-history")
def admin_department_history():

    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))

    search = request.args.get("search", "").strip()
    selected_department = request.args.get("department", "").strip()

    # --------------------------------------------------------
    # AVAILABLE DEPARTMENTS
    # --------------------------------------------------------

    departments = [
        "Library",
        "Communication Skills",
        "Mathematics",
        "Human Resource",
        "Sports",
        "AME Stores",
        "Head of Training Section",
        "Accounts",
        "Technical Services Office",
        "Stores",
        "Hostel",
    ]

    # --------------------------------------------------------
    # STUDENT LOOKUP
    # --------------------------------------------------------

    students = {}

    for student in Student.query.all():
        students[str(student.student_id)] = student

    # --------------------------------------------------------
    # COMBINED HISTORY
    # --------------------------------------------------------

    history = []

    # ========================================================
    # DEPARTMENT HISTORY
    # ========================================================

    department_query = DepartmentHistory.query

    if selected_department:
        department_query = department_query.filter(
            db.func.lower(DepartmentHistory.department)
            == selected_department.lower()
        )

    department_records = (
        department_query
        .order_by(DepartmentHistory.created_at.desc())
        .all()
    )

    for record in department_records:

        student_id = str(record.student_id)
        student = students.get(student_id)

        student_name = (
            getattr(student, "name", None)
            if student
            else None
        )

        # Search
        if search:
            searchable = " ".join([
                student_id,
                student_name or "",
                record.department or "",
                record.status or "",
                record.action or "",
                record.remarks or "",
                record.performed_by or "",
            ]).lower()

            if search.lower() not in searchable:
                continue

        history.append({
            "source": "Department Activity",
            "student_id": student_id,
            "student_name": student_name or "Unknown Student",
            "department": record.department or "—",
            "item": record.action or "Department Clearance",
            "item_type": "Department Activity",
            "status": record.status or "—",
            "performed_by": record.performed_by or "—",
            "assigned_at": record.created_at,
            "responded_at": None,
            "remarks": record.remarks or "",
        })

    # ========================================================
    # ITEM REQUEST HISTORY
    # ========================================================

    request_query = ItemRequest.query

    if selected_department:
        request_query = request_query.filter(
            db.func.lower(ItemRequest.department)
            == selected_department.lower()
        )

    request_records = (
        request_query
        .order_by(ItemRequest.id.desc())
        .all()
    )

    for record in request_records:

        student_id = str(record.student_id)
        student = students.get(student_id)

        student_name = (
            getattr(student, "name", None)
            if student
            else None
        )

        # Search
        if search:
            searchable = " ".join([
                student_id,
                student_name or "",
                record.department or "",
                record.item or "",
                record.item_type or "",
                record.status or "",
                record.assigned_by or "",
                record.remarks or "",
            ]).lower()

            if search.lower() not in searchable:
                continue

        history.append({
            "source": "Item Request",
            "student_id": student_id,
            "student_name": student_name or "Unknown Student",
            "department": record.department or "—",
            "item": record.item or "—",
            "item_type": record.item_type or "—",
            "status": record.status or "Pending",
            "performed_by": get_staff_display_name(
                record.assigned_by
            ),
            "assigned_at": record.assigned_at,
            "responded_at": record.responded_at,
            "remarks": record.remarks or "",
        })

    # --------------------------------------------------------
    # SORT EVERYTHING TOGETHER
    # --------------------------------------------------------

    def history_time(record):

        return (
            record.get("responded_at")
            or record.get("assigned_at")
            or datetime.min
        )

    history.sort(
        key=history_time,
        reverse=True
    )

    return render_template(
        "admin/department_history.html",
        history=history,
        departments=departments,
        selected_department=selected_department,
        search=search,
        total_records=len(history),
    )



# ============================================================
# HUMAN RESOURCE — STUDENT DISCIPLINE
# ============================================================









# ============================================================
# NEW STAFF APPLICATION
# ============================================================


@app.route("/new-staff/dashboard")
def new_staff_dashboard():

    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    return render_template(
        "new_staff/dashboard.html",
        staff_name=session.get("staff_name"),
        department=session.get("department")
    )

@app.route("/new-staff/login", methods=["GET", "POST"])
def new_staff_login():

    if request.method == "POST":

        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        if not username or not password:
            return render_template(
                "new_staff/login.html",
                error="Please enter your username and password."
            )

        # --------------------------------------------------
        # STAFF AUTHENTICATION ONLY
        # --------------------------------------------------

        user = User.query.filter_by(
            username=username
        ).first()

        if not user:
            return render_template(
                "new_staff/login.html",
                error="Invalid username or password."
            )

        # This login is ONLY for Staff.
        if str(user.role).strip().lower() != "staff":
            return render_template(
                "new_staff/login.html",
                error="This login is for Staff accounts only."
            )

        # --------------------------------------------------
        # STAFF ACCOUNT STATUS CHECK
        # --------------------------------------------------
        # Admin activates/deactivates staff through the Staff
        # record, so login must respect Staff.active.
        staff_member = Staff.query.filter_by(
            user_id=user.id
        ).first()

        if not staff_member:
            return render_template(
                "new_staff/login.html",
                error="Staff account is not properly configured."
            )

        if not staff_member.active:
            return render_template(
                "new_staff/login.html",
                error="This staff account has been deactivated. Please contact the administrator."
            )

        # --------------------------------------------------
        # PASSWORD CHECK
        # Supports the password format already used by
        # the existing application.
        # --------------------------------------------------

        password_valid = False

        try:
            from werkzeug.security import check_password_hash

            password_valid = check_password_hash(
                user.password,
                password
            )
        except Exception:
            password_valid = False

        # Compatibility with systems where passwords were
        # previously stored as plain text.
        if not password_valid:
            password_valid = str(user.password) == password

        if not password_valid:
            return render_template(
                "new_staff/login.html",
                error="Invalid username or password."
            )

        # --------------------------------------------------
        # CREATE STAFF SESSION
        # Uses the existing User record.
        # Staff profile is NOT required for login.
        # --------------------------------------------------

        session.clear()

        session["role"] = "staff"
        session["user_id"] = user.id
        session["username"] = user.username

        # Get the full name registered by Admin in the Staff profile.
        staff_member = Staff.query.filter_by(
            user_id=user.id
        ).first()

        staff_full_name = (
            staff_member.name
            if staff_member and staff_member.name
            else user.username
        )

        session["staff_name"] = staff_full_name
        session["name"] = staff_full_name
        session["department"] = user.department or ""

        # --------------------------------------------------
        # FIRST LOGIN PASSWORD CHANGE
        # --------------------------------------------------

        if getattr(user, "password_change_required", False):
            return redirect(url_for("staff_change_password"))

        # --------------------------------------------------
        # DEPARTMENT ROUTING
        # --------------------------------------------------

        department = (
            user.department or ""
        ).strip().lower()

        if department in {
            "library",
            "library department"
        }:
            return redirect(
                url_for("new_staff_library_dashboard")
            )

        if department in {
            "sports",
            "sports department"
        }:
            return redirect(
                url_for("new_staff_sports_dashboard")
            )

        if department in {
            "accounts",
            "accounts department"
        }:
            return redirect(
                url_for("new_staff_accounts_dashboard")
            )

        if department in {
            "stores",
            "stores department",
            "stores office",
            "stores officer"
        }:
            return redirect(
                url_for("new_staff_stores_dashboard")
            )

        if department in {
            "hostel",
            "hostel department",
            "hostel office",
            "hostels (hos)"
        }:
            return redirect(
                url_for("hostel_dashboard")
            )

        if department in {
            "tso",
            "tso department",
            "tso office",
            "technical services office",
            "technical services office department",
            "technical services office (tso)"
        }:
            return redirect(
                url_for("tso_dashboard")
            )

        if department in {
            "training section"
        }:
            return redirect(
                url_for("new_staff_training_section_dashboard")
            )

        if department in {
            "ame stores",
            "ame stores department",
            "ame",
        }:
            return redirect(
                url_for("new_staff_ame_dashboard")
            )

        if department in {
            "communication skills (rel/sc)",
            "communication skills (rel sc)",
            "communication skills",
        }:
            return redirect(
                url_for("new_staff_communication_dashboard")
            )

        if department in {
            "mathematics",
            "mathematics department",
        }:
            return redirect(
                url_for("new_staff_mathematics_dashboard")
            )


        if department in {
            "human resource / admin officer",
            "human resource/admin officer",
            "human resource",
            "hr",
        }:
            return redirect(
                url_for("new_staff_hr_dashboard")
            )
        # Other departments will be connected one-by-one.
        return render_template(
            "new_staff/login.html",
            error=(
                f"Staff login successful, but the "
                f"{user.department} dashboard has not been "
                f"connected yet."
            )
        )

    return render_template(
        "new_staff/login.html"
    )




# ============================================================
# NEW STAFF SPORTS — STUDENTS
# ============================================================


# ============================================================
# NEW STAFF SPORTS — FOOTBALL
# ============================================================

@app.route("/new-staff/sports/football")
def new_staff_sports_football():

    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    department = (
        session.get("department") or ""
    ).strip().lower()

    if department not in {
        "sports",
        "sports department"
    }:
        return redirect(url_for("new_staff_login"))

    search = (
        request.args.get("search") or ""
    ).strip()

    query = Student.query

    if search:
        query = query.filter(
            db.or_(
                Student.student_id.ilike(f"%{search}%"),
                Student.name.ilike(f"%{search}%")
            )
        )

    students = query.order_by(
        Student.name.asc()
    ).all()

    football_students = []

    for student in students:

        items = SportsItem.query.filter(
            SportsItem.student_id == student.student_id,
            db.func.lower(
                db.func.trim(SportsItem.sport)
            ) == "football"
        ).order_by(
            SportsItem.id.desc()
        ).all()

        if items:
            football_students.append({
                "student": student,
                "items": items
            })

    return render_template(
        "new_staff/sports/football.html",
        staff_name=session.get("staff_name"),
        department=session.get("department"),
        students=football_students,
        search=search
    )


# ============================================================
# NEW STAFF SPORTS — STUDENTS / ASSIGN ITEMS
# ============================================================

@app.route("/new-staff/sports/students", methods=["GET", "POST"])
def new_staff_sports_students():

    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    department = (
        session.get("department") or ""
    ).strip().lower()

    if department not in {
        "sports",
        "sports department"
    }:
        return redirect(url_for("new_staff_login"))

    disciplines = [
        "football",
        "basketball",
        "volleyball",
        "netball",
        "chess"
    ]

    # ========================================================
    # ASSIGN SPORTS ITEM
    # ========================================================

    if request.method == "POST":

        student_id = (
            request.form.get("student_id") or ""
        ).strip()

        sport = (
            request.form.get("sport") or ""
        ).strip().lower()

        item_name = (
            request.form.get("item") or ""
        ).strip()

        if not student_id:
            flash("Student ID is required.", "error")
            return redirect(
                url_for("new_staff_sports_students")
            )

        if sport not in disciplines:
            flash("Invalid sport selected.", "error")
            return redirect(
                url_for("new_staff_sports_students")
            )

        if not item_name:
            flash(
                "Please enter the item being assigned.",
                "error"
            )
            return redirect(
                url_for("new_staff_sports_students")
            )

        student = Student.query.filter_by(
            student_id=student_id
        ).first()

        if not student:
            flash("Student not found.", "error")
            return redirect(
                url_for("new_staff_sports_students")
            )

        existing = SportsItem.query.filter(
            SportsItem.student_id == student_id,
            db.func.lower(
                db.func.trim(SportsItem.sport)
            ) == sport,
            db.func.lower(
                db.func.trim(SportsItem.item)
            ) == item_name.lower(),
            db.func.lower(
                db.func.trim(
                    db.func.coalesce(
                        SportsItem.status,
                        ""
                    )
                )
            ) == "pending"
        ).first()

        if existing:
            flash(
                "This item is already pending confirmation for this student.",
                "error"
            )
            return redirect(
                url_for("new_staff_sports_students")
            )

        new_item = SportsItem(
            student_id=student_id,
            sport=sport,
            item=item_name,
            status="pending",
            created_at=zambia_now(),
            responded_at=None,
            returned_at=None,
            remarks=(
                "Assigned by Sports Staff. "
                "Awaiting student confirmation."
            )
        )

        db.session.add(new_item)
        db.session.commit()

        flash(
            f"{item_name} assigned to {student.name}. "
            "Waiting for student confirmation.",
            "success"
        )

        return redirect(
            url_for("new_staff_sports_students")
        )

    # ========================================================
    # SEARCH STUDENTS
    # ========================================================

    search = (
        request.args.get("search") or ""
    ).strip()

    query = Student.query

    if search:
        query = query.filter(
            db.or_(
                Student.student_id.ilike(f"%{search}%"),
                Student.name.ilike(f"%{search}%")
            )
        )

    students = query.order_by(
        Student.name.asc()
    ).all()

    # ========================================================
    # GROUP SPORTS ITEMS
    # ========================================================

    students_data = []

    for student in students:

        items = SportsItem.query.filter_by(
            student_id=student.student_id
        ).order_by(
            SportsItem.id.desc()
        ).all()

        grouped = {
            sport: []
            for sport in disciplines
        }

        for item in items:

            sport = (
                item.sport or ""
            ).strip().lower()

            if sport in grouped:
                grouped[sport].append(item)

        students_data.append({
            "student": student,
            "sports": grouped,
            "total_items": len(items)
        })

    return render_template(
        "new_staff/sports/students.html",
        staff_name=(
            session.get("staff_name")
            or session.get("name")
            or session.get("username")
            or "Sports Staff"
        ),
        department=(
            session.get("department")
            or "Sports"
        ),
        students=students_data,
        search=search,
        disciplines=disciplines
    )


# ============================================================
# NEW STAFF SPORTS — DASHBOARD
# ============================================================


# ============================================================
# NEW STAFF SPORTS — SPORTS CLEARANCE RECORDS
# ============================================================

@app.route("/new-staff/sports/records", methods=["GET"])
def new_staff_sports_records():

    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    department = (
        session.get("department") or ""
    ).strip().lower()

    if department not in {
        "sports",
        "sports department"
    }:
        return redirect(url_for("new_staff_login"))

    import sqlite3

    con = sqlite3.connect("database.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    search = (
        request.args.get("search") or ""
    ).strip()

    status_filter = (
        request.args.get("status") or ""
    ).strip().lower()

    query = """
        SELECT
            si.id,
            si.student_id,
            si.sport,
            si.item,
            si.status,
            si.remarks,
            si.created_at,
            si.returned_at,
            si.responded_at,
            s.name AS student_name,
            s.program
        FROM sports_items si
        LEFT JOIN students s
            ON s.student_id = si.student_id
        WHERE 1 = 1
    """

    params = []

    if search:
        query += """
            AND (
                LOWER(COALESCE(si.student_id, '')) LIKE ?
                OR LOWER(COALESCE(si.sport, '')) LIKE ?
                OR LOWER(COALESCE(si.item, '')) LIKE ?
                OR LOWER(COALESCE(si.remarks, '')) LIKE ?
                OR LOWER(COALESCE(s.name, '')) LIKE ?
                OR LOWER(COALESCE(s.program, '')) LIKE ?
            )
        """

        value = f"%{search.lower()}%"

        params.extend([
            value,
            value,
            value,
            value,
            value,
            value
        ])

    if status_filter:
        query += """
            AND LOWER(COALESCE(si.status, '')) = ?
        """

        params.append(status_filter)

    query += """
        ORDER BY si.id DESC
    """

    records = cur.execute(
        query,
        params
    ).fetchall()

    con.close()

    return render_template(
        "new_staff/sports/records.html",
        records=records,
        search=search,
        status_filter=status_filter
    )


@app.route("/new-staff/sports/dashboard")
def new_staff_sports_dashboard():

    # --------------------------------------------------
    # SPORTS STAFF ONLY
    # --------------------------------------------------

    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    if (session.get("department") or "").strip().lower() != "sports":
        department = (
            session.get("department") or ""
        ).strip().lower()

        if department in {
            "accounts",
            "accounts department"
        }:
            return redirect(
                url_for("new_staff_accounts_dashboard")
            )

        if department in {
            "library",
            "library department"
        }:
            return redirect(
                url_for("new_staff_library_dashboard")
            )

        return redirect(
            url_for("new_staff_login")
        )

    # --------------------------------------------------
    # SEARCH
    # --------------------------------------------------

    search = (request.args.get("search") or "").strip()

    query = Student.query

    if search:
        query = query.filter(
            db.or_(
                Student.student_id.ilike(f"%{search}%"),
                Student.name.ilike(f"%{search}%")
            )
        )

    students = query.order_by(
        Student.name.asc()
    ).all()

    # --------------------------------------------------
    # SPORTS DATA
    # --------------------------------------------------

    sports_data = []

    disciplines = [
        "football",
        "basketball",
        "volleyball",
        "netball",
        "chess"
    ]

    for student in students:

        items = SportsItem.query.filter_by(
            student_id=student.student_id
        ).order_by(
            SportsItem.id.desc()
        ).all()

        grouped = {
            discipline: []
            for discipline in disciplines
        }

        for item in items:

            sport = (item.sport or "").strip().lower()

            if sport not in grouped:
                grouped[sport] = []

            grouped[sport].append(item)

        sports_data.append({
            "student": student,
            "sports": grouped,
            "total_items": len(items)
        })

    # --------------------------------------------------
    # ANNOUNCEMENTS
    # --------------------------------------------------

    announcement_count = Announcement.query.filter(
        db.func.coalesce(Announcement.active, True) == True,
        db.func.lower(
            db.func.trim(
                db.func.coalesce(Announcement.audience, "")
            )
        ).in_(["staff", "all"])
    ).count()

    announcements = Announcement.query.filter(
        db.func.coalesce(Announcement.active, True) == True,
        db.func.lower(
            db.func.trim(
                db.func.coalesce(Announcement.audience, "")
            )
        ).in_(["staff", "all"])
    ).order_by(
        Announcement.created_at.desc()
    ).limit(5).all()

    # --------------------------------------------------
    # DASHBOARD
    # --------------------------------------------------

    # --------------------------------------------------
    # DASHBOARD SETTINGS
    # Existing staff mini academic calendar/clock uses
    # these values from system_settings.
    # --------------------------------------------------
    import sqlite3

    calendar_conn = sqlite3.connect(DATABASE_URL)
    calendar_cursor = calendar_conn.cursor()

    calendar_cursor.execute("""
        SELECT setting_key, setting_value
        FROM system_settings
    """)

    settings = dict(calendar_cursor.fetchall())

    calendar_conn.close()

    return render_template(
        "new_staff/sports/dashboard.html",
        staff_name=session.get("staff_name"),
        department=session.get("department"),
        students=sports_data,
        search=search,
        disciplines=disciplines,
        announcement_count=announcement_count,
        announcements=announcements,
        settings=settings,
    )


# ============================================================
# NEW STAFF LIBRARY — RETURN BOOKS
# ============================================================

@app.route("/new-staff/library/return-books", methods=["GET", "POST"])
def new_staff_library_return_books():

    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    department = (
        session.get("department") or ""
    ).strip().lower()

    if department not in {
        "library",
        "library department"
    }:
        return redirect(url_for("new_staff_login"))

    import sqlite3
    from datetime import datetime

    con = sqlite3.connect("database.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    error = None
    success = None

    # ========================================================
    # RETURN SELECTED BOOKS
    # ========================================================

    if request.method == "POST":

        student_id = (
            request.form.get("student_id") or ""
        ).strip()

        selected_books = request.form.getlist("book_ids")

        if not student_id:

            error = "Please select a student."

        elif not selected_books:

            error = "Please select at least one book to return."

        else:

            student = cur.execute(
                """
                SELECT student_id, name, program
                FROM students
                WHERE student_id = ?
                """,
                (student_id,)
            ).fetchone()

            if not student:

                error = "Student not found."

            else:

                returned_count = 0

                returned_names = []

                returned_at = zambia_now().strftime(
                    "%d %B %Y | %I:%M %p"
                )

                for book_id in selected_books:

                    try:
                        book_id = int(book_id)
                    except (TypeError, ValueError):
                        continue

                    book = cur.execute(
                        """
                        SELECT id, name
                        FROM library_books
                        WHERE id = ?
                          AND student_id = ?
                          AND COALESCE(status, '') = 'borrowed'
                          AND COALESCE(returned, 0) = 0
                        LIMIT 1
                        """,
                        (
                            book_id,
                            student_id
                        )
                    ).fetchone()

                    if not book:
                        continue

                    cur.execute(
                        """
                        UPDATE library_books
                        SET
                            returned = 1,
                            returned_at = ?
                        WHERE id = ?
                          AND student_id = ?
                          AND COALESCE(status, '') = 'borrowed'
                          AND COALESCE(returned, 0) = 0
                        """,
                        (
                            returned_at,
                            book_id,
                            student_id
                        )
                    )

                    returned_count += 1
                    returned_names.append(book["name"])

                    staff_name = (
                        session.get("staff_name")
                        or session.get("name")
                        or session.get("username")
                        or "Unknown Staff"
                    )
                    cur.execute(
                        """
                        INSERT INTO department_history
                        (student_id, department, status, remarks,
                         action, performed_by, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            student_id,
                            "library",
                            "Returned",
                            f"Book: {book['name']}",
                            "Book returned",
                            staff_name,
                            zambia_now().strftime("%Y-%m-%d %H:%M:%S"),
                        ),
                    )

                con.commit()

                if returned_count == 0:

                    error = (
                        "No valid borrowed books were found "
                        "to return."
                    )

                else:

                    success = (
                        f"{returned_count} book(s) returned for "
                        f"{student['name']}."
                    )

    # ========================================================
    # STUDENTS
    # ========================================================

    students = cur.execute(
        """
        SELECT
            student_id,
            name,
            program
        FROM students
        ORDER BY name
        """
    ).fetchall()

    # ========================================================
    # CURRENTLY BORROWED BOOKS
    # ========================================================

    borrowed_books = cur.execute(
        """
        SELECT
            lb.id,
            lb.student_id,
            lb.name AS book_name,
            lb.borrowed_at,
            s.name AS student_name,
            s.program
        FROM library_books lb
        LEFT JOIN students s
            ON s.student_id = lb.student_id
        WHERE COALESCE(lb.status, '') = 'borrowed'
          AND COALESCE(lb.returned, 0) = 0
        ORDER BY
            s.name,
            lb.id DESC
        """
    ).fetchall()

    # ========================================================
    # GROUP BOOKS BY STUDENT
    # ========================================================

    student_books = {}

    for book in borrowed_books:
        sid = book["student_id"]

        if sid not in student_books:
            student_books[sid] = []

        student_books[sid].append({
            "id": book["id"],
            "student_id": book["student_id"],
            "book_name": book["book_name"],
            "borrowed_at": book["borrowed_at"],
            "student_name": book["student_name"],
            "program": book["program"]
        })
    con.close()

    return render_template(
        "new_staff/library/return_books.html",
        students=students,
        student_books=student_books,
        error=error,
        success=success
    )



# ============================================================
# NEW STAFF LIBRARY — BOOK RECORDS
# ============================================================

@app.route("/new-staff/library/book-records", methods=["GET"])
def new_staff_library_book_records():
    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    department = (
        session.get("department") or ""
    ).strip().lower()

    if department not in {
        "library",
        "library department"
    }:
        return redirect(url_for("new_staff_login"))

    import sqlite3

    con = sqlite3.connect("database.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    search = (
        request.args.get("search") or ""
    ).strip()

    status_filter = (
        request.args.get("status") or ""
    ).strip().lower()

    print(
        "BOOK RECORDS FILTER RECEIVED:",
        repr(status_filter)
    )

    query = """
        SELECT
            lb.id,
            lb.student_id,
            lb.name AS book_name,
            lb.borrowed_at,
            lb.returned,
            lb.returned_at,
            lb.status,
            s.name AS student_name,
            s.program
        FROM library_books lb
        LEFT JOIN students s
            ON s.student_id = lb.student_id
        WHERE 1 = 1
    """

    params = []

    if search:
        query += """
            AND (
                LOWER(COALESCE(lb.student_id, '')) LIKE ?
                OR LOWER(COALESCE(lb.name, '')) LIKE ?
                OR LOWER(COALESCE(s.name, '')) LIKE ?
                OR LOWER(COALESCE(s.program, '')) LIKE ?
            )
        """

        search_value = f"%{search.lower()}%"

        params.extend([
            search_value,
            search_value,
            search_value,
            search_value
        ])

    if status_filter == "borrowed":

        query += """
            AND COALESCE(lb.returned, 0) = 0
            AND LOWER(COALESCE(lb.status, 'borrowed')) = 'borrowed'
        """

    elif status_filter == "returned":

        query += """
            AND COALESCE(lb.returned, 0) = 1
            AND LOWER(COALESCE(lb.status, '')) != 'declined'
        """

    elif status_filter == "pending":

        query += """
            AND LOWER(COALESCE(lb.status, '')) = 'pending'
            AND COALESCE(lb.returned, 0) = 0
        """

    elif status_filter == "declined":

        query += """
            AND LOWER(COALESCE(lb.status, '')) = 'declined'
        """

    query += """
        ORDER BY lb.id DESC
    """

    print(
        "BOOK RECORDS FILTER SQL:",
        status_filter
    )

    records = cur.execute(
        query,
        params
    ).fetchall()

    print(
        "BOOK RECORDS FILTER RESULT:",
        status_filter or "all",
        "=>",
        len(records),
        "records"
    )

    con.close()

    return render_template(
        "new_staff/library/book_records.html",
        records=records,
        search=search,
        status_filter=status_filter
    )

@app.route("/new-staff/library/assign-books", methods=["GET", "POST"])
def new_staff_library_assign_books():

    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    department = (
        session.get("department") or ""
    ).strip().lower()

    if department not in {
        "library",
        "library department"
    }:
        return redirect(url_for("new_staff_login"))

    import sqlite3

    from datetime import datetime

    con = sqlite3.connect("database.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    error = None
    success = None

    # ========================================================
    # AVAILABLE BOOKS
    # ========================================================

    book_names = [
        row["name"]
        for row in cur.execute(
            """
            SELECT DISTINCT name
            FROM library_books
            WHERE name IS NOT NULL
              AND TRIM(name) != ''
            ORDER BY name COLLATE NOCASE
            """
        ).fetchall()
    ]

    # ========================================================
    # ASSIGN BOOKS
    # ========================================================

    if request.method == "POST":

        student_id = (
            request.form.get("student_id") or ""
        ).strip()

        book_1 = (
            request.form.get("book_1") or ""
        ).strip()

        book_2 = (
            request.form.get("book_2") or ""
        ).strip()

        selected_books = []

        for book in (book_1, book_2):
            if book and book not in selected_books:
                selected_books.append(book)

        if not student_id:
            error = "Student ID is required."

        elif not selected_books:
            error = "Please select at least one book."

        else:

            student = cur.execute(
                """
                SELECT
                    student_id,
                    name,
                    program
                FROM students
                WHERE student_id = ?
                """,
                (student_id,)
            ).fetchone()

            if not student:

                error = "Student not found."

            else:

                active_count = cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM library_books
                    WHERE student_id = ?
                      AND COALESCE(status, '') = 'borrowed'
                      AND COALESCE(returned, 0) = 0
                    """,
                    (student_id,)
                ).fetchone()[0]

                pending_count = cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM library_books
                    WHERE student_id = ?
                      AND COALESCE(status, '') = 'pending'
                    """,
                    (student_id,)
                ).fetchone()[0]

                available_slots = 2 - active_count - pending_count

                if available_slots <= 0:

                    error = (
                        "This student already has 2 active or "
                        "pending book assignments."
                    )

                elif len(selected_books) > available_slots:

                    error = (
                        f"Only {available_slots} book slot(s) "
                        f"are available for this student."
                    )

                else:

                    added = []
                    skipped = []

                    for book_name in selected_books:

                        existing_pending = cur.execute(
                            """
                            SELECT id
                            FROM library_books
                            WHERE student_id = ?
                              AND LOWER(TRIM(name)) =
                                  LOWER(TRIM(?))
                              AND COALESCE(status, '') = 'pending'
                            LIMIT 1
                            """,
                            (
                                student_id,
                                book_name
                            )
                        ).fetchone()

                        if existing_pending:
                            skipped.append(book_name)
                            continue

                        cur.execute(
                            """
                            INSERT INTO library_books
                            (
                                student_id,
                                name,
                                borrowed_at,
                                returned,
                                returned_at,
                                status
                            )
                            VALUES (?, ?, NULL, 0, NULL, 'pending')
                            """,
                            (
                                student_id,
                                book_name
                            )
                        )

                        staff_name = (
                            session.get("staff_name")
                            or session.get("name")
                            or session.get("username")
                            or "Unknown Staff"
                        )
                        cur.execute(
                            """
                            INSERT INTO department_history
                            (student_id, department, status, remarks,
                             action, performed_by, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                student_id,
                                "library",
                                "Assigned",
                                f"Book: {book_name}",
                                "Book assigned",
                                staff_name,
                                zambia_now().strftime("%Y-%m-%d %H:%M:%S"),
                            ),
                        )

                        added.append(book_name)

                    con.commit()

                    if added:

                        success = (
                            f"{len(added)} book assignment(s) sent to "
                            f"{student['name']} for confirmation."
                        )

                        if skipped:
                            success += (
                                " Duplicate pending assignments were skipped."
                            )

                    elif skipped:

                        error = (
                            "The selected book assignment(s) are "
                            "already awaiting student confirmation."
                        )

    # ========================================================
    # STUDENTS
    # ========================================================

    students = cur.execute(
        """
        SELECT
            student_id,
            name,
            program
        FROM students
        ORDER BY name COLLATE NOCASE
        """
    ).fetchall()

    # ========================================================
    # CURRENT BOOK STATUS
    # ========================================================

    student_books = {}

    for student in students:

        rows = cur.execute(
            """
            SELECT
                id,
                name,
                status,
                borrowed_at,
                returned
            FROM library_books
            WHERE student_id = ?
              AND COALESCE(status, '') IN
                    ('pending', 'borrowed')
              AND (
                    COALESCE(status, '') = 'pending'
                    OR COALESCE(returned, 0) = 0
                  )
            ORDER BY id DESC
            """,
            (student["student_id"],)
        ).fetchall()

        student_books[student["student_id"]] = rows

    con.close()

    return render_template(
        "new_staff/library/assign_books.html",
        students=students,
        book_names=book_names,
        student_books=student_books,
        error=error,
        success=success
    )


@app.route("/new-staff/library/dashboard")
def new_staff_library_dashboard():

    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    department = (session.get("department") or "").strip().lower()

    if department not in {
        "library",
        "library department"
    }:
        return redirect(url_for("new_staff_login"))

    import sqlite3

    con = sqlite3.connect("database.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    total_students = cur.execute(
        "SELECT COUNT(*) FROM students"
    ).fetchone()[0]

    pending_students = cur.execute(
        """
        SELECT COUNT(*)
        FROM department_clearances
        WHERE LOWER(TRIM(department)) = 'library'
          AND LOWER(TRIM(COALESCE(status, ''))) NOT IN
              ('cleared', 'approved', 'complete', 'completed')
        """
    ).fetchone()[0]

    cleared_students = cur.execute(
        """
        SELECT COUNT(*)
        FROM department_clearances
        WHERE LOWER(TRIM(department)) = 'library'
          AND LOWER(TRIM(COALESCE(status, ''))) IN
              ('cleared', 'approved', 'complete', 'completed')
        """
    ).fetchone()[0]

    announcement_count = cur.execute(
        """
        SELECT COUNT(*)
        FROM announcements
        WHERE COALESCE(active, 1) = 1
          AND LOWER(TRIM(COALESCE(audience, ''))) IN ('staff', 'all')
        """
    ).fetchone()[0]

    books_issued = cur.execute(
        """
        SELECT COUNT(*)
        FROM library_books
        WHERE COALESCE(returned, 0) = 0
        """
    ).fetchone()[0]

    books_returned = cur.execute(
        """
        SELECT COUNT(*)
        FROM library_books
        WHERE COALESCE(returned, 0) = 1
        """
    ).fetchone()[0]

    pending_list = cur.execute(
        """
        SELECT
            s.student_id,
            s.name,
            s.program
        FROM students s
        INNER JOIN department_clearances dc
            ON dc.student_id = s.student_id
        WHERE LOWER(TRIM(dc.department)) = 'library'
          AND LOWER(TRIM(COALESCE(dc.status, ''))) NOT IN
              ('cleared', 'approved', 'complete', 'completed')
        ORDER BY s.name
        LIMIT 10
        """
    ).fetchall()

    announcements = cur.execute(
        """
        SELECT title, message, created_at
        FROM announcements
        WHERE COALESCE(active, 1) = 1
          AND LOWER(TRIM(COALESCE(audience, ''))) IN ('staff', 'all')
        ORDER BY created_at DESC
        LIMIT 5
        """
    ).fetchall()

    con.close()


    # --------------------------------------------------
    # DASHBOARD SETTINGS
    # --------------------------------------------------

    import sqlite3

    calendar_conn = sqlite3.connect(DATABASE_URL)
    calendar_cursor = calendar_conn.cursor()

    calendar_cursor.execute("""
        SELECT setting_key, setting_value
        FROM system_settings
    """)

    settings = dict(calendar_cursor.fetchall())

    calendar_conn.close()

    return render_template(
        "new_staff/library/dashboard.html",
        staff_name=session.get("staff_name") or session.get("name") or session.get("username") or "Library Staff",
        department=session.get("department") or "Library",
        total_students=total_students,
        pending_students=pending_students,
        cleared_students=cleared_students,
        announcement_count=announcement_count,
        books_issued=books_issued,
        books_returned=books_returned,
        pending_list=pending_list,
        announcements=announcements,
        settings=settings
    )


# ============================================================
# LIBRARY — PENDING CLEARANCE
# ============================================================

@app.route("/new-staff/library/pending")
def new_staff_library_pending():

    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    department = (
        session.get("department") or ""
    ).strip().lower()

    if department not in {
        "library",
        "library department"
    }:
        return redirect(url_for("new_staff_login"))

    import sqlite3

    con = sqlite3.connect("database.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    # --------------------------------------------------------
    # Find students who currently have unreturned books.
    # --------------------------------------------------------

    pending_students = cur.execute(
        """
        SELECT
            s.student_id,
            s.name,
            s.program,
            COUNT(lb.id) AS active_books
        FROM students s
        INNER JOIN library_books lb
            ON lb.student_id = s.student_id
        WHERE COALESCE(lb.returned, 0) = 0
        GROUP BY
            s.student_id,
            s.name,
            s.program
        ORDER BY s.name
        """
    ).fetchall()

    # --------------------------------------------------------
    # Full active-book information for the pending students.
    # --------------------------------------------------------

    books = cur.execute(
        """
        SELECT
            lb.*,
            s.name AS student_name,
            s.program AS student_program
        FROM library_books lb
        INNER JOIN students s
            ON s.student_id = lb.student_id
        WHERE COALESCE(lb.returned, 0) = 0
        ORDER BY s.name, lb.id DESC
        """
    ).fetchall()

    con.close()

    return render_template(
        "new_staff/library/pending.html",
        staff_name=(
            session.get("staff_name")
            or session.get("name")
            or session.get("username")
            or "Library Staff"
        ),
        department=session.get("department") or "Library",
        pending_students=pending_students,
        books=books
    )


# ============================================================
# LIBRARY — CLEARED STUDENTS
# ============================================================

@app.route("/new-staff/library/cleared")
def new_staff_library_cleared():

    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    department = (
        session.get("department") or ""
    ).strip().lower()

    if department not in {
        "library",
        "library department"
    }:
        return redirect(url_for("new_staff_login"))

    import sqlite3

    con = sqlite3.connect("database.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    # --------------------------------------------------------
    # Students with NO active/unreturned library books.
    # --------------------------------------------------------

    cleared_students = cur.execute(
        """
        SELECT
            s.student_id,
            s.name,
            s.program
        FROM students s
        WHERE NOT EXISTS (
            SELECT 1
            FROM library_books lb
            WHERE lb.student_id = s.student_id
              AND COALESCE(lb.returned, 0) = 0
        )
        ORDER BY s.name
        """
    ).fetchall()

    con.close()

    return render_template(
        "new_staff/library/cleared.html",
        staff_name=(
            session.get("staff_name")
            or session.get("name")
            or session.get("username")
            or "Library Staff"
        ),
        department=session.get("department") or "Library",
        cleared_students=cleared_students
    )


# ============================================================
# LIBRARY — ASSIGN BOOKS
# ============================================================



# ============================================================
# SPORTS — ANNOUNCEMENTS
# ============================================================

@app.route("/new-staff/sports/announcements")
def new_staff_sports_announcements():

    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    department = (
        session.get("department") or ""
    ).strip().lower()

    if department not in {
        "sports",
        "sports department"
    }:
        return redirect(url_for("new_staff_login"))

    import sqlite3

    con = sqlite3.connect("database.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    announcements = cur.execute(
        """
        SELECT
            id,
            title,
            message,
            created_at
        FROM announcements
        WHERE COALESCE(active, 1) = 1
          AND LOWER(TRIM(COALESCE(audience, ''))) IN
              ('staff', 'all')
        ORDER BY created_at DESC
        """
    ).fetchall()

    con.close()

    return render_template(
        "new_staff/sports/announcements.html",
        staff_name=(
            session.get("staff_name")
            or session.get("name")
            or session.get("username")
            or "Sports Staff"
        ),
        department=session.get("department") or "Sports",
        announcements=announcements
    )



# ============================================================
# SPORTS — BASKETBALL
# ============================================================

@app.route("/new-staff/sports/basketball")
def new_staff_sports_basketball():

    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    department = (
        session.get("department") or ""
    ).strip().lower()

    if department not in {
        "sports",
        "sports department"
    }:
        return redirect(url_for("new_staff_login"))

    search = (
        request.args.get("search") or ""
    ).strip()

    query = Student.query

    if search:
        query = query.filter(
            db.or_(
                Student.student_id.ilike(f"%{search}%"),
                Student.name.ilike(f"%{search}%")
            )
        )

    students = query.order_by(
        Student.name.asc()
    ).all()

    basketball_students = []

    for student in students:

        items = SportsItem.query.filter_by(
            student_id=student.student_id,
            sport="basketball"
        ).order_by(
            SportsItem.id.desc()
        ).all()

        if items:

            basketball_students.append({
                "student": student,
                "items": items,
                "total_items": len(items)
            })

    return render_template(
        "new_staff/sports/basketball.html",
        staff_name=(
            session.get("staff_name")
            or session.get("name")
            or session.get("username")
            or "Sports Staff"
        ),
        department=session.get("department") or "Sports",
        students=basketball_students,
        search=search
    )


# ============================================================
# SPORTS — NETBALL
# ============================================================

@app.route("/new-staff/sports/netball")
def new_staff_sports_netball():

    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    department = (
        session.get("department") or ""
    ).strip().lower()

    if department not in {
        "sports",
        "sports department"
    }:
        return redirect(url_for("new_staff_login"))

    search = (
        request.args.get("search") or ""
    ).strip()

    query = Student.query

    if search:
        query = query.filter(
            db.or_(
                Student.student_id.ilike(f"%{search}%"),
                Student.name.ilike(f"%{search}%")
            )
        )

    students = query.order_by(
        Student.name.asc()
    ).all()

    netball_students = []

    for student in students:

        items = SportsItem.query.filter(
            SportsItem.student_id == student.student_id,
            db.func.lower(
                db.func.trim(SportsItem.sport)
            ) == "netball"
        ).order_by(
            SportsItem.id.desc()
        ).all()

        if items:

            netball_students.append({
                "student": student,
                "items": items,
                "total_items": len(items)
            })

    return render_template(
        "new_staff/sports/netball.html",
        staff_name=(
            session.get("staff_name")
            or session.get("name")
            or session.get("username")
            or "Sports Staff"
        ),
        department=session.get("department") or "Sports",
        students=netball_students,
        search=search
    )


# ============================================================
# SPORTS — VOLLEYBALL
# ============================================================

@app.route("/new-staff/sports/volleyball")
def new_staff_sports_volleyball():

    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    department = (
        session.get("department") or ""
    ).strip().lower()

    if department not in {
        "sports",
        "sports department"
    }:
        return redirect(url_for("new_staff_login"))

    search = (
        request.args.get("search") or ""
    ).strip()

    query = Student.query

    if search:
        query = query.filter(
            db.or_(
                Student.student_id.ilike(f"%{search}%"),
                Student.name.ilike(f"%{search}%")
            )
        )

    students = query.order_by(
        Student.name.asc()
    ).all()

    volleyball_students = []

    for student in students:

        items = SportsItem.query.filter(
            SportsItem.student_id == student.student_id,
            db.func.lower(
                db.func.trim(SportsItem.sport)
            ) == "volleyball"
        ).order_by(
            SportsItem.id.desc()
        ).all()

        if items:
            volleyball_students.append({
                "student": student,
                "items": items,
                "total_items": len(items)
            })

    return render_template(
        "new_staff/sports/volleyball.html",
        staff_name=(
            session.get("staff_name")
            or session.get("name")
            or session.get("username")
            or "Sports Staff"
        ),
        department=session.get("department") or "Sports",
        students=volleyball_students,
        search=search
    )


# ============================================================
# SPORTS — CHESS
# ============================================================

@app.route("/new-staff/sports/chess")
def new_staff_sports_chess():

    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    department = (
        session.get("department") or ""
    ).strip().lower()

    if department not in {
        "sports",
        "sports department"
    }:
        return redirect(url_for("new_staff_login"))

    search = (
        request.args.get("search") or ""
    ).strip()

    query = Student.query

    if search:
        query = query.filter(
            db.or_(
                Student.student_id.ilike(f"%{search}%"),
                Student.name.ilike(f"%{search}%")
            )
        )

    students = query.order_by(
        Student.name.asc()
    ).all()

    chess_students = []

    for student in students:

        items = SportsItem.query.filter(
            SportsItem.student_id == student.student_id,
            db.func.lower(
                db.func.trim(SportsItem.sport)
            ) == "chess"
        ).order_by(
            SportsItem.id.desc()
        ).all()

        if items:
            chess_students.append({
                "student": student,
                "items": items,
                "total_items": len(items)
            })

    return render_template(
        "new_staff/sports/chess.html",
        staff_name=(
            session.get("staff_name")
            or session.get("name")
            or session.get("username")
            or "Sports Staff"
        ),
        department=session.get("department") or "Sports",
        students=chess_students,
        search=search
    )




# ============================================================
# SPORTS — RETURN
# ============================================================

@app.route("/new-staff/sports/return", methods=["GET", "POST"])
def new_staff_sports_return():

    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    department = (
        session.get("department") or ""
    ).strip().lower()

    if department not in {
        "sports",
        "sports department"
    }:
        return redirect(url_for("new_staff_login"))

    # ========================================================
    # PROCESS RETURN
    # ========================================================

    if request.method == "POST":

        item_id = request.form.get("item_id")

        if not item_id:
            flash(
                "Sports item was not specified.",
                "error"
            )
            return redirect(
                url_for("new_staff_sports_return")
            )

        try:
            item_id = int(item_id)
        except (TypeError, ValueError):
            flash(
                "Invalid sports item.",
                "error"
            )
            return redirect(
                url_for("new_staff_sports_return")
            )

        item = SportsItem.query.get(item_id)

        if not item:
            flash(
                "Sports item not found.",
                "error"
            )
            return redirect(
                url_for("new_staff_sports_return")
            )

        current_status = (
            (item.status or "")
            .strip()
            .lower()
        )

        if current_status in {
            "returned",
            "cleared"
        }:
            flash(
                "This sports item has already been returned.",
                "error"
            )
            return redirect(
                url_for("new_staff_sports_return")
            )

        # Mark item as returned
        item.status = "returned"

        item.remarks = (
            f"Handled by {session.get('staff_name') or 'Sports Staff'}."
        )

        # Record the actual return date/time
        from datetime import datetime

        item.returned_at = zambia_now()

        db.session.commit()

        flash(
            f"{item.item or 'Sports item'} "
            "was returned successfully.",
            "success"
        )

        return redirect(
            url_for("new_staff_sports_return")
        )

    # ========================================================
    # SEARCH
    # ========================================================

    search = (
        request.args.get("search") or ""
    ).strip()

    query = Student.query

    if search:
        query = query.filter(
            db.or_(
                Student.student_id.ilike(
                    f"%{search}%"
                ),
                Student.name.ilike(
                    f"%{search}%"
                )
            )
        )

    students = query.order_by(
        Student.name.asc()
    ).all()

    return_items = []

    for student in students:

        items = SportsItem.query.filter(
            SportsItem.student_id == student.student_id,
            db.func.lower(
                db.func.trim(SportsItem.sport)
            ).in_([
                "football",
                "basketball",
                "volleyball",
                "netball",
                "chess"
            ]),
            db.func.lower(
                db.func.trim(
                    db.func.coalesce(
                        SportsItem.status,
                        ""
                    )
                )
            ).notin_([
                "returned",
                "cleared",
                "declined"
            ])
        ).order_by(
            SportsItem.id.desc()
        ).all()

        if items:
            return_items.append({
                "student": student,
                "items": items,
                "total_items": len(items)
            })

    return render_template(
        "new_staff/sports/return.html",
        staff_name=(
            session.get("staff_name")
            or session.get("name")
            or session.get("username")
            or "Sports Staff"
        ),
        department=(
            session.get("department")
            or "Sports"
        ),
        students=return_items,
        search=search
    )


# ============================================================
# NEW STAFF SPORTS — CLEARANCE HISTORY
# ============================================================

@app.route("/new-staff/sports/clearance-history")
def new_staff_sports_clearance_history():

    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    department = (
        session.get("department") or ""
    ).strip().lower()

    if department not in {
        "sports",
        "sports department"
    }:
        return redirect(url_for("new_staff_login"))

    history = (
        ClearanceHistory.query
        .order_by(ClearanceHistory.id.desc())
        .all()
    )

    return render_template(
        "new_staff/sports/clearance_history.html",
        staff_name=(
            session.get("staff_name")
            or session.get("name")
            or session.get("username")
            or "Sports Staff"
        ),
        department=session.get("department") or "Sports",
        history=history
    )




# ============================================================


# ============================================================
# NEW STAFF STORES — DASHBOARD
# ============================================================


# ============================================================
# NEW STAFF STORES — STUDENTS
# ============================================================




# ============================================================
# NEW STAFF MATHEMATICS — PROPERTY RECORDS
# ============================================================

@app.route("/new-staff/mathematics/property-records")
def new_staff_mathematics_property_records():
    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    department = (
        session.get("department") or ""
    ).strip().lower()

    if department not in {
        "mathematics",
        "mathematics department",
    }:
        return redirect(url_for("new_staff_login"))

    search = (
        request.args.get("search") or ""
    ).strip()

    query = MathematicsProperty.query

    if search:
        matching_student_ids = {
            student.student_id
            for student in Student.query.filter(
                db.or_(
                    Student.student_id.ilike(f"%{search}%"),
                    Student.name.ilike(f"%{search}%")
                )
            ).all()
        }

        if matching_student_ids:
            query = query.filter(
                db.or_(
                    MathematicsProperty.student_id.in_(
                        matching_student_ids
                    ),
                    MathematicsProperty.name.ilike(
                        f"%{search}%"
                    )
                )
            )
        else:
            query = query.filter(
                MathematicsProperty.name.ilike(
                    f"%{search}%"
                )
            )

    property_records = (
        query
        .order_by(
            MathematicsProperty.issued_at.desc(),
            MathematicsProperty.id.desc()
        )
        .all()
    )

    # Get student names for the Mathematics property records.
    student_ids = {
        item.student_id
        for item in property_records
        if item.student_id
    }

    students = (
        Student.query
        .filter(Student.student_id.in_(student_ids))
        .all()
        if student_ids
        else []
    )

    student_names = {
        student.student_id: student.name
        for student in students
    }

    return render_template(
        "new_staff/mathematics/property_records.html",
        staff_name=session.get("staff_name"),
        department=session.get("department"),
        property_records=property_records,
        student_names=student_names,
        search=search,
    )

@app.route("/new-staff/training-section/property-records")
def new_staff_training_section_property_records():

    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    department = (
        session.get("department") or ""
    ).strip().lower()

    if department != "training section":
        return redirect(url_for("new_staff_login"))

    search = (
        request.args.get("search") or ""
    ).strip()

    query = TrainingSectionProperty.query

    if search:
        matching_student_ids = {
            student.student_id
            for student in Student.query.filter(
                db.or_(
                    Student.student_id.ilike(
                        f"%{search}%"
                    ),
                    Student.name.ilike(
                        f"%{search}%"
                    )
                )
            ).all()
        }

        if matching_student_ids:
            query = query.filter(
                db.or_(
                    TrainingSectionProperty.student_id.in_(
                        matching_student_ids
                    ),
                    TrainingSectionProperty.name.ilike(
                        f"%{search}%"
                    )
                )
            )
        else:
            query = query.filter(
                TrainingSectionProperty.name.ilike(
                    f"%{search}%"
                )
            )

    property_records = (
        query
        .order_by(
            TrainingSectionProperty.issued_at.desc(),
            TrainingSectionProperty.id.desc()
        )
        .all()
    )

    student_ids = {
        item.student_id
        for item in property_records
        if item.student_id
    }

    students = (
        Student.query
        .filter(
            Student.student_id.in_(student_ids)
        )
        .all()
        if student_ids
        else []
    )

    student_names = {
        student.student_id: student.name
        for student in students
    }

    return render_template(
        "new_staff/training_section/property_records.html",
        staff_name=session.get("staff_name"),
        department=session.get("department"),
        property_records=property_records,
        student_names=student_names,
        search=search,
    )


@app.route("/new-staff/communication/property-records")
def new_staff_communication_property_records():

    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    department = (
        session.get("department") or ""
    ).strip().lower()

    if department not in {
        "communication skills (rel/sc)",
        "communication skills (rel sc)",
        "communication skills",
    }:
        return redirect(url_for("new_staff_login"))

    search = (
        request.args.get("search") or ""
    ).strip()

    query = CommunicationProperty.query

    if search:
        matching_student_ids = {
            student.student_id
            for student in Student.query.filter(
                db.or_(
                    Student.student_id.ilike(f"%{search}%"),
                    Student.name.ilike(f"%{search}%")
                )
            ).all()
        }

        query = query.filter(
            db.or_(
                CommunicationProperty.student_id.in_(
                    matching_student_ids
                ),
                CommunicationProperty.name.ilike(
                    f"%{search}%"
                )
            )
        )

    property_records = (
        query
        .order_by(
            CommunicationProperty.issued_at.desc(),
            CommunicationProperty.id.desc()
        )
        .all()
    )

    return render_template(
        "new_staff/communication/property_records.html",
        staff_name=session.get("staff_name"),
        department=session.get("department"),
        property_records=property_records,
        search=search,
    )


@app.route("/new-staff/communication/return-property", methods=["GET", "POST"])
def new_staff_communication_return_property():
    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    department = (
        session.get("department") or ""
    ).strip().lower()

    if department not in {
        "communication skills (rel/sc)",
        "communication skills (rel sc)",
        "communication skills",
    }:
        return redirect(url_for("new_staff_login"))

    if request.method == "POST":
        property_id = request.form.get("property_id")

        if not property_id:
            flash("Please select a property to return.", "error")
            return redirect(
                url_for("new_staff_communication_return_property")
            )

        property_record = CommunicationProperty.query.filter_by(
            id=property_id
        ).first()

        if not property_record:
            flash("Property record not found.", "error")
            return redirect(
                url_for("new_staff_communication_return_property")
            )

        if property_record.returned_at is not None:
            flash("This property has already been returned.", "error")
            return redirect(
                url_for("new_staff_communication_return_property")
            )

        staff_name = (
            session.get("staff_name")
            or "Communication Skills Staff"
        )

        returned_at = zambia_now()

        property_record.status = "Returned"
        property_record.returned_by = staff_name
        property_record.returned_at = returned_at

        db.session.commit()

        flash(
            f"{property_record.name} returned successfully.",
            "success"
        )

        return redirect(
            url_for("new_staff_communication_return_property")
        )

    outstanding_items = (
        CommunicationProperty.query
        .filter(
            CommunicationProperty.returned_at.is_(None),
            db.func.lower(
                db.func.trim(
                    db.func.coalesce(
                        CommunicationProperty.status,
                        ""
                    )
                )
            ).notin_([
                "returned",
                "cleared",
                "declined"
            ])
        )
        .order_by(
            CommunicationProperty.issued_at.desc(),
            CommunicationProperty.id.desc()
        )
        .all()
    )

    return render_template(
        "new_staff/communication/return_property.html",
        staff_name=session.get("staff_name"),
        department=session.get("department"),
        outstanding_items=outstanding_items
    )

@app.route("/new-staff/training-section/return-property", methods=["GET", "POST"])
def new_staff_training_section_return_property():
    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    department = (
        session.get("department") or ""
    ).strip().lower()

    if department != "training section":
        return redirect(url_for("new_staff_login"))

    if request.method == "POST":
        property_id = request.form.get("property_id")

        if not property_id:
            flash(
                "Please select a property to return.",
                "error"
            )
            return redirect(
                url_for(
                    "new_staff_training_section_return_property"
                )
            )

        property_record = (
            TrainingSectionProperty.query
            .filter_by(id=property_id)
            .first()
        )

        if not property_record:
            flash(
                "Property record not found.",
                "error"
            )
            return redirect(
                url_for(
                    "new_staff_training_section_return_property"
                )
            )

        if property_record.returned_at is not None:
            flash(
                "This property has already been returned.",
                "error"
            )
            return redirect(
                url_for(
                    "new_staff_training_section_return_property"
                )
            )

        staff_name = (
            session.get("staff_name")
            or "Training Section Staff"
        )

        returned_at = zambia_now()

        property_record.status = "Returned"
        property_record.returned_by = staff_name
        property_record.returned_at = returned_at

        db.session.commit()

        flash(
            f"{property_record.name} returned successfully.",
            "success"
        )

        return redirect(
            url_for(
                "new_staff_training_section_return_property"
            )
        )

    outstanding_items = (
        TrainingSectionProperty.query
        .filter(
            TrainingSectionProperty.returned_at.is_(None),
            db.func.lower(
                db.func.trim(
                    db.func.coalesce(
                        TrainingSectionProperty.status,
                        ""
                    )
                )
            ).notin_([
                "returned",
                "cleared",
                "declined"
            ])
        )
        .order_by(
            TrainingSectionProperty.issued_at.desc(),
            TrainingSectionProperty.id.desc()
        )
        .all()
    )

    student_ids = {
        item.student_id
        for item in outstanding_items
        if item.student_id
    }

    students = (
        Student.query
        .filter(
            Student.student_id.in_(student_ids)
        )
        .all()
        if student_ids
        else []
    )

    student_names = {
        student.student_id: student.name
        for student in students
    }

    return render_template(
        "new_staff/training_section_return_property.html",
        staff_name=session.get("staff_name"),
        department=session.get("department"),
        outstanding_items=outstanding_items,
        student_names=student_names
    )


@app.route("/new-staff/mathematics/return-property", methods=["GET", "POST"])
def new_staff_mathematics_return_property():
    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    department = (
        session.get("department") or ""
    ).strip().lower()

    if department not in {
        "mathematics",
        "mathematics department",
    }:
        return redirect(url_for("new_staff_login"))

    if request.method == "POST":
        property_id = request.form.get("property_id")

        if not property_id:
            flash("Please select a property to return.", "error")
            return redirect(
                url_for("new_staff_mathematics_return_property")
            )

        property_record = MathematicsProperty.query.filter_by(
            id=property_id
        ).first()

        if not property_record:
            flash("Property record not found.", "error")
            return redirect(
                url_for("new_staff_mathematics_return_property")
            )

        if property_record.returned_at is not None:
            flash("This property has already been returned.", "error")
            return redirect(
                url_for("new_staff_mathematics_return_property")
            )

        staff_name = (
            session.get("staff_name")
            or "Mathematics Staff"
        )

        returned_at = zambia_now()

        property_record.status = "Returned"
        property_record.returned_by = staff_name
        property_record.returned_at = returned_at

        db.session.commit()

        flash(
            f"{property_record.name} returned successfully.",
            "success"
        )

        return redirect(
            url_for("new_staff_mathematics_return_property")
        )

    outstanding_items = (
        MathematicsProperty.query
        .filter(
            MathematicsProperty.returned_at.is_(None),
            db.func.lower(
                db.func.trim(
                    db.func.coalesce(
                        MathematicsProperty.status,
                        ""
                    )
                )
            ).notin_([
                "returned",
                "cleared",
                "declined"
            ])
        )
        .order_by(
            MathematicsProperty.issued_at.desc(),
            MathematicsProperty.id.desc()
        )
        .all()
    )

    # Get student names for the outstanding Mathematics properties.
    student_ids = {
        item.student_id
        for item in outstanding_items
        if item.student_id
    }

    students = (
        Student.query
        .filter(Student.student_id.in_(student_ids))
        .all()
        if student_ids
        else []
    )

    student_names = {
        student.student_id: student.name
        for student in students
    }

    return render_template(
        "new_staff/mathematics_return_property.html",
        staff_name=session.get("staff_name"),
        department=session.get("department"),
        outstanding_items=outstanding_items,
        student_names=student_names
    )

@app.route("/new-staff/communication/issue-property", methods=["GET", "POST"])
def new_staff_communication_issue_property():
    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    department = (
        session.get("department") or ""
    ).strip().lower()

    if department not in {
        "communication skills (rel/sc)",
        "communication skills (rel sc)",
        "communication skills",
    }:
        return redirect(url_for("new_staff_login"))

    if request.method == "POST":
        student_id = (
            request.form.get("student_id") or ""
        ).strip()

        property_name = (
            request.form.get("property_name")
            or request.form.get("item")
            or ""
        ).strip()

        remarks = (
            request.form.get("remarks") or ""
        ).strip()

        if not student_id:
            flash("Please select a student.", "error")
            return redirect(
                url_for("new_staff_communication_issue_property")
            )

        if not property_name:
            flash("Please enter the property or material name.", "error")
            return redirect(
                url_for(
                    "new_staff_communication_issue_property",
                    student_id=student_id
                )
            )

        student = Student.query.filter_by(
            student_id=student_id
        ).first()

        if not student:
            flash("Student not found.", "error")
            return redirect(
                url_for("new_staff_communication_issue_property")
            )

        staff_name = (
            session.get("staff_name")
            or "Communication Skills Staff"
        )

        existing_request = ItemRequest.query.filter(
            ItemRequest.student_id == student.student_id,
            db.func.lower(
                db.func.trim(
                    db.func.coalesce(
                        ItemRequest.item,
                        ""
                    )
                )
            ) == property_name.lower(),
            db.func.lower(
                db.func.trim(
                    db.func.coalesce(
                        ItemRequest.status,
                        ""
                    )
                )
            ) == "pending",
            db.func.lower(
                db.func.trim(
                    db.func.coalesce(
                        ItemRequest.department,
                        ""
                    )
                )
            ).in_([
                "communication skills (rel/sc)",
                "communication skills (rel sc)",
                "communication skills",
            ])
        ).first()

        existing_property = CommunicationProperty.query.filter(
            CommunicationProperty.student_id == student.student_id,
            db.func.lower(
                db.func.trim(
                    db.func.coalesce(
                        CommunicationProperty.name,
                        ""
                    )
                )
            ) == property_name.lower(),
            CommunicationProperty.returned_at.is_(None)
        ).first()

        if existing_request or existing_property:
            flash(
                "That property is already issued or awaiting student confirmation.",
                "error"
            )
            return redirect(
                url_for(
                    "new_staff_communication_issue_property",
                    student_id=student.student_id
                )
            )

        item_request = ItemRequest(
            student_id=student.student_id,
            department="Communication Skills (REL/SC)",
            item=property_name,
            item_type="Institutional Property",
            status="Pending",
            assigned_by=staff_name,
            remarks=(
                remarks
                or "Communication Skills institutional property "
                   "issued pending student confirmation."
            )
        )

        db.session.add(item_request)
        db.session.commit()

        flash(
            f"Property request sent to {student.name} for confirmation.",
            "success"
        )

        return redirect(
            url_for(
                "new_staff_communication_issue_property",
                student_id=student.student_id,
                success="1"
            )
        )

    search = (
        request.args.get("search") or ""
    ).strip()

    selected_student_id = (
        request.args.get("student_id") or ""
    ).strip()

    selected_student = None

    if selected_student_id:
        selected_student = Student.query.filter_by(
            student_id=selected_student_id
        ).first()

    query = Student.query

    if search:
        query = query.filter(
            db.or_(
                Student.student_id.ilike(
                    f"%{search}%"
                ),
                Student.name.ilike(
                    f"%{search}%"
                )
            )
        )

    students = query.order_by(
        Student.name.asc()
    ).all()

    return render_template(
        "new_staff/communication/issue_property.html",
        staff_name=session.get("staff_name"),
        department=session.get("department"),
        students=students,
        search=search,
        selected_student=selected_student,
        success=request.args.get("success") == "1"
    )

@app.route("/new-staff/mathematics/issue-property", methods=["GET", "POST"])
def new_staff_mathematics_issue_property():
    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    department = (
        session.get("department") or ""
    ).strip().lower()

    if department not in {
        "mathematics",
        "mathematics department",
        "mathematics",
    }:
        return redirect(url_for("new_staff_login"))

    if request.method == "POST":
        student_id = (
            request.form.get("student_id") or ""
        ).strip()

        property_name = (
            request.form.get("property_name")
            or request.form.get("item")
            or ""
        ).strip()

        remarks = (
            request.form.get("remarks") or ""
        ).strip()

        if not student_id:
            flash("Please select a student.", "error")
            return redirect(
                url_for("new_staff_mathematics_issue_property")
            )

        if not property_name:
            flash("Please enter the property or material name.", "error")
            return redirect(
                url_for(
                    "new_staff_mathematics_issue_property",
                    student_id=student_id
                )
            )

        student = Student.query.filter_by(
            student_id=student_id
        ).first()

        if not student:
            flash("Student not found.", "error")
            return redirect(
                url_for("new_staff_mathematics_issue_property")
            )

        staff_name = (
            session.get("staff_name")
            or "Mathematics Staff"
        )

        existing_request = ItemRequest.query.filter(
            ItemRequest.student_id == student.student_id,
            db.func.lower(
                db.func.trim(
                    db.func.coalesce(
                        ItemRequest.item,
                        ""
                    )
                )
            ) == property_name.lower(),
            db.func.lower(
                db.func.trim(
                    db.func.coalesce(
                        ItemRequest.status,
                        ""
                    )
                )
            ) == "pending",
            db.func.lower(
                db.func.trim(
                    db.func.coalesce(
                        ItemRequest.department,
                        ""
                    )
                )
            ).in_([
                "mathematics",
                "mathematics department",
                "mathematics",
            ])
        ).first()

        existing_property = MathematicsProperty.query.filter(
            MathematicsProperty.student_id == student.student_id,
            db.func.lower(
                db.func.trim(
                    db.func.coalesce(
                        MathematicsProperty.name,
                        ""
                    )
                )
            ) == property_name.lower(),
            MathematicsProperty.returned_at.is_(None)
        ).first()

        if existing_request or existing_property:
            flash(
                "That property is already issued or awaiting student confirmation.",
                "error"
            )
            return redirect(
                url_for(
                    "new_staff_mathematics_issue_property",
                    student_id=student.student_id
                )
            )

        item_request = ItemRequest(
            student_id=student.student_id,
            department="Mathematics",
            item=property_name,
            item_type="Institutional Property",
            status="Pending",
            assigned_by=staff_name,
            remarks=(
                remarks
                or "Mathematics institutional property "
                   "issued pending student confirmation."
            )
        )

        db.session.add(item_request)
        db.session.commit()

        flash(
            f"Property request sent to {student.name} for confirmation.",
            "success"
        )

        return redirect(
            url_for(
                "new_staff_mathematics_issue_property",
                student_id=student.student_id,
                success="1"
            )
        )

    search = (
        request.args.get("search") or ""
    ).strip()

    selected_student_id = (
        request.args.get("student_id") or ""
    ).strip()

    selected_student = None

    if selected_student_id:
        selected_student = Student.query.filter_by(
            student_id=selected_student_id
        ).first()

    query = Student.query

    if search:
        query = query.filter(
            db.or_(
                Student.student_id.ilike(
                    f"%{search}%"
                ),
                Student.name.ilike(
                    f"%{search}%"
                )
            )
        )

    students = query.order_by(
        Student.name.asc()
    ).all()

    return render_template(
        "new_staff/mathematics_issue_property.html",
        staff_name=session.get("staff_name"),
        department=session.get("department"),
        students=students,
        search=search,
        selected_student=selected_student,
        success=request.args.get("success") == "1"
    )


@app.route("/new-staff/training-section/issue-property", methods=["GET", "POST"])
def new_staff_training_section_issue_property():
    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    department = (
        session.get("department") or ""
    ).strip()

    if department.lower() != "training section":
        return redirect(url_for("new_staff_login"))

    if request.method == "POST":
        student_id = (
            request.form.get("student_id") or ""
        ).strip()

        property_name = (
            request.form.get("property_name")
            or request.form.get("item")
            or ""
        ).strip()

        remarks = (
            request.form.get("remarks") or ""
        ).strip()

        if not student_id:
            flash("Please select a student.", "error")
            return redirect(
                url_for(
                    "new_staff_training_section_issue_property"
                )
            )

        if not property_name:
            flash(
                "Please enter the property or material name.",
                "error"
            )
            return redirect(
                url_for(
                    "new_staff_training_section_issue_property",
                    student_id=student_id
                )
            )

        student = Student.query.filter_by(
            student_id=student_id
        ).first()

        if not student:
            flash("Student not found.", "error")
            return redirect(
                url_for(
                    "new_staff_training_section_issue_property"
                )
            )

        staff_name = (
            session.get("staff_name")
            or "Training Section Staff"
        )

        existing_request = ItemRequest.query.filter(
            ItemRequest.student_id == student.student_id,
            db.func.lower(
                db.func.trim(
                    db.func.coalesce(
                        ItemRequest.item,
                        ""
                    )
                )
            ) == property_name.lower(),
            db.func.lower(
                db.func.trim(
                    db.func.coalesce(
                        ItemRequest.status,
                        ""
                    )
                )
            ) == "pending",
            db.func.lower(
                db.func.trim(
                    db.func.coalesce(
                        ItemRequest.department,
                        ""
                    )
                )
            ) == "training section"
        ).first()

        existing_property = TrainingSectionProperty.query.filter(
            TrainingSectionProperty.student_id == student.student_id,
            db.func.lower(
                db.func.trim(
                    db.func.coalesce(
                        TrainingSectionProperty.name,
                        ""
                    )
                )
            ) == property_name.lower(),
            TrainingSectionProperty.returned_at.is_(None)
        ).first()

        if existing_request or existing_property:
            flash(
                "That property is already issued or awaiting student confirmation.",
                "error"
            )
            return redirect(
                url_for(
                    "new_staff_training_section_issue_property",
                    student_id=student.student_id
                )
            )

        item_request = ItemRequest(
            student_id=student.student_id,
            department="Training Section",
            item=property_name,
            item_type="Institutional Property",
            status="Pending",
            assigned_by=staff_name,
            remarks=(
                remarks
                or "Training Section institutional property "
                   "issued pending student confirmation."
            )
        )

        db.session.add(item_request)
        db.session.commit()

        flash(
            f"Property request sent to {student.name} for confirmation.",
            "success"
        )

        return redirect(
            url_for(
                "new_staff_training_section_issue_property",
                student_id=student.student_id,
                success="1"
            )
        )

    search = (
        request.args.get("search") or ""
    ).strip()

    selected_student_id = (
        request.args.get("student_id") or ""
    ).strip()

    selected_student = None

    if selected_student_id:
        selected_student = Student.query.filter_by(
            student_id=selected_student_id
        ).first()

    query = Student.query

    if search:
        query = query.filter(
            db.or_(
                Student.student_id.ilike(
                    f"%{search}%"
                ),
                Student.name.ilike(
                    f"%{search}%"
                )
            )
        )

    students = (
        query
        .order_by(Student.name.asc())
        .all()
    )

    return render_template(
        "new_staff/training_section_issue_property.html",
        staff_name=session.get("staff_name"),
        department=session.get("department"),
        students=students,
        search=search,
        selected_student=selected_student,
        success=request.args.get("success") == "1"
    )


@app.route("/new-staff/communication/students")
def new_staff_communication_students():

    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    department = (
        session.get("department") or ""
    ).strip().lower()

    if department not in {
        "communication skills (rel/sc)",
        "communication skills (rel sc)",
        "communication skills",
    }:
        return redirect(url_for("new_staff_login"))

    search = (
        request.args.get("search") or ""
    ).strip()

    query = Student.query

    if search:
        query = query.filter(
            db.or_(
                Student.student_id.ilike(
                    f"%{search}%"
                ),
                Student.name.ilike(
                    f"%{search}%"
                )
            )
        )

    students = (
        query
        .order_by(Student.name.asc())
        .all()
    )

    # --------------------------------------------------
    # COMMUNICATION SKILLS CLEARANCE
    # --------------------------------------------------
    #
    # A student is cleared when they have no outstanding
    # Communication Skills institutional property.
    # --------------------------------------------------

    outstanding_properties = (
        CommunicationProperty.query
        .filter(
            CommunicationProperty.returned_at.is_(None),
            db.func.lower(
                db.func.trim(
                    db.func.coalesce(
                        CommunicationProperty.status,
                        ""
                    )
                )
            ).in_(["issued", "assigned"])
        )
        .all()
    )

    pending_student_ids = {
        property_record.student_id
        for property_record in outstanding_properties
    }

    cleared_student_ids = {
        student.student_id
        for student in students
        if student.student_id not in pending_student_ids
    }

    return render_template(
        "new_staff/mathematics_students.html",
        staff_name=session.get("staff_name"),
        department=session.get("department"),
        students=students,
        search=search,
        cleared_student_ids=cleared_student_ids,
    )


@app.route("/new-staff/mathematics/students")
def new_staff_mathematics_students():

    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    department = (
        session.get("department") or ""
    ).strip().lower()

    if department not in {
        "mathematics",
        "mathematics department",
        "mathematics",
    }:
        return redirect(url_for("new_staff_login"))

    search = (
        request.args.get("search") or ""
    ).strip()

    query = Student.query

    if search:
        query = query.filter(
            db.or_(
                Student.student_id.ilike(
                    f"%{search}%"
                ),
                Student.name.ilike(
                    f"%{search}%"
                )
            )
        )

    students = (
        query
        .order_by(Student.name.asc())
        .all()
    )

    # --------------------------------------------------
    # COMMUNICATION SKILLS CLEARANCE
    # --------------------------------------------------
    #
    # A student is cleared when they have no outstanding
    # Communication Skills institutional property.
    # --------------------------------------------------

    outstanding_properties = (
        MathematicsProperty.query
        .filter(
            MathematicsProperty.returned_at.is_(None),
            db.func.lower(
                db.func.trim(
                    db.func.coalesce(
                        MathematicsProperty.status,
                        ""
                    )
                )
            ).in_(["issued", "assigned"])
        )
        .all()
    )

    pending_student_ids = {
        property_record.student_id
        for property_record in outstanding_properties
    }

    cleared_student_ids = {
        student.student_id
        for student in students
        if student.student_id not in pending_student_ids
    }

    return render_template(
        "new_staff/mathematics_students.html",
        staff_name=session.get("staff_name"),
        department=session.get("department"),
        students=students,
        search=search,
        cleared_student_ids=cleared_student_ids,
    )



@app.route("/new-staff/training-section/students")
def new_staff_training_section_students():

    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    department = (
        session.get("department") or ""
    ).strip().lower()

    if department != "training section":
        return redirect(url_for("new_staff_login"))

    search = (
        request.args.get("search") or ""
    ).strip()

    query = Student.query

    if search:
        query = query.filter(
            db.or_(
                Student.student_id.ilike(
                    f"%{search}%"
                ),
                Student.name.ilike(
                    f"%{search}%"
                )
            )
        )

    students = (
        query
        .order_by(Student.name.asc())
        .all()
    )

    # --------------------------------------------------
    # TRAINING SECTION CLEARANCE
    # --------------------------------------------------
    #
    # A student is cleared when they have no outstanding
    # Training Section institutional property.
    # --------------------------------------------------

    outstanding_properties = (
        TrainingSectionProperty.query
        .filter(
            TrainingSectionProperty.returned_at.is_(None),
            db.func.lower(
                db.func.trim(
                    db.func.coalesce(
                        TrainingSectionProperty.status,
                        ""
                    )
                )
            ).in_([
                "issued",
                "assigned"
            ])
        )
        .all()
    )

    pending_student_ids = {
        property_record.student_id
        for property_record in outstanding_properties
    }

    cleared_student_ids = {
        student.student_id
        for student in students
        if student.student_id not in pending_student_ids
    }

    return render_template(
        "new_staff/training_section_students.html",
        staff_name=session.get("staff_name"),
        department=session.get("department"),
        students=students,
        search=search,
        cleared_student_ids=cleared_student_ids,
    )


@app.route("/new-staff/communication/dashboard")
def new_staff_communication_dashboard():
    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    department = (
        session.get("department") or ""
    ).strip().lower()

    if department not in {
        "communication skills (rel/sc)",
        "communication skills (rel sc)",
        "communication skills"
    }:
        return redirect(url_for("new_staff_login"))

    search = (
        request.args.get("search") or ""
    ).strip()

    query = Student.query

    if search:
        query = query.filter(
            db.or_(
                Student.student_id.ilike(
                    f"%{search}%"
                ),
                Student.name.ilike(
                    f"%{search}%"
                )
            )
        )

    students = query.order_by(
        Student.name.asc()
    ).all()

    total_students = Student.query.count()

    issued_properties = CommunicationProperty.query.filter(
        db.func.lower(
            db.func.trim(
                db.func.coalesce(
                    CommunicationProperty.status,
                    ""
                )
            )
        ).in_([
            "issued",
            "assigned"
        ])
    ).count()

    returned_properties = CommunicationProperty.query.filter(
        CommunicationProperty.returned_at.isnot(None)
    ).count()

    outstanding_items = (
        CommunicationProperty.query
        .filter(
            CommunicationProperty.returned_at.is_(None),
            db.func.lower(
                db.func.trim(
                    db.func.coalesce(
                        CommunicationProperty.status,
                        ""
                    )
                )
            ).notin_([
                "returned",
                "cleared",
                "declined"
            ])
        )
        .order_by(
            CommunicationProperty.issued_at.desc(),
            CommunicationProperty.id.desc()
        )
        .limit(8)
        .all()
    )

    pending_student_ids = {
        record.student_id
        for record in CommunicationProperty.query.filter(
            CommunicationProperty.returned_at.is_(None),
            db.func.lower(
                db.func.trim(
                    db.func.coalesce(
                        CommunicationProperty.status,
                        ""
                    )
                )
            ).notin_([
                "returned",
                "cleared",
                "declined"
            ])
        ).all()
    }

    pending_students = len(pending_student_ids)

    students_cleared = max(
        total_students - pending_students,
        0
    )

    clearance_percentage = (
        round(
            (students_cleared / total_students) * 100
        )
        if total_students
        else 0
    )

    recent_properties = (
        CommunicationProperty.query
        .order_by(
            CommunicationProperty.issued_at.desc(),
            CommunicationProperty.id.desc()
        )
        .limit(8)
        .all()
    )

    recent_returns = (
        CommunicationProperty.query
        .filter(
            CommunicationProperty.returned_at.isnot(None)
        )
        .order_by(
            CommunicationProperty.returned_at.desc(),
            CommunicationProperty.id.desc()
        )
        .limit(8)
        .all()
    )

    from datetime import datetime, timedelta

    today = zambia_now().date()

    communication_activity = []

    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        next_day = day + timedelta(days=1)

        issued_count = CommunicationProperty.query.filter(
            CommunicationProperty.issued_at >= datetime.combine(
                day,
                datetime.min.time()
            ),
            CommunicationProperty.issued_at < datetime.combine(
                next_day,
                datetime.min.time()
            )
        ).count()

        returned_count = CommunicationProperty.query.filter(
            CommunicationProperty.returned_at >= datetime.combine(
                day,
                datetime.min.time()
            ),
            CommunicationProperty.returned_at < datetime.combine(
                next_day,
                datetime.min.time()
            )
        ).count()

        communication_activity.append({
            "date": day.strftime("%a"),
            "issued": issued_count,
            "returned": returned_count
        })

    announcements = Announcement.query.filter(
        db.func.coalesce(
            Announcement.active,
            True
        ) == True,
        db.func.lower(
            db.func.trim(
                db.func.coalesce(
                    Announcement.audience,
                    ""
                )
            )
        ).in_([
            "staff",
            "all"
        ])
    ).order_by(
        Announcement.created_at.desc()
    ).limit(5).all()

    announcement_count = Announcement.query.filter(
        db.func.coalesce(
            Announcement.active,
            True
        ) == True,
        db.func.lower(
            db.func.trim(
                db.func.coalesce(
                    Announcement.audience,
                    ""
                )
            )
        ).in_([
            "staff",
            "all"
        ])
    ).count()

    settings = {}

    try:
        import sqlite3

        conn = sqlite3.connect(DATABASE_URL)
        conn.row_factory = sqlite3.Row

        rows = conn.execute(
            "SELECT setting_key, setting_value FROM system_settings"
        ).fetchall()

        settings = {
            row["setting_key"]: row["setting_value"]
            for row in rows
        }

        conn.close()

    except Exception:
        settings = {}

    return render_template(
        "new_staff/communication/dashboard.html",
        staff_name=session.get("staff_name"),
        department=session.get("department"),
        students=students,
        search=search,
        total_students=total_students,
        issued_properties=issued_properties,
        returned_properties=returned_properties,
        outstanding_items=outstanding_items,
        pending_students=pending_students,
        students_cleared=students_cleared,
        clearance_percentage=clearance_percentage,
        recent_properties=recent_properties,
        recent_returns=recent_returns,
        communication_activity=communication_activity,
        announcements=announcements,
        announcement_count=announcement_count,
        settings=settings
    )




@app.route("/new-staff/training-section/dashboard")
def new_staff_training_section_dashboard():
    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    department = (
        session.get("department") or ""
    ).strip()

    if department.lower() != "training section":
        return redirect(url_for("new_staff_login"))

    search = (
        request.args.get("search") or ""
    ).strip()

    query = Student.query

    if search:
        query = query.filter(
            db.or_(
                Student.student_id.ilike(
                    f"%{search}%"
                ),
                Student.name.ilike(
                    f"%{search}%"
                )
            )
        )

    students = (
        query
        .order_by(Student.name.asc())
        .all()
    )

    total_students = Student.query.count()

    issued_properties = TrainingSectionProperty.query.filter(
        db.func.lower(
            db.func.trim(
                db.func.coalesce(
                    TrainingSectionProperty.status,
                    ""
                )
            )
        ).in_([
            "issued",
            "assigned"
        ])
    ).count()

    returned_properties = TrainingSectionProperty.query.filter(
        TrainingSectionProperty.returned_at.isnot(None)
    ).count()

    outstanding_items = (
        TrainingSectionProperty.query
        .filter(
            TrainingSectionProperty.returned_at.is_(None),
            db.func.lower(
                db.func.trim(
                    db.func.coalesce(
                        TrainingSectionProperty.status,
                        ""
                    )
                )
            ).notin_([
                "returned",
                "cleared",
                "declined"
            ])
        )
        .order_by(
            TrainingSectionProperty.issued_at.desc(),
            TrainingSectionProperty.id.desc()
        )
        .limit(8)
        .all()
    )

    pending_student_ids = {
        record.student_id
        for record in TrainingSectionProperty.query.filter(
            TrainingSectionProperty.returned_at.is_(None),
            db.func.lower(
                db.func.trim(
                    db.func.coalesce(
                        TrainingSectionProperty.status,
                        ""
                    )
                )
            ).notin_([
                "returned",
                "cleared",
                "declined"
            ])
        ).all()
    }

    pending_students = len(pending_student_ids)

    students_cleared = max(
        total_students - pending_students,
        0
    )

    clearance_percentage = (
        round(
            (students_cleared / total_students) * 100
        )
        if total_students
        else 0
    )

    recent_properties = (
        TrainingSectionProperty.query
        .order_by(
            TrainingSectionProperty.issued_at.desc(),
            TrainingSectionProperty.id.desc()
        )
        .limit(8)
        .all()
    )

    recent_returns = (
        TrainingSectionProperty.query
        .filter(
            TrainingSectionProperty.returned_at.isnot(None)
        )
        .order_by(
            TrainingSectionProperty.returned_at.desc(),
            TrainingSectionProperty.id.desc()
        )
        .limit(8)
        .all()
    )

    from datetime import datetime, timedelta

    today = zambia_now().date()

    training_section_activity = []

    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        next_day = day + timedelta(days=1)

        issued_count = TrainingSectionProperty.query.filter(
            TrainingSectionProperty.issued_at >= datetime.combine(
                day,
                datetime.min.time()
            ),
            TrainingSectionProperty.issued_at < datetime.combine(
                next_day,
                datetime.min.time()
            )
        ).count()

        returned_count = TrainingSectionProperty.query.filter(
            TrainingSectionProperty.returned_at >= datetime.combine(
                day,
                datetime.min.time()
            ),
            TrainingSectionProperty.returned_at < datetime.combine(
                next_day,
                datetime.min.time()
            )
        ).count()

        training_section_activity.append({
            "date": day.strftime("%a"),
            "issued": issued_count,
            "returned": returned_count
        })

    announcements = Announcement.query.filter(
        db.func.coalesce(
            Announcement.active,
            True
        ) == True,
        db.func.lower(
            db.func.trim(
                db.func.coalesce(
                    Announcement.audience,
                    ""
                )
            )
        ).in_([
            "staff",
            "all"
        ])
    ).order_by(
        Announcement.created_at.desc()
    ).limit(5).all()

    announcement_count = Announcement.query.filter(
        db.func.coalesce(
            Announcement.active,
            True
        ) == True,
        db.func.lower(
            db.func.trim(
                db.func.coalesce(
                    Announcement.audience,
                    ""
                )
            )
        ).in_([
            "staff",
            "all"
        ])
    ).count()

    settings = {}

    try:
        import sqlite3

        conn = sqlite3.connect(DATABASE_URL)
        conn.row_factory = sqlite3.Row

        rows = conn.execute(
            "SELECT setting_key, setting_value FROM system_settings"
        ).fetchall()

        settings = {
            row["setting_key"]: row["setting_value"]
            for row in rows
        }

        conn.close()

    except Exception:
        settings = {}

    return render_template(
        "new_staff/training_section_dashboard.html",
        staff_name=session.get("staff_name"),
        department=session.get("department"),
        students=students,
        search=search,
        total_students=total_students,
        issued_properties=issued_properties,
        returned_properties=returned_properties,
        outstanding_items=outstanding_items,
        pending_students=pending_students,
        students_cleared=students_cleared,
        clearance_percentage=clearance_percentage,
        recent_properties=recent_properties,
        recent_returns=recent_returns,
        training_section_activity=training_section_activity,
        announcements=announcements,
        announcement_count=announcement_count,
        settings=settings
    )



@app.route("/new-staff/hr/dashboard")
def new_staff_hr_dashboard():
    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    department = (session.get("department") or "").strip().lower()

    if department not in {
        "human resource / admin officer",
        "human resource/admin officer",
        "human resource",
        "hr",
    }:
        return redirect(url_for("new_staff_login"))

    search = (request.args.get("search") or "").strip()

    query = Student.query

    if search:
        query = query.filter(
            db.or_(
                Student.student_id.ilike(f"%{search}%"),
                Student.name.ilike(f"%{search}%")
            )
        )

    students = query.order_by(
        Student.name.asc()
    ).all()

    total_students = Student.query.count()

    active_cases = DisciplinaryCase.query.filter(
        db.func.lower(
            db.func.trim(
                db.func.coalesce(
                    DisciplinaryCase.status,
                    ""
                )
            )
        ).in_([
            "reported",
            "under review",
            "committee review",
        ])
    ).count()

    under_review = DisciplinaryCase.query.filter(
        db.func.lower(
            db.func.trim(
                db.func.coalesce(
                    DisciplinaryCase.status,
                    ""
                )
            )
        ) == "under review"
    ).count()

    committee_review = DisciplinaryCase.query.filter(
        db.func.lower(
            db.func.trim(
                db.func.coalesce(
                    DisciplinaryCase.status,
                    ""
                )
            )
        ) == "committee review"
    ).count()

    resolved_cases = DisciplinaryCase.query.filter(
        db.func.lower(
            db.func.trim(
                db.func.coalesce(
                    DisciplinaryCase.status,
                    ""
                )
            )
        ) == "resolved"
    ).count()

    suspended_students = DisciplinaryCase.query.filter(
        db.func.lower(
            db.func.trim(
                db.func.coalesce(
                    DisciplinaryCase.sanction,
                    ""
                )
            )
        ) == "suspension",
        db.func.lower(
            db.func.trim(
                db.func.coalesce(
                    DisciplinaryCase.sanction_status,
                    ""
                )
            )
        ).in_([
            "active",
            "ongoing",
        ])
    ).count()

    # --------------------------------------------------------
    # Past 7 Days Statistics
    # --------------------------------------------------------

    seven_days_ago = datetime.now() - timedelta(days=7)

    cases_reported_7d = DisciplinaryCase.query.filter(
        DisciplinaryCase.reported_at >= seven_days_ago
    ).count()

    cases_resolved_7d = DisciplinaryCase.query.filter(
        DisciplinaryCase.resolved_at >= seven_days_ago
    ).count()

    sanctions_issued_7d = DisciplinaryCase.query.filter(
        DisciplinaryCase.sanction_start >= seven_days_ago
    ).count()

    # --------------------------------------------------------
    # Past 7 Days Disciplinary Activity
    # --------------------------------------------------------
    today = zambia_now().date()

    disciplinary_activity = []

    for i in range(6, -1, -1):

        day = today - timedelta(days=i)

        start = datetime.combine(
            day,
            datetime.min.time()
        )

        end = start + timedelta(days=1)

        reported = DisciplinaryCase.query.filter(
            DisciplinaryCase.reported_at >= start,
            DisciplinaryCase.reported_at < end
        ).count()

        resolved = DisciplinaryCase.query.filter(
            DisciplinaryCase.resolved_at >= start,
            DisciplinaryCase.resolved_at < end
        ).count()

        sanctioned = DisciplinaryCase.query.filter(
            DisciplinaryCase.sanction_start >= start,
            DisciplinaryCase.sanction_start < end
        ).count()

        disciplinary_activity.append({
            "date": day.strftime("%a"),
            "reported": reported,
            "resolved": resolved
        })

    recent_cases = (
        DisciplinaryCase.query
        .order_by(
            DisciplinaryCase.reported_at.desc(),
            DisciplinaryCase.id.desc()
        )
        .limit(8)
        .all()
    )

    student_names = {}

    if recent_cases:
        student_ids = {
            case.student_id
            for case in recent_cases
        }

        if student_ids:
            student_rows = Student.query.filter(
                Student.student_id.in_(student_ids)
            ).all()

            student_names = {
                student.student_id: student.name
                for student in student_rows
            }

    announcements = Announcement.query.filter(
        db.func.coalesce(
            Announcement.active,
            True
        ) == True,
        db.func.lower(
            db.func.trim(
                db.func.coalesce(
                    Announcement.audience,
                    ""
                )
            )
        ).in_([
            "staff",
            "all",
        ])
    ).order_by(
        Announcement.created_at.desc()
    ).limit(5).all()

    announcement_count = Announcement.query.filter(
        db.func.coalesce(
            Announcement.active,
            True
        ) == True,
        db.func.lower(
            db.func.trim(
                db.func.coalesce(
                    Announcement.audience,
                    ""
                )
            )
        ).in_([
            "staff",
            "all",
        ])
    ).count()

    settings = {}
    try:
        import sqlite3
        conn = sqlite3.connect(DATABASE_URL)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT setting_key, setting_value FROM system_settings"
        ).fetchall()
        settings = {
            row["setting_key"]: row["setting_value"]
            for row in rows
        }
        conn.close()
    except Exception:
        settings = {}

    return render_template(
        "new_staff/hr_dashboard.html",
        staff_name=session.get("staff_name"),
        department=session.get("department"),
        students=students,
        search=search,
        total_students=total_students,
        active_cases=active_cases,
        under_review=under_review,
        committee_review=committee_review,
        resolved_cases=resolved_cases,
        suspended_students=suspended_students,
        cases_reported_7d=cases_reported_7d,
        cases_resolved_7d=cases_resolved_7d,
        sanctions_issued_7d=sanctions_issued_7d,
        disciplinary_activity=disciplinary_activity,
        recent_cases=recent_cases,
        student_names=student_names,
        announcements=announcements,
        announcement_count=announcement_count,
        settings=settings,
    )



@app.route("/new-staff/hr/students")
def new_staff_hr_students():

    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    department = (
        session.get("department") or ""
    ).strip().lower()

    if department not in {
        "human resource / admin officer",
        "human resource/admin officer",
        "human resource",
        "hr",
    }:
        return redirect(url_for("new_staff_login"))

    search = (
        request.args.get("search") or ""
    ).strip()

    query = Student.query

    if search:
        query = query.filter(
            db.or_(
                Student.student_id.ilike(
                    f"%{search}%"
                ),
                Student.name.ilike(
                    f"%{search}%"
                )
            )
        )

    students = (
        query
        .order_by(Student.name.asc())
        .all()
    )

    # Build a case summary for each student.
    case_counts = {}
    current_status = {}

    cases = (
        DisciplinaryCase.query
        .order_by(
            DisciplinaryCase.reported_at.desc(),
            DisciplinaryCase.id.desc()
        )
        .all()
    )

    for case in cases:
        case_counts[case.student_id] = (
            case_counts.get(case.student_id, 0) + 1
        )

        if case.student_id not in current_status:
            current_status[case.student_id] = (
                case.status or "Reported"
            )

    return render_template(
        "new_staff/hr_students.html",
        staff_name=session.get("staff_name"),
        department=session.get("department"),
        students=students,
        search=search,
        case_counts=case_counts,
        current_status=current_status,
    )



@app.route(
    "/new-staff/hr/report-offence",
    methods=["GET", "POST"]
)
def new_staff_hr_report_offence():

    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    department = (
        session.get("department") or ""
    ).strip().lower()

    if department not in {
        "human resource / admin officer",
        "human resource/admin officer",
        "human resource",
        "hr",
    }:
        return redirect(url_for("new_staff_login"))

    students = (
        Student.query
        .order_by(Student.name.asc())
        .all()
    )

    if request.method == "POST":

        student_id = (
            request.form.get("student_id") or ""
        ).strip()

        offence = (
            request.form.get("offence") or ""
        ).strip()

        offence_date_raw = (
            request.form.get("offence_date") or ""
        ).strip()

        location = (
            request.form.get("location") or ""
        ).strip()

        description = (
            request.form.get("description") or ""
        ).strip()

        reported_by = (
            request.form.get("reported_by")
            or session.get("staff_name")
            or ""
        ).strip()

        student = Student.query.filter_by(
            student_id=student_id
        ).first()

        if not student:
            flash(
                "Please select a valid student.",
                "error"
            )

            return render_template(
                "new_staff/hr_report_offence.html",
                staff_name=session.get("staff_name"),
                department=session.get("department"),
                students=students,
                selected_student_id=student_id,
                offence=offence,
                offence_date=offence_date_raw,
                location=location,
                description=description,
                reported_by=reported_by,
            )

        if not offence:
            flash(
                "Please enter the disciplinary offence.",
                "error"
            )

            return render_template(
                "new_staff/hr_report_offence.html",
                staff_name=session.get("staff_name"),
                department=session.get("department"),
                students=students,
                selected_student_id=student_id,
                offence=offence,
                offence_date=offence_date_raw,
                location=location,
                description=description,
                reported_by=reported_by,
            )

        if not description:
            flash(
                "Please enter an incident description.",
                "error"
            )

            return render_template(
                "new_staff/hr_report_offence.html",
                staff_name=session.get("staff_name"),
                department=session.get("department"),
                students=students,
                selected_student_id=student_id,
                offence=offence,
                offence_date=offence_date_raw,
                location=location,
                description=description,
                reported_by=reported_by,
            )

        offence_date = None

        if offence_date_raw:
            try:
                offence_date = datetime.strptime(
                    offence_date_raw,
                    "%Y-%m-%d"
                )
            except ValueError:
                flash(
                    "The incident date is invalid.",
                    "error"
                )

                return render_template(
                    "new_staff/hr_report_offence.html",
                    staff_name=session.get("staff_name"),
                    department=session.get("department"),
                    students=students,
                    selected_student_id=student_id,
                    offence=offence,
                    offence_date=offence_date_raw,
                    location=location,
                    description=description,
                    reported_by=reported_by,
                )

        case = DisciplinaryCase(
            student_id=student.student_id,
            offence=offence,
            offence_date=offence_date,
            location=location or None,
            description=description,
            reported_by=reported_by or None,
            status="Reported",
        )

        db.session.add(case)
        db.session.commit()

        flash(
            f"Disciplinary case reported for {student.name}.",
            "success"
        )

        return redirect(
            url_for("new_staff_hr_report_offence")
        )

    return render_template(
        "new_staff/hr_report_offence.html",
        staff_name=session.get("staff_name"),
        department=session.get("department"),
        students=students,
        selected_student_id="",
        offence="",
        offence_date="",
        location="",
        description="",
        reported_by=session.get("staff_name") or "",
    )



@app.route("/new-staff/hr/disciplinary-records")
def new_staff_hr_disciplinary_records():

    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    department = (
        session.get("department") or ""
    ).strip().lower()

    if department not in {
        "human resource / admin officer",
        "human resource/admin officer",
        "human resource",
        "hr",
    }:
        return redirect(url_for("new_staff_login"))

    search = (
        request.args.get("search") or ""
    ).strip()

    query = DisciplinaryCase.query

    if search:
        matching_students = Student.query.filter(
            db.or_(
                Student.student_id.ilike(
                    f"%{search}%"
                ),
                Student.name.ilike(
                    f"%{search}%"
                )
            )
        ).all()

        matching_student_ids = [
            student.student_id
            for student in matching_students
        ]

        query = query.filter(
            db.or_(
                DisciplinaryCase.offence.ilike(
                    f"%{search}%"
                ),
                DisciplinaryCase.student_id.in_(
                    matching_student_ids
                ) if matching_student_ids else False
            )
        )

    cases = (
        query
        .order_by(
            DisciplinaryCase.reported_at.desc(),
            DisciplinaryCase.id.desc()
        )
        .all()
    )

    student_ids = {
        case.student_id
        for case in cases
    }

    student_map = {}

    if student_ids:
        student_rows = Student.query.filter(
            Student.student_id.in_(student_ids)
        ).all()

        student_map = {
            student.student_id: student
            for student in student_rows
        }

    return render_template(
        "new_staff/hr_disciplinary_records.html",
        staff_name=session.get("staff_name"),
        department=session.get("department"),
        cases=cases,
        student_map=student_map,
        search=search,
    )


@app.route("/new-staff/mathematics/dashboard")
def new_staff_mathematics_dashboard():
    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    department = (
        session.get("department") or ""
    ).strip().lower()

    if department not in {
        "mathematics",
        "mathematics department",
        "communication skills"
    }:
        return redirect(url_for("new_staff_login"))

    search = (
        request.args.get("search") or ""
    ).strip()

    query = Student.query

    if search:
        query = query.filter(
            db.or_(
                Student.student_id.ilike(
                    f"%{search}%"
                ),
                Student.name.ilike(
                    f"%{search}%"
                )
            )
        )

    students = query.order_by(
        Student.name.asc()
    ).all()

    total_students = Student.query.count()

    issued_properties = MathematicsProperty.query.filter(
        db.func.lower(
            db.func.trim(
                db.func.coalesce(
                    MathematicsProperty.status,
                    ""
                )
            )
        ).in_([
            "issued",
            "assigned"
        ])
    ).count()

    returned_properties = MathematicsProperty.query.filter(
        MathematicsProperty.returned_at.isnot(None)
    ).count()

    outstanding_items = (
        MathematicsProperty.query
        .filter(
            MathematicsProperty.returned_at.is_(None),
            db.func.lower(
                db.func.trim(
                    db.func.coalesce(
                        MathematicsProperty.status,
                        ""
                    )
                )
            ).notin_([
                "returned",
                "cleared",
                "declined"
            ])
        )
        .order_by(
            MathematicsProperty.issued_at.desc(),
            MathematicsProperty.id.desc()
        )
        .limit(8)
        .all()
    )

    pending_student_ids = {
        record.student_id
        for record in MathematicsProperty.query.filter(
            MathematicsProperty.returned_at.is_(None),
            db.func.lower(
                db.func.trim(
                    db.func.coalesce(
                        MathematicsProperty.status,
                        ""
                    )
                )
            ).notin_([
                "returned",
                "cleared",
                "declined"
            ])
        ).all()
    }

    pending_students = len(pending_student_ids)

    students_cleared = max(
        total_students - pending_students,
        0
    )

    clearance_percentage = (
        round(
            (students_cleared / total_students) * 100
        )
        if total_students
        else 0
    )

    recent_properties = (
        MathematicsProperty.query
        .order_by(
            MathematicsProperty.issued_at.desc(),
            MathematicsProperty.id.desc()
        )
        .limit(8)
        .all()
    )

    recent_returns = (
        MathematicsProperty.query
        .filter(
            MathematicsProperty.returned_at.isnot(None)
        )
        .order_by(
            MathematicsProperty.returned_at.desc(),
            MathematicsProperty.id.desc()
        )
        .limit(8)
        .all()
    )

    from datetime import datetime, timedelta

    today = zambia_now().date()

    mathematics_activity = []

    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        next_day = day + timedelta(days=1)

        issued_count = MathematicsProperty.query.filter(
            MathematicsProperty.issued_at >= datetime.combine(
                day,
                datetime.min.time()
            ),
            MathematicsProperty.issued_at < datetime.combine(
                next_day,
                datetime.min.time()
            )
        ).count()

        returned_count = MathematicsProperty.query.filter(
            MathematicsProperty.returned_at >= datetime.combine(
                day,
                datetime.min.time()
            ),
            MathematicsProperty.returned_at < datetime.combine(
                next_day,
                datetime.min.time()
            )
        ).count()

        mathematics_activity.append({
            "date": day.strftime("%a"),
            "issued": issued_count,
            "returned": returned_count
        })

    announcements = Announcement.query.filter(
        db.func.coalesce(
            Announcement.active,
            True
        ) == True,
        db.func.lower(
            db.func.trim(
                db.func.coalesce(
                    Announcement.audience,
                    ""
                )
            )
        ).in_([
            "staff",
            "all"
        ])
    ).order_by(
        Announcement.created_at.desc()
    ).limit(5).all()

    announcement_count = Announcement.query.filter(
        db.func.coalesce(
            Announcement.active,
            True
        ) == True,
        db.func.lower(
            db.func.trim(
                db.func.coalesce(
                    Announcement.audience,
                    ""
                )
            )
        ).in_([
            "staff",
            "all"
        ])
    ).count()

    settings = {}

    try:
        import sqlite3

        conn = sqlite3.connect(DATABASE_URL)
        conn.row_factory = sqlite3.Row

        rows = conn.execute(
            "SELECT setting_key, setting_value FROM system_settings"
        ).fetchall()

        settings = {
            row["setting_key"]: row["setting_value"]
            for row in rows
        }

        conn.close()

    except Exception:
        settings = {}

    return render_template(
        "new_staff/mathematics_dashboard.html",
        staff_name=session.get("staff_name"),
        department=session.get("department"),
        students=students,
        search=search,
        total_students=total_students,
        issued_properties=issued_properties,
        returned_properties=returned_properties,
        outstanding_items=outstanding_items,
        pending_students=pending_students,
        students_cleared=students_cleared,
        clearance_percentage=clearance_percentage,
        recent_properties=recent_properties,
        recent_returns=recent_returns,
        mathematics_activity=mathematics_activity,
        announcements=announcements,
        announcement_count=announcement_count,
        settings=settings
    )




# ============================================================
# NEW STAFF COMMUNICATION SKILLS — ANNOUNCEMENTS
# ============================================================

@app.route("/new-staff/communication/announcements")
def new_staff_communication_announcements():

    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    department = (
        session.get("department") or ""
    ).strip().lower()

    if department not in {
        "communication skills (rel/sc)",
        "communication skills (rel sc)",
        "communication skills",
    }:
        return redirect(url_for("new_staff_login"))

    announcements = (
        Announcement.query
        .filter(
            db.func.coalesce(
                Announcement.active,
                True
            ) == True,
            db.func.lower(
                db.func.trim(
                    db.func.coalesce(
                        Announcement.audience,
                        ""
                    )
                )
            ).in_([
                "staff",
                "all"
            ])
        )
        .order_by(
            Announcement.created_at.desc()
        )
        .all()
    )

    return render_template(
        "new_staff/communication/announcements.html",
        staff_name=(
            session.get("staff_name")
            or session.get("name")
            or session.get("username")
            or "Communication Skills Staff"
        ),
        department=(
            session.get("department")
            or "Communication Skills (REL/SC)"
        ),
        announcements=announcements
    )


# ============================================================
# NEW STAFF MATHEMATICS — ANNOUNCEMENTS
# ============================================================

@app.route("/new-staff/mathematics/announcements")
def new_staff_mathematics_announcements():
    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    department = (
        session.get("department") or ""
    ).strip().lower()

    if department not in {
        "mathematics",
        "mathematics department",
        "communication skills"
    }:
        return redirect(url_for("new_staff_login"))

    announcements = (
        Announcement.query
        .filter(
            db.func.coalesce(
                Announcement.active,
                True
            ) == True,
            db.func.lower(
                db.func.trim(
                    db.func.coalesce(
                        Announcement.audience,
                        ""
                    )
                )
            ).in_([
                "staff",
                "all"
            ])
        )
        .order_by(
            Announcement.created_at.desc()
        )
        .all()
    )

    return render_template(
        "new_staff/mathematics/announcements.html",
        staff_name=(
            session.get("staff_name")
            or session.get("name")
            or session.get("username")
            or "Mathematics Staff"
        ),
        department=(
            session.get("department")
            or "Mathematics"
        ),
        announcements=announcements
    )


# ============================================================
# NEW STAFF TRAINING SECTION — ANNOUNCEMENTS
# ============================================================

@app.route("/new-staff/training-section/announcements")
def new_staff_training_section_announcements():

    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    department = (
        session.get("department") or ""
    ).strip().lower()

    if department != "training section":
        return redirect(url_for("new_staff_login"))

    announcements = (
        Announcement.query
        .filter(
            db.func.coalesce(
                Announcement.active,
                True
            ) == True,
            db.func.lower(
                db.func.trim(
                    db.func.coalesce(
                        Announcement.audience,
                        ""
                    )
                )
            ).in_([
                "staff",
                "all"
            ])
        )
        .order_by(
            Announcement.created_at.desc()
        )
        .all()
    )

    return render_template(
        "new_staff/training_section/announcements.html",
        staff_name=(
            session.get("staff_name")
            or session.get("name")
            or session.get("username")
            or "Training Section Staff"
        ),
        department=(
            session.get("department")
            or "Training Section"
        ),
        announcements=announcements
    )


@app.route("/new-staff/stores/dashboard")
def new_staff_stores_dashboard():

    # --------------------------------------------------
    # STORES STAFF ONLY
    # --------------------------------------------------

    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    department = (
        session.get("department") or ""
    ).strip().lower()

    if department not in {
        "stores",
        "stores department",
        "stores office",
        "stores officer"
    }:

        if department in {
            "accounts",
            "accounts department"
        }:
            return redirect(
                url_for("new_staff_accounts_dashboard")
            )

        if department in {
            "library",
            "library department"
        }:
            return redirect(
                url_for("new_staff_library_dashboard")
            )

        if department in {
            "sports",
            "sports department"
        }:
            return redirect(
                url_for("new_staff_sports_dashboard")
            )

        return redirect(
            url_for("new_staff_login")
        )

    # --------------------------------------------------
    # SEARCH
    # --------------------------------------------------

    search = (
        request.args.get("search") or ""
    ).strip()

    # --------------------------------------------------
    # STUDENTS
    # --------------------------------------------------

    query = Student.query

    if search:
        query = query.filter(
            db.or_(
                Student.student_id.ilike(
                    f"%{search}%"
                ),
                Student.name.ilike(
                    f"%{search}%"
                )
            )
        )

    students = query.order_by(
        Student.name.asc()
    ).all()

    # --------------------------------------------------
    # STORES STATISTICS
    # --------------------------------------------------

    total_students = Student.query.count()

    issued_properties = StoreProperty.query.filter(
        db.func.lower(
            db.func.trim(
                db.func.coalesce(
                    StoreProperty.status,
                    ""
                )
            )
        ) == "issued"
    ).count()

    returned_properties = StoreProperty.query.filter(
        StoreProperty.returned_at.isnot(None)
    ).count()

    outstanding_properties = StoreProperty.query.filter(
        StoreProperty.returned_at.is_(None),
        db.func.lower(
            db.func.trim(
                db.func.coalesce(
                    StoreProperty.status,
                    ""
                )
            )
        ).notin_([
            "returned",
            "cleared",
            "declined"
        ])
    ).count()

    mattress_assigned = StoreProperty.query.filter(
        db.func.lower(
            db.func.trim(
                db.func.coalesce(
                    StoreProperty.name,
                    ""
                )
            )
        ) == "mattress",
        db.func.lower(
            db.func.trim(
                db.func.coalesce(
                    StoreProperty.status,
                    ""
                )
            )
        ).in_([
            "assigned",
            "issued"
        ])
    ).count()

    # --------------------------------------------------
    # RECENT STORES ACTIVITY
    # --------------------------------------------------

    recent_properties = (
        StoreProperty.query
        .order_by(
            StoreProperty.issued_at.desc(),
            StoreProperty.id.desc()
        )
        .limit(8)
        .all()
    )

    # --------------------------------------------------
    # OUTSTANDING PROPERTY DETAILS
    # --------------------------------------------------

    outstanding_items = (
        StoreProperty.query
        .filter(
            StoreProperty.returned_at.is_(None),
            db.func.lower(
                db.func.trim(
                    db.func.coalesce(
                        StoreProperty.status,
                        ""
                    )
                )
            ).notin_([
                "returned",
                "cleared",
                "declined"
            ])
        )
        .order_by(
            StoreProperty.issued_at.desc(),
            StoreProperty.id.desc()
        )
        .limit(8)
        .all()
    )

    # --------------------------------------------------
    # RECENT RETURNS
    # --------------------------------------------------

    recent_returns = (
        StoreProperty.query
        .filter(
            StoreProperty.returned_at.isnot(None)
        )
        .order_by(
            StoreProperty.returned_at.desc(),
            StoreProperty.id.desc()
        )
        .limit(8)
        .all()
    )

    # --------------------------------------------------
    # 7-DAY STORES ACTIVITY
    # --------------------------------------------------

    from datetime import datetime, timedelta

    today = zambia_now().date()

    store_activity = []

    for offset in range(6, -1, -1):

        day = today - timedelta(days=offset)

        next_day = day + timedelta(days=1)

        issued_count = StoreProperty.query.filter(
            StoreProperty.issued_at >= datetime.combine(
                day,
                datetime.min.time()
            ),
            StoreProperty.issued_at < datetime.combine(
                next_day,
                datetime.min.time()
            )
        ).count()

        returned_count = StoreProperty.query.filter(
            StoreProperty.returned_at >= datetime.combine(
                day,
                datetime.min.time()
            ),
            StoreProperty.returned_at < datetime.combine(
                next_day,
                datetime.min.time()
            )
        ).count()

        store_activity.append({
            "date": day.strftime("%a"),
            "issued": issued_count,
            "returned": returned_count
        })

    # --------------------------------------------------
    # ANNOUNCEMENTS
    # --------------------------------------------------

    announcements = Announcement.query.filter(
        db.func.coalesce(
            Announcement.active,
            True
        ) == True,

        db.func.lower(
            db.func.trim(
                db.func.coalesce(
                    Announcement.audience,
                    ""
                )
            )
        ).in_([
            "staff",
            "all"
        ])
    ).order_by(
        Announcement.created_at.desc()
    ).limit(5).all()

    # --------------------------------------------------
    # ANNOUNCEMENT COUNT
    # --------------------------------------------------

    announcement_count = Announcement.query.filter(
        db.func.coalesce(
            Announcement.active,
            True
        ) == True,

        db.func.lower(
            db.func.trim(
                db.func.coalesce(
                    Announcement.audience,
                    ""
                )
            )
        ).in_([
            "staff",
            "all"
        ])
    ).count()

    # --------------------------------------------------
    # DASHBOARD SETTINGS
    # --------------------------------------------------

    import sqlite3

    calendar_conn = sqlite3.connect(DATABASE_URL)
    calendar_cursor = calendar_conn.cursor()

    calendar_cursor.execute("""
        SELECT setting_key, setting_value
        FROM system_settings
    """)

    settings = dict(
        calendar_cursor.fetchall()
    )

    calendar_conn.close()

    # --------------------------------------------------
    # CLEARANCE PERCENTAGE
    # --------------------------------------------------

    if total_students > 0:
        students_with_no_outstanding = 0

        for student in Student.query.all():

            student_items = StoreProperty.query.filter_by(
                student_id=student.student_id
            ).all()

            outstanding_for_student = [
                item
                for item in student_items
                if not item.returned_at
                and (
                    (item.status or "").strip().lower()
                    not in {
                        "returned",
                        "cleared",
                        "declined"
                    }
                )
            ]

            if not outstanding_for_student:
                students_with_no_outstanding += 1

        clearance_percentage = round(
            (
                students_with_no_outstanding
                / total_students
            ) * 100
        )
    else:
        students_with_no_outstanding = 0
        clearance_percentage = 0

    # --------------------------------------------------
    # STAFF NAME
    # --------------------------------------------------

    staff_name = (
        session.get("staff_name")
        or session.get("name")
        or session.get("username")
        or "Stores Staff"
    )

    # --------------------------------------------------
    # DASHBOARD
    # --------------------------------------------------

    return render_template(
        "new_staff/stores/dashboard.html",

        staff_name=staff_name,

        department=(
            session.get("department")
            or "Stores"
        ),

        students=students,

        search=search,

        total_students=total_students,

        issued_properties=issued_properties,

        returned_properties=returned_properties,

        outstanding_properties=(
            outstanding_properties
        ),

        mattress_assigned=mattress_assigned,

        recent_properties=recent_properties,

        outstanding_items=outstanding_items,

        recent_returns=recent_returns,

        store_activity=store_activity,

        announcements=announcements,

        announcement_count=announcement_count,

        students_with_no_outstanding=(
            students_with_no_outstanding
        ),

        clearance_percentage=(
            clearance_percentage
        ),

        settings=settings
    )

@app.route("/new-staff/stores/announcements")
def new_staff_stores_announcements():

    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    department = (
        session.get("department") or ""
    ).strip().lower()

    if department not in {
        "stores",
        "stores department",
        "stores office",
        "stores officer"
    }:
        return redirect(url_for("new_staff_login"))

    announcements = Announcement.query.filter(
        db.func.coalesce(
            Announcement.active,
            True
        ) == True,
        db.func.lower(
            db.func.trim(
                db.func.coalesce(
                    Announcement.audience,
                    ""
                )
            )
        ).in_(["staff", "all"])
    ).order_by(
        Announcement.created_at.desc()
    ).all()

    return render_template(
        "new_staff/stores/announcements.html",
        staff_name=(
            session.get("staff_name")
            or session.get("name")
            or session.get("username")
            or "Stores Staff"
        ),
        department=session.get("department") or "Stores",
        announcements=announcements
    )


# ============================================================
# NEW STAFF STORES — PROPERTY RECORDS
# ============================================================


# ============================================================
# NEW STAFF STORES — PROPERTY RECORDS
# ============================================================

@app.route("/new-staff/stores/students")
def new_staff_stores_students():

    # Stores staff are already authenticated by the
    # Stores dashboard/login flow.

    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    search = (
        request.args.get("search") or ""
    ).strip()

    query = Student.query

    if search:
        query = query.filter(
            db.or_(
                Student.student_id.ilike(
                    f"%{search}%"
                ),
                Student.name.ilike(
                    f"%{search}%"
                )
            )
        )

    students = query.order_by(
        Student.name.asc()
    ).all()

    return render_template(
        "new_staff/stores/students.html",
        staff_name=session.get("staff_name"),
        department=session.get("department"),
        students=students,
        search=search
    )



# ============================================================
# NEW STAFF STORES — STUDENT DETAILS
# ============================================================

@app.route("/new-staff/stores/students/<student_id>")
def new_staff_stores_student_details(student_id):

    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    student = Student.query.filter_by(
        student_id=student_id
    ).first_or_404()

    store_properties = StoreProperty.query.filter_by(
        student_id=student.student_id
    ).order_by(
        StoreProperty.issued_at.desc()
    ).all()

    outstanding = [
        item for item in store_properties
        if not item.returned_at
    ]

    returned = [
        item for item in store_properties
        if item.returned_at
    ]

    return render_template(
        "new_staff/stores/student_details.html",
        staff_name=session.get("staff_name"),
        department=session.get("department"),
        student=student,
        store_properties=store_properties,
        outstanding=outstanding,
        returned=returned
    )


# ============================================================
# NEW STAFF STORES — ISSUE PROPERTY
# ============================================================

@app.route("/new-staff/stores/issue-property", methods=["GET", "POST"])
def new_staff_stores_issue_property():

    # --------------------------------------------------
    # STORES STAFF ONLY
    # --------------------------------------------------

    if session.get("role") != "staff":
        return redirect(
            url_for("new_staff_login")
        )

    # --------------------------------------------------
    # CREATE PENDING PROPERTY REQUESTS
    # --------------------------------------------------

    if request.method == "POST":

        student_id = (
            request.form.get("student_id") or ""
        ).strip()

        issue_mattress = (
            request.form.get("mattress") == "yes"
        )

        optional_property = (
            request.form.get("optional_property") or ""
        ).strip()

        if not student_id:
            flash(
                "Please select a student.",
                "error"
            )
            return redirect(
                url_for("new_staff_stores_issue_property")
            )

        student = Student.query.filter_by(
            student_id=student_id
        ).first()

        if not student:
            flash(
                "Student not found.",
                "error"
            )
            return redirect(
                url_for("new_staff_stores_issue_property")
            )

        staff_name = (
            session.get("staff_name")
            or "Stores Staff"
        )

        created_requests = []

        # --------------------------------------------------
        # MATTRESS REQUEST
        # --------------------------------------------------

        if issue_mattress:

            existing_mattress_request = ItemRequest.query.filter(
                ItemRequest.student_id == student.student_id,
                db.func.lower(ItemRequest.item) == "mattress",
                db.func.lower(ItemRequest.status) == "pending"
            ).first()

            existing_mattress = StoreProperty.query.filter(
                StoreProperty.student_id == student.student_id,
                db.func.lower(StoreProperty.name) == "mattress",
                db.func.lower(StoreProperty.status) != "returned"
            ).first()

            if not existing_mattress_request and not existing_mattress:

                mattress_request = ItemRequest(
                    student_id=student.student_id,
                    department="stores",
                    item="Mattress",
                    item_type="Institutional Property",
                    status="Pending",
                    assigned_by=staff_name,
                    remarks="Mattress issued by Stores pending student confirmation."
                )

                db.session.add(mattress_request)
                created_requests.append("Mattress")

        # --------------------------------------------------
        # OPTIONAL PROPERTY REQUEST
        # --------------------------------------------------

        if optional_property:

            existing_optional_request = ItemRequest.query.filter(
                ItemRequest.student_id == student.student_id,
                db.func.lower(ItemRequest.item) == optional_property.lower(),
                db.func.lower(ItemRequest.status) == "pending"
            ).first()

            existing_optional_property = StoreProperty.query.filter(
                StoreProperty.student_id == student.student_id,
                db.func.lower(StoreProperty.name) == optional_property.lower(),
                db.func.lower(StoreProperty.status) != "returned"
            ).first()

            if not existing_optional_request and not existing_optional_property:

                optional_request = ItemRequest(
                    student_id=student.student_id,
                    department="stores",
                    item=optional_property,
                    item_type="Institutional Property",
                    status="Pending",
                    assigned_by=staff_name,
                    remarks=(
                        f"Optional property issued by Stores "
                        f"pending student confirmation."
                    )
                )

                db.session.add(optional_request)
                created_requests.append(optional_property)

        # --------------------------------------------------
        # NOTHING NEW TO REQUEST
        # --------------------------------------------------

        if not created_requests:

            flash(
                "No new property request was created. "
                "The selected property may already be issued "
                "or awaiting student confirmation.",
                "error"
            )

            return redirect(
                url_for(
                    "new_staff_stores_issue_property",
                    student_id=student.student_id
                )
            )

        db.session.commit()

        flash(
            f"Property request sent to {student.name} "
            f"for confirmation.",
            "success"
        )

        return redirect(
            url_for(
                "new_staff_stores_issue_property",
                student_id=student.student_id,
                success="1"
            )
        )

    # --------------------------------------------------
    # STUDENT SEARCH / SELECTION
    # --------------------------------------------------

    search = (
        request.args.get("search") or ""
    ).strip()

    selected_student_id = (
        request.args.get("student_id") or ""
    ).strip()

    selected_student = None

    if selected_student_id:

        selected_student = Student.query.filter_by(
            student_id=selected_student_id
        ).first()

    query = Student.query

    if search:

        query = query.filter(
            db.or_(
                Student.student_id.ilike(
                    f"%{search}%"
                ),
                Student.name.ilike(
                    f"%{search}%"
                )
            )
        )

    students = query.order_by(
        Student.name.asc()
    ).all()

    return render_template(
        "new_staff/stores/issue_property.html",
        staff_name=session.get("staff_name"),
        department=session.get("department"),
        students=students,
        search=search,
        selected_student=selected_student,
        success=request.args.get("success") == "1"
    )



# ============================================================
# NEW STAFF STORES — RETURN STORES ITEMS
# ============================================================

@app.route("/new-staff/stores/return-property", methods=["GET", "POST"])
def new_staff_stores_return_property():
    """
    Stores staff return-property page.

    Source of truth:
    - ItemRequest must be Accepted.
    - StoreProperty must be linked to that request through request_id.
    - Only currently Issued properties are available for return.
    """

    if session.get("role") != "staff":
        flash("Access denied.", "error")
        return redirect(url_for("login"))

    department = (session.get("department") or "").strip().lower()

    if department not in {"stores", "stores department", "stores office", "stores officer"}:
        flash("Access denied.", "error")
        return redirect(url_for("login"))

    if request.method == "POST":
        student_id = (request.form.get("student_id") or "").strip()
        property_id = (request.form.get("property_id") or "").strip()
        return_status = (request.form.get("status") or "Good").strip()
        remarks = (request.form.get("remarks") or "").strip()

        if not student_id or not property_id:
            flash("Please select both a student and a property.", "error")
            return redirect(url_for("new_staff_stores_return_property"))

        try:
            property_id_int = int(property_id)
        except ValueError:
            flash("Invalid property selected.", "error")
            return redirect(url_for("new_staff_stores_return_property"))

        prop = StoreProperty.query.filter_by(
            id=property_id_int,
            student_id=student_id
        ).first()

        if not prop:
            flash("The selected property could not be found.", "error")
            return redirect(url_for("new_staff_stores_return_property"))

        if prop.status and prop.status.strip().lower() == "returned":
            flash("This property has already been returned.", "error")
            return redirect(url_for("new_staff_stores_return_property"))

        if not prop.request_id:
            flash("This property is not linked to a valid Stores issue request.", "error")
            return redirect(url_for("new_staff_stores_return_property"))

        item_request = ItemRequest.query.filter_by(
            id=prop.request_id,
            student_id=student_id
        ).first()

        if not item_request:
            flash("The original Stores issue request could not be found.", "error")
            return redirect(url_for("new_staff_stores_return_property"))

        if item_request.status.strip().lower() != "accepted":
            flash("This property does not belong to an accepted Stores request.", "error")
            return redirect(url_for("new_staff_stores_return_property"))

        returned_at = zambia_now()

        prop.status = "Returned"
        prop.returned_by = session.get("user") or "Stores Staff"
        prop.returned_at = returned_at

        # Preserve the actual return condition/notes.
        return_details = f"Condition: {return_status}"
        if remarks:
            return_details += f" | {remarks}"

        prop.remarks = return_details

        db.session.commit()

        flash(f"{prop.name} returned successfully.", "success")
        return redirect(url_for("new_staff_stores_return_property"))

    # ------------------------------------------------------------
    # Build dropdown data from currently issued Stores properties.
    # ------------------------------------------------------------

    issued_properties = (
        StoreProperty.query
        .filter(
            StoreProperty.status.isnot(None),
            db.func.lower(StoreProperty.status) == "issued",
            StoreProperty.request_id.isnot(None)
        )
        .order_by(StoreProperty.issued_at.desc(), StoreProperty.id.desc())
        .all()
    )

    # Keep only properties whose original Stores request is Accepted.
    active_records = []

    for prop in issued_properties:
        item_request = ItemRequest.query.filter_by(
            id=prop.request_id,
            student_id=prop.student_id
        ).first()

        if not item_request:
            continue

        if item_request.status.strip().lower() != "accepted":
            continue

        active_records.append((prop, item_request))

    # ------------------------------------------------------------
    # The existing template expects:
    #     students
    #     properties
    #
    # Therefore provide exactly those variables.
    # ------------------------------------------------------------

    students_by_id = {}

    for prop, item_request in active_records:
        student = Student.query.filter_by(
            student_id=prop.student_id
        ).first()

        if student:
            students_by_id[student.student_id] = student

    students = list(students_by_id.values())

    # Sort students by name, then student ID.
    students.sort(
        key=lambda s: (
            (getattr(s, "name", None) or "").lower(),
            getattr(s, "student_id", "") or ""
        )
    )

    # Properties are already ordered newest-first.
    properties = [prop for prop, item_request in active_records]

    return render_template(
        "new_staff/stores/return_property.html",
        students=students,
        properties=properties
    )


@app.route("/new-staff/stores/property-records", methods=["GET"])
def new_staff_stores_property_records():
    # ============================================================
    # STORES STAFF ONLY
    # ============================================================

    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    department = (
        session.get("department") or ""
    ).strip().lower()

    if department not in {
        "stores",
        "stores department",
        "stores office",
        "stores officer"
    }:
        return redirect(url_for("new_staff_login"))

    # ============================================================
    # FILTERS
    # ============================================================

    search = (
        request.args.get("search") or ""
    ).strip()

    status_filter = (
        request.args.get("status") or ""
    ).strip().lower()

    # Normalize the filter values.
    if status_filter == "pending":
        status_filter = "pending_confirmation"

    # ============================================================
    # ITEM REQUESTS ARE THE SOURCE OF TRUTH
    #
    # Pending  -> Pending Confirmation
    # Accepted -> matching StoreProperty
    # Declined -> not displayed
    #
    # We deliberately DO NOT use unmatched/legacy StoreProperty
    # records as current Stores records.
    # ============================================================

    stores_requests = ItemRequest.query.filter(
        db.func.lower(
            db.func.trim(
                db.func.coalesce(
                    ItemRequest.department,
                    ""
                )
            )
        ) == "stores"
    ).order_by(
        ItemRequest.assigned_at.desc(),
        ItemRequest.id.desc()
    ).all()

    # All StoreProperty records are loaded once so exact
    # request_id matching is efficient and predictable.
    property_records = StoreProperty.query.order_by(
        StoreProperty.id.desc()
    ).all()

    properties_by_request = {}

    for prop in property_records:
        request_id = getattr(prop, "request_id", None)

        if request_id is not None:
            properties_by_request[request_id] = prop

    records = []

    # ============================================================
    # PROCESS STORES REQUESTS
    # ============================================================

    for req in stores_requests:

        req_status = (
            (req.status or "")
            .strip()
            .lower()
        )

        # --------------------------------------------------------
        # DECLINED REQUESTS ARE NOT PROPERTY RECORDS
        # --------------------------------------------------------

        if req_status == "declined":
            continue

        # --------------------------------------------------------
        # STUDENT
        # --------------------------------------------------------

        student = Student.query.filter_by(
            student_id=req.student_id
        ).first()

        student_name = (
            student.name
            if student
            else "Unknown Student"
        )

        property_name = (
            req.item or ""
        ).strip()

        property_type = (
            "Mattress"
            if property_name.lower() == "mattress"
            else "Optional Stores Property"
        )

        # --------------------------------------------------------
        # SEARCH
        # --------------------------------------------------------

        if search:
            search_lower = search.lower()

            searchable = " ".join([
                student_name or "",
                str(req.student_id or ""),
                property_name,
                req.assigned_by or "",
                req.remarks or ""
            ]).lower()

            if search_lower not in searchable:
                continue

        # ========================================================
        # PENDING CONFIRMATION
        #
        # There is NO StoreProperty yet.
        #
        # Therefore:
        # issued_by  = —
        # issued_at  = —
        # returned_by = —
        # returned_at = —
        # ========================================================

        if req_status == "pending":

            if status_filter not in {
                "",
                "pending_confirmation"
            }:
                continue

            records.append({
                "id": f"request-{req.id}",
                "student_id": req.student_id,
                "student_name": student_name,
                "property_name": property_name,
                "property_type": property_type,

                "issued_by": None,
                "issued_at": None,

                "returned_by": None,
                "returned_at": None,

                "status": "Pending Confirmation",
                "remarks": req.remarks
            })

            continue

        # ========================================================
        # ACCEPTED
        #
        # Accepted requests must have an actual StoreProperty
        # created by the student acceptance route.
        #
        # Match ONLY by request_id.
        # ========================================================

        if req_status == "accepted":

            prop = properties_by_request.get(req.id)

            # ----------------------------------------------------
            # Safety: accepted request with no property record
            #
            # Do NOT invent an Issued record.
            # ----------------------------------------------------

            if prop is None:
                continue

            prop_status = (
                (prop.status or "")
                .strip()
                .lower()
            )

            if prop_status == "returned":
                display_status = "Returned"
            else:
                display_status = "Issued"

            # ----------------------------------------------------
            # STATUS FILTER
            # ----------------------------------------------------

            if status_filter == "pending_confirmation":
                continue

            if status_filter == "issued":
                if display_status != "Issued":
                    continue

            if status_filter == "returned":
                if display_status != "Returned":
                    continue

            # ----------------------------------------------------
            # ACTUAL STORES PROPERTY DATA
            # ----------------------------------------------------

            records.append({
                "id": f"property-{prop.id}",

                "student_id": prop.student_id,
                "student_name": student_name,

                "property_name": prop.name,
                "property_type": (
                    "Mattress"
                    if (
                        (prop.name or "")
                        .strip()
                        .lower()
                        == "mattress"
                    )
                    else "Optional Stores Property"
                ),

                "issued_by": (
                    getattr(prop, "issued_by", None)
                    or req.assigned_by
                ),

                "issued_at": (
                    prop.issued_at
                    or req.responded_at
                ),

                "returned_by": getattr(
                    prop,
                    "returned_by",
                    None
                ),

                "returned_at": prop.returned_at,

                "status": display_status,

                "remarks": (
                    prop.remarks
                    or req.remarks
                )
            })

            continue

        # --------------------------------------------------------
        # UNKNOWN STATUS
        #
        # Do not expose unexpected request states as issued
        # property records.
        # --------------------------------------------------------

        continue

    # ============================================================
    # SORT
    # ============================================================

    def record_sort_key(record):
        return (
            record.get("issued_at")
            or record.get("returned_at")
            or datetime.min
        )

    records.sort(
        key=record_sort_key,
        reverse=True
    )

    # ============================================================
    # RENDER
    # ============================================================

    return render_template(
        "new_staff/stores/property_records.html",

        staff_name=(
            session.get("staff_name")
            or session.get("name")
            or session.get("username")
            or "Stores Staff"
        ),

        department=(
            session.get("department")
            or "Stores"
        ),

        records=records,

        search=search,

        status_filter=status_filter
    )

@app.route("/new-staff/stores/records", methods=["GET"])
def new_staff_stores_records():

    # --------------------------------------------------
    # STORES STAFF ONLY
    # --------------------------------------------------

    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    department = (
        session.get("department") or ""
    ).strip().lower()

    if department not in {
        "stores",
        "stores department",
        "stores office",
        "stores officer"
    }:
        return redirect(url_for("new_staff_login"))

    # --------------------------------------------------
    # SEARCH
    # --------------------------------------------------

    search = (
        request.args.get("search") or ""
    ).strip()

    status_filter = (
        request.args.get("status") or ""
    ).strip().lower()

    # --------------------------------------------------
    # STORE PROPERTY RECORDS
    # --------------------------------------------------

    store_query = StoreProperty.query

    if search:
        store_query = store_query.filter(
            db.or_(
                StoreProperty.student_id.ilike(
                    f"%{search}%"
                ),
                StoreProperty.name.ilike(
                    f"%{search}%"
                ),
                StoreProperty.status.ilike(
                    f"%{search}%"
                )
            )
        )

    if status_filter:
        store_query = store_query.filter(
            db.func.lower(
                db.func.trim(
                    db.func.coalesce(
                        StoreProperty.status,
                        ""
                    )
                )
            ) == status_filter
        )

    store_properties = store_query.order_by(
        StoreProperty.id.desc()
    ).all()

    # --------------------------------------------------
    # HOSTEL PROPERTY RECORDS
    # --------------------------------------------------

    hostel_query = HostelItem.query

    if search:
        hostel_query = hostel_query.filter(
            db.or_(
                HostelItem.student_id.ilike(
                    f"%{search}%"
                ),
                HostelItem.item.ilike(
                    f"%{search}%"
                ),
                HostelItem.status.ilike(
                    f"%{search}%"
                )
            )
        )

    if status_filter:
        hostel_query = hostel_query.filter(
            db.func.lower(
                db.func.trim(
                    db.func.coalesce(
                        HostelItem.status,
                        ""
                    )
                )
            ) == status_filter
        )

    hostel_properties = hostel_query.order_by(
        HostelItem.id.desc()
    ).all()

    # --------------------------------------------------
    # COMBINE RECORDS
    # --------------------------------------------------

    records = []

    for item in store_properties:

        student = Student.query.filter_by(
            student_id=item.student_id
        ).first()

        records.append({
            "student_id": item.student_id,
            "student_name": (
                student.name
                if student
                else "Unknown Student"
            ),
            "program": (
                student.program
                if student
                else "—"
            ),
            "property": item.name,
            "type": "Store Property",
            "status": item.status or "—",
            "remarks": item.remarks or "—",
            "id": item.id
        })

    for item in hostel_properties:

        student = Student.query.filter_by(
            student_id=item.student_id
        ).first()

        records.append({
            "student_id": item.student_id,
            "student_name": (
                student.name
                if student
                else "Unknown Student"
            ),
            "program": (
                student.program
                if student
                else "—"
            ),
            "property": item.item,
            "type": "Hostel Property",
            "status": item.status or "—",
            "remarks": item.remarks or "—",
            "id": item.id
        })

    records.sort(
        key=lambda x: x["id"],
        reverse=True
    )

    return render_template(
        "new_staff/stores/records.html",
        staff_name=(
            session.get("staff_name")
            or session.get("name")
            or session.get("username")
            or "Stores Staff"
        ),
        department=(
            session.get("department")
            or "Stores"
        ),
        records=records,
        search=search,
        status_filter=status_filter
    )


# ============================================================
# APPLICATION STARTUP
# ============================================================


# ============================================================
# APPLICATION STARTUP
# ============================================================



# ============================================================
# HOSTEL STUDENTS
# ============================================================

@app.route("/hostel/students")
def hostel_students():

    if not _hostel_staff_allowed():
        return redirect("/login")

    search = request.args.get(
        "search",
        ""
    ).strip()

    accommodation_filter = request.args.get(
        "accommodation",
        "all"
    ).strip().lower()

    query = Student.query

    if search:
        pattern = f"%{search}%"

        query = query.filter(
            db.or_(
                Student.student_id.ilike(pattern),
                Student.name.ilike(pattern),
            )
        )

    if accommodation_filter == "boarders":
        query = query.filter(
            Student.accommodation.isnot(None),
            db.func.lower(
                Student.accommodation
            ).like("%board%")
        )

    elif accommodation_filter == "day_scholars":
        query = query.filter(
            Student.accommodation.isnot(None),
            db.func.lower(
                Student.accommodation
            ).like("%day%")
        )

    students = (
        query
        .order_by(Student.name.asc())
        .all()
    )

    active_accommodation_student_ids = {
        row[0]
        for row in (
            db.session.query(
                AccommodationAssignment.student_id
            )
            .filter(
                db.func.lower(
                    db.func.trim(
                        db.func.coalesce(
                            AccommodationAssignment.status,
                            ""
                        )
                    )
                ).in_(["occupying", "active"])
            )
            .all()
        )
    }

    return render_template(
        "new_staff/hostel/students.html",
        staff_name=(
            session.get("staff_name")
            or session.get("name")
            or "Hostel Staff"
        ),
        students=students,
        search=search,
        accommodation_filter=accommodation_filter,
    )



# ============================================================
# HOSTEL DAY SCHOLARS
# ============================================================

@app.route(
    "/hostel/day-scholars",
    methods=["GET", "POST"]
)
def hostel_day_scholars():

    if not _hostel_staff_allowed():
        return redirect("/login")

    if request.method == "POST":

        student_id = (
            request.form.get(
                "student_id",
                ""
            ).strip()
        )

        student = Student.query.filter_by(
            student_id=student_id
        ).first()

        if not student:
            return redirect(
                url_for(
                    "hostel_day_scholars"
                )
            )

        # A student cannot be made a Day Scholar
        # while already occupying a hostel room.
        hostel_value = (student.hostel or "").strip().lower()
        room_value = (student.room or "").strip().lower()

        invalid_hostel_values = {
            "",
            "n/a",
            "na",
            "nil",
            "not set",
            "not_set",
        }

        invalid_room_values = {
            "",
            "n/a",
            "na",
            "nil",
            "not set",
            "not_set",
        }

        if (
            hostel_value not in invalid_hostel_values
            or room_value not in invalid_room_values
        ):
            return redirect(
                url_for(
                    "hostel_day_scholars"
                )
            )

        student.accommodation = "Day Scholar"
        student.hostel = None
        student.room = None

        db.session.commit()

        return redirect(
            url_for(
                "hostel_day_scholars"
            )
        )

    search = request.args.get(
        "search",
        ""
    ).strip()

    # Show students who have not been assigned
    # a hostel room yet.
    #
    # Day Scholars already have accommodation
    # set to "Day Scholar", so they are excluded.
    query = Student.query.filter(
        db.or_(
            Student.accommodation.is_(None),
            db.func.lower(
                db.func.trim(
                    Student.accommodation
                )
            ).in_([
                "",
                "not set",
                "not_set",
                "n/a",
                "na"
            ])
        ),
        db.or_(
            Student.hostel.is_(None),
            db.func.lower(
                db.func.trim(
                    Student.hostel
                )
            ).in_([
                "",
                "n/a",
                "na",
                "nil",
                "not set",
                "not_set"
            ])
        ),
        db.or_(
            Student.room.is_(None),
            db.func.lower(
                db.func.trim(
                    Student.room
                )
            ).in_([
                "",
                "n/a",
                "na",
                "nil",
                "not set",
                "not_set"
            ])
        )
    )

    if search:

        pattern = f"%{search}%"

        query = query.filter(
            db.or_(
                Student.student_id.ilike(pattern),
                Student.name.ilike(pattern),
            )
        )

    students = (
        query
        .order_by(Student.name.asc())
        .all()
    )

    return render_template(
        "new_staff/hostel/day_scholars.html",
        staff_name=(
            session.get("staff_name")
            or session.get("name")
            or "Hostel Staff"
        ),
        students=students,
        search=search,
    )


# ============================================================
# HOSTEL MANAGEMENT
# ============================================================

@app.route("/hostel/hostels", methods=["GET", "POST"])
def new_staff_hostels():

    if (
        session.get("role") != "staff"
        or session.get("department", "").strip().lower()
        not in {
            "hostel",
            "hostel department",
            "hostel office",
            "hostels (hos)",
        }
    ):
        return redirect("/login")

    hostel_defaults = [
        ("Antelope", "female"),
        ("Impala", "male"),
        ("Zebra", "male"),
        ("Kudu", "both"),
        ("Enugu", "male"),
        ("Katilungu", "both"),
        ("Pegasus", "both"),
        ("Brown House", "both"),
        ("Kacha House", "both"),
        ("China Jianxi", "both"),
    ]

    # Create missing institutional hostels only.
    existing_names = {
        hostel.name.strip().lower()
        for hostel in Hostel.query.all()
        if hostel.name
    }

    for name, gender_policy in hostel_defaults:

        if name.lower() not in existing_names:

            db.session.add(
                Hostel(
                    name=name,
                    gender_policy=gender_policy,
                    active=True,
                )
            )

    db.session.commit()

    hostels = (
        Hostel.query
        .filter_by(active=True)
        .order_by(Hostel.name.asc())
        .all()
    )

    # Load the physical structures used by the special hostels.
    structures_by_hostel = {}

    for hostel in hostels:

        hostel_name = (
            hostel.name or ""
        ).strip().lower()

        if hostel_name == "katilungu":

            structures_by_hostel[hostel.id] = (
                HostelBlock.query
                .filter_by(
                    hostel_id=hostel.id,
                    group_type="cube",
                    active=True,
                )
                .order_by(
                    HostelBlock.name.asc()
                )
                .all()
            )

        elif hostel_name == "china jianxi":

            structures_by_hostel[hostel.id] = (
                HostelBlock.query
                .filter_by(
                    hostel_id=hostel.id,
                    group_type="block",
                    active=True,
                )
                .order_by(
                    HostelBlock.name.asc()
                )
                .all()
            )

        else:

            structures_by_hostel[hostel.id] = []

    return render_template(
        "new_staff/hostel/hostels.html",
        staff_name=session.get(
            "user",
            "Hostel Staff"
        ),
        hostels=hostels,
        structures_by_hostel=structures_by_hostel,
    )


# ============================================================

@app.route(
    "/hostel/hostels/<int:hostel_id>/edit-policy",
    methods=["POST"]
)
def hostel_edit_policy(hostel_id):
    if not _hostel_staff_allowed():
        return redirect("/login")

    hostel = db.session.get(Hostel, hostel_id)
    if not hostel:
        return redirect(url_for("new_staff_hostels"))

    policy = request.form.get(
        "gender_policy", ""
    ).strip().lower()

    if policy not in {"male", "female", "both"}:
        flash("Invalid hostel gender policy.", "error")
        return redirect(url_for("new_staff_hostels"))

    descendants = (
        HostelSection.query.filter_by(hostel_id=hostel.id).all()
        + HostelBlock.query.filter_by(hostel_id=hostel.id).all()
        + HostelRoom.query.filter_by(hostel_id=hostel.id).all()
    )

    for item in descendants:
        child_policy = (
            (item.gender_policy or "both").strip().lower()
        )

        if child_policy not in {"male", "female", "both"}:
            flash(
                "A section, block or room has an invalid gender policy. "
                "Correct it before changing the hostel policy.",
                "error"
            )
            return redirect(url_for("new_staff_hostels"))

        if (
            policy != "both"
            and child_policy != "both"
            and child_policy != policy
        ):
            flash(
                "The new hostel policy conflicts with an existing "
                "section, block or room policy.",
                "error"
            )
            return redirect(url_for("new_staff_hostels"))

    assignments = (
        AccommodationAssignment.query
        .join(
            HostelRoom,
            AccommodationAssignment.room_id == HostelRoom.id
        )
        .filter(
            HostelRoom.hostel_id == hostel.id,
            AccommodationAssignment.status.in_([
                "Occupying", "occupying", "Active", "active"
            ])
        )
        .all()
    )

    if policy != "both":
        for assignment in assignments:
            student = Student.query.filter_by(
                student_id=assignment.student_id
            ).first()

            student_gender = (
                (student.gender or "").strip().lower()
                if student else ""
            )

            if student_gender not in {"male", "female"}:
                flash(
                    "A current occupant has no valid gender recorded. "
                    "Correct the student record before changing "
                    "the hostel policy.",
                    "error"
                )
                return redirect(url_for("new_staff_hostels"))

            if student_gender != policy:
                flash(
                    "The new hostel policy would conflict with a "
                    "current occupant. No changes were made.",
                    "error"
                )
                return redirect(url_for("new_staff_hostels"))

    hostel.gender_policy = policy
    db.session.commit()

    flash("Hostel gender policy updated successfully.", "success")
    return redirect(url_for("new_staff_hostels"))


# HOSTEL STRUCTURE MANAGEMENT
# ============================================================

def _hostel_staff_allowed():
    return (
        session.get("role") == "staff"
        and session.get("department", "").strip().lower()
        in {
            "hostel",
            "hostel department",
            "hostel office",
            "hostels (hos)",
            "hostels (hos)",
        }
    )


def _hostel_redirect(hostel_id):
    return redirect(
        url_for(
            "new_staff_hostel_detail",
            hostel_id=hostel_id,
        )
    )


# ------------------------------------------------------------
# SECTIONS / SIDES
# ------------------------------------------------------------

@app.route(
    "/hostel/hostels/<int:hostel_id>/sections/add",
    methods=["POST"]
)
def hostel_add_section(hostel_id):
    if not _hostel_staff_allowed():
        return redirect("/login")

    hostel = db.session.get(Hostel, hostel_id)

    if not hostel:
        return redirect(url_for("new_staff_hostels"))

    name = request.form.get("name", "").strip()
    gender_policy = request.form.get(
        "gender_policy",
        "both"
    ).strip().lower()

    if not name:
        return _hostel_redirect(hostel.id)

    if gender_policy not in {
        "male",
        "female",
        "both",
    }:
        gender_policy = "both"

    duplicate = HostelSection.query.filter(
        HostelSection.hostel_id == hostel.id,
        db.func.lower(HostelSection.name) == name.lower(),
    ).first()

    if duplicate:
        return _hostel_redirect(hostel.id)

    highest_order = (
        db.session.query(
            db.func.max(HostelSection.display_order)
        )
        .filter(
            HostelSection.hostel_id == hostel.id
        )
        .scalar()
    )

    section = HostelSection(
        hostel_id=hostel.id,
        name=name,
        gender_policy=gender_policy,
        active=True,
        display_order=(highest_order or 0) + 1,
    )

    db.session.add(section)
    db.session.commit()

    return _hostel_redirect(hostel.id)


@app.route(
    "/hostel/sections/<int:section_id>/edit",
    methods=["POST"]
)
def hostel_edit_section(section_id):
    if not _hostel_staff_allowed():
        return redirect("/login")

    section = db.session.get(
        HostelSection,
        section_id
    )

    if not section:
        return redirect(url_for("new_staff_hostels"))

    hostel = db.session.get(
        Hostel,
        section.hostel_id
    )

    if not hostel:
        return redirect(url_for("new_staff_hostels"))

    name = request.form.get("name", "").strip()
    gender_policy = request.form.get(
        "gender_policy",
        "both"
    ).strip().lower()

    if not name:
        return _hostel_redirect(hostel.id)

    if gender_policy not in {
        "male",
        "female",
        "both",
    }:
        gender_policy = "both"

    duplicate = HostelSection.query.filter(
        HostelSection.hostel_id == hostel.id,
        HostelSection.id != section.id,
        db.func.lower(HostelSection.name) == name.lower(),
    ).first()

    if duplicate:
        return _hostel_redirect(hostel.id)

    section.name = name
    section.gender_policy = gender_policy

    db.session.commit()

    return _hostel_redirect(hostel.id)


@app.route(
    "/hostel/sections/<int:section_id>/toggle",
    methods=["POST"]
)
def hostel_toggle_section(section_id):
    if not _hostel_staff_allowed():
        return redirect("/login")

    section = db.session.get(
        HostelSection,
        section_id
    )

    if not section:
        return redirect(url_for("new_staff_hostels"))

    hostel = db.session.get(
        Hostel,
        section.hostel_id
    )

    if not hostel:
        return redirect(url_for("new_staff_hostels"))

    if section.active:
        active_assignments = (
            AccommodationAssignment.query
            .join(
                HostelRoom,
                AccommodationAssignment.room_id
                == HostelRoom.id
            )
            .filter(
                HostelRoom.section_id == section.id,
                AccommodationAssignment.status.in_([
                    "Occupying",
                    "occupying",
                    "Active",
                    "active",
                ]),
            )
            .count()
        )

        if active_assignments > 0:
            return _hostel_redirect(hostel.id)

    section.active = not bool(section.active)

    db.session.commit()

    return _hostel_redirect(hostel.id)


# ------------------------------------------------------------
# GROUPS / BLOCKS / CUBES
# ------------------------------------------------------------

@app.route(
    "/hostel/hostels/<int:hostel_id>/blocks/add",
    methods=["POST"]
)
def hostel_add_block(hostel_id):

    if not _hostel_staff_allowed():
        return redirect("/login")

    hostel = db.session.get(
        Hostel,
        hostel_id
    )

    if not hostel:
        return redirect(
            url_for("new_staff_hostels")
        )

    hostel_name = (
        hostel.name or ""
    ).strip().lower()

    # Only Katilungu and China Jianxi use structures.
    if hostel_name not in {
        "katilungu",
        "china jianxi",
    }:
        return redirect(
            url_for("new_staff_hostels")
        )

    name = (
        request.form.get(
            "name",
            ""
        ).strip()
    )

    if not name:
        return redirect(
            url_for("new_staff_hostels")
        )

    # Katilungu = Cube
    # China Jianxi = Block
    if hostel_name == "katilungu":
        group_type = "cube"
    else:
        group_type = "block"

    # Prevent duplicate active structures.
    duplicate = HostelBlock.query.filter(
        HostelBlock.hostel_id == hostel.id,
        db.func.lower(
            HostelBlock.name
        ) == name.lower(),
        HostelBlock.active == True,
        HostelBlock.group_type == group_type,
    ).first()

    if duplicate:
        return redirect(
            url_for("new_staff_hostels")
        )

    gender_policy = request.form.get(
        "gender_policy",
        hostel.gender_policy or "both"
    ).strip().lower()

    if gender_policy not in {"male", "female", "both"}:
        flash("Invalid block/cube gender policy.", "error")
        return _hostel_redirect(hostel.id)

    hostel_policy = (
        (hostel.gender_policy or "both").strip().lower()
    )

    if (
        gender_policy != "both"
        and hostel_policy != "both"
        and gender_policy != hostel_policy
    ):
        flash(
            "Block/cube policy conflicts with the hostel gender policy.",
            "error"
        )
        return _hostel_redirect(hostel.id)

    structure = HostelBlock(
        hostel_id=hostel.id,
        section_id=None,
        name=name,
        group_type=group_type,
        gender_policy=gender_policy,
        active=True,
    )

    db.session.add(structure)
    db.session.commit()

    # Return to the Hostels page so the saved
    # structure is immediately visible.
    return redirect(
        url_for("new_staff_hostels")
    )


@app.route(
    "/hostel/blocks/<int:block_id>/edit",
    methods=["POST"]
)
def hostel_edit_block(block_id):
    if not _hostel_staff_allowed():
        return redirect("/login")

    block = db.session.get(
        HostelBlock,
        block_id
    )

    if not block:
        return redirect(url_for("new_staff_hostels"))

    hostel = db.session.get(
        Hostel,
        block.hostel_id
    )

    if not hostel:
        return redirect(url_for("new_staff_hostels"))

    name = request.form.get(
        "name",
        ""
    ).strip()

    group_type = request.form.get(
        "group_type",
        block.group_type or "block"
    ).strip().lower()

    section_id_raw = request.form.get(
        "section_id",
        ""
    ).strip()

    if not name:
        return _hostel_redirect(hostel.id)

    if group_type not in {
        "block",
        "cube",
    }:
        group_type = "block"

    section_id = None

    if section_id_raw:
        try:
            candidate_section_id = int(
                section_id_raw
            )
        except (TypeError, ValueError):
            candidate_section_id = None

        if candidate_section_id:
            section = HostelSection.query.filter_by(
                id=candidate_section_id,
                hostel_id=hostel.id,
                active=True,
            ).first()

            if section:
                section_id = section.id

    duplicate = HostelBlock.query.filter(
        HostelBlock.hostel_id == hostel.id,
        HostelBlock.id != block.id,
        HostelBlock.section_id == section_id,
        db.func.lower(HostelBlock.name) == name.lower(),
    ).first()

    if duplicate:
        return _hostel_redirect(hostel.id)

    gender_policy = request.form.get(
        "gender_policy",
        block.gender_policy or "both"
    ).strip().lower()

    if gender_policy not in {"male", "female", "both"}:
        flash("Invalid block/cube gender policy.", "error")
        return _hostel_redirect(hostel.id)

    hostel_policy = (
        hostel.gender_policy or "both"
    ).strip().lower()

    selected_section = (
        db.session.get(HostelSection, section_id)
        if section_id else None
    )

    section_policy = (
        (selected_section.gender_policy or "both").strip().lower()
        if selected_section else "both"
    )

    for parent_name, parent_policy in (
        ("hostel", hostel_policy),
        ("section", section_policy),
    ):
        if (
            gender_policy != "both"
            and parent_policy != "both"
            and gender_policy != parent_policy
        ):
            flash(
                f"Block/cube policy conflicts with the {parent_name} policy.",
                "error"
            )
            return _hostel_redirect(hostel.id)

    child_rooms = HostelRoom.query.filter_by(
        block_id=block.id
    ).all()

    for child_room in child_rooms:
        room_policy = (
            (child_room.gender_policy or "both").strip().lower()
        )

        for parent_name, parent_policy in (
            ("hostel", hostel_policy),
            ("section", section_policy),
            ("block/cube", gender_policy),
        ):
            if (
                room_policy not in {"male", "female", "both"}
                or parent_policy not in {"male", "female", "both"}
            ):
                flash(
                    "Policy change stopped: a room or parent has an invalid gender policy.",
                    "error"
                )
                return _hostel_redirect(hostel.id)

            if (
                room_policy != "both"
                and parent_policy != "both"
                and room_policy != parent_policy
            ):
                flash(
                    f"Policy change stopped: a room's gender policy conflicts with the {parent_name} policy.",
                    "error"
                )
                return _hostel_redirect(hostel.id)

    active_statuses = [
        "Occupying", "occupying", "Active", "active"
    ]

    current_assignments = (
        AccommodationAssignment.query
        .join(
            HostelRoom,
            AccommodationAssignment.room_id == HostelRoom.id
        )
        .filter(
            HostelRoom.block_id == block.id,
            AccommodationAssignment.status.in_(active_statuses)
        )
        .all()
    )

    for assignment in current_assignments:
        occupant = Student.query.filter_by(
            student_id=assignment.student_id
        ).first()

        occupant_gender = (
            (occupant.gender or "").strip().lower()
            if occupant else ""
        )

        if occupant_gender not in {"male", "female"}:
            flash(
                "Policy change stopped: a current occupant has no valid gender record.",
                "error"
            )
            return _hostel_redirect(hostel.id)

        if (
            gender_policy != "both"
            and occupant_gender != gender_policy
        ):
            flash(
                "Policy change stopped: the block/cube has current occupants who do not match the selected gender policy.",
                "error"
            )
            return _hostel_redirect(hostel.id)

    block.name = name
    block.group_type = group_type
    block.section_id = section_id
    block.gender_policy = gender_policy

    db.session.commit()

    return _hostel_redirect(hostel.id)


@app.route(
    "/hostel/blocks/<int:block_id>/toggle",
    methods=["POST"]
)
def hostel_toggle_block(block_id):
    if not _hostel_staff_allowed():
        return redirect("/login")

    block = db.session.get(
        HostelBlock,
        block_id
    )

    if not block:
        return redirect(url_for("new_staff_hostels"))

    hostel = db.session.get(
        Hostel,
        block.hostel_id
    )

    if not hostel:
        return redirect(url_for("new_staff_hostels"))

    if block.active:
        active_assignments = (
            AccommodationAssignment.query
            .join(
                HostelRoom,
                AccommodationAssignment.room_id
                == HostelRoom.id
            )
            .filter(
                HostelRoom.block_id == block.id,
                AccommodationAssignment.status.in_([
                    "Occupying",
                    "occupying",
                    "Active",
                    "active",
                ]),
            )
            .count()
        )

        if active_assignments > 0:
            return _hostel_redirect(hostel.id)

    block.active = not bool(block.active)

    db.session.commit()

    return redirect(url_for("new_staff_hostels"))


# ------------------------------------------------------------
# ROOMS
# ------------------------------------------------------------

@app.route(
    "/hostel/hostels/<int:hostel_id>/rooms/add",
    methods=["POST"]
)
def hostel_add_room(hostel_id):
    if not _hostel_staff_allowed():
        return redirect("/login")

    hostel = db.session.get(
        Hostel,
        hostel_id
    )

    if not hostel:
        return redirect(url_for("new_staff_hostels"))

    room_number = request.form.get(
        "room_number",
        ""
    ).strip()

    capacity_raw = request.form.get(
        "capacity",
        ""
    ).strip()

    gender_policy = request.form.get(
        "gender_policy",
        ""
    ).strip().lower()

    room_type = request.form.get(
        "room_type",
        "normal"
    ).strip().lower()

    section_id_raw = request.form.get(
        "section_id",
        ""
    ).strip()

    block_id_raw = request.form.get(
        "block_id",
        ""
    ).strip()

    if not room_number:
        return _hostel_redirect(hostel.id)

    try:
        capacity = int(capacity_raw)
    except (TypeError, ValueError):
        capacity = 1

    if capacity < 1:
        capacity = 1

    if room_type not in {
        "normal",
        "common",
    }:
        room_type = "normal"

    section_id = None

    if section_id_raw:
        try:
            candidate_section_id = int(
                section_id_raw
            )
        except (TypeError, ValueError):
            candidate_section_id = None

        if candidate_section_id:
            section = HostelSection.query.filter_by(
                id=candidate_section_id,
                hostel_id=hostel.id,
                active=True,
            ).first()

            if section:
                section_id = section.id

    block_id = None

    if block_id_raw:
        try:
            candidate_block_id = int(
                block_id_raw
            )
        except (TypeError, ValueError):
            candidate_block_id = None

        if candidate_block_id:
            block = HostelBlock.query.filter_by(
                id=candidate_block_id,
                hostel_id=hostel.id,
                active=True,
            ).first()

            if block:
                # A block must belong to the same section
                # as the room when the block has a section.
                if (
                    block.section_id is None
                    or block.section_id == section_id
                ):
                    block_id = block.id

                    if section_id is None:
                        section_id = block.section_id

    hostel_policy = (
        (hostel.gender_policy or "both").strip().lower()
    )

    selected_section = (
        db.session.get(HostelSection, section_id)
        if section_id else None
    )

    selected_block = (
        db.session.get(HostelBlock, block_id)
        if block_id else None
    )

    section_policy = (
        (selected_section.gender_policy or "both").strip().lower()
        if selected_section else "both"
    )

    block_policy = (
        (selected_block.gender_policy or "both").strip().lower()
        if selected_block else "both"
    )

    if not gender_policy:
        gender_policy = (
            block_policy if selected_block
            else section_policy if selected_section
            else hostel_policy
        )

    if gender_policy not in {"male", "female", "both"}:
        flash("Invalid room gender policy.", "error")
        return _hostel_redirect(hostel.id)

    for parent_name, parent_policy in (
        ("hostel", hostel_policy),
        ("section", section_policy),
        ("block/cube", block_policy),
    ):
        if parent_policy not in {"male", "female", "both"}:
            flash(
                f"Invalid {parent_name} gender policy. Room was not added.",
                "error"
            )
            return _hostel_redirect(hostel.id)

        if (
            gender_policy != "both"
            and parent_policy != "both"
            and gender_policy != parent_policy
        ):
            flash(
                f"Room gender policy conflicts with the {parent_name} policy.",
                "error"
            )
            return _hostel_redirect(hostel.id)

    duplicate = HostelRoom.query.filter(
        HostelRoom.hostel_id == hostel.id,
        HostelRoom.section_id == section_id,
        HostelRoom.block_id == block_id,
        db.func.lower(
            HostelRoom.room_number
        ) == room_number.lower(),
    ).first()

    if duplicate:
        return _hostel_redirect(hostel.id)

    room = HostelRoom(
        hostel_id=hostel.id,
        section_id=section_id,
        block_id=block_id,
        room_number=room_number,
        capacity=capacity,
        gender_policy=gender_policy,
        room_type=room_type,
        active=True,
    )

    db.session.add(room)
    db.session.commit()

    return _hostel_redirect(hostel.id)


@app.route(
    "/hostel/rooms/<int:room_id>/edit",
    methods=["POST"]
)
def hostel_edit_room(room_id):
    if not _hostel_staff_allowed():
        return redirect("/login")

    room = db.session.get(
        HostelRoom,
        room_id
    )

    if not room:
        return redirect(url_for("new_staff_hostels"))

    hostel = db.session.get(
        Hostel,
        room.hostel_id
    )

    if not hostel:
        return redirect(url_for("new_staff_hostels"))

    room_number = request.form.get(
        "room_number",
        ""
    ).strip()

    capacity_raw = request.form.get(
        "capacity",
        ""
    ).strip()

    gender_policy = request.form.get(
        "gender_policy",
        room.gender_policy or "both"
    ).strip().lower()

    room_type = request.form.get(
        "room_type",
        room.room_type or "normal"
    ).strip().lower()

    section_id_raw = request.form.get(
        "section_id",
        ""
    ).strip()

    block_id_raw = request.form.get(
        "block_id",
        ""
    ).strip()

    if not room_number:
        return _hostel_redirect(hostel.id)

    try:
        capacity = int(capacity_raw)
    except (TypeError, ValueError):
        capacity = room.capacity or 1

    if capacity < 1:
        capacity = 1

    active_assignments = (
        AccommodationAssignment.query.filter(
            AccommodationAssignment.room_id == room.id,
            AccommodationAssignment.status.in_([
                "Occupying",
                "occupying",
                "Active",
                "active",
            ]),
        )
        .count()
    )

    if capacity < active_assignments:
        capacity = active_assignments

    if gender_policy not in {"male", "female", "both"}:
        flash("Invalid room gender policy.", "error")
        return _hostel_redirect(hostel.id)

    if room_type not in {
        "normal",
        "common",
    }:
        room_type = "normal"

    section_id = None

    if section_id_raw:
        try:
            candidate_section_id = int(
                section_id_raw
            )
        except (TypeError, ValueError):
            candidate_section_id = None

        if candidate_section_id:
            section = HostelSection.query.filter_by(
                id=candidate_section_id,
                hostel_id=hostel.id,
                active=True,
            ).first()

            if section:
                section_id = section.id

    block_id = None

    if block_id_raw:
        try:
            candidate_block_id = int(
                block_id_raw
            )
        except (TypeError, ValueError):
            candidate_block_id = None

        if candidate_block_id:
            block = HostelBlock.query.filter_by(
                id=candidate_block_id,
                hostel_id=hostel.id,
                active=True,
            ).first()

            if block:
                if (
                    block.section_id is None
                    or block.section_id == section_id
                ):
                    block_id = block.id

                    if section_id is None:
                        section_id = block.section_id

    hostel_policy = (
        (hostel.gender_policy or "both").strip().lower()
    )

    selected_section = (
        db.session.get(HostelSection, section_id)
        if section_id else None
    )

    selected_block = (
        db.session.get(HostelBlock, block_id)
        if block_id else None
    )

    section_policy = (
        (selected_section.gender_policy or "both").strip().lower()
        if selected_section else "both"
    )

    block_policy = (
        (selected_block.gender_policy or "both").strip().lower()
        if selected_block else "both"
    )

    for parent_name, parent_policy in (
        ("hostel", hostel_policy),
        ("section", section_policy),
        ("block/cube", block_policy),
    ):
        if parent_policy not in {"male", "female", "both"}:
            flash(
                f"Invalid {parent_name} gender policy. Room was not updated.",
                "error"
            )
            return _hostel_redirect(hostel.id)

        if (
            gender_policy != "both"
            and parent_policy != "both"
            and gender_policy != parent_policy
        ):
            flash(
                f"Room gender policy conflicts with the {parent_name} policy.",
                "error"
            )
            return _hostel_redirect(hostel.id)

    active_statuses = [
        "Occupying", "occupying", "Active", "active"
    ]

    current_assignments = AccommodationAssignment.query.filter(
        AccommodationAssignment.room_id == room.id,
        AccommodationAssignment.status.in_(active_statuses),
    ).all()

    for assignment in current_assignments:
        occupant = Student.query.filter_by(
            student_id=assignment.student_id
        ).first()

        occupant_gender = (
            (occupant.gender or "").strip().lower()
            if occupant else ""
        )

        if occupant_gender not in {"male", "female"}:
            flash(
                "Room policy change stopped: a current occupant has no valid gender record.",
                "error"
            )
            return _hostel_redirect(hostel.id)

        for policy_name, policy in (
            ("hostel", hostel_policy),
            ("section", section_policy),
            ("block/cube", block_policy),
            ("room", gender_policy),
        ):
            if policy != "both" and occupant_gender != policy:
                flash(
                    f"Room policy change stopped: a current occupant does not match the {policy_name} policy.",
                    "error"
                )
                return _hostel_redirect(hostel.id)

    duplicate = HostelRoom.query.filter(
        HostelRoom.hostel_id == hostel.id,
        HostelRoom.id != room.id,
        HostelRoom.section_id == section_id,
        HostelRoom.block_id == block_id,
        db.func.lower(
            HostelRoom.room_number
        ) == room_number.lower(),
    ).first()

    if duplicate:
        return _hostel_redirect(hostel.id)

    room.room_number = room_number
    room.capacity = capacity
    room.gender_policy = gender_policy
    room.room_type = room_type
    room.section_id = section_id
    room.block_id = block_id

    db.session.commit()

    return _hostel_redirect(hostel.id)


@app.route(
    "/hostel/rooms/<int:room_id>/toggle",
    methods=["POST"]
)
def hostel_toggle_room(room_id):
    if not _hostel_staff_allowed():
        return redirect("/login")

    room = db.session.get(
        HostelRoom,
        room_id
    )

    if not room:
        return redirect(url_for("new_staff_hostels"))

    hostel = db.session.get(
        Hostel,
        room.hostel_id
    )

    if not hostel:
        return redirect(url_for("new_staff_hostels"))

    if room.active:
        active_assignments = (
            AccommodationAssignment.query.filter(
                AccommodationAssignment.room_id == room.id,
                AccommodationAssignment.status.in_([
                    "Occupying",
                    "occupying",
                    "Active",
                    "active",
                ]),
            )
            .count()
        )

        if active_assignments > 0:
            return _hostel_redirect(hostel.id)

    room.active = not bool(room.active)

    db.session.commit()

    return _hostel_redirect(hostel.id)



@app.route(
    "/hostel/hostels/<int:hostel_id>",
    methods=["GET", "POST"]
)
def new_staff_hostel_detail(hostel_id):

    if not _hostel_staff_allowed():
        return redirect("/login")

    hostel = db.session.get(
        Hostel,
        hostel_id
    )

    if not hostel:
        return redirect(
            url_for("new_staff_hostels")
        )

    hostel_name = hostel.name.strip()
    hostel_key = hostel_name.lower()

    # ----------------------------------------------------
    # HOSTEL STRUCTURE
    # ----------------------------------------------------

    if hostel_key == "katilungu":

        structure_mode = "cube"

        blocks = (
            HostelBlock.query
            .filter_by(
                hostel_id=hostel.id,
                group_type="cube",
                active=True
            )
            .order_by(
                HostelBlock.name.asc()
            )
            .all()
        )

    elif hostel_key == "china jianxi":

        structure_mode = "block"

        # Create the starting China Jianxi blocks
        # only when they do not already exist.
        existing_blocks = (
            HostelBlock.query
            .filter_by(
                hostel_id=hostel.id,
                group_type="block"
            )
            .all()
        )

        existing_names = {
            block.name.strip().lower()
            for block in existing_blocks
        }

        changed = False

        for letter in "ABCDE":

            name = f"Block {letter}"

            if name.lower() not in existing_names:

                db.session.add(
                    HostelBlock(
                        hostel_id=hostel.id,
                        name=name,
                        group_type="block",
                        active=True
                    )
                )

                changed = True

        if changed:
            db.session.commit()

        blocks = (
            HostelBlock.query
            .filter_by(
                hostel_id=hostel.id,
                group_type="block",
                active=True
            )
            .order_by(
                HostelBlock.name.asc()
            )
            .all()
        )

    else:

        structure_mode = "room"
        blocks = []

    # ----------------------------------------------------
    # ACTIVE ROOMS
    # ----------------------------------------------------

    rooms = (
        HostelRoom.query
        .filter_by(
            hostel_id=hostel.id,
            active=True
        )
        .order_by(
            HostelRoom.room_number.asc()
        )
        .all()
    )

    # ----------------------------------------------------
    # CURRENT OCCUPANTS
    # ----------------------------------------------------

    active_assignments = (
        AccommodationAssignment.query
        .filter(
            AccommodationAssignment.status.in_([
                "Occupying",
                "occupying",
                "Active",
                "active",
            ])
        )
        .all()
    )

    occupants_by_room = {}

    for assignment in active_assignments:

        occupants_by_room.setdefault(
            assignment.room_id,
            []
        ).append(assignment)

    return render_template(
        "new_staff/hostel/hostel_detail.html",
        hostel=hostel,
        hostel_name=hostel_name,
        structure_mode=structure_mode,
        blocks=blocks,
        rooms=rooms,
        occupants_by_room=occupants_by_room,
    )

# ------------------------------------------------------------
# ACCOMMODATION RECORDS
# ------------------------------------------------------------

@app.route("/hostel/accommodation-records")
def hostel_accommodation_records():
    if not _hostel_staff_allowed():
        return redirect("/login")

    search = request.args.get("search", "").strip()
    status_filter = request.args.get("status", "all").strip().lower()

    query = (
        db.session.query(
            AccommodationAssignment,
            Student,
            HostelRoom,
            Hostel,
        )
        .join(
            Student,
            AccommodationAssignment.student_id == Student.student_id,
        )
        .join(
            HostelRoom,
            AccommodationAssignment.room_id == HostelRoom.id,
        )
        .join(
            Hostel,
            HostelRoom.hostel_id == Hostel.id,
        )
    )

    if status_filter == "occupying":
        query = query.filter(
            AccommodationAssignment.status.in_([
                "Occupying",
                "occupying",
                "Active",
                "active",
            ])
        )
    elif status_filter == "vacated":
        query = query.filter(
            ~AccommodationAssignment.status.in_([
                "Occupying",
                "occupying",
                "Active",
                "active",
            ])
        )

    if search:
        pattern = f"%{search}%"
        query = query.filter(
            db.or_(
                Student.student_id.ilike(pattern),
                Student.name.ilike(pattern),
                Hostel.name.ilike(pattern),
                HostelRoom.room_number.ilike(pattern),
            )
        )

    records = (
        query
        .order_by(AccommodationAssignment.assigned_at.desc())
        .all()
    )

    return render_template(
        "new_staff/hostel/accommodation_records.html",
        records=records,
        search=search,
        status_filter=status_filter,
    )


# ------------------------------------------------------------
# HOSTEL — ANNOUNCEMENTS
# ------------------------------------------------------------

@app.route("/hostel/announcements")
def hostel_announcements():

    if not _hostel_staff_allowed():
        return redirect("/login")

    announcements = Announcement.query.filter(
        Announcement.active == True,
        Announcement.audience.in_(["staff", "all"])
    ).order_by(
        Announcement.created_at.desc()
    ).all()

    return render_template(
        "new_staff/hostel/announcements.html",
        announcements=announcements
    )





# ============================================================
# HOSTEL — FINAL ROOM INSPECTION / VACATE ROOM
# ============================================================


@app.route("/hostel/vacate-room")
def hostel_vacate_room():
    if not _hostel_staff_allowed():
        return redirect(url_for("new_staff_login"))

    # --------------------------------------------------------
    # ONLY STUDENTS WITH ACTIVE ACCOMMODATION
    # --------------------------------------------------------

    active_assignments = (
        AccommodationAssignment.query
        .filter(
            db.func.lower(
                db.func.trim(
                    db.func.coalesce(
                        AccommodationAssignment.status,
                        ""
                    )
                )
            ).in_([
                "occupying",
                "active",
            ])
        )
        .order_by(
            AccommodationAssignment.assigned_at.desc(),
            AccommodationAssignment.id.desc()
        )
        .all()
    )

    eligible_students = []

    for assignment in active_assignments:

        student = Student.query.filter_by(
            student_id=assignment.student_id
        ).first()

        if not student:
            continue

        room = HostelRoom.query.filter_by(
            id=assignment.room_id
        ).first()

        if not room:
            continue

        hostel = Hostel.query.filter_by(
            id=room.hostel_id
        ).first()

        eligible_students.append({
            "student": student,
            "assignment": assignment,
            "room": room,
            "hostel": hostel,
        })

    return render_template(
        "new_staff/hostel/vacate_room_list.html",
        eligible_students=eligible_students,
        staff_name=(
            session.get("staff_name")
            or session.get("name")
            or "Hostel Staff"
        ),
        department=(
            session.get("department")
            or "Hostel"
        ),
    )


@app.route("/hostel/vacate/<student_id>", methods=["GET", "POST"])
def hostel_vacate_student(student_id):
    if not _hostel_staff_allowed():
        return redirect(url_for("new_staff_login"))

    student_id = (student_id or "").strip()

    student = Student.query.filter_by(
        student_id=student_id
    ).first()

    if not student:
        flash("Student not found.", "error")
        return redirect(url_for("hostel_students"))

    # --------------------------------------------------------
    # ACTIVE ACCOMMODATION
    # --------------------------------------------------------

    assignment = (
        AccommodationAssignment.query
        .filter(
            AccommodationAssignment.student_id == student.student_id,
            db.func.lower(
                db.func.trim(
                    db.func.coalesce(
                        AccommodationAssignment.status,
                        ""
                    )
                )
            ).in_(["occupying", "active"])
        )
        .order_by(
            AccommodationAssignment.assigned_at.desc(),
            AccommodationAssignment.id.desc()
        )
        .first()
    )

    if not assignment:
        flash(
            "This student does not have an active hostel room.",
            "error"
        )
        return redirect(url_for("hostel_students"))

    # --------------------------------------------------------
    # ROOM / HOSTEL DETAILS
    # --------------------------------------------------------

    room = HostelRoom.query.filter_by(
        id=assignment.room_id
    ).first()

    if not room:
        flash(
            "The student's hostel room could not be found.",
            "error"
        )
        return redirect(url_for("hostel_students"))

    hostel = Hostel.query.filter_by(
        id=room.hostel_id
    ).first()

    # --------------------------------------------------------
    # TSO CLEARANCE — CURRENT ROOM ASSIGNMENT ONLY
    # --------------------------------------------------------

    tso_inspection = (
        TSOInspection.query
        .filter(
            TSOInspection.student_id == student.student_id,
            TSOInspection.accommodation_assignment_id
            == assignment.id,
        )
        .order_by(TSOInspection.id.desc())
        .first()
    )

    tso_cleared = (
        tso_inspection is not None
        and (tso_inspection.status or "").strip().lower()
        == "cleared"
    )

    # --------------------------------------------------------
    # STORES CLEARANCE
    #
    # Source of truth:
    # currently issued StoreProperty records whose original
    # ItemRequest belongs to Stores and was accepted.
    # --------------------------------------------------------

    issued_store_properties = (
        StoreProperty.query
        .filter(
            StoreProperty.student_id == student.student_id,
            StoreProperty.status.isnot(None),
            db.func.lower(
                db.func.trim(StoreProperty.status)
            ) == "issued",
            StoreProperty.request_id.isnot(None),
        )
        .all()
    )

    stores_outstanding = []

    for prop in issued_store_properties:
        item_request = ItemRequest.query.filter(
            ItemRequest.id == prop.request_id,
            ItemRequest.student_id == student.student_id,
            db.func.lower(
                db.func.trim(
                    db.func.coalesce(
                        ItemRequest.department,
                        ""
                    )
                )
            ) == "stores",
        ).first()

        if not item_request:
            continue

        if (
            (item_request.status or "").strip().lower()
            != "accepted"
        ):
            continue

        stores_outstanding.append(prop)

    stores_cleared = not stores_outstanding

    # --------------------------------------------------------
    # HOSTEL INSPECTION
    # --------------------------------------------------------

    inspection = (
        HostelInspection.query
        .filter(
            HostelInspection.student_id == student.student_id,
            HostelInspection.accommodation_assignment_id
            == assignment.id,
        )
        .order_by(
            HostelInspection.id.desc()
        )
        .first()
    )

    # --------------------------------------------------------
    # POST — FINAL VACATING
    # --------------------------------------------------------

    if request.method == "POST":

        # Backend gate — BOTH upstream clearances are required.
        if not tso_cleared or not stores_cleared:

            missing = []

            if not tso_cleared:
                missing.append("TSO clearance")

            if not stores_cleared:
                missing.append("Stores clearance")

            flash(
                "The student cannot be vacated yet. "
                + " and ".join(missing)
                + " is still pending.",
                "error"
            )

            return redirect(
                url_for(
                    "hostel_vacate_student",
                    student_id=student.student_id
                )
            )

        def form_value(name):
            return (request.form.get(name) or "").strip()

        # Create inspection if this is the first submission.
        if not inspection:
            inspection = HostelInspection(
                student_id=student.student_id,
                accommodation_assignment_id=assignment.id,
                room_id=assignment.room_id,
            )
            db.session.add(inspection)

        inspection.accommodation_assignment_id = assignment.id
        inspection.room_id = assignment.room_id

        # ----------------------------------------------------
        # ROOM CONDITION
        # ----------------------------------------------------

        inspection.walls = form_value("walls")
        inspection.paint = form_value("paint")
        inspection.floor = form_value("floor")
        inspection.ceiling = form_value("ceiling")
        inspection.windows = form_value("windows")
        inspection.door = form_value("door")

        # ----------------------------------------------------
        # FURNITURE / PROPERTY
        # ----------------------------------------------------

        inspection.bed = form_value("bed")
        inspection.missing_damaged_property = form_value(
            "missing_damaged_property"
        )

        # ----------------------------------------------------
        # GENERAL
        # ----------------------------------------------------

        inspection.room_cleanliness = form_value(
            "room_cleanliness"
        )
        inspection.remarks = form_value("remarks")

        inspection.inspected_by = (
            session.get("staff_name")
            or session.get("name")
            or session.get("user")
            or "Hostel Staff"
        )

        inspection.inspected_at = zambia_now()
        inspection.status = "Cleared"

        # ----------------------------------------------------
        # HOSTEL DEPARTMENT CLEARANCE
        # ----------------------------------------------------

        hostel_clearance = (
            DepartmentClearance.query
            .filter(
                DepartmentClearance.student_id
                == student.student_id,
                db.func.lower(
                    db.func.trim(
                        db.func.coalesce(
                            DepartmentClearance.department,
                            ""
                        )
                    )
                ) == "hostel",
            )
            .order_by(
                DepartmentClearance.id.desc()
            )
            .first()
        )

        if not hostel_clearance:
            hostel_clearance = DepartmentClearance(
                student_id=student.student_id,
                department="Hostel",
                status="Cleared",
                reason=None,
                remarks=inspection.remarks,
            )
            db.session.add(hostel_clearance)
        else:
            hostel_clearance.department = "Hostel"
            hostel_clearance.status = "Cleared"
            hostel_clearance.reason = None
            hostel_clearance.remarks = inspection.remarks

        # ----------------------------------------------------
        # VACATE ACCOMMODATION
        # ----------------------------------------------------

        assignment.status = "Vacated"
        assignment.vacated_at = zambia_now()
        assignment.vacated_by = (
            inspection.inspected_by
            or session.get("staff_name")
            or session.get("name")
            or session.get("username")
            or session.get("user")
            or "Hostel Staff"
        )

        # Keep the student's accommodation details in sync
        # with the final room-vacation status.
        student.accommodation = "Vacated"
        student.hostel = None
        student.room = None

        db.session.add(DepartmentHistory(
            student_id=student.student_id,
            department="hostel",
            status="Cleared",
            action="Room vacated",
            remarks=(
                inspection.remarks
                or f"Room {room.room_number} vacated."
            ),
            performed_by=(
                inspection.inspected_by
                or session.get("staff_name")
                or session.get("name")
                or "Hostel Staff"
            ),
            created_at=zambia_now()
        ))

        db.session.commit()

        flash(
            f"{student.name} has been cleared by Hostel "
            f"and room {room.room_number} has been vacated.",
            "success"
        )

        return redirect(
            url_for(
                "hostel_vacate_student",
                student_id=student.student_id
            )
        )

    return render_template(
        "new_staff/hostel/vacate_room.html",
        student=student,
        assignment=assignment,
        room=room,
        hostel=hostel,
        tso_inspection=tso_inspection,
        tso_cleared=tso_cleared,
        stores_outstanding=stores_outstanding,
        stores_cleared=stores_cleared,
        inspection=inspection,
        staff_name=(
            session.get("staff_name")
            or session.get("name")
            or "Hostel Staff"
        ),
        department=(
            session.get("department")
            or "Hostel"
        ),
    )


# ============================================================
# TSO — TECHNICAL SERVICES OFFICE
# ============================================================

def _tso_staff_allowed():
    if session.get("role") != "staff":
        return False

    department = (
        session.get("department") or ""
    ).strip().lower()

    return department in {
        "tso",
        "tso department",
        "tso office",
        "technical services office",
        "technical services office department",
        "technical services office (tso)",
    }


def _tso_redirect(endpoint="tso_dashboard"):
    return redirect(url_for(endpoint))


def _tso_get_active_assignment(student_id):
    return (
        AccommodationAssignment.query
        .filter(
            AccommodationAssignment.student_id == student_id,
            db.func.lower(
                db.func.trim(
                    db.func.coalesce(
                        AccommodationAssignment.status,
                        ""
                    )
                )
            ).in_([
                "occupying",
                "active",
            ])
        )
        .order_by(
            AccommodationAssignment.assigned_at.desc(),
            AccommodationAssignment.id.desc()
        )
        .first()
    )


def _tso_accommodation_details(assignment):
    if not assignment:
        return None

    room = db.session.get(
        HostelRoom,
        assignment.room_id
    )

    if not room:
        return None

    hostel = db.session.get(
        Hostel,
        room.hostel_id
    )

    if not hostel:
        return None

    hostel_name = (
        hostel.name or ""
    ).strip()

    structure_name = ""

    if room.block_id:
        block = db.session.get(
            HostelBlock,
            room.block_id
        )

        if block:
            structure_name = (
                block.name or ""
            ).strip()

    section_name = ""

    if room.section_id:
        section = db.session.get(
            HostelSection,
            room.section_id
        )

        if section:
            section_name = (
                getattr(section, "name", None) or ""
            ).strip()

    room_number = (
        room.room_number or ""
    ).strip()

    key_parts = [hostel_name]

    if structure_name:
        key_parts.append(structure_name)

    if room_number:
        key_parts.append(
            f"Room {room_number}"
        )

    key_name = " — ".join(
        part for part in key_parts
        if part
    )

    return {
        "hostel": hostel_name,
        "structure": structure_name,
        "section": section_name,
        "room": room_number,
        "key_name": key_name,
        "room_id": room.id,
        "assignment_id": assignment.id,
    }



# --------------------------------------------------
# TSO — ANNOUNCEMENTS
# --------------------------------------------------

@app.route("/new-staff/tso/announcements")
def tso_announcements():

    if not _tso_staff_allowed():
        return redirect(url_for("new_staff_login"))

    announcements = (
        Announcement.query
        .filter(
            Announcement.active == True,
            Announcement.audience.in_(["staff", "all"])
        )
        .order_by(
            Announcement.created_at.desc()
        )
        .all()
    )

    return render_template(
        "new_staff/tso/announcements.html",
        announcements=announcements,
        staff_name=(
            session.get("staff_name")
            or session.get("name")
            or "TSO Staff"
        ),
        department=(
            session.get("department")
            or "Technical Services Office"
        ),
    )


@app.route("/tso/dashboard", methods=["GET"])
def tso_dashboard():

    if not _tso_staff_allowed():
        return redirect(url_for("new_staff_login"))

    # Students currently occupying an accommodation assignment.
    active_assignments = (
        AccommodationAssignment.query
        .filter(
            db.func.lower(
                db.func.trim(
                    db.func.coalesce(
                        AccommodationAssignment.status,
                        ""
                    )
                )
            ).in_([
                "occupying",
                "active",
            ])
        )
        .all()
    )

    active_student_ids = {
        assignment.student_id
        for assignment in active_assignments
    }

    # --------------------------------------------------
    # TSO INSPECTION QUEUE
    # --------------------------------------------------
    # The dashboard MUST use the exact same lifecycle rule
    # as /tso/inspection-queue.
    #
    # A TSO inspection belongs to the CURRENT
    # AccommodationAssignment, not merely to the student.
    #
    # Therefore:
    #
    #   Active accommodation
    #       +
    #   no TSO inspection for this assignment
    #       = awaiting inspection
    #
    #   Active accommodation
    #       +
    #   current inspection not cleared
    #       = awaiting inspection
    #
    #   Active accommodation
    #       +
    #   current inspection cleared
    #       = completed / not in queue
    #
    # Old cleared inspections from previous accommodation
    # assignments must NEVER hide a new inspection.

    queue_student_ids = set()

    for assignment in active_assignments:

        student_id = assignment.student_id

        current_inspection = (
            TSOInspection.query
            .filter(
                TSOInspection.student_id == student_id,
                TSOInspection.accommodation_assignment_id
                == assignment.id,
            )
            .order_by(
                TSOInspection.id.desc()
            )
            .first()
        )

        if (
            not current_inspection
            or (
                current_inspection.status or ""
            ).strip().lower() != "cleared"
        ):
            queue_student_ids.add(student_id)

    queue_count = len(queue_student_ids)

    # The dashboard pending count must match the inspection queue.
    pending_count = queue_count

    completed_count = (
        TSOInspection.query
        .filter(
            db.func.lower(
                db.func.trim(
                    db.func.coalesce(
                        TSOInspection.status,
                        ""
                    )
                )
            ) == "cleared"
        )
        .count()
    )

    keys_count = (
        TSOInspection.query
        .filter(
            TSOInspection.key_collected.is_(True)
        )
        .count()
    )

    recent_rows = (
        TSOInspection.query
        .filter(
            TSOInspection.inspected_at.isnot(None)
        )
        .order_by(
            TSOInspection.inspected_at.desc()
        )
        .limit(8)
        .all()
    )

    recent_inspections = []

    for inspection in recent_rows:
        student = Student.query.filter_by(
            student_id=inspection.student_id
        ).first()

        if student:
            recent_inspections.append({
                "student": student,
                "inspection": inspection,
            })

    announcements = (
        Announcement.query
        .filter(
            Announcement.active == True,
            Announcement.audience.in_(["staff", "all"])
        )
        .order_by(
            Announcement.created_at.desc()
        )
        .limit(5)
        .all()
    )

    # --------------------------------------------------
    # DASHBOARD SETTINGS
    # Existing staff mini academic calendar/clock uses
    # these values from system_settings.
    # --------------------------------------------------
    import sqlite3

    calendar_conn = sqlite3.connect(DATABASE_URL)
    calendar_cursor = calendar_conn.cursor()

    calendar_cursor.execute("""
        SELECT setting_key, setting_value
        FROM system_settings
    """)

    settings = dict(calendar_cursor.fetchall())

    calendar_conn.close()

    return render_template(
        "new_staff/tso/overview.html",
        staff_name=(
            session.get("staff_name")
            or session.get("name")
            or "TSO Staff"
        ),
        department=(
            session.get("department")
            or "Technical Services Office"
        ),
        queue_count=queue_count,
        pending_count=pending_count,
        completed_count=completed_count,
        keys_count=keys_count,
        recent_inspections=recent_inspections,
        announcements=announcements,
        settings=settings,
    )

@app.route("/tso/records", methods=["GET"])
def tso_records():

    if not _tso_staff_allowed():
        return redirect(url_for("new_staff_login"))

    search = (request.args.get("search") or "").strip()

    inspections = (
        TSOInspection.query
        .filter(
            db.func.lower(
                db.func.trim(
                    db.func.coalesce(
                        TSOInspection.status,
                        ""
                    )
                )
            ) == "cleared"
        )
        .order_by(
            TSOInspection.inspected_at.desc(),
            TSOInspection.id.desc()
        )
        .all()
    )

    record_rows = []

    for inspection in inspections:

        student = Student.query.filter_by(
            student_id=inspection.student_id
        ).first()

        if not student:
            continue

        if search:
            search_lower = search.lower()

            student_name = (
                getattr(student, "name", "") or ""
            ).lower()

            student_id = (
                getattr(student, "student_id", "") or ""
            ).lower()

            if (
                search_lower not in student_name
                and search_lower not in student_id
            ):
                continue

        assignment = AccommodationAssignment.query.filter_by(
            id=inspection.accommodation_assignment_id
        ).first()

        room = HostelRoom.query.filter_by(
            id=inspection.room_id
        ).first()

        record_rows.append({
            "student": student,
            "inspection": inspection,
            "assignment": assignment,
            "room": room,
        })

    return render_template(
        "new_staff/tso/records.html",
        staff_name=(
            session.get("staff_name")
            or session.get("name")
            or "TSO Staff"
        ),
        department=(
            session.get("department")
            or "Technical Services Office"
        ),
        records=record_rows,
        search=search,
    )


@app.route("/tso/records/<int:inspection_id>", methods=["GET"])
def tso_record_detail(inspection_id):

    if not _tso_staff_allowed():
        return redirect(url_for("new_staff_login"))

    inspection = TSOInspection.query.get_or_404(inspection_id)

    student = Student.query.filter_by(
        student_id=inspection.student_id
    ).first_or_404()

    assignment = AccommodationAssignment.query.filter_by(
        id=inspection.accommodation_assignment_id
    ).first()

    room = HostelRoom.query.filter_by(
        id=inspection.room_id
    ).first()

    return render_template(
        "new_staff/tso/record_detail.html",
        staff_name=(
            session.get("staff_name")
            or session.get("name")
            or "TSO Staff"
        ),
        department=(
            session.get("department")
            or "Technical Services Office"
        ),
        student=student,
        inspection=inspection,
        assignment=assignment,
        room=room,
    )


@app.route("/tso/inspection-queue", methods=["GET"])
def tso_inspection_queue():

    if not _tso_staff_allowed():
        return redirect(url_for("new_staff_login"))

    search = (
        request.args.get("search") or ""
    ).strip()

    query = (
        Student.query
        .join(
            AccommodationAssignment,
            Student.student_id
            == AccommodationAssignment.student_id
        )
        .filter(
            db.func.lower(
                db.func.trim(
                    db.func.coalesce(
                        AccommodationAssignment.status,
                        ""
                    )
                )
            ).in_([
                "occupying",
                "active",
            ])
        )
    )

    if search:
        query = query.filter(
            db.or_(
                Student.student_id.ilike(
                    f"%{search}%"
                ),
                Student.name.ilike(
                    f"%{search}%"
                ),
            )
        )

    students = (
        query
        .order_by(Student.name.asc())
        .distinct()
        .all()
    )

    student_rows = []

    for student in students:

        assignment = _tso_get_active_assignment(
            student.student_id
        )

        if not assignment:
            continue

        accommodation = _tso_accommodation_details(
            assignment
        )

        if not accommodation:
            continue

        clearance = (
            DepartmentClearance.query
            .filter(
                DepartmentClearance.student_id
                == student.student_id,
                db.func.lower(
                    db.func.trim(
                        DepartmentClearance.department
                    )
                ).in_([
                    "tso",
                    "technical services office",
                ])
            )
            .order_by(
                DepartmentClearance.id.desc()
            )
            .first()
        )

        # --------------------------------------------------
        # CURRENT-ASSIGNMENT TSO INSPECTION
        # --------------------------------------------------
        # IMPORTANT:
        # Never use an old TSO inspection merely because it
        # belongs to the same student.
        #
        # A new accommodation assignment creates a new TSO
        # inspection lifecycle. Therefore the inspection must
        # belong to THIS active accommodation assignment.
        # --------------------------------------------------

        inspection = (
            TSOInspection.query
            .filter(
                TSOInspection.student_id
                == student.student_id,
                TSOInspection.accommodation_assignment_id
                == assignment.id,
            )
            .order_by(
                TSOInspection.id.desc()
            )
            .first()
        )

        # Only remove the student when the TSO inspection for
        # THIS CURRENT accommodation assignment is cleared.
        #
        # An old cleared inspection from a previous room/
        # accommodation must never hide a new inspection.
        if (
            inspection
            and (inspection.status or "").strip().lower()
            == "cleared"
        ):
            continue

        student_rows.append({
            "student": student,
            "assignment": assignment,
            "accommodation": accommodation,
            "clearance": clearance,
            "inspection": inspection,
            # Queue status belongs to the current room assignment.
            # Previous DepartmentClearance records must not clear it.
            "status": (
                inspection.status
                if inspection
                else "Pending"
            ),
        })

    return render_template(
        "new_staff/tso/dashboard.html",
        staff_name=(
            session.get("staff_name")
            or session.get("name")
            or "TSO Staff"
        ),
        department=(
            session.get("department")
            or "Technical Services Office"
        ),
        students=student_rows,
        search=search,
    )


@app.route(
    "/tso/inspect/<student_id>",
    methods=["GET", "POST"]
)
def tso_inspect_student(student_id):

    if not _tso_staff_allowed():
        return redirect(url_for("new_staff_login"))

    student_id = (
        student_id or ""
    ).strip()

    student = Student.query.filter_by(
        student_id=student_id
    ).first()

    if not student:
        flash(
            "Student not found.",
            "error"
        )
        return _tso_redirect()

    assignment = _tso_get_active_assignment(
        student.student_id
    )

    if not assignment:
        flash(
            "This student does not have an active hostel room.",
            "error"
        )
        return _tso_redirect()

    accommodation = _tso_accommodation_details(
        assignment
    )

    if not accommodation:
        flash(
            "The student's accommodation details could not be loaded.",
            "error"
        )
        return _tso_redirect()

    clearance = (
        DepartmentClearance.query
        .filter(
            DepartmentClearance.student_id
            == student.student_id,
            db.func.lower(
                db.func.trim(
                    DepartmentClearance.department
                )
            ).in_([
                "tso",
                "technical services office",
            ])
        )
        .order_by(
            DepartmentClearance.id.desc()
        )
        .first()
    )

    inspection = (
        TSOInspection.query
        .filter_by(
            student_id=student.student_id,
            accommodation_assignment_id=assignment.id,
        )
        .order_by(
            TSOInspection.id.desc()
        )
        .first()
    )

    if request.method == "POST":

        if inspection and (
            (inspection.status or "").strip().lower()
            == "cleared"
        ):
            flash(
                "This accommodation has already been inspected and cleared by TSO.",
                "error"
            )
            return _tso_redirect()

        def form_value(name):
            return (
                request.form.get(name) or ""
            ).strip()

        if not inspection:
            inspection = TSOInspection(
                student_id=student.student_id,
                accommodation_assignment_id=assignment.id,
                room_id=assignment.room_id,
            )
            db.session.add(inspection)

        inspection.accommodation_assignment_id = assignment.id
        inspection.room_id = assignment.room_id

        inspection.electrical_outlets = form_value(
            "electrical_outlets"
        )
        inspection.lights = form_value("lights")
        inspection.switches = form_value("switches")
        inspection.wiring = form_value("wiring")
        inspection.ventilation = form_value("ventilation")
        inspection.door_lock = form_value("door_lock")
        inspection.windows = form_value("windows")
        inspection.plumbing = form_value("plumbing")
        inspection.furniture = form_value("furniture")
        inspection.general_condition = form_value(
            "general_condition"
        )
        inspection.other = form_value("other")
        inspection.remarks = form_value("remarks")

        inspection.key_collected = True
        inspection.key_name = accommodation["key_name"]
        inspection.inspected_by = (
            session.get("staff_name")
            or session.get("name")
            or session.get("user")
            or "TSO Staff"
        )
        inspection.inspected_at = zambia_now()
        inspection.status = "Cleared"

        if not clearance:
            clearance = DepartmentClearance(
                student_id=student.student_id,
                department="Technical Services Office",
                status="Cleared",
                reason=None,
                remarks=inspection.remarks,
            )
            db.session.add(clearance)
        else:
            clearance.department = (
                "Technical Services Office"
            )
            clearance.status = "Cleared"
            clearance.reason = None
            clearance.remarks = inspection.remarks

        db.session.commit()

        flash(
            f"{student.name} has been cleared by TSO. "
            f"Key collected: {accommodation['key_name']}.",
            "success"
        )

        return redirect(
            url_for(
                "tso_inspect_student",
                student_id=student.student_id,
            )
        )

    return render_template(
        "new_staff/tso/inspect_student.html",
        student=student,
        assignment=assignment,
        accommodation=accommodation,
        clearance=clearance,
        inspection=inspection,
        staff_name=(
            session.get("staff_name")
            or session.get("name")
            or "TSO Staff"
        ),
        department=(
            session.get("department")
            or "Technical Services Office"
        ),
    )





@app.route(
    "/new-staff/hr/case/<int:case_id>",
    methods=["GET", "POST"]
)
def new_staff_hr_case_details(case_id):
    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    department = (session.get("department") or "").strip().lower()

    allowed_departments = {
        "human resource / admin officer",
        "human resource/admin officer",
        "human resource",
        "hr",
    }

    if department not in allowed_departments:
        return redirect(url_for("new_staff_login"))

    case = DisciplinaryCase.query.get_or_404(case_id)

    student = Student.query.filter_by(
        student_id=case.student_id
    ).first()

    if request.method == "POST":
        action = (request.form.get("action") or "").strip().lower()

        # ------------------------------------------
        # RECORD STUDENT RESPONSE
        # ------------------------------------------
        if action == "student_response":
            response = (
                request.form.get("student_response") or ""
            ).strip()

            if not response:
                flash(
                    "Please enter the student's response or statement.",
                    "error"
                )
                return redirect(
                    url_for(
                        "new_staff_hr_case_details",
                        case_id=case.id
                    )
                )

            case.student_response = response
            case.response_at = (
                globals().get("zambia_now", datetime.now)()
            )

            # Move a newly reported case into review once
            # the student's response has been recorded.
            if (
                not case.sanction
                and (case.status or "").strip().lower()
                == "reported"
            ):
                case.status = "Under Review"

            db.session.commit()

            flash(
                "Student response recorded successfully.",
                "success"
            )

            return redirect(
                url_for(
                    "new_staff_hr_case_details",
                    case_id=case.id
                )
            )

        # ------------------------------------------
        # RECORD RESOLUTION
        # ------------------------------------------
        if action == "resolution":
            resolution = (
                request.form.get("resolution") or ""
            ).strip()

            remarks = (
                request.form.get("remarks") or ""
            ).strip()

            if not resolution:
                flash(
                    "Please enter the final resolution.",
                    "error"
                )
                return redirect(
                    url_for(
                        "new_staff_hr_case_details",
                        case_id=case.id
                    )
                )

            case.resolution = resolution
            case.remarks = remarks or None
            case.resolved_at = (
                globals().get("zambia_now", datetime.now)()
            )
            case.resolved_by = session.get("staff_name")
            case.status = "Resolved"

            # A completed resolution is the final stage of
            # the disciplinary case.
            db.session.commit()

            flash(
                f"Case #{case.id} has been resolved successfully.",
                "success"
            )

            return redirect(
                url_for(
                    "new_staff_hr_case_details",
                    case_id=case.id
                )
            )

        flash(
            "Invalid case action.",
            "error"
        )

        return redirect(
            url_for(
                "new_staff_hr_case_details",
                case_id=case.id
            )
        )

    return render_template(
        "new_staff/hr_case_details.html",
        staff_name=session.get("staff_name"),
        department=session.get("department"),
        case=case,
        student=student,
    )


@app.route("/new-staff/hr/active-cases")
def new_staff_hr_active_cases():
    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    department = (session.get("department") or "").strip().lower()

    allowed_departments = {
        "human resource / admin officer",
        "human resource/admin officer",
        "human resource",
        "hr",
    }

    if department not in allowed_departments:
        return redirect(url_for("new_staff_login"))

    search = (request.args.get("search") or "").strip()

    active_statuses = [
        "reported",
        "under review",
        "committee review",
    ]

    query = DisciplinaryCase.query.filter(
        db.func.lower(
            db.func.trim(
                db.func.coalesce(DisciplinaryCase.status, "")
            )
        ).in_(active_statuses),
        db.or_(
            DisciplinaryCase.sanction.is_(None),
            db.func.trim(DisciplinaryCase.sanction) == ""
        )
    )

    if search:
        matching_students = Student.query.filter(
            db.or_(
                Student.student_id.ilike(f"%{search}%"),
                Student.name.ilike(f"%{search}%")
            )
        ).all()

        matching_student_ids = [
            student.student_id
            for student in matching_students
        ]

        filters = [
            DisciplinaryCase.offence.ilike(f"%{search}%")
        ]

        if matching_student_ids:
            filters.append(
                DisciplinaryCase.student_id.in_(matching_student_ids)
            )

        query = query.filter(db.or_(*filters))

    cases = query.order_by(
        DisciplinaryCase.reported_at.desc(),
        DisciplinaryCase.id.desc()
    ).all()

    student_ids = {case.student_id for case in cases}

    student_map = {}

    if student_ids:
        student_rows = Student.query.filter(
            Student.student_id.in_(student_ids)
        ).all()

        student_map = {
            student.student_id: student
            for student in student_rows
        }

    return render_template(
        "new_staff/hr_active_cases.html",
        staff_name=session.get("staff_name"),
        department=session.get("department"),
        cases=cases,
        student_map=student_map,
        search=search,
    )




@app.route("/new-staff/hr/sanctions", methods=["GET", "POST"])
def new_staff_hr_sanctions():
    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    department = (session.get("department") or "").strip().lower()

    allowed_departments = {
        "human resource / admin officer",
        "human resource/admin officer",
        "human resource",
        "hr",
    }

    if department not in allowed_departments:
        return redirect(url_for("new_staff_login"))

    if request.method == "POST":
        case_id_raw = (request.form.get("case_id") or "").strip()
        sanction = (request.form.get("sanction") or "").strip()
        sanction_details = (request.form.get("sanction_details") or "").strip()
        sanction_start_raw = (request.form.get("sanction_start") or "").strip()
        sanction_end_raw = (request.form.get("sanction_end") or "").strip()
        sanction_status = (request.form.get("sanction_status") or "").strip()
        committee_decision = (request.form.get("committee_decision") or "").strip()

        if not case_id_raw.isdigit():
            flash("Invalid disciplinary case selected.", "error")
            return redirect(url_for("new_staff_hr_sanctions"))

        case = DisciplinaryCase.query.get(int(case_id_raw))

        if not case:
            flash("Disciplinary case not found.", "error")
            return redirect(url_for("new_staff_hr_sanctions"))

        if not sanction:
            flash("Please select a sanction.", "error")
            return redirect(url_for("new_staff_hr_sanctions"))

        sanction_start = None
        sanction_end = None

        if sanction_start_raw:
            try:
                sanction_start = datetime.strptime(
                    sanction_start_raw,
                    "%Y-%m-%d"
                )
            except ValueError:
                flash("Invalid sanction start date.", "error")
                return redirect(url_for("new_staff_hr_sanctions"))

        if sanction_end_raw:
            try:
                sanction_end = datetime.strptime(
                    sanction_end_raw,
                    "%Y-%m-%d"
                )
            except ValueError:
                flash("Invalid sanction end date.", "error")
                return redirect(url_for("new_staff_hr_sanctions"))

        if sanction_start and sanction_end and sanction_end < sanction_start:
            flash("Sanction end date cannot be before the start date.", "error")
            return redirect(url_for("new_staff_hr_sanctions"))

        case.sanction = sanction
        case.sanction_details = sanction_details or None
        case.sanction_start = sanction_start
        case.sanction_end = sanction_end
        case.sanction_status = sanction_status or "Pending"

        # Once a sanction has been formally recorded, the
        # disciplinary review stage is complete. The case
        # therefore leaves Active Cases, but is NOT resolved
        # until HR records the final resolution.
        sanction_stage = (case.sanction_status or "Pending").strip().lower()

        if sanction_stage in {"completed"}:
            case.status = "Sanction Completed"
        elif sanction_stage in {"cancelled"}:
            case.status = "Sanction Cancelled"
        else:
            case.status = "Sanction Active"

        if committee_decision:
            case.committee_decision = committee_decision

        if not case.decision_date:
            case.decision_date = (
                globals().get("zambia_now", datetime.now)()
            )

        if not case.decided_by:
            case.decided_by = session.get("staff_name")

        db.session.commit()

        flash(
            f"Sanction recorded successfully for case #{case.id}.",
            "success"
        )

        return redirect(url_for("new_staff_hr_sanctions"))

    search = (request.args.get("search") or "").strip()

    query = DisciplinaryCase.query.filter(
        DisciplinaryCase.sanction.isnot(None),
        db.func.trim(DisciplinaryCase.sanction) != ""
    )

    if search:
        matching_students = Student.query.filter(
            db.or_(
                Student.student_id.ilike(f"%{search}%"),
                Student.name.ilike(f"%{search}%")
            )
        ).all()

        matching_student_ids = [
            student.student_id
            for student in matching_students
        ]

        filters = [
            DisciplinaryCase.offence.ilike(f"%{search}%"),
            DisciplinaryCase.sanction.ilike(f"%{search}%"),
        ]

        if matching_student_ids:
            filters.append(
                DisciplinaryCase.student_id.in_(matching_student_ids)
            )

        query = query.filter(db.or_(*filters))

    sanctioned_cases = query.order_by(
        DisciplinaryCase.decision_date.desc(),
        DisciplinaryCase.id.desc()
    ).all()

    # Cases that still need a disciplinary sanction/outcome.
    pending_cases = DisciplinaryCase.query.filter(
        db.func.lower(
            db.func.trim(
                db.func.coalesce(DisciplinaryCase.status, "")
            )
        ).in_([
            "reported",
            "under review",
            "committee review",
        ]),
        db.or_(
            DisciplinaryCase.sanction.is_(None),
            db.func.trim(DisciplinaryCase.sanction) == ""
        )
    ).order_by(
        DisciplinaryCase.reported_at.desc(),
        DisciplinaryCase.id.desc()
    ).all()

    student_ids = {
        case.student_id
        for case in sanctioned_cases
    }

    student_ids.update(
        case.student_id
        for case in pending_cases
    )

    student_map = {}

    if student_ids:
        student_rows = Student.query.filter(
            Student.student_id.in_(student_ids)
        ).all()

        student_map = {
            student.student_id: student
            for student in student_rows
        }

    selected_case_id = (request.args.get("case_id") or "").strip()

    return render_template(
        "new_staff/hr_sanctions.html",
        staff_name=session.get("staff_name"),
        department=session.get("department"),
        cases=sanctioned_cases,
        pending_cases=pending_cases,
        student_map=student_map,
        search=search,
        selected_case_id=selected_case_id,
    )




# ============================================================
# NEW STAFF AME STORES — DASHBOARD
# ============================================================

@app.route("/new-staff/ame/dashboard")
def new_staff_ame_dashboard():

    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    department = (
        session.get("department") or ""
    ).strip().lower()

    if department not in {
        "ame stores",
        "ame stores department",
        "ame"
    }:
        return redirect(url_for("new_staff_login"))

    search = (
        request.args.get("search") or ""
    ).strip()

    query = Student.query

    if search:
        query = query.filter(
            db.or_(
                Student.student_id.ilike(
                    f"%{search}%"
                ),
                Student.name.ilike(
                    f"%{search}%"
                )
            )
        )

    students = query.order_by(
        Student.name.asc()
    ).all()

    total_students = Student.query.count()

    # --------------------------------------------------
    # AME TOOL COUNTS
    # --------------------------------------------------

    issued_tools = AMETool.query.filter_by(
        returned=False
    ).count()

    returned_tools = AMETool.query.filter_by(
        returned=True
    ).count()

    # --------------------------------------------------
    # OUTSTANDING TOOLS
    # --------------------------------------------------

    outstanding_tools = (
        AMETool.query
        .filter_by(returned=False)
        .order_by(
            AMETool.id.desc()
        )
        .limit(8)
        .all()
    )

    # --------------------------------------------------
    # STUDENTS WITH OUTSTANDING TOOLS
    # --------------------------------------------------

    pending_student_ids = {
        tool.student_id
        for tool in AMETool.query.filter_by(
            returned=False
        ).all()
    }

    pending_students = len(
        pending_student_ids
    )

    students_cleared = max(
        total_students - pending_students,
        0
    )

    clearance_percentage = (
        round(
            (students_cleared / total_students) * 100
        )
        if total_students
        else 0
    )

    # --------------------------------------------------
    # RECENT TOOL ACTIVITY
    # --------------------------------------------------

    recent_tools = (
        AMETool.query
        .order_by(
            AMETool.id.desc()
        )
        .limit(8)
        .all()
    )

    recent_returns = (
        AMETool.query
        .filter_by(returned=True)
        .order_by(
            AMETool.id.desc()
        )
        .limit(8)
        .all()
    )

    # AMETool records now contain issue and return
    # timestamps and staff tracking information.
    # --------------------------------------------------
    # AME ACTIVITY — LAST 7 DAYS
    # --------------------------------------------------

    from datetime import datetime, timedelta

    today = datetime.now().date()

    ame_activity = []

    for offset in range(6, -1, -1):

        day = today - timedelta(days=offset)

        issued_count = 0
        returned_count = 0

        for tool in AMETool.query.all():

            # Count an issue on its issue date.
            if tool.issued_at:
                try:
                    issued_date = datetime.fromisoformat(
                        str(tool.issued_at)
                    ).date()

                    if issued_date == day:
                        issued_count += 1

                except (ValueError, TypeError):
                    pass

            # Count a return on its return date.
            if tool.returned and tool.returned_at:
                try:
                    returned_date = datetime.fromisoformat(
                        str(tool.returned_at)
                    ).date()

                    if returned_date == day:
                        returned_count += 1

                except (ValueError, TypeError):
                    pass

        ame_activity.append({
            "date": day.strftime("%a"),
            "issued": issued_count,
            "returned": returned_count
        })

    # --------------------------------------------------
    # ANNOUNCEMENTS
    # --------------------------------------------------

    announcements = Announcement.query.filter(
        db.func.coalesce(
            Announcement.active,
            True
        ) == True,
        db.func.lower(
            db.func.trim(
                db.func.coalesce(
                    Announcement.audience,
                    ""
                )
            )
        ).in_([
            "staff",
            "all"
        ])
    ).order_by(
        Announcement.created_at.desc()
    ).limit(5).all()

    announcement_count = Announcement.query.filter(
        db.func.coalesce(
            Announcement.active,
            True
        ) == True,
        db.func.lower(
            db.func.trim(
                db.func.coalesce(
                    Announcement.audience,
                    ""
                )
            )
        ).in_([
            "staff",
            "all"
        ])
    ).count()

    settings = {}

    try:
        import sqlite3

        conn = sqlite3.connect(DATABASE_URL)
        conn.row_factory = sqlite3.Row

        rows = conn.execute(
            "SELECT setting_key, setting_value FROM system_settings"
        ).fetchall()

        settings = {
            row["setting_key"]: row["setting_value"]
            for row in rows
        }

        conn.close()

    except Exception:
        settings = {}

    return render_template(
        "new_staff/ame/dashboard.html",
        staff_name=session.get("staff_name"),
        department=session.get("department"),
        students=students,
        search=search,
        total_students=total_students,
        issued_tools=issued_tools,
        returned_tools=returned_tools,
        outstanding_tools=outstanding_tools,
        pending_students=pending_students,
        students_cleared=students_cleared,
        clearance_percentage=clearance_percentage,
        recent_tools=recent_tools,
        recent_returns=recent_returns,
        ame_activity=ame_activity,
        announcements=announcements,
        announcement_count=announcement_count,
        settings=settings
    )


# ============================================================
# NEW STAFF AME STORES — STUDENTS
# ============================================================

@app.route("/new-staff/ame/students")
def new_staff_ame_students():

    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    department = (
        session.get("department") or ""
    ).strip().lower()

    if department not in {
        "ame stores",
        "ame stores department",
        "ame"
    }:
        return redirect(url_for("new_staff_login"))

    search = (
        request.args.get("search") or ""
    ).strip()

    query = Student.query

    if search:
        query = query.filter(
            db.or_(
                Student.student_id.ilike(
                    f"%{search}%"
                ),
                Student.name.ilike(
                    f"%{search}%"
                )
            )
        )

    students = query.order_by(
        Student.name.asc()
    ).all()

    student_records = []

    for student in students:

        tools = AMETool.query.filter_by(
            student_id=student.student_id,
            returned=False
        ).order_by(
            AMETool.id.desc()
        ).all()

        student_records.append({
            "student": student,
            "tools": tools
        })

    return render_template(
        "new_staff/ame/students.html",
        staff_name=session.get("staff_name"),
        department=session.get("department"),
        students=student_records,
        search=search
    )


# ============================================================
# NEW STAFF AME STORES — ISSUE TOOL
# ============================================================

@app.route("/new-staff/ame/issue-tool", methods=["GET", "POST"])
def new_staff_ame_issue_tool():

    if session.get("role") != "staff":
        return redirect(url_for("new_staff_login"))

    department = (
        session.get("department") or ""
    ).strip().lower()

    if department not in {
        "ame stores",
        "ame stores department",
        "ame"
    }:
        return redirect(url_for("new_staff_login"))

    students = Student.query.order_by(
        Student.name.asc()
    ).all()

    if request.method == "POST":

        student_id = (
            request.form.get("student_id") or ""
        ).strip()

        name = (
            request.form.get("name") or ""
        ).strip()

        remarks = (
            request.form.get("remarks") or ""
        ).strip()

        student = Student.query.filter_by(
            student_id=student_id
        ).first()

        if not student:
            flash("Please select a valid student.", "error")
            return redirect(
                url_for("new_staff_ame_issue_tool")
            )

        if not name:
            flash("Please enter the tool name.", "error")
            return redirect(
                url_for("new_staff_ame_issue_tool")
            )

        # ----------------------------------------------------
        # CHECK FOR AN EXISTING PENDING REQUEST
        # ----------------------------------------------------

        existing_request = ItemRequest.query.filter_by(
            student_id=student.student_id,
            department="AME Stores",
            item=name,
            item_type="Institutional Property",
            status="Pending"
        ).first()

        if existing_request:
            flash(
                f"A pending request for '{name}' already exists "
                f"for {student.name}.",
                "error"
            )
            return redirect(
                url_for("new_staff_ame_issue_tool")
            )

        # ----------------------------------------------------
        # CREATE REQUEST ONLY
        #
        # The tool is NOT issued yet.
        # The student must accept the request first.
        # ----------------------------------------------------

        item_request = ItemRequest(
            student_id=student.student_id,
            department="AME Stores",
            item=name,
            item_type="Institutional Property",
            status="Pending",
            assigned_by=(
                session.get("staff_name")
                or session.get("username")
                or "AME Stores Staff"
            ),
            remarks=remarks or None
        )

        db.session.add(item_request)

        # ----------------------------------------------------
        # DEPARTMENT HISTORY
        # ----------------------------------------------------

        history = DepartmentHistory(
            student_id=student.student_id,
            department="AME Stores",
            status="Pending",
            remarks=(
                f"Tool: {name} | "
                f"Tool request sent to student for confirmation. | "
                f"Requested by: "
                f"{item_request.assigned_by or 'AME Stores Staff'}"
            ),
            action="AME Tool Request Created",
            performed_by=(
                item_request.assigned_by
                or "AME Stores Staff"
            )
        )

        db.session.add(history)
        db.session.commit()

        flash(
            f"Tool request for '{name}' sent to {student.name}. "
            f"Awaiting student confirmation.",
            "success"
        )

        return redirect(
            url_for("new_staff_ame_issue_tool")
        )

    return render_template(
        "new_staff/ame/issue_tool.html",
        staff_name=session.get("staff_name"),
        department=session.get("department"),
        students=students
    )


# ============================================================
# NEW STAFF AME STORES — RETURN TOOL
# ============================================================

@app.route(
    "/new-staff/ame/return-tool",
    methods=["GET", "POST"]
)
@app.route(
    "/new-staff/ame/return-tool",
    methods=["GET", "POST"]
)
@app.route(
    "/new-staff/ame/return-tool/<int:tool_id>",
    methods=["POST"]
)
def new_staff_ame_return_tool(tool_id=None):

    if session.get("role") != "staff":
        return redirect(
            url_for("new_staff_login")
        )

    department = (
        session.get("department") or ""
    ).strip().lower()

    if department not in {
        "ame stores",
        "ame stores department",
        "ame"
    }:
        return redirect(
            url_for("new_staff_login")
        )

    # --------------------------------------------------------
    # RETURN A TOOL
    # --------------------------------------------------------

    if request.method == "POST":

        if tool_id is None:
            tool_id = request.form.get("tool_id", type=int)

        if tool_id is None:
            flash(
                "No AME tool was selected for return.",
                "error"
            )
            return redirect(
                url_for("new_staff_ame_return_tool")
            )

        tool = AMETool.query.filter_by(
            id=tool_id,
            returned=False
        ).first()

        if not tool:
            flash(
                "AME tool not found or it has already been returned.",
                "error"
            )
            return redirect(
                url_for("new_staff_ame_return_tool")
            )

        student = Student.query.filter_by(
            student_id=tool.student_id
        ).first()

        response_time = zambia_now()

        tool.returned = True
        tool.returned_at = response_time.strftime(
            "%d %b %Y %H:%M:%S"
        )
        tool.returned_by = (
            session.get("staff_name")
            or session.get("username")
            or "AME Stores Staff"
        )

        existing_remarks = tool.remarks or ""

        return_note = (
            f"Returned by AME Stores staff "
            f"({session.get('staff_name') or session.get('username') or 'Staff'}) "
            f"on {response_time.strftime('%d %b %Y %H:%M:%S')}."
        )

        if existing_remarks:
            tool.remarks = (
                f"{existing_remarks} | {return_note}"
            )
        else:
            tool.remarks = return_note

        history = DepartmentHistory(
            student_id=tool.student_id,
            department="AME Stores",
            status="Returned",
            remarks=(
                f"Tool: {tool.name} | "
                f"Tool returned by AME Stores staff. | "
                f"Returned by: "
                f"{session.get('staff_name') or session.get('username') or 'Staff'}"
            ),
            action="AME Tool Returned",
            performed_by=(
                session.get('staff_name')
                or session.get('username')
                or "AME Stores Staff"
            )
        )

        db.session.add(history)
        db.session.commit()

        student_name = (
            student.name
            if student
            else tool.student_id
        )

        flash(
            f"Tool '{tool.name}' returned by {student_name}.",
            "success"
        )

        return redirect(
            url_for("new_staff_ame_return_tool")
        )

    # --------------------------------------------------------
    # CURRENTLY OUTSTANDING TOOLS ONLY
    # --------------------------------------------------------

    active_tools = AMETool.query.filter_by(
        returned=False
    ).order_by(
        AMETool.id.desc()
    ).all()

    tool_records = []

    for tool in active_tools:

        student = Student.query.filter_by(
            student_id=tool.student_id
        ).first()

        if student:

            tool_records.append({
                "tool": tool,
                "student": student
            })

    return render_template(
        "new_staff/ame/return_tool.html",
        staff_name=session.get("staff_name"),
        department=session.get("department"),
        tools=tool_records
    )



# ============================================================
# NEW STAFF AME STORES — ANNOUNCEMENTS
# ============================================================

@app.route("/new-staff/ame/announcements")
def new_staff_ame_announcements():

    if session.get("role") != "staff":
        return redirect(
            url_for("new_staff_login")
        )

    department = (
        session.get("department") or ""
    ).strip().lower()

    if department not in {
        "ame stores",
        "ame stores department",
        "ame"
    }:
        return redirect(
            url_for("new_staff_login")
        )

    announcements = (
        Announcement.query
        .filter(
            db.func.coalesce(
                Announcement.active,
                True
            ) == True,
            db.func.lower(
                db.func.trim(
                    db.func.coalesce(
                        Announcement.audience,
                        ""
                    )
                )
            ).in_([
                "staff",
                "all"
            ])
        )
        .order_by(
            Announcement.created_at.desc()
        )
        .all()
    )

    return render_template(
        "new_staff/ame/announcements.html",
        staff_name=(
            session.get("staff_name")
            or session.get("name")
            or session.get("username")
            or "AME Stores Staff"
        ),
        department=(
            session.get("department")
            or "AME Stores"
        ),
        announcements=announcements
    )



# ============================================================
# NEW STAFF AME STORES — TOOL RECORDS
# ============================================================

@app.route("/new-staff/ame/tool-records")
def new_staff_ame_tool_records():

    if session.get("role") != "staff":
        return redirect(
            url_for("new_staff_login")
        )

    department = (
        session.get("department") or ""
    ).strip().lower()

    if department not in {
        "ame stores",
        "ame stores department",
        "ame"
    }:
        return redirect(
            url_for("new_staff_login")
        )

    search = (
        request.args.get("search") or ""
    ).strip()

    query = AMETool.query

    if search:

        matching_students = Student.query.filter(
            db.or_(
                Student.student_id.ilike(
                    f"%{search}%"
                ),
                Student.name.ilike(
                    f"%{search}%"
                )
            )
        ).all()

        matching_student_ids = [
            student.student_id
            for student in matching_students
        ]

        query = query.filter(
            db.or_(
                AMETool.name.ilike(
                    f"%{search}%"
                ),
                AMETool.student_id.in_(
                    matching_student_ids
                ) if matching_student_ids else db.false()
            )
        )

    tools = query.order_by(
        AMETool.id.desc()
    ).all()

    tool_records = []

    for tool in tools:

        student = Student.query.filter_by(
            student_id=tool.student_id
        ).first()

        tool_records.append({
            "tool": tool,
            "student": student
        })

    return render_template(
        "new_staff/ame/tool_records.html",
        staff_name=session.get("staff_name"),
        department=session.get("department"),
        records=tool_records,
        search=search
    )

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
