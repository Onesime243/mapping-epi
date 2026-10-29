"""Version web de Mapping Épi (Flask).

- Connexion par identifiant + mot de passe (comptes créés par l'administrateur).
- Un agent saisit et télécharge SES cas ; un administrateur voit tous les cas
  et gère les comptes.
- Toutes les données restent dans le dossier local (core/paths.py), partagé
  avec l'application de bureau.
"""
from __future__ import annotations

import io
import logging
import os
import secrets
import time
from datetime import date, timedelta
from functools import wraps
from pathlib import Path

from flask import (Flask, Response, abort, flash, g, jsonify, redirect, render_template, request, send_file,
                   send_from_directory, session, url_for)

from config import theme
from core import pyramide, rules, schema, storage
from core.models import Action, Case, Event
from core.paths import data_dir
from core.users import Users, generate_password
from render import dashboard, gantt, html_renderer as H, map_view, network
from render.pptx_exporter import export_mapping_pptx
from web import render_client

log = logging.getLogger("mapping_epi.web")
ROOT = Path(__file__).resolve().parent.parent
VISUALS = {"mapping": "Mapping", "network": "Réseau de contacts", "route": "Carte du parcours",
           "gantt": "Frise temporelle", "dashboard": "Multi-cas"}


def _secret_key() -> bytes:
    f = data_dir() / "secret.key"
    if not f.exists():
        f.write_bytes(secrets.token_bytes(32))
        try:
            f.chmod(0o600)
        except OSError:
            pass
    return f.read_bytes()


