import os
import uuid
import secrets
import string
import threading
import webbrowser
from datetime import datetime
from functools import wraps

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    abort,
    jsonify,
    send_from_directory
)

from flask_sqlalchemy import SQLAlchemy

from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from werkzeug.utils import secure_filename


# ============================================================
# BASIC SETUP
# ============================================================

BASE = os.path.abspath(
    os.path.dirname(__file__)
)

UPLOADS = os.path.join(
    BASE,
    "uploads"
)

os.makedirs(
    UPLOADS,
    exist_ok=True
)


app = Flask(__name__)


app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY",
    "classconnect-secret-change-this"
)


app.config["MAX_CONTENT_LENGTH"] = (
    50 * 1024 * 1024
)


# ============================================================
# DATABASE
# ============================================================

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "sqlite:///" + os.path.join(
        BASE,
        "classconnect.db"
    )
)


if DATABASE_URL.startswith("postgres://"):

    DATABASE_URL = DATABASE_URL.replace(
        "postgres://",
        "postgresql://",
        1
    )


app.config[
    "SQLALCHEMY_DATABASE_URI"
] = DATABASE_URL


app.config[
    "SQLALCHEMY_TRACK_MODIFICATIONS"
] = False


db = SQLAlchemy(app)


# ============================================================
# LOGIN SYSTEM
# ============================================================

login_manager = LoginManager(
    app
)

login_manager.login_view = "login"


# ============================================================
# USER MODEL
# ============================================================

