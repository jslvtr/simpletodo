"""
Flask Documentation:     http://flask.pocoo.org/docs/
Jinja2 Documentation:    http://jinja.pocoo.org/2/documentation/
Werkzeug Documentation:  http://werkzeug.pocoo.org/documentation/

This file creates your application.
"""

from flask import Flask, render_template, request, redirect, url_for, jsonify, g
import jinja2
import os
import datetime
from src.app import Utils
from src.db.models import User, Group, Invite
from src.db.database import Database


app = Flask(__name__)
mongodb_uri = os.environ.get('MONGOLAB_URI')

###
# Routing for your application.
###

def log(to_write):
    print("{} {}".format(datetime.datetime.now().strftime("%b %d %H:%M:%S"),
                         to_write))


@app.before_request
def init_db():
    g.database = Database(mongodb_uri)


@app.route('/users/register', methods=['POST'])
def register_user():
    email = request.json.get('email')
    password = request.json.get('password')

    if not Utils.email_is_valid(email):
        response_data = Utils.create_response_error(
            'InvalidEmail',
            'This email is invalid',
            409
        )

        return jsonify(response_data)

    if not password:
        response_data = Utils.create_response_error(
            'InvalidPassword',
            'This password is invalid',
            409
        )

        return jsonify(response_data)

    try:
        user = User.register(email, password)
    except User.EmailAlreadyInUse:
        response_data = Utils.create_response_error(
            'UsedEmail',
            'This email is already in use',
            409
        )
        return jsonify(response_data)

    user.save()
    g.user = user

    # Create a Friends default group for the user
    # This group has the same id as the user id
    friends_group = Group.create(group_id=user.id,
                                 name="Friends",
                                 creator=user.id)

    friends_group.save()

    response_data = Utils.create_response_data(
        user.to_dict(),
        200
    )
    return jsonify(response_data), response_data['status_code']

@app.route('/users/login', methods=['POST'])
def login_user():
    email = request.json.get('email')
    password = request.json.get('password')

    if not (email or password):
        response_data = Utils.create_response_error(
            'EmptyEmailOrPassword',
            'The email or password is empty',
            409
        )
        return jsonify(response_data)

    try:
        user = User.login(email, password)
    except User.IncorrectEmailOrPassword:
        response_data = Utils.create_response_error(
            'IncorrectEmailOrPassword',
            'The email or password is incorrect',
            409
        )
        return jsonify(response_data)

    except User.UserNotExists:
        response_data = Utils.create_response_error(
            'UserNotExists',
            'The user was not found in the database!',
            409
        )
        return jsonify(response_data)

    g.user = user
    response_data = Utils.create_response_data(
        user.to_dict(),
        200
    )
    return jsonify(response_data)

@app.route('/groups/<group_id>/add', methods=['POST'])
@Utils.login_required
def add_member_to_group(group_id):
    log("Adding member to group...")
    user_id = request.json.get('user_id')
    user_email = request.json.get('email')

    log("Going to check e-mail and user id...")

    if user_email != "" and user_email is not None and Utils.email_is_valid(user_email):
            user = User.get_by_email(user_email)
            if user is not None:
                log("Email: Adding {} to group {}".format(user_email, group_id))
                Group.add_member(group_id, user.id)
            else:
                invite = Invite.create(user_email, g.user.id)
                invite.save()
                invite.send()
    else:
        if user_id != "" and user_id is not None:
            log("ID: Adding {} to group {}".format(user_id, group_id))
            Group.add_member(group_id, user_id)
        else:
            response_data = Utils.create_response_error(
                "InternalServerError",
                "The server could not fulfil your request",
                500
            )
            return jsonify(response_data), response_data['status_code']

    response_data = Utils.create_response_data(
        Group.get_by_id(group_id).to_dict(),
        200
    )
    return jsonify(response_data), response_data['status_code']


@app.route('/groups', methods=['POST'])
@Utils.login_required
def create_group():
    group_id = request.json.get('group_id')
    name = request.json.get('name')

    group = Group.create(group_id=group_id,
                         creator=g.user.id,
                         name=name)

    group.save()

    response_data = Utils.create_response_data(
        group.to_dict(),
        200
    )
    return jsonify(response_data), response_data['status_code']


@app.route('/confirm/<token>', methods=['GET'])
def confirm(token):
    log("Starting confirmation...")
    invite = Invite.get_by_token(token)
    log("Inviter ID: {}".format(invite.inviter_id))
    inviter = User.get_by_id(invite.inviter_id)
    log("Invited by: {}".format(inviter.email))

    try:
        return render_template('invite.html',
                               email=invite.email,
                               token=token,
                               inviter_email=inviter.email), 200
    except jinja2.TemplateNotFound:
        response_data = Utils.create_response_error(
            "InternalServerError",
            "The server could not display the template",
            500
        )
        return jsonify(response_data), response_data['status_code']


@app.route('/activate/<token>', methods=['POST'])
def activate_invite(token):
    password = request.form['password']
    Invite.activate(token, password)

    response_data = Utils.create_response_data(
        "Success!",
        200
    )
    return jsonify(response_data), response_data['status_code']



@app.errorhandler(400)
def bad_request(e):
    response_data = Utils.create_response_error(
        'BadRequest',
        'Bad request',
        400
    )
    return jsonify(response_data), response_data['status_code']


@app.errorhandler(403)
def forbidden(e):
    response_data = Utils.create_response_error(
        'Forbidden',
        'Forbidden',
        403
    )
    return jsonify(response_data), response_data['status_code']


@app.errorhandler(404)
def page_not_found(e):
    response_data = Utils.create_response_error(
        'PageNotFound',
        'Sorry, nothing at this URL',
        404
    )
    return jsonify(response_data), response_data['status_code']


@app.errorhandler(405)
def method_not_allowed(e):
    response_data = Utils.create_response_error(
        'MethodNotAllowed',
        'The method is not allowed for the requested URL',
        405
    )
    return jsonify(response_data), response_data['status_code']


@app.errorhandler(500)
def internal_server_error(e):
    response_data = Utils.create_response_error(
        'InternalServerError',
        'The server could not fulfill the request',
        500
    )
    return jsonify(response_data), response_data['status_code']


@app.route('/')
def home():
    """Render website's home page."""
    return render_template('home.html')


@app.route('/about/')
def about():
    """Render the website's about page."""
    return render_template('about.html')


###
# The functions below should be applicable to all Flask apps.
###

@app.route('/<file_name>.txt')
def send_text_file(file_name):
    """Send your static text file."""
    file_dot_text = file_name + '.txt'
    return app.send_static_file(file_dot_text)


@app.after_request
def add_header(response):
    """
    Add headers to both force latest IE rendering engine or Chrome Frame,
    and also to cache the rendered page for 10 minutes.
    """
    response.headers['X-UA-Compatible'] = 'IE=Edge,chrome=1'
    response.headers['Cache-Control'] = 'public, max-age=600'
    return response


@app.errorhandler(404)
def page_not_found(error):
    """Custom 404 page."""
    return render_template('404.html'), 404


if __name__ == '__main__':
    app.run(debug=True)
