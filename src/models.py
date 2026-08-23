import enum
import secrets
from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


def _now():
    return datetime.now(timezone.utc)


class Role(enum.Enum):
    ADMIN = "admin"
    VIEWER = "viewer"


class Status(enum.Enum):
    IDEA = "idea"
    IN_DEVELOPMENT = "in_development"
    READY_NOT_LAUNCHED = "ready_not_launched"
    LIVE = "live"
    ARCHIVED = "archived"

    @property
    def label(self):
        return {
            Status.IDEA: "Ідея",
            Status.IN_DEVELOPMENT: "У розробці",
            Status.READY_NOT_LAUNCHED: "Готово, не запущено",
            Status.LIVE: "Працює",
            Status.ARCHIVED: "Зупинено / Архів",
        }[self]

    @property
    def dot_color(self):
        """oklch() token name (see style.css :root) used for the status dot."""
        return {
            Status.IDEA: "var(--text-muted)",
            Status.IN_DEVELOPMENT: "var(--amber)",
            Status.READY_NOT_LAUNCHED: "var(--accent)",
            Status.LIVE: "var(--green)",
            Status.ARCHIVED: "var(--red)",
        }[self]


def hue_for(name):
    """Deterministic hue (0-359) for a category/department name, same
    approach the reference design uses: hash the name, don't hand-pick a
    color per row so a new department never needs a design decision."""
    h = 0
    for ch in name:
        h = (h * 31 + ord(ch)) % 360
    return h


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum(Role), nullable=False, default=Role.VIEWER)
    # Per-automator token so a skill can push automation data on their behalf
    # (see the "register-automation" skill this is meant to support) without
    # sharing a browser login/password. Never displayed after generation -
    # only regenerated, same as CLICKUP_API_TOKEN's own security posture.
    api_key = db.Column(db.String(64), unique=True, nullable=False, default=lambda: secrets.token_hex(32))
    created_at = db.Column(db.DateTime, default=_now)

    automations = db.relationship("Automation", back_populates="owner")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == Role.ADMIN

    @property
    def initials(self):
        parts = self.name.split()
        letters = "".join(p[0] for p in parts[:2] if p)
        return letters.upper() or "?"


automation_departments = db.Table(
    "automation_departments",
    db.Column("automation_id", db.Integer, db.ForeignKey("automation.id"), primary_key=True),
    db.Column("department_id", db.Integer, db.ForeignKey("department.id"), primary_key=True),
)


class Department(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    hue = db.Column(db.Integer, nullable=False, default=0)  # 0-359, oklch() hue for this department's pill

    @property
    def pill_style(self):
        return f"background: oklch(93% 0.03 {self.hue}); color: oklch(35% 0.09 {self.hue});"


automation_skills = db.Table(
    "automation_skills",
    db.Column("automation_id", db.Integer, db.ForeignKey("automation.id"), primary_key=True),
    db.Column("skill_id", db.Integer, db.ForeignKey("skill.id"), primary_key=True),
)


class Automation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    one_liner = db.Column(db.String(500))
    status = db.Column(db.Enum(Status), nullable=False, default=Status.IDEA)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    repo_url = db.Column(db.String(500))
    clickup_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=_now)
    updated_at = db.Column(db.DateTime, default=_now, onupdate=_now)

    owner = db.relationship("User", back_populates="automations")
    departments = db.relationship("Department", secondary=automation_departments, backref="automations")
    skills = db.relationship("Skill", secondary=automation_skills, backref="automations")
    roi = db.relationship("ROIEntry", back_populates="automation", uselist=False, cascade="all, delete-orphan")
    comparison = db.relationship("Comparison", back_populates="automation", uselist=False, cascade="all, delete-orphan")
    review_log = db.relationship(
        "ReviewLogEntry", back_populates="automation", cascade="all, delete-orphan",
        order_by="ReviewLogEntry.created_at.desc()",
    )
    connections = db.relationship(
        "Connection", foreign_keys="Connection.automation_id",
        back_populates="automation", cascade="all, delete-orphan",
    )


class ROIEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    automation_id = db.Column(db.Integer, db.ForeignKey("automation.id"), nullable=False)
    hypothesis = db.Column(db.Text)
    metric_description = db.Column(db.Text)
    confidence = db.Column(db.String(20), default="estimated")  # estimated | measured
    measured_value = db.Column(db.String(255))
    measured_at = db.Column(db.DateTime)
    qualitative_notes = db.Column(db.Text)

    automation = db.relationship("Automation", back_populates="roi")


class Comparison(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    automation_id = db.Column(db.Integer, db.ForeignKey("automation.id"), nullable=False)
    old_way_description = db.Column(db.Text)
    limitations = db.Column(db.Text)

    automation = db.relationship("Automation", back_populates="comparison")
    features = db.relationship("FeatureRow", back_populates="comparison", cascade="all, delete-orphan")


class FeatureRow(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    comparison_id = db.Column(db.Integer, db.ForeignKey("comparison.id"), nullable=False)
    feature = db.Column(db.String(255))
    old_way = db.Column(db.String(255))
    new_way = db.Column(db.String(255))
    why_it_matters = db.Column(db.String(255))

    comparison = db.relationship("Comparison", back_populates="features")


class Connection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    automation_id = db.Column(db.Integer, db.ForeignKey("automation.id"), nullable=False)
    connected_automation_id = db.Column(db.Integer, db.ForeignKey("automation.id"), nullable=False)
    relationship_type = db.Column(db.String(100))
    shared_resource = db.Column(db.String(255))

    automation = db.relationship("Automation", foreign_keys=[automation_id], back_populates="connections")
    connected_automation = db.relationship("Automation", foreign_keys=[connected_automation_id])


class ReviewLogEntry(db.Model):
    """Mirrors stage-0-supplax's backlog/BACKLOG.md concept, in the DB."""
    id = db.Column(db.Integer, primary_key=True)
    automation_id = db.Column(db.Integer, db.ForeignKey("automation.id"), nullable=False)
    round_label = db.Column(db.String(100))
    found = db.Column(db.Text)
    changed = db.Column(db.Text)
    rejected = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=_now)

    automation = db.relationship("Automation", back_populates="review_log")


class Skill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.Text)
    when_to_use = db.Column(db.Text)
    doc_url = db.Column(db.String(500))
