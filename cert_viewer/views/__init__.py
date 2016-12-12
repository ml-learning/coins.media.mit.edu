import logging

from flask import request
from flask_themes2 import render_theme_template
from werkzeug.routing import BaseConverter

from cert_viewer import certificate_store_bridge
from cert_viewer import introduction_store_bridge
from cert_viewer import verifier

DEFAULT_THEME = 'default'
GUID_REGEX = '[0-9a-fA-F]{8}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{12}'


def update_app_config(app, config):
    app.config.update(
        SECRET_KEY=config.secret_key,
        ISSUER_NAME=config.issuer_name,
        SITE_DESCRIPTION=config.site_description,
        ISSUER_LOGO_PATH=config.issuer_logo_path,
        ISSUER_EMAIL=config.issuer_email,
        THEME=config.theme,
    )
    if config.recent_certids:
        recent_certs = str.split(config.recent_certids, ',')
    else:
        recent_certs = []
    app.config['RECENT_CERT_IDS'] = recent_certs


def render(template, **context):
    from cert_viewer import app
    return render_theme_template(app.config['THEME'], template, **context)


def configure_views(app, config):
    update_app_config(app, config)
    add_rules(app, config)


from flask.views import View


class GenericView(View):
    def __init__(self, template):
        self.template = template

        super(GenericView, self).__init__()

    def dispatch_request(self):
        return render(self.template)


def add_rules(app, config):
    from cert_viewer.views.award_view import AwardView
    from cert_viewer.views.json_award_view import JsonAwardView
    from cert_viewer.views.renderable_view import RenderableView
    from cert_viewer.views.issuer_view import IssuerView
    from cert_viewer.views.verify_view import VerifyView
    from cert_viewer.views.request_view import RequestView

    update_app_config(app, config)
    app.url_map.converters['regex'] = RegexConverter

    app.add_url_rule('/', view_func=GenericView.as_view('index', template='index.html'))

    app.add_url_rule(rule='/<regex("{}"):certificate_uid>'.format(GUID_REGEX), endpoint='award',
                     view_func=AwardView.as_view(name='award', template='award.html',
                                                 view=certificate_store_bridge.award))

    app.add_url_rule('/certificate/<regex("{}"):certificate_uid>'.format(GUID_REGEX),
                     view_func=JsonAwardView.as_view('certificate', view=certificate_store_bridge.get_award_json))

    app.add_url_rule('/verify/<regex("{}"):certificate_uid>'.format(GUID_REGEX),
                     view_func=VerifyView.as_view('verify', view=verifier.verify))

    app.add_url_rule('/intro/', view_func=introduction_store_bridge.insert_introduction, methods=['POST', ])
    app.add_url_rule('/request', view_func=RequestView.as_view(name='request'))
    app.add_url_rule('/faq', view_func=GenericView.as_view('faq', template='faq.html'))
    app.add_url_rule('/bitcoinkeys', view_func=GenericView.as_view('bitcoinkeys', template='bitcoinkeys.html'))

    app.register_error_handler(404, page_not_found)
    app.register_error_handler(500, internal_server_error)
    app.register_error_handler(Exception, unhandled_exception)


class RegexConverter(BaseConverter):
    def __init__(self, url_map, *items):
        super(RegexConverter, self).__init__(url_map)
        self.regex = items[0]


# Errors
def page_not_found(error):
    logging.error('Page not found: %s, error: ', request.path, error)
    return 'This page does not exist', 404


def internal_server_error(error):
    logging.error('Server Error: %s', error, exc_info=True)
    return 'Server error: {0}'.format(error), 500


def unhandled_exception(e):
    logging.exception('Unhandled Exception: %s', e, exc_info=True)
    return 'Unhandled exception: {0}'.format(e), 500
