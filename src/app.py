import os
from datetime import datetime
from functools import wraps
from pathlib import Path

import click
from dotenv import load_dotenv
from flask import Flask, abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from . import github_sync
from .extensions import db, login_manager
from .models import (
    Automation,
    AutomationPage,
    AutomationTodoItem,
    Comparison,
    Connection,
    Department,
    FeatureRow,
    ROIEntry,
    ReviewLogEntry,
    Role,
    Skill,
    Status,
    User,
    _now,
    hue_for,
)

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")

    default_db = f"sqlite:///{(BASE_DIR / 'data' / 'portfolio.db').as_posix()}"
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL") or default_db
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.environ.get("AUTH_SECRET") or "dev-only-insecure-key-set-AUTH_SECRET-in-.env"

    db.init_app(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    register_routes(app)
    register_cli(app)
    return app


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def register_routes(app):
    @app.route("/")
    def index():
        return redirect(url_for("automations_list"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            user = User.query.filter_by(email=email).first()
            if user and user.check_password(password):
                login_user(user)
                return redirect(url_for("automations_list"))
            flash("Невірний email або пароль.")
        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        return redirect(url_for("login"))

    @app.route("/automations")
    @login_required
    def automations_list():
        query = Automation.query
        status_filter = request.args.get("status")
        dept_filter = request.args.get("department", type=int)
        search = request.args.get("q", "").strip()

        if status_filter:
            query = query.filter(Automation.status == Status(status_filter))
        if dept_filter:
            query = query.filter(Automation.departments.any(Department.id == dept_filter))
        if search:
            query = query.filter(Automation.name.ilike(f"%{search}%"))

        automations = query.order_by(Automation.updated_at.desc()).all()
        counts = {s: Automation.query.filter_by(status=s).count() for s in Status}
        departments = Department.query.order_by(Department.name).all()
        return render_template(
            "automations_list.html",
            automations=automations,
            statuses=Status,
            counts=counts,
            departments=departments,
            active_status=status_filter,
            active_department=dept_filter,
            search=search,
        )

    def apply_manual_form(automation, form):
        automation.name = form["name"].strip()
        automation.one_liner = form.get("one_liner", "").strip()
        automation.status = Status(form["status"])
        automation.owner_id = int(form.get("owner_id") or automation.owner_id)
        automation.repo_url = form.get("repo_url", "").strip() or None
        automation.clickup_url = form.get("clickup_url", "").strip() or None
        automation.departments = Department.query.filter(
            Department.id.in_(form.getlist("departments"))).all()
        automation.skills = Skill.query.filter(Skill.id.in_(form.getlist("skills"))).all()
        if automation.roi is None:
            automation.roi = ROIEntry()
        automation.roi.hypothesis = form.get("hypothesis", "").strip()
        automation.roi.metric_description = form.get("metric_description", "").strip()
        automation.roi.confidence = form.get("confidence", "estimated")
        automation.roi.presentation_url = form.get("presentation_url", "").strip() or None

    @app.route("/automations/new", methods=["GET", "POST"])
    @login_required
    @admin_required
    def automation_new():
        users = User.query.order_by(User.name).all()
        departments = Department.query.order_by(Department.name).all()
        skills = Skill.query.order_by(Skill.name).all()
        if request.method == "POST":
            automation = Automation(slug=request.form["slug"].strip(), owner_id=current_user.id)
            apply_manual_form(automation, request.form)
            db.session.add(automation)
            db.session.commit()
            return redirect(url_for("automation_detail", slug=automation.slug))
        return render_template("automation_form.html", departments=departments, skills=skills,
                                users=users, statuses=Status, automation=None)

    @app.route("/automations/<slug>/edit", methods=["GET", "POST"])
    @login_required
    @admin_required
    def automation_edit(slug):
        automation = Automation.query.filter_by(slug=slug).first_or_404()
        users = User.query.order_by(User.name).all()
        departments = Department.query.order_by(Department.name).all()
        skills = Skill.query.order_by(Skill.name).all()
        if request.method == "POST":
            apply_manual_form(automation, request.form)
            db.session.commit()
            return redirect(url_for("automation_detail", slug=automation.slug))
        return render_template("automation_form.html", departments=departments, skills=skills,
                                users=users, statuses=Status, automation=automation)

    def sync_automation_from_github(automation, repo_url, owner_id, form_status, selected_dept_ids, slug=None):
        """Shared by the first-time import form and the per-automation
        'Оновити з GitHub' button: fetch README.md/dashboard/ROI.md/
        dashboard/SUMMARY.md and apply them to `automation` (a new unsaved
        instance, or an existing one being refreshed). These two live in a
        dedicated dashboard/ folder because they're a generated sync
        contract, not hand-maintained project docs - the automation's repo
        keeps its own real ROI/functionality writeups elsewhere (docs/
        roi_explained.md, docs/functions.md) and regenerates these two from
        them. Raises on a GitHub fetch failure - callers turn that into a
        flash message."""
        parsed = github_sync.parse_repo_url(repo_url)
        if not parsed:
            raise ValueError("Не схоже на посилання на GitHub-репозиторій "
                              "(очікую https://github.com/власник/репо).")
        owner_gh, repo = parsed

        branch = github_sync.default_branch(owner_gh, repo)
        readme_text = github_sync.fetch_raw_file(owner_gh, repo, "README.md", branch)
        roi_text = github_sync.fetch_raw_file(owner_gh, repo, "dashboard/ROI.md", branch)
        summary_text = github_sync.fetch_raw_file(owner_gh, repo, "dashboard/SUMMARY.md", branch)
        backlog_text = github_sync.fetch_raw_file(owner_gh, repo, "backlog/BACKLOG.md", branch)
        todo_text = github_sync.fetch_raw_file(owner_gh, repo, "TODO.md", branch)
        latest_commit = github_sync.fetch_latest_commit(owner_gh, repo, branch)

        title, one_liner = github_sync.parse_readme(readme_text)
        roi_sections = github_sync.parse_roi_md(roi_text)
        summary = github_sync.summary_fields_from_sections(
            github_sync.parse_markdown_sections(summary_text))

        if automation is None:
            automation = Automation(slug=slug or repo.lower(), owner_id=owner_id,
                                     name=summary["name"] or title or repo)
            db.session.add(automation)
        # dashboard/SUMMARY.md is the purpose-built contract - prefer it over
        # README's prose whenever it's actually present.
        automation.name = summary["name"] or title or automation.name
        automation.one_liner = summary["one_liner"] or one_liner or automation.one_liner
        automation.description = summary["description"] or automation.description
        automation.repo_url = repo_url
        automation.owner_id = owner_id
        automation.last_synced_at = _now()
        automation.current_stage_override = summary["current_stage_override"]
        if latest_commit:
            automation.last_commit_message = latest_commit["message"]
            if latest_commit["date"]:
                automation.last_commit_at = datetime.fromisoformat(latest_commit["date"].replace("Z", "+00:00"))

        warnings = []
        if not summary_text:
            warnings.append("dashboard/SUMMARY.md не знайдено — дані неповні (взято тільки з README.md/dashboard/ROI.md).")
        if form_status:
            automation.status = Status(form_status)
        elif summary["status"]:
            try:
                automation.status = Status(summary["status"])
            except ValueError:
                warnings.append(f"Невідомий статус '{summary['status']}' у dashboard/SUMMARY.md — залишив попередній.")

        if selected_dept_ids:
            automation.departments = Department.query.filter(Department.id.in_(selected_dept_ids)).all()
        elif summary["departments"]:
            depts = []
            for name in summary["departments"]:
                dept = Department.query.filter_by(name=name).first()
                if not dept:
                    dept = Department(name=name, hue=hue_for(name))
                    db.session.add(dept)
                depts.append(dept)
            automation.departments = depts

        if summary["connections"]:
            links = []
            skipped = []
            for c in summary["connections"]:
                target = Automation.query.filter_by(slug=c["slug"]).first()
                if target and target.id != automation.id:
                    links.append(Connection(connected_automation_id=target.id,
                                             relationship_type=c["relationship_type"]))
                elif c["slug"]:
                    skipped.append(c["slug"])
            if links:
                automation.connections = links
            if skipped:
                warnings.append("Не знайдено (ще?) автоматизації для зв'язку: " + ", ".join(skipped))

        if roi_sections:
            fields = github_sync.roi_fields_from_sections(roi_sections)
            if automation.roi is None:
                automation.roi = ROIEntry()
            automation.roi.hypothesis = fields["hypothesis"] or automation.roi.hypothesis
            automation.roi.metric_description = fields["metric_description"] or automation.roi.metric_description
            automation.roi.confidence = fields["confidence"]
            automation.roi.measured_value = fields["measured_value"] or automation.roi.measured_value
            automation.roi.presentation_url = fields["presentation_url"] or automation.roi.presentation_url
        elif not roi_text:
            warnings.append("dashboard/ROI.md у репозиторії не знайдено.")

        if summary["pages"]:
            automation.pages = [
                AutomationPage(name=p["name"], description=p["description"], order_index=i)
                for i, p in enumerate(summary["pages"])
            ]

        backlog_entries = github_sync.parse_backlog_md(backlog_text, limit=5)
        if backlog_entries:
            automation.review_log = [
                ReviewLogEntry(round_label=e["round_label"], found=e["found"],
                                changed=e["changed"], rejected=e["rejected"], order_index=i)
                for i, e in enumerate(backlog_entries)
            ]

        todo_items = github_sync.parse_todo_md(todo_text)
        if todo_items:
            automation.todo_items = [
                AutomationTodoItem(text=t["text"], done=t["done"], order_index=i)
                for i, t in enumerate(todo_items)
            ]

        return automation, warnings

    @app.route("/automations/import-github", methods=["GET", "POST"])
    @login_required
    @admin_required
    def automation_import_github():
        users = User.query.order_by(User.name).all()
        departments = Department.query.order_by(Department.name).all()
        if request.method == "POST":
            repo_url = request.form["repo_url"].strip()
            slug = request.form.get("slug", "").strip() or None
            existing = Automation.query.filter_by(slug=slug).first() if slug else None
            try:
                automation, warnings = sync_automation_from_github(
                    existing, repo_url, int(request.form["owner_id"]),
                    request.form.get("status") or "", request.form.getlist("departments"), slug=slug)
            except ValueError as e:
                flash(str(e))
                return redirect(url_for("automation_import_github"))
            except Exception:
                app.logger.exception("GitHub import failed for %s", repo_url)
                flash("Не вдалося звернутися до GitHub — перевір посилання і чи репозиторій публічний "
                      "(або що GITHUB_TOKEN в .env дійсний, якщо приватний).")
                return redirect(url_for("automation_import_github"))

            db.session.commit()
            flash(f"Синхронізовано з {repo_url}." + (" " + " ".join(warnings) if warnings else ""))
            return redirect(url_for("automation_detail", slug=automation.slug))

        prefill_slug = request.args.get("slug", "")
        prefill_owner_id = request.args.get("owner_id", type=int)
        return render_template("automation_import.html", users=users, departments=departments, statuses=Status,
                                prefill_slug=prefill_slug, prefill_owner_id=prefill_owner_id)

    @app.route("/automations/<slug>/resync", methods=["POST"])
    @login_required
    @admin_required
    def automation_resync(slug):
        """The per-automation 'Оновити з GitHub' button - re-fetches from the
        repo_url already on file, no form to refill."""
        automation = Automation.query.filter_by(slug=slug).first_or_404()
        if not automation.repo_url:
            flash("У цієї автоматизації не вказано посилання на репозиторій.")
            return redirect(url_for("automation_detail", slug=slug))
        try:
            automation, warnings = sync_automation_from_github(
                automation, automation.repo_url, automation.owner_id, "", [])
        except Exception:
            flash("Не вдалося звернутися до GitHub — перевір, чи репозиторій усе ще доступний.")
            return redirect(url_for("automation_detail", slug=slug))

        db.session.commit()
        flash("Оновлено з GitHub." + (" " + " ".join(warnings) if warnings else ""))
        return redirect(url_for("automation_detail", slug=automation.slug))

    @app.route("/automations/<slug>")
    @login_required
    def automation_detail(slug):
        automation = Automation.query.filter_by(slug=slug).first_or_404()
        return render_template("automation_detail.html", automation=automation)

    @app.route("/departments")
    @login_required
    @admin_required
    def departments_list():
        departments = Department.query.order_by(Department.name).all()
        return render_template("departments.html", departments=departments)

    @app.route("/departments/<int:dept_id>/rename", methods=["POST"])
    @login_required
    @admin_required
    def department_rename(dept_id):
        dept = Department.query.get_or_404(dept_id)
        new_name = request.form.get("name", "").strip()
        if not new_name:
            flash("Назва відділу не може бути порожньою.")
        elif Department.query.filter(Department.name == new_name, Department.id != dept_id).first():
            flash(f"Відділ з назвою «{new_name}» вже існує — злий їх через об'єднання нижче, а не перейменування.")
        else:
            dept.name = new_name
            db.session.commit()
        return redirect(url_for("departments_list"))

    @app.route("/departments/merge", methods=["POST"])
    @login_required
    @admin_required
    def department_merge():
        from_dept = Department.query.get_or_404(int(request.form["from_id"]))
        into_dept = Department.query.get_or_404(int(request.form["into_id"]))
        if from_dept.id == into_dept.id:
            flash("Неможливо об'єднати відділ сам із собою.")
            return redirect(url_for("departments_list"))
        for automation in list(from_dept.automations):
            if into_dept not in automation.departments:
                automation.departments.append(into_dept)
            automation.departments.remove(from_dept)
        db.session.delete(from_dept)
        db.session.commit()
        flash(f"«{from_dept.name}» об'єднано з «{into_dept.name}».")
        return redirect(url_for("departments_list"))

    @app.route("/departments/<int:dept_id>/delete", methods=["POST"])
    @login_required
    @admin_required
    def department_delete(dept_id):
        dept = Department.query.get_or_404(dept_id)
        if dept.automations:
            flash(f"«{dept.name}» використовується у {len(dept.automations)} автоматизаціях — "
                  f"спочатку об'єднай з іншим відділом, потім видаляй.")
        else:
            db.session.delete(dept)
            db.session.commit()
        return redirect(url_for("departments_list"))

    @app.route("/automators/<int:user_id>")
    @login_required
    def automator_profile(user_id):
        automator = User.query.get_or_404(user_id)
        return render_template("automator_profile.html", automator=automator)

    @app.route("/skills")
    @login_required
    def skills_library():
        skills = Skill.query.order_by(Skill.name).all()
        return render_template("skills_library.html", skills=skills)

    @app.route("/api/automations/<slug>/sync", methods=["POST"])
    def api_sync_automation(slug):
        """Machine-facing endpoint for stage-0-supplax's portfolio-sync step to
        push a full automation record after a build finishes, authenticated by
        the owning automator's personal api_key rather than a browser session.
        Idempotent: safe to call again for the same slug to update it (owner
        must match). Departments and skills named here that don't exist yet
        are auto-created - see references/portfolio-sync.md's payload schema
        for the exact shape expected."""
        api_key = request.headers.get("X-API-Key")
        owner = User.query.filter_by(api_key=api_key).first() if api_key else None
        if not owner:
            return jsonify({"error": "invalid or missing X-API-Key"}), 401

        payload = request.get_json(silent=True) or {}
        if "name" not in payload:
            return jsonify({"error": "'name' is required"}), 400

        automation = Automation.query.filter_by(slug=slug).first()
        if automation is None:
            automation = Automation(slug=slug, owner_id=owner.id, name=payload["name"])
            db.session.add(automation)
        elif automation.owner_id != owner.id:
            return jsonify({"error": "automation exists under a different owner"}), 403

        automation.name = payload.get("name", automation.name)
        automation.one_liner = payload.get("one_liner", automation.one_liner)
        automation.repo_url = payload.get("repo_url", automation.repo_url)
        automation.clickup_url = payload.get("clickup_url", automation.clickup_url)
        if "status" in payload:
            try:
                automation.status = Status(payload["status"])
            except ValueError:
                return jsonify({"error": f"unknown status '{payload['status']}'"}), 400

        if "departments" in payload:
            names = [n.strip() for n in payload["departments"] if n.strip()]
            depts = []
            for name in names:
                dept = Department.query.filter_by(name=name).first()
                if not dept:
                    dept = Department(name=name, hue=hue_for(name))
                    db.session.add(dept)
                depts.append(dept)
            automation.departments = depts

        if "skills" in payload:
            names = [n.strip() for n in payload["skills"] if n.strip()]
            skills = []
            for name in names:
                skill = Skill.query.filter_by(name=name).first()
                if not skill:
                    skill = Skill(name=name)
                    db.session.add(skill)
                skills.append(skill)
            automation.skills = skills

        if "roi" in payload:
            roi = payload["roi"] or {}
            if automation.roi is None:
                automation.roi = ROIEntry()
            automation.roi.hypothesis = roi.get("hypothesis", automation.roi.hypothesis)
            automation.roi.metric_description = roi.get("metric_description", automation.roi.metric_description)
            automation.roi.confidence = roi.get("confidence", automation.roi.confidence)
            automation.roi.measured_value = roi.get("measured_value", automation.roi.measured_value)
            automation.roi.presentation_url = roi.get("presentation_url", automation.roi.presentation_url)

        if "comparison" in payload:
            comp = payload["comparison"] or {}
            if automation.comparison is None:
                automation.comparison = Comparison()
            automation.comparison.old_way_description = comp.get(
                "old_way_description", automation.comparison.old_way_description)
            automation.comparison.limitations = comp.get("limitations", automation.comparison.limitations)
            if "features" in comp:
                automation.comparison.features = [
                    FeatureRow(
                        feature=f.get("feature", ""), old_way=f.get("old_way", ""),
                        new_way=f.get("new_way", ""), why_it_matters=f.get("why_it_matters", ""),
                    )
                    for f in comp["features"]
                ]

        db.session.commit()
        return jsonify({"ok": True, "slug": automation.slug}), 200


def register_cli(app):
    @app.cli.command("init-db")
    def init_db():
        """Create all tables."""
        db.create_all()
        click.echo("Database tables created.")

    @app.cli.command("create-user")
    @click.argument("email")
    @click.argument("name")
    @click.option("--admin", is_flag=True, help="Make this user an admin (default: viewer).")
    def create_user(email, name, admin):
        """Create a login account. Prompts for the password (hidden input) -
        never pass it as a command-line argument."""
        password = click.prompt("Password", hide_input=True, confirmation_prompt=True)
        user = User(email=email.strip().lower(), name=name.strip(), role=Role.ADMIN if admin else Role.VIEWER)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"Created {user.role.value} user {user.email} (api_key: {user.api_key})")

    @app.cli.command("seed-demo")
    @click.argument("owner_email")
    def seed_demo(owner_email):
        """Seed the two real pilot automations found in ClickUp (Stage 0
        sales-forecast model, HR-бот) plus the stage-0-supplax skill entry,
        owned by an existing user. Run create-user first."""
        owner = User.query.filter_by(email=owner_email.strip().lower()).first()
        if not owner:
            click.echo(f"No user with email {owner_email} - run create-user first.")
            return

        def get_or_create_department(name, hue):
            dept = Department.query.filter_by(name=name).first()
            if not dept:
                dept = Department(name=name, hue=hue)
                db.session.add(dept)
            return dept

        sales = get_or_create_department("Sales", 275)
        hr = get_or_create_department("HR", 148)

        skill = Skill.query.filter_by(name="stage-0-supplax").first()
        if not skill:
            skill = Skill(
                name="stage-0-supplax",
                description="Бутстрапить новий проєкт повним набором документації й реальною структурою папок "
                             "за один прохід: README/ARCHITECTURE/ROI/PIPELINE, бібліотека довідників, і опційна "
                             "глибока перевірка документів кількома агентами.",
                when_to_use="На самому старті нового проєкту, або щоб перезапустити цикл перевірки документації "
                            "існуючого проєкту.",
            )
            db.session.add(skill)

        if not Automation.query.filter_by(slug="stage-0-forecast").first():
            forecast = Automation(
                slug="stage-0-forecast",
                name="Stage 0 — прогноз продажів",
                one_liner="Прогноз обсягу лідів, конверсії лід→угода та середнього чека по каналах.",
                status=Status.LIVE,
                owner=owner,
                departments=[sales],
                skills=[skill],
            )
            forecast.roi = ROIEntry(
                hypothesis="Точніший щомісячний прогноз DA$ дає керівництву час відреагувати на відхилення "
                            "раніше, ніж це видно по факту в кінці місяця.",
                metric_description="MAPE прогнозу DA$ проти факту, місяць до місяця.",
                confidence="measured",
                measured_value="9.8% MAPE",
            )
            db.session.add(forecast)

        if not Automation.query.filter_by(slug="hr-vacancy-bot").first():
            hr_bot = Automation(
                slug="hr-vacancy-bot",
                name="HR-бот моніторингу вакансій (@HRSupplaxBOT)",
                one_liner="Telegram-бот, який стежить за застряглими кандидатами й дедлайнами вакансій у PeopleForce.",
                status=Status.LIVE,
                owner=owner,
                departments=[hr],
                skills=[skill],
            )
            hr_bot.roi = ROIEntry(
                hypothesis="Рекрутери дізнаються про застряглого кандидата чи прострочену вакансію одразу, "
                            "а не під час ручної перевірки воронки раз на тиждень.",
                metric_description="Час між появою проблеми у воронці й реакцією рекрутера.",
                confidence="estimated",
            )
            db.session.add(hr_bot)

        db.session.commit()
        click.echo("Seeded departments, 2 pilot automations, and 1 skill entry.")


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