def create_app(store: storage.Store | None = None) -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    public = os.environ.get("MAPPING_EPI_PUBLIC") == "1"      # serveur sur internet, derrière Caddy (HTTPS)
    app.config.update(SECRET_KEY=_secret_key(), SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
                      SESSION_COOKIE_SECURE=public, SESSION_COOKIE_NAME="mapping_epi",
                      PERMANENT_SESSION_LIFETIME=timedelta(hours=12), MAX_CONTENT_LENGTH=8 * 1024 * 1024,
                      TEMPLATES_AUTO_RELOAD=False)
    # derrière Caddy, waitress (serveur_web.py --public) restaure l'adresse réelle du client et le schéma https
    app.public = public
    app.store = store or storage.Store()
    app.users = Users(app.store)
    failures: dict = {}

    # ------------------------------------------------------------------ outils
    def current_user():
        u = session.get("user")
        if not u:
            return None
        user = app.users.get(u)
        if not user or not user.actif:
            session.clear()
            return None
        return user

    def login_required(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            if app.users.count() == 0:
                return redirect(url_for("setup"))
            g.user = current_user()
            if not g.user:
                if request.path.startswith("/api/"):
                    return jsonify(error="Session expirée : reconnectez-vous."), 401
                return redirect(url_for("login", next=request.path))
            return fn(*a, **kw)
        return wrapper

    def admin_required(fn):
        @wraps(fn)
        @login_required
        def wrapper(*a, **kw):
            if not g.user.is_admin:
                abort(403)
            return fn(*a, **kw)
        return wrapper

    def csrf_token() -> str:
        if "csrf" not in session:
            session["csrf"] = secrets.token_urlsafe(24)
        return session["csrf"]

    @app.before_request
    def check_csrf():
        if request.method in ("POST", "PUT", "DELETE"):
            sent = request.headers.get("X-CSRF") or request.form.get("csrf")
            if not sent or not secrets.compare_digest(sent, session.get("csrf", "")):
                abort(400, "Jeton de sécurité invalide : rechargez la page.")

    @app.context_processor
    def inject():
        return {"csrf": csrf_token(), "me": getattr(g, "user", None) or current_user(), "app_version": H.APP_VERSION}

    @app.after_request
    def headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("Referrer-Policy", "same-origin")
        resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        if app.public:
            resp.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
        return resp

    def get_case(cid: str) -> Case:
        c = app.store.load(cid)
        if not c:
            abort(404)
        if not g.user.is_admin and app.store.owner_of(cid) != g.user.username:
            abort(403)
        return c

    def visible_cases():
        return app.store.all_cases(None if g.user.is_admin else g.user.username)

    # -------------------------------------------------------------- comptes
    @app.route("/installation", methods=["GET", "POST"])
    def setup():
        if app.users.count() > 0:
            return redirect(url_for("login"))
        if app.public and os.environ.get("MAPPING_EPI_WEB_SETUP") != "1":
            return render_template("error.html", code=503,
                                   msg="Aucun compte administrateur. Sur le serveur, lancez : "
                                       "sudo mapping-epi creer-admin"), 503
        error = None
        if request.method == "POST":
            if request.form.get("password") != request.form.get("password2"):
                error = "Les deux mots de passe ne correspondent pas."
            else:
                try:
                    app.users.create(request.form.get("username", ""), request.form.get("password", ""),
                                     request.form.get("nom", ""), "admin")
                    flash("Compte administrateur créé. Connectez-vous.", "ok")
                    return redirect(url_for("login"))
                except ValueError as exc:
                    error = str(exc)
        return render_template("setup.html", error=error)

    @app.route("/connexion", methods=["GET", "POST"])
    def login():
        if app.users.count() == 0:
            return redirect(url_for("setup"))
        error = None
        ip = request.remote_addr or "?"
        if request.method == "POST":
            key = ip + "|" + request.form.get("username", "").strip().lower()
            n, until = max(failures.get(ip, (0, 0)), failures.get(key, (0, 0)))
            if until > time.time():
                error = "Trop de tentatives. Réessayez dans quelques minutes."
            else:
                user = app.users.authenticate(request.form.get("username", ""), request.form.get("password", ""))
                if user:
                    failures.pop(key, None)
                    session.clear()
                    session.permanent = True
                    session["user"] = user.username
                    csrf_token()
                    nxt = request.args.get("next", "")
                    return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//") else url_for("cases"))
                n += 1
                lock = time.time() + 300 if n >= 8 else 0
                failures[key] = (n, lock)
                ip_n = failures.get(ip, (0, 0))[0] + 1
                failures[ip] = (ip_n, time.time() + 900 if ip_n >= 30 else 0)
                if len(failures) > 5000:
                    failures.clear()
                log.warning("Échec de connexion pour %s depuis %s", request.form.get("username", "")[:40], ip)
                error = "Identifiant ou mot de passe incorrect."
        return render_template("login.html", error=error)

    @app.route("/deconnexion")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.route("/mon-compte", methods=["GET", "POST"])
    @login_required
    def account():
        msg = err = None
        if request.method == "POST":
            if not app.users.authenticate(g.user.username, request.form.get("old", "")):
                err = "Mot de passe actuel incorrect."
            elif request.form.get("new") != request.form.get("new2"):
                err = "Les deux nouveaux mots de passe ne correspondent pas."
            else:
                try:
                    app.users.set_password(g.user.username, request.form.get("new", ""))
                    msg = "Mot de passe modifié."
                except ValueError as exc:
                    err = str(exc)
        return render_template("account.html", msg=msg, err=err)

    @app.route("/utilisateurs", methods=["GET", "POST"])
    @admin_required
    def users_admin():
        new_pwd = None
        err = None
        if request.method == "POST":
            action = request.form.get("action")
            uname = request.form.get("username", "").strip().lower()
            try:
                if action == "create":
                    pwd = request.form.get("password") or generate_password()
                    app.users.create(uname, pwd, request.form.get("nom", ""), request.form.get("role", "agent"),
                                     request.form.get("zs", ""))
                    new_pwd = (uname, pwd)
                elif action == "reset":
                    pwd = generate_password()
                    app.users.set_password(uname, pwd)
                    new_pwd = (uname, pwd)
                elif action == "toggle":
                    u = app.users.get(uname)
                    if u.username == g.user.username:
                        raise ValueError("Vous ne pouvez pas désactiver votre propre compte.")
                    app.users.update(uname, actif=not u.actif)
                elif action == "role":
                    u = app.users.get(uname)
                    app.users.update(uname, role="agent" if u.is_admin else "admin")
            except ValueError as exc:
                err = str(exc)
        counts = {}
        for _cid, _t, _u, owner in app.store.list_full():
            counts[owner] = counts.get(owner, 0) + 1
        return render_template("users.html", users=app.users.list(), new_pwd=new_pwd, err=err, counts=counts,
                               suggested=generate_password())

    # ------------------------------------------------------------------ cas
    @app.route("/")
    @login_required
    def home():
        return redirect(url_for("cases"))

    @app.route("/cas")
    @login_required
    def cases():
        rows = app.store.list_full(None if g.user.is_admin else g.user.username)
        q = request.args.get("q", "").strip().lower()
        items = []
        for cid, titre, updated, owner in rows:
            if q and q not in (titre or "").lower() and q not in (owner or "").lower():
                continue
            items.append({"id": cid, "titre": titre, "updated": (updated or "")[:16].replace("T", " "), "owner": owner})
        return render_template("cases.html", items=items, q=q)

    @app.route("/cas/nouveau", methods=["POST"])
    @login_required
    def new_case():
        c = Case(investigateur=g.user.nom, zs=g.user.zs)
        p = pyramide.get().province_of(g.user.zs) if g.user.zs else None
        if p:
            c.province = p
        app.store.save(c, version=True, auteur=g.user.username, commentaire="Création (web)", owner=g.user.username)
        return redirect(url_for("editor", cid=c.id))

    @app.route("/cas/demo", methods=["POST"])
    @login_required
    def demo_case():
        c = storage.load_json(ROOT / "sample_data" / "cas_exemple_fictif.json")
        import uuid
        c.id = uuid.uuid4().hex
        app.store.save(c, version=True, auteur=g.user.username, commentaire="Exemple fictif", owner=g.user.username)
        return redirect(url_for("editor", cid=c.id))

    @app.route("/cas/importer", methods=["POST"])
    @login_required
    def import_case():
        f = request.files.get("fichier")
        if not f:
            abort(400)
        try:
            raw = f.read()
            if f.filename.lower().endswith(".xlsx"):
                tmp = data_dir() / "exports" / f"import_{secrets.token_hex(4)}.xlsx"
                tmp.write_bytes(raw)
                try:
                    c = storage.import_excel(tmp)
                except storage.ExcelImportError as exc:
                    c = exc.case
                tmp.unlink(missing_ok=True)
            else:
                c = Case.model_validate_json(raw)
        except Exception as exc:
            flash(f"Fichier illisible : {exc}", "err")
            return redirect(url_for("cases"))
        import uuid
        c.id = uuid.uuid4().hex
        app.store.save(c, version=True, auteur=g.user.username, commentaire=f"Import {f.filename}", owner=g.user.username)
        return redirect(url_for("editor", cid=c.id))

    @app.route("/cas/<cid>")
    @login_required
    def editor(cid):
        c = get_case(cid)
        return render_template("editor.html", case=c, visuals=VISUALS)

    @app.route("/cas/<cid>/supprimer", methods=["POST"])
    @login_required
    def delete_case(cid):
        get_case(cid)
        app.store.delete(cid)
        flash("Fiche supprimée (récupérable dans l'historique par un administrateur).", "ok")
        return redirect(url_for("cases"))

    # ------------------------------------------------------------------ API
    @app.route("/api/schema")
    @login_required
    def api_schema():
        def cols(cs):
            return [{"key": c.key, "label": c.label, "kind": c.kind, "choices": list(c.choices), "width": c.width,
                     "tip": c.tip, "complete": c.complete} for c in cs]
        return jsonify(
            tables={"events": cols(schema.EVENT_COLS), "places": cols(schema.PLACE_COLS),
                    "contacts": cols(schema.CONTACT_COLS), "ipc": cols(schema.IPC_COLS), "labs": cols(schema.LAB_COLS),
                    "actions": cols(schema.ACTION_COLS)},
            choices={"diseases": theme.DISEASES, "sexes": theme.SEXES, "status": theme.CASE_STATUS,
                     "issues": theme.ISSUE_CHOICES, "risks": theme.RISK_CHOICES, "symptoms": theme.SYMPTOMS,
                     "hemorrhagic": sorted(theme.HEMORRHAGIC)},
            annee_min=theme.ANNEE_MIN,
            defaults={"events": Event().model_dump(mode="json"), "actions": Action().model_dump(mode="json")})

    @app.route("/api/pyramide")
    @login_required
    def api_pyramide():
        resp = jsonify(pyramide.get().as_dict())
        resp.headers["Cache-Control"] = "private, max-age=3600"
        return resp

    @app.route("/api/cas/<cid>", methods=["GET", "PUT"])
    @login_required
    def api_case(cid):
        c = get_case(cid)
        if request.method == "GET":
            return jsonify(case=c.model_dump(mode="json"), controls=controls(c))
        try:
            data = request.get_json(force=True)
            data["id"] = cid
            new = Case.model_validate(data)
        except Exception as exc:
            return jsonify(error=f"Données invalides : {exc}"), 400
        pyr = pyramide.get()
        new.province, new.zs, new.aire_sante = pyr.canonical(new.province, new.zs, new.aire_sante)
        pyr.remember(new.province, new.zs, new.aire_sante)
        version = request.args.get("version") == "1"
        app.store.save(new, version=version, auteur=g.user.username,
                       commentaire=request.args.get("commentaire", "")[:200])
        return jsonify(ok=True, saved_at=new.modifie_le.isoformat(), controls=controls(new),
                       case=new.model_dump(mode="json") if request.args.get("echo") else None)

    def controls(c: Case) -> dict:
        w = rules.windows(c)
        p = rules.disease_params(c.maladie)
        score, missing = rules.completeness(c)
        cs = rules.contact_summary(c)
        grisk, why = rules.global_risk(c)
        d = rules.lab_delay_hours(c)
        return {
            "score": score, "missing": missing, "risk": grisk, "risk_why": why, "risk_color": theme.risk_color(grisk),
            "exposure": [w.exposition[0].isoformat(), w.exposition[1].isoformat()] if w.exposition else None,
            "contagious": [w.contagiosite[0].isoformat(), w.contagiosite[1].isoformat()] if w.contagiosite else None,
            "incubation": [p["incubation_min"], p["incubation_max"]], "followup": p["suivi_contacts"],
            "contacts": {"phrase": cs.phrase, "total": cs.total_connu, "suivis": cs.suivis, "pct": cs.pct_suivi},
            "lab_delay": d, "lab_threshold": p["labo_delai_alerte_h"],
            "issues": [{"level": i.niveau, "msg": i.message} for i in rules.check_consistency(c)],
            "suggestions": [{"texte": s.texte, "priorite": s.priorite, "raison": s.raison}
                            for s in rules.suggest_actions(c)],
            "computed": {
                "events": [dict(zip(("lvl", "why"), rules.suggest_event_risk(e, c, w))) |
                           {"color": theme.risk_color(rules.suggest_event_risk(e, c, w)[0])} for e in c.events],
                "places": [rules.suggest_place_risk(pl.model_copy(update={"risque": ""}), c) for pl in c.places],
                "contacts": [(lambda e: e.strftime("%d/%m/%Y") if e else "?")(rules.contact_followup_end(gr, c))
                             for gr in c.contacts],
                "labs": [f"{(lb.resultat_le - lb.prelevement).total_seconds() / 3600:.0f} h"
                         if lb.prelevement and lb.resultat_le else "?" for lb in c.labs],
            },
        }

    @app.route("/api/cas/<cid>/places-depuis-chronologie", methods=["POST"])
    @login_required
    def api_prefill(cid):
        c = get_case(cid)
        return jsonify(places=[p.model_dump(mode="json") for p in rules.places_from_events(c)])

    @app.route("/api/cas/<cid>/trous", methods=["POST"])
    @login_required
    def api_gaps(cid):
        c = get_case(cid)
        return jsonify(events=[Event(date_debut=a, date_fin=b, type="Période à documenter", titre="Période à documenter",
                                     description="Activités et contacts à reconstituer", risque="Inconnu",
                                     lieu="?").model_dump(mode="json") for a, b in rules.coverage_gaps(c)])

    @app.route("/api/cas/<cid>/versions")
    @login_required
    def api_versions(cid):
        get_case(cid)
        return jsonify([{"vid": v, "ts": ts, "auteur": a, "commentaire": com}
                        for v, ts, a, com in app.store.versions(cid)])

    # -------------------------------------------------------------- visuels
    def visual_html(c: Case, key: str) -> str:
        if key == "mapping":
            return H.render_mapping_html(c, assets="/assets/")
        if key == "network":
            return H.render_svg_page(network.render_svg(c), "Réseau", assets="/assets/")
        if key == "route":
            return H.render_svg_page(map_view.render_svg(c), "Parcours", assets="/assets/")
        if key == "gantt":
            return H.render_svg_page(gantt.render_svg(c), "Frise", assets="/assets/")
        if key == "dashboard":
            return H.render_svg_page(dashboard.render_svg(visible_cases(), c.zs), "Multi-cas", assets="/assets/")
        abort(404)

    @app.route("/cas/<cid>/apercu/<key>")
    @login_required
    def preview(cid, key):
        c = get_case(cid)
        resp = Response(visual_html(c, key), mimetype="text/html")
        resp.headers["Cache-Control"] = "no-store"
        return resp

    @app.route("/assets/<path:p>")
    def assets(p):
        return send_from_directory(str(H.ASSETS), p, max_age=86400)

    @app.route("/cas/<cid>/telecharger/<fmt>")
    @login_required
    def download(cid, fmt):
        c = get_case(cid)
        key = request.args.get("visuel", "mapping")
        if key not in VISUALS:
            abort(404)
        name = _filename(c, key, fmt)
        if fmt == "json":
            return send_file(io.BytesIO(c.model_dump_json(indent=2).encode("utf-8")), as_attachment=True,
                             download_name=name, mimetype="application/json")
        if fmt == "xlsx":
            out = data_dir() / "exports" / f"{secrets.token_hex(6)}.xlsx"
            storage.export_excel(c, out)
            return _send_and_delete(out, name)
        if fmt == "svg":
            if key == "mapping":
                svg = H.html_to_svg_wrapper(H.render_mapping_html(c))
            elif key == "dashboard":
                svg = dashboard.render_svg(visible_cases(), c.zs)
            else:
                svg = {"network": network, "route": map_view, "gantt": gantt}[key].render_svg(c)
            return send_file(io.BytesIO(svg.encode("utf-8")), as_attachment=True, download_name=name,
                             mimetype="image/svg+xml")
        if fmt == "pptx":
            out = data_dir() / "exports" / f"{secrets.token_hex(6)}.pptx"
            export_mapping_pptx(c, out)
            return _send_and_delete(out, name)
        if fmt in ("png", "png4k", "pdf", "pdfa4", "rapport-pdf", "rapport-pptx"):
            others = [x.model_dump(mode="json") for x in visible_cases()] if key == "dashboard" else []
            out = data_dir() / "exports" / f"{secrets.token_hex(6)}{Path(name).suffix}"
            ok, msg = render_client.render(c.model_dump(mode="json"), key, fmt, out, others)
            if not ok:
                return Response(f"Export impossible sur ce serveur : {msg}\n\nAstuce : utilisez « Imprimer → "
                                "Enregistrer en PDF » depuis l'aperçu, ou les formats SVG / PowerPoint.",
                                status=503, mimetype="text/plain; charset=utf-8")
            return _send_and_delete(out, name)
        abort(404)

    def _send_and_delete(path: Path, name: str):
        data = path.read_bytes()
        try:
            path.unlink()
        except OSError:
            pass
        return send_file(io.BytesIO(data), as_attachment=True, download_name=name)

    @app.route("/modele-excel")
    @login_required
    def excel_model():
        out = data_dir() / "exports" / f"{secrets.token_hex(6)}.xlsx"
        storage.export_excel_template(out)
        return _send_and_delete(out, "Modele_Mapping_ZS_vierge.xlsx")

    @app.route("/sante")
    def health():
        return jsonify(ok=True, version=H.APP_VERSION)

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("error.html", code=403, msg="Accès refusé : cette fiche ne vous appartient pas."), 403

    @app.errorhandler(404)
    def notfound(e):
        return render_template("error.html", code=404, msg="Page ou fiche introuvable."), 404

    return app


def _filename(c: Case, key: str, fmt: str) -> str:
    import re

    def slug(s):
        return re.sub(r"[^\w\-]+", "_", s or "", flags=re.UNICODE).strip("_") or "x"
    base = {"mapping": "Mapping", "network": "Reseau", "route": "Parcours", "gantt": "Frise", "dashboard": "MultiCas"}[key]
    if fmt.startswith("rapport"):
        base = "Rapport"
    ext = {"png": "png", "png4k": "png", "pdf": "pdf", "pdfa4": "pdf", "svg": "svg", "pptx": "pptx", "json": "json",
           "xlsx": "xlsx", "rapport-pdf": "pdf", "rapport-pptx": "pptx"}[fmt]
    suffix = "_4K" if fmt == "png4k" else ("_A4" if fmt == "pdfa4" else "")
    return f"{base}_{slug(c.maladie)}_{slug(c.zs or 'ZS')}_Cas{c.rang or ''}_{date.today():%Y%m%d}{suffix}.{ext}"
