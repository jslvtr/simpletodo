from functools import wraps
from flask import request, g, abort
from src.db.models import User

__author__ = 'jslvtr'


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        authorization = request.headers.get('Authorization')

        if not check_authorization(authorization):
            abort(403)

        return f(*args, **kwargs)

    return decorated


def check_authorization(authorization):
    if authorization is not None:
        try:
            prefix, access_key = authorization.split(' ')
        except ValueError:
            return False

        if prefix != '<DEFINE_PREFIX_HERE>':
            return False

        try:
            g.user = User.get_by_access_token(access_key)
        except User.DoesNotExist:
            return False

        return True


def create_response_data(data, status_code):
    return {
        'data': data,
        'status_code': status_code
    }


def create_response_error(error_name, error_message, status_code):
    return {
        'error': {
            'name': error_name,
            'message': error_message
        },
        'status_code': status_code
    }