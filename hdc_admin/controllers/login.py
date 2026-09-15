from odoo.http import request
from odoo.addons.web.controllers.home import Home


class HdcHome(Home):

    def web_login(self, redirect=None, **kw):
        was_logged_in = bool(request.session.uid)
        response = super().web_login(redirect=redirect, **kw)

        if (
            request.httprequest.method == 'POST'
            and not was_logged_in
            and request.session.uid
        ):
            user = request.env['res.users'].sudo().browse(request.session.uid)
            forwarded_for = request.httprequest.headers.get('X-Forwarded-For')
            ip_address = (
                forwarded_for.split(',')[0].strip()
                if forwarded_for
                else request.httprequest.remote_addr
            )
            request.env['hdc.login.log'].sudo().create({
                'user_id': user.id,
                'login': user.login,
                'ip_address': ip_address,
                'user_agent': request.httprequest.headers.get('User-Agent'),
            })

        return response
