# FLASK Tutorial 1 -- We show the bare bones code to get an app up and running

# imports
import os  # os is used to get environment variables IP & PORT
from flask import Flask  # Flask is the web app that we will customize
from flask import render_template
from flask import request
from flask import redirect, url_for, session
from database import db
from models import Post as Post
from models import User as User
from models import Reply as Reply
from forms import RegisterForm, LoginForm, ReplyForm
import werkzeug
import bcrypt

# Path for uploaded files
UPLOAD_FOLDER = 'static/uploads/'

app = Flask(__name__)  # create an app
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///flask_qna_app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'SE3155'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB max limit
#  Bind SQLAlchemy db object to this Flask app
db.init_app(app)
# Setup models
with app.app_context():
    db.create_all()  # run under the app context


# @app.route is a decorator. It gives the function "index" special powers.
# In this case it makes it so anyone going to "your-url/" makes this function
# get called. What it returns is what is shown as the web page


@app.route('/')
@app.route('/index')
def index():
    if session.get('user'):
        return render_template("index.html", user=session['user'])
    return render_template("index.html")


@app.route('/profile')
def get_posts():
    if session.get('user'):
        my_posts = db.session.query(Post).filter_by(user_id=session['user_id']).all()
        user = db.session.query(User).filter_by(id=session['user_id']).one()
        return render_template('profile.html', posts=my_posts, user=user)
    else:
        return redirect(url_for('login'))


@app.route('/posts/<post_id>')
def get_post(post_id):
    if session.get('user'):
        a_post = db.session.query(Post).filter_by(id=post_id).one()
        form = ReplyForm()
        if request.method == 'GET':
            viewed_post = db.session.query(Post).filter_by(id=post_id).one()
            total_views = viewed_post.views
            total_views += 1
            viewed_post.views = total_views
            db.session.add(viewed_post)
            db.session.commit()
        return render_template("post.html", post=a_post, user=session['user'], form=form)
    else:
        return redirect(url_for('login'))


@app.route('/posts/new', methods=['GET', 'POST'])
def new_post():
    if session.get('user'):
        if request.method == 'POST':
            title = request.form['title']
            text = request.form['postText']
            from datetime import date
            today = date.today()
            today = today.strftime("%m-%d-%Y")
            new_record = Post(title, text, today, session['user_id'], report_total=0, views=0)
            db.session.add(new_record)
            db.session.commit()
            # TODO: LOGIC FOR UPLOADING AN IMAGE
            return redirect(url_for('get_posts'))
        else:
            return render_template("new.html", user=session['user'])
    else:
        return redirect(url_for('login'))


@app.route('/posts/edit/<post_id>', methods=['GET', 'POST'])
def update_post(post_id):
    if session.get('user'):
        if request.method == 'POST':
            title = request.form['title']
            text = request.form['postText']
            my_post = db.session.query(Post).filter_by(id=post_id).one()
            # update note data
            my_post.title = title
            my_post.text = text

            db.session.add(my_post)
            db.session.commit()
            return redirect(url_for('get_posts'))
        else:
            my_post = db.session.query(Post).filter_by(id=post_id).one()
            return render_template("new.html", post=my_post, user=session['user'])
    else:
        return redirect(url_for('login'))


@app.route('/posts/delete/<post_id>', methods=['POST'])
def delete_post(post_id):
    if session.get('user'):
        # retrieve note from database
        my_post = db.session.query(Post).filter_by(id=post_id).one()
        db.session.delete(my_post)
        db.session.commit()

        return redirect(url_for('get_posts'))
    else:
        return redirect(url_for('login'))


@app.route('/register', methods=['POST', 'GET'])
def register():
    form = RegisterForm()

    if request.method == 'POST' and form.validate_on_submit():
        # salt and hash password
        h_password = bcrypt.hashpw(
            request.form['password'].encode('utf-8'), bcrypt.gensalt())
        # get entered user data
        first_name = request.form['firstname']
        last_name = request.form['lastname']
        # create user model
        new_user = User(first_name, last_name, request.form['email'], h_password)
        # add user to database and commit
        db.session.add(new_user)
        db.session.commit()
        # save the user's name to the session
        session['user'] = first_name
        session['user_id'] = new_user.id  # access id value from user model of this newly added user
        # show user dashboard view
        return redirect(url_for('get_posts'))

    # something went wrong - display register view
    return render_template('register.html', form=form)


