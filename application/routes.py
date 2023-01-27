import os
import secrets
from PIL import Image
from flask import render_template, url_for, flash, redirect, request, abort
from application import app, db, bcrypt
from application.forms import RegistrationForm, LoginForm, UpdateAccountForm, PostForm, FollowForm , SearchForm
from application.models import User, Post, Comment, Like
from flask_login import login_user, current_user, logout_user, login_required


@app.route("/")
def index():
    return render_template('index.html')

@app.route("/home")
def home():
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.date_posted.desc()).paginate(page=page, per_page=5)
    return render_template('home.html', posts=posts)

@app.route("/signup", methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created!', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html', title='Register', form=form)


@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Login Unsuccessful. Incorrect email or password', 'danger')
    return render_template('login.html', title='Login', form=form)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.context_processor
def layout():
    form=SearchForm()
    return dict(form=form)

@app.route('/search', methods=["POST"])
def search():
    form = SearchForm()
    users  = User.query
    
    if form.validate_on_submit():
        user.searched = form.searched.data
        users = users.filter(User.username.like( '%' + user.searched + '%' ))
        users = users.order_by(User.username).all()
            
    return render_template("search.html", form = form, users=users, searched=user.searched)

def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)
    return picture_fn


@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('account.html', title='Account',
                           image_file=image_file, form=form)




def save_picture_post(form_picture):

    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/post_photos', picture_fn)
    form_picture.save(picture_path)

    output_size = (1080 , 566)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn

@app.route("/post/new", methods=['GET', 'POST'])
@login_required
def new_post():
    form = PostForm()
    if form.validate_on_submit():

        if form.picture.data:
            picture_file = save_picture_post(form.picture.data)
            current_user.image_file = picture_file

        post = Post(title=form.title.data, content=form.content.data, author=current_user, image_file=current_user.image_file )
        db.session.add(post)
        db.session.commit()
        flash('Your post has been created!', 'success')
        return redirect(url_for('home'))
    image_file = url_for('static', filename='post_photos/'+ current_user.image_file)
    
    return render_template('create_post.html', title='New Post',
                           form=form, legend='New Post', image_file=image_file)


@app.route("/post/<int:post_id>")
def post(post_id):

    post = Post.query.get_or_404(post_id)
    return render_template('post.html', title=post.title, post=post, legend='post' ,image_file=post.image_file)


@app.route("/post/<int:post_id>/update", methods=['GET', 'POST'])
@login_required
def update_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        db.session.commit()
        flash('Your post has been updated!', 'success')
        return redirect(url_for('post', post_id=post.id))
    elif request.method == 'GET':
        form.title.data = post.title
        form.content.data = post.content
    return render_template('create_post.html', title='Update Post', form=form, legend='Update Post')


@app.route("/post/<int:post_id>/delete", methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted!', 'success')
    return redirect(url_for('home'))


@app.route("/feed/<string:username>")
def user_posts(username):
    page = request.args.get('page', 1, type=int)
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(author=user)\
        .order_by(Post.date_posted.desc())\
        .paginate(page=page, per_page=5)
    return render_template('user.html', user=user, posts=posts)

@app.route("/user/<string:username>")
def user(username):
    page = request.args.get('page', 1, type=int)
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(author=user)\
         .order_by(Post.date_posted.desc())\
         .paginate(page=page, per_page=5)
    form = FollowForm()

    return render_template('user.html', user=user, form=form, posts=posts) 

@app.route('/follow/<username>', methods=['POST'])
@login_required
def follow(username):
    form = FollowForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=username).first()
        if user is None:
            flash('User {} not found.'.format(username))
            return redirect(url_for('home'))
        if user == current_user:
            flash('You cannot follow yourself!')
            return redirect(url_for('user', username=username, form=form))
        current_user.follow(user)
        db.session.commit()
        flash('You are following {}!'.format(username))
        return redirect(url_for('user', username=username, form=form))
    else:
        return redirect(url_for('home'))

@app.route('/unfollow/<username>', methods=['POST'])
@login_required
def unfollow(username):
    form = FollowForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=username).first()
        if user is None:
            flash('User {} not found.'.format(username))
            return redirect(url_for('home'))
        if user == current_user:
            flash('You cannot unfollow yourself!')
            return redirect(url_for('user', username=username, form=form))
        current_user.unfollow(user)
        db.session.commit()
        flash('You are not following {}.'.format(username))
        return redirect(url_for('user', username=username, form=form))
    else:
        return redirect(url_for('home'))

@app.route("/create_comment/<post_id>", methods=['POST'])
@login_required
def create_comment(post_id):
    text = request.form.get('text')
    if not text:
        flash('Comment cannot be empty.', category='error')
    else:
        post = Post.query.filter_by(id=post_id)
        if post:
            comment = Comment(
                text=text, author=current_user.id, post_id=post_id)
            db.session.add(comment)
            db.session.commit()
        else:
            flash('Post does not exist.', category='error')
    return redirect(url_for('home'))

@app.route("/delete_comment/<comment_id>")
@login_required
def delete_comment(comment_id):
    comment = Comment.query.filter_by(id=comment_id).first()
    if not comment:
        flash('Comment does not exist.', category='error')
    elif current_user.id != comment.author and current_user.id != comment.post.author:
        flash('You do not have permission to delete this comment.', category='error')
    else:
        db.session.delete(comment)
        db.session.commit()
    return redirect(url_for('home'))

@app.route("/like-post/<post_id>", methods=['GET'])
@login_required
def like(post_id):
    post = Post.query.filter_by(id=post_id).first()
    like = Like.query.filter_by(author=current_user.id, post_id=post_id).first()

    if not post:
        flash('Post does not exist.', category='error')
    elif like:
        db.session.delete(like)
        db.session.commit()
    else:
        like = Like(author=current_user.id, post_id=post_id)
        db.session.add(like)
        db.session.commit()
    
    return redirect (url_for('home'))