class User(
    UserMixin,
    db.Model
):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(120),
        nullable=False
    )

    email = db.Column(
        db.String(255),
        unique=True,
        nullable=False,
        index=True
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


# ============================================================
# CLASSROOM MODEL
# ============================================================

class Classroom(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(160),
        nullable=False
    )

    code = db.Column(
        db.String(10),
        unique=True,
        nullable=False,
        index=True
    )

    description = db.Column(
        db.Text,
        default=""
    )

    owner_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    owner = db.relationship(
        "User",
        foreign_keys=[owner_id]
    )


# ============================================================
# CLASSROOM MEMBERSHIP
# ============================================================

class Membership(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    classroom_id = db.Column(
        db.Integer,
        db.ForeignKey("classroom.id"),
        nullable=False
    )

    role = db.Column(
        db.String(20),
        default="student"
    )

    user = db.relationship(
        "User"
    )

    classroom = db.relationship(
        "Classroom"
    )

    __table_args__ = (
        db.UniqueConstraint(
            "user_id",
            "classroom_id",
            name="uq_member"
        ),
    )


# ============================================================
# ANNOUNCEMENT MODEL
# ============================================================

class Post(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    classroom_id = db.Column(
        db.Integer,
        db.ForeignKey("classroom.id"),
        nullable=False
    )

    author_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    body = db.Column(
        db.Text,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    author = db.relationship(
        "User"
    )


# ============================================================
# ASSIGNMENT MODEL
# ============================================================

class Assignment(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    classroom_id = db.Column(
        db.Integer,
        db.ForeignKey("classroom.id"),
        nullable=False
    )

    title = db.Column(
        db.String(200),
        nullable=False
    )

    description = db.Column(
        db.Text,
        default=""
    )

    due_date = db.Column(
        db.DateTime
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


# ============================================================
# SUBMISSION MODEL
# ============================================================

class Submission(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    assignment_id = db.Column(
        db.Integer,
        db.ForeignKey("assignment.id"),
        nullable=False
    )

    student_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    content = db.Column(
        db.Text,
        default=""
    )

    filename = db.Column(
        db.String(255),
        default=""
    )

    submitted_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    __table_args__ = (
        db.UniqueConstraint(
            "assignment_id",
            "student_id",
            name="uq_submission"
        ),
    )


# ============================================================
# CLASSROOM CHAT MESSAGE
# ============================================================

class ClassMessage(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    classroom_id = db.Column(
        db.Integer,
        db.ForeignKey("classroom.id"),
        nullable=False
    )

    sender_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    body = db.Column(
        db.Text,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    sender = db.relationship(
        "User"
    )


# ============================================================
# PRIVATE CONVERSATION
# ============================================================

class Conversation(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user1_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    user2_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


# ============================================================
# PRIVATE MESSAGE
# ============================================================

class DirectMessage(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    conversation_id = db.Column(
        db.Integer,
        db.ForeignKey("conversation.id"),
        nullable=False
    )

    sender_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    body = db.Column(
        db.Text,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    sender = db.relationship(
        "User"
    )


# ============================================================
# LOGIN USER LOADER
# ============================================================

@login_manager.user_loader
def load_user(user_id):

    return db.session.get(
        User,
        int(user_id)
    )


# ============================================================
# GENERATE CLASS CODE
# ============================================================

def make_code():

    alphabet = (
        string.ascii_uppercase
        + string.digits
    )

    while True:

        code = "".join(
            secrets.choice(alphabet)
            for _ in range(7)
        )

        existing = db.session.execute(
            db.select(Classroom)
            .filter_by(code=code)
        ).scalar_one_or_none()

        if not existing:

            return code


# ============================================================
# CHECK CLASS MEMBERSHIP
# ============================================================

def membership_for(class_id):

    return db.session.execute(
        db.select(Membership)
        .filter_by(
            user_id=current_user.id,
            classroom_id=class_id
        )
    ).scalar_one_or_none()


# ============================================================
# MEMBER-ONLY DECORATOR
# ============================================================

def member_required(function):

    @wraps(function)
    @login_required
    def wrapped(
        class_id,
        *args,
        **kwargs
    ):

        classroom = db.session.get(
            Classroom,
            class_id
        )

        if not classroom:

            abort(404)

        if not membership_for(
            class_id
        ):

            abort(403)

        return function(
            class_id,
            classroom,
            *args,
            **kwargs
        )

    return wrapped


# ============================================================
# TEACHER-ONLY DECORATOR
# ============================================================

def teacher_required(function):

    @wraps(function)
    @login_required
    def wrapped(
        class_id,
        *args,
        **kwargs
    ):

        classroom = db.session.get(
            Classroom,
            class_id
        )

        if not classroom:

            abort(404)

        if classroom.owner_id != current_user.id:

            abort(403)

        return function(
            class_id,
            classroom,
            *args,
            **kwargs
        )

    return wrapped


# ============================================================
# PRIVATE CHAT CREATION
# ============================================================

def get_or_create_conversation(
    user_a,
    user_b
):

    first = min(
        user_a,
        user_b
    )

    second = max(
        user_a,
        user_b
    )

    conversation = db.session.execute(
        db.select(Conversation)
        .filter_by(
            user1_id=first,
            user2_id=second
        )
    ).scalar_one_or_none()

    if not conversation:

        conversation = Conversation(
            user1_id=first,
            user2_id=second
        )

        db.session.add(
            conversation
        )

        db.session.commit()

    return conversation


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    if current_user.is_authenticated:

        return redirect(
            url_for("dashboard")
        )

    return render_template(
        "landing.html"
    )


# ============================================================
# REGISTER
# ============================================================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if current_user.is_authenticated:

        return redirect(
            url_for("dashboard")
        )

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        if (
            not name
            or not email
            or len(password) < 6
        ):

            flash(
                "Enter your name, a valid email and a password of at least 6 characters.",
                "error"
            )

        elif db.session.execute(
            db.select(User)
            .filter_by(email=email)
        ).scalar_one_or_none():

            flash(
                "An account with that email already exists.",
                "error"
            )

        else:

            user = User(
                name=name,
                email=email,
                password_hash=generate_password_hash(
                    password
                )
            )

            db.session.add(
                user
            )

            db.session.commit()

            login_user(
                user,
                remember=True
            )

            return redirect(
                url_for("dashboard")
            )

    return render_template(
        "auth.html",
        mode="register"
    )


# ============================================================
# LOGIN
# ============================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if current_user.is_authenticated:

        return redirect(
            url_for("dashboard")
        )

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        user = db.session.execute(
            db.select(User)
            .filter_by(email=email)
        ).scalar_one_or_none()

        if (
            not user
            or not check_password_hash(
                user.password_hash,
                password
            )
        ):

            flash(
                "Incorrect email or password.",
                "error"
            )

        else:

            login_user(
                user,
                remember=True
            )

            return redirect(
                url_for("dashboard")
            )

    return render_template(
        "auth.html",
        mode="login"
    )


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
@login_required
def logout():

    logout_user()

    return redirect(
        url_for("home")
    )


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/dashboard")
@login_required
def dashboard():

    memberships = db.session.execute(
        db.select(Membership)
        .filter_by(
            user_id=current_user.id
        )
        .order_by(
            Membership.id.desc()
        )
    ).scalars().all()

    return render_template(
        "dashboard.html",
        memberships=memberships
    )


# ============================================================
# CREATE CLASSROOM
# ============================================================

@app.route(
    "/class/create",
    methods=["POST"]
)
@login_required
def create_class():

    name = request.form.get(
        "name",
        ""
    ).strip()

    description = request.form.get(
        "description",
        ""
    ).strip()

    if not name:

        flash(
            "Class name is required.",
            "error"
        )

        return redirect(
            url_for("dashboard")
        )

    classroom = Classroom(
        name=name,
        description=description,
        code=make_code(),
        owner_id=current_user.id
    )

    db.session.add(
        classroom
    )

    db.session.flush()

    db.session.add(
        Membership(
            user_id=current_user.id,
            classroom_id=classroom.id,
            role="teacher"
        )
    )

    db.session.commit()

    return redirect(
        url_for(
            "classroom",
            class_id=classroom.id
        )
    )


# ============================================================
# JOIN CLASSROOM
# ============================================================

@app.route(
    "/class/join",
    methods=["POST"]
)
@login_required
def join_class():

    code = request.form.get(
        "code",
        ""
    ).strip().upper()

    classroom = db.session.execute(
        db.select(Classroom)
        .filter_by(code=code)
    ).scalar_one_or_none()

    if not classroom:

        flash(
            "Class code not found.",
            "error"
        )

    elif membership_for(
        classroom.id
    ):

        flash(
            "You are already in this class.",
            "success"
        )

    else:

        db.session.add(
            Membership(
                user_id=current_user.id,
                classroom_id=classroom.id,
                role="student"
            )
        )

        db.session.commit()

        flash(
            "Class joined successfully.",
            "success"
        )

    return redirect(
        url_for("dashboard")
    )


# ============================================================
# CLASSROOM PAGE
# ============================================================

@app.route(
    "/class/<int:class_id>"
)
@member_required
def classroom(
    class_id,
    classroom
):

    posts = db.session.execute(
        db.select(Post)
        .filter_by(
            classroom_id=class_id
        )
        .order_by(
            Post.created_at.desc()
        )
    ).scalars().all()

    assignments = db.session.execute(
        db.select(Assignment)
        .filter_by(
            classroom_id=class_id
        )
        .order_by(
            Assignment.created_at.desc()
        )
    ).scalars().all()

    messages = db.session.execute(
        db.select(ClassMessage)
        .filter_by(
            classroom_id=class_id
        )
        .order_by(
            ClassMessage.created_at.desc()
        )
        .limit(100)
    ).scalars().all()

    messages.reverse()

    members = db.session.execute(
        db.select(Membership)
        .filter_by(
            classroom_id=class_id
        )
        .order_by(
            Membership.role.desc(),
            Membership.id
        )
    ).scalars().all()

    return render_template(
        "classroom.html",
        classroom=classroom,
        posts=posts,
        assignments=assignments,
        messages=messages,
        members=members
    )


# ============================================================
# POST ANNOUNCEMENT
# ============================================================

@app.route(
    "/class/<int:class_id>/post",
    methods=["POST"]
)
@teacher_required
def post(
    class_id,
    classroom
):

    body = request.form.get(
        "body",
        ""
    ).strip()

    if body:

        db.session.add(
            Post(
                classroom_id=class_id,
                author_id=current_user.id,
                body=body
            )
        )

        db.session.commit()

    return redirect(
        url_for(
            "classroom",
            class_id=class_id
        )
    )


# ============================================================
# CREATE ASSIGNMENT
# ============================================================

@app.route(
    "/class/<int:class_id>/assignment",
    methods=["POST"]
)
@teacher_required
def assignment(
    class_id,
    classroom
):

    title = request.form.get(
        "title",
        ""
    ).strip()

    description = request.form.get(
        "description",
        ""
    ).strip()

    due = request.form.get(
        "due_date",
        ""
    )

    due_dt = None

    if due:

        try:

            due_dt = datetime.fromisoformat(
                due
            )

        except ValueError:

            pass

    if title:

        db.session.add(
            Assignment(
                classroom_id=class_id,
                title=title,
                description=description,
                due_date=due_dt
            )
        )

        db.session.commit()

    return redirect(
        url_for(
            "classroom",
            class_id=class_id
        )
    )


# ============================================================
# CLASSROOM MESSAGE
# ============================================================

@app.route(
    "/class/<int:class_id>/message",
    methods=["POST"]
)
@member_required
def class_message(
    class_id,
    classroom
):

    body = request.form.get(
        "body",
        ""
    ).strip()

    if body:

        db.session.add(
            ClassMessage(
                classroom_id=class_id,
                sender_id=current_user.id,
                body=body
            )
        )

        db.session.commit()

    return redirect(
        url_for(
            "classroom",
            class_id=class_id
        ) + "#class-chat"
    )


# ============================================================
# CLASSROOM CHAT API
# ============================================================

@app.route(
    "/api/class/<int:class_id>/messages"
)
@member_required
def class_messages_api(
    class_id,
    classroom
):

    messages = db.session.execute(
        db.select(ClassMessage)
        .filter_by(
            classroom_id=class_id
        )
        .order_by(
            ClassMessage.created_at.desc()
        )
        .limit(100)
    ).scalars().all()

    messages.reverse()

    return jsonify([
        {
            "name": m.sender.name,
            "body": m.body,
            "time": m.created_at.strftime("%H:%M")
        }

        for m in messages
    ])


# ============================================================
# SUBMIT ASSIGNMENT
# ============================================================

@app.route(
    "/assignment/<int:assignment_id>/submit",
    methods=["POST"]
)
@login_required
def submit_assignment(
    assignment_id
):

    assignment = db.session.get(
        Assignment,
        assignment_id
    )

    if not assignment:

        abort(404)

    if not membership_for(
        assignment.classroom_id
    ):

        abort(403)

    file = request.files.get(
        "file"
    )

    filename = ""

    if file and file.filename:

        filename = (
            uuid.uuid4().hex
            + "_"
            + secure_filename(
                file.filename
            )
        )

        file.save(
            os.path.join(
                UPLOADS,
                filename
            )
        )

    submission = db.session.execute(
        db.select(Submission)
        .filter_by(
            assignment_id=assignment_id,
            student_id=current_user.id
        )
    ).scalar_one_or_none()

    if not submission:

        submission = Submission(
            assignment_id=assignment_id,
            student_id=current_user.id
        )

        db.session.add(
            submission
        )

    submission.content = request.form.get(
        "content",
        ""
    ).strip()

    if filename:

        submission.filename = filename

    submission.submitted_at = datetime.utcnow()

    db.session.commit()

    flash(
        "Assignment submitted.",
        "success"
    )

    return redirect(
        url_for(
            "classroom",
            class_id=assignment.classroom_id
        )
    )


# ============================================================
# DOWNLOAD UPLOADED FILE
# ============================================================

@app.route(
    "/uploads/<path:name>"
)
@login_required
def upload(name):

    return send_from_directory(
        UPLOADS,
        name,
        as_attachment=True
    )


# ============================================================
# PEOPLE SEARCH
# ============================================================

@app.route("/people")
@login_required
def people():

    q = request.args.get(
        "q",
        ""
    ).strip()

    users = []

    if q:

        users = db.session.execute(
            db.select(User)
            .filter(
                User.id != current_user.id,
                (
                    User.name.ilike(
                        "%" + q + "%"
                    )
                    |
                    User.email.ilike(
                        "%" + q.lower() + "%"
                    )
                )
            )
            .order_by(
                User.name
            )
            .limit(30)
        ).scalars().all()

    return render_template(
        "people.html",
        users=users,
        q=q
    )


# ============================================================
# START PRIVATE CHAT
# ============================================================

@app.route(
    "/chat/start/<int:user_id>"
)
@login_required
def start_chat(user_id):

    other = db.session.get(
        User,
        user_id
    )

    if not other:

        abort(404)

    if other.id == current_user.id:

        abort(404)

    conversation = get_or_create_conversation(
        current_user.id,
        other.id
    )

    return redirect(
        url_for(
            "direct_chat",
            conversation_id=conversation.id
        )
    )


# ============================================================
# PRIVATE CHAT
# ============================================================

@app.route(
    "/chat/<int:conversation_id>",
    methods=["GET", "POST"]
)
@login_required
def direct_chat(
    conversation_id
):

    conversation = db.session.get(
        Conversation,
        conversation_id
    )

    if not conversation:

        abort(404)

    if current_user.id not in (
        conversation.user1_id,
        conversation.user2_id
    ):

        abort(403)

    if conversation.user1_id == current_user.id:

        other_id = conversation.user2_id

    else:

        other_id = conversation.user1_id

    other = db.session.get(
        User,
        other_id
    )

    if request.method == "POST":

        body = request.form.get(
            "body",
            ""
        ).strip()

        if body:

            db.session.add(
                DirectMessage(
                    conversation_id=conversation.id,
                    sender_id=current_user.id,
                    body=body
                )
            )

            db.session.commit()

        return redirect(
            url_for(
                "direct_chat",
                conversation_id=conversation.id
            )
        )

    messages = db.session.execute(
        db.select(DirectMessage)
        .filter_by(
            conversation_id=conversation.id
        )
        .order_by(
            DirectMessage.created_at.asc()
        )
    ).scalars().all()

    return render_template(
        "direct_chat.html",
        conversation=conversation,
        other=other,
        messages=messages
    )


# ============================================================
# PRIVATE CHAT API
# ============================================================

@app.route(
    "/api/chat/<int:conversation_id>/messages"
)
@login_required
def direct_messages_api(
    conversation_id
):

    conversation = db.session.get(
        Conversation,
        conversation_id
    )

    if not conversation:

        abort(404)

    if current_user.id not in (
        conversation.user1_id,
        conversation.user2_id
    ):

        abort(403)

    messages = db.session.execute(
        db.select(DirectMessage)
        .filter_by(
            conversation_id=conversation.id
        )
        .order_by(
            DirectMessage.created_at.asc()
        )
    ).scalars().all()

    return jsonify([
        {
            "name": m.sender.name,
            "body": m.body,
            "time": m.created_at.strftime("%H:%M")
        }

        for m in messages
    ])


# ============================================================
# ERROR HANDLERS
# ============================================================

@app.errorhandler(403)
def error_403(error):

    return render_template(
        "error.html",
        code=403,
        message="You do not have access to this page."
    ), 403


@app.errorhandler(404)
def error_404(error):

    return render_template(
        "error.html",
        code=404,
        message="That page does not exist."
    ), 404


# ============================================================
# CREATE DATABASE TABLES
# ============================================================

with app.app_context():

    db.create_all()


# ============================================================
# AUTOMATICALLY OPEN BROWSER
# ============================================================

def open_browser():

    webbrowser.open(
        "http://127.0.0.1:5000"
    )


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    # Only automatically open the browser
    # when running locally.
    if not os.environ.get("RENDER"):

        threading.Timer(
            1.5,
            open_browser
        ).start()

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