@app.route('/login', methods=['POST', 'GET'])
def login():
    login_form = LoginForm()
    # validate_on_submit only validates using POST
    if login_form.validate_on_submit():
        # we know user exists. We can use one()
        the_user = db.session.query(User).filter_by(email=request.form['email']).one()
        # user exists check password entered matches stored password
        if bcrypt.checkpw(request.form['password'].encode('utf-8'), the_user.password):
            # password match add user info to session
            session['user'] = the_user.first_name
            session['user_id'] = the_user.id
            # render view
            return redirect(url_for('get_posts'))

        # password check failed
        # set error message to alert user
        login_form.password.errors = ["Incorrect username or password."]
        return render_template("login.html", form=login_form)
    else:
        # form did not validate or GET request
        return render_template("login.html", form=login_form)


@app.route('/logout')
def logout():
    # check if a user is saved in session
    if session.get('user'):
        session.clear()

    return redirect(url_for('index'))


@app.route('/allPosts')
def all_posts():
    if session.get('user'):
        posts = db.session.query(Post).all()
        return render_template("allPosts.html", posts=posts, user=session['user'])
    return render_template("index.html")


@app.route('/posts/<post_id>/reply', methods=['POST'])
def reply(post_id):
    if session.get('user'):
        reply_form = ReplyForm()
        # validate_on_submit only validates using POST
        if reply_form.validate_on_submit():
            # get comment data
            reply_text = request.form['reply']
            new_record = Reply(reply_text, int(post_id), session['user_id'])
            db.session.add(new_record)
            db.session.commit()

        return redirect(url_for('get_post', post_id=post_id))
    else:
        return redirect(url_for('login'))


@app.route('/posts/<post_id>/like_unlike')
def like_action(post_id):
    if session.get('user'):
        post = db.session.query(Post).filter_by(id=post_id).one()
        user = db.session.query(User).filter_by(id=session['user_id']).one()
        form = ReplyForm()
        if request.method == 'GET':
            if user.has_disliked_post(post) > 0:
                user.undislike_post(post)
                user.like_post(post)
                db.session.commit()
            else:
                if user.has_liked_post(post) == 0:
                    user.like_post(post)
                    db.session.commit()
                elif user.has_liked_post(post) > 0:
                    user.unlike_post(post)
                    db.session.commit()

        return render_template("post.html", post=post, user=session['user'], form=form)
    else:
        return redirect(url_for('login'))


@app.route('/posts/<post_id>/dislike_undislike')
def dislike_action(post_id):
    if session.get('user'):
        post = db.session.query(Post).filter_by(id=post_id).one()
        user = db.session.query(User).filter_by(id=session['user_id']).one()
        form = ReplyForm()
        if request.method == 'GET':
            if user.has_liked_post(post) > 0:
                user.unlike_post(post)
                user.dislike_post(post)
                db.session.commit()
            else:
                if user.has_disliked_post(post) == 0:
                    user.dislike_post(post)
                    db.session.commit()
                elif user.has_disliked_post(post) > 0:
                    user.undislike_post(post)
                    db.session.commit()

        return render_template("post.html", post=post, user=session['user'], form=form)
    else:
        return redirect(url_for('login'))


@app.route('/index/<post_id>/report', methods=['GET', 'POST'])
def report(post_id):
    if session.get('user'):
        reported_post = db.session.query(Post).filter_by(id=post_id).one()
        report_total = reported_post.report_total
        # Increment the report total by 1everytime it is reported
        report_total = report_total + 1
        reported_post.report_total = report_total

        db.session.add(reported_post)
        db.session.commit()

        if report_total >= 5:
            db.session.delete(reported_post)
            db.session.commit()

            return redirect(url_for('index'))

        return render_template("report.html", post=reported_post, user=session['user'])
    else:
        return redirect(url_for('login'))


app.run(host=os.getenv('IP', '127.0.0.1'), port=int(os.getenv('PORT', 5000)), debug=True)

# To see the web page in your web browser, go to the url,
#   http://127.0.0.1:5000

# Note that we are running with "debug=True", so if you make changes and save it
# the server will automatically update. This is great for development but is a
# security risk for production.
