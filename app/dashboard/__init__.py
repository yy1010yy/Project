from flask import Blueprint


dashboard_bp = Blueprint(
    "dashboard", __name__, template_folder="../../templates",
    static_folder="../../static", static_url_path="/assets",
)

from app.utils.presentation import money, pretty_date, site_context, stay_nights

dashboard_bp.app_context_processor(site_context)
dashboard_bp.add_app_template_filter(money, "money")
dashboard_bp.add_app_template_filter(pretty_date, "pretty_date")
dashboard_bp.add_app_template_filter(stay_nights, "stay_nights")


def register_routes():
    # import route modules to bind endpoints to dashboard_bp
    from app.dashboard import routes


register_routes()
