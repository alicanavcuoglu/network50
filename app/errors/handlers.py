from flask import render_template
from app import db
from app.errors import bp

@bp.app_errorhandler(401)
def unauthorized(error):
    return render_template("errors/401.html"), 401

@bp.app_errorhandler(404)
def not_found_error(error):
    return render_template("errors/404.html"), 404


@bp.app_errorhandler(413)
def too_large(error):
    return "File is too large", 413


@bp.app_errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template("errors/500.html"), 500
