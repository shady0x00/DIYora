from flask import Flask, render_template, request, url_for, redirect, flash, session, jsonify
from pymongo import MongoClient
from bson.objectid import ObjectId
from bcrypt import hashpw, gensalt, checkpw
import os
from werkzeug.utils import secure_filename
import random

app = Flask(__name__)

# MongoDB setup
client = MongoClient('localhost', 27017)
db = client.flask_database
users = db.users
admins = db.admins
posts = db.posts
help_messages = db.help_messages 

# Secret key for flash messages and sessions
app.secret_key = 'your_secret_key'

# File upload settings
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'avi', 'mov', 'mkv'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Helper function to check allowed file types
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# User registration
# User registration
from flask import Flask, render_template, request, url_for, redirect, flash, session, jsonify
from pymongo import MongoClient
from bson.objectid import ObjectId
from bcrypt import hashpw, gensalt, checkpw
import os
from werkzeug.utils import secure_filename
import random

app = Flask(__name__)

# MongoDB setup
client = MongoClient('localhost', 27017)
db = client.flask_database
users = db.users
admins = db.admins
posts = db.posts
help_messages = db.help_messages 
notifications = db.notifications 

# Secret key for flash messages and sessions
app.secret_key = 'your_secret_key'

# File upload settings
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'avi', 'mov', 'mkv'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Helper function to check allowed file types
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# User registration
@app.route("/signup", methods=('GET', 'POST'))
def user():
    if request.method == "POST":
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm = request.form['confirm']
        user_type = request.form['user_type']

        if password != confirm:
            flash("Passwords do not match. Please try again.")
            return redirect(url_for('user'))

        existing_user = users.find_one({'email': email}) or admins.find_one({'email': email})
        if existing_user:
            flash("User already exists with this email.")
            return redirect(url_for('user'))

        hashed_password = hashpw(password.encode('utf-8'), gensalt())

        user_data = {
            'username': username,
            'email': email,
            'password': hashed_password,
            'user_type': user_type
        }

        if user_type == 'creator':
            admins.insert_one(user_data)
            flash("Creator registration successful!")
        elif user_type == 'client':
            users.insert_one(user_data)
            flash("Client registration successful!")

        return redirect(url_for('login'))

    return render_template('user.html')

@app.route('/delete_post/<post_id>', methods=['DELETE'])
def delete_post(post_id):
    if 'admin_email' not in session:
        flash("Please log in.")
        return redirect(url_for('admin_login'))

    post = posts.find_one({"_id": ObjectId(post_id)})
    if post:
        # Delete the post from the database
        posts.delete_one({"_id": ObjectId(post_id)})
        flash("Post deleted successfully.")
        return jsonify({"success": True})
    else:
        flash("Post not found.")
        return jsonify({"success": False, "message": "Post not found."})



@app.route('/login')
def login():
    return render_template('login.html')

# User login
@app.route('/user_login', methods=["GET", "POST"])
def user_login():
    if request.method == "POST":
        email = request.form['email']
        password = request.form['password']

        existing_user = users.find_one({'email': email})
        if existing_user:
            hashed_password = existing_user['password']
            if checkpw(password.encode('utf-8'), hashed_password):
                session['user_email'] = email
                return redirect(url_for('user_dashboard'))
            else:
                flash("Incorrect password.")
                return redirect(url_for('user_login'))
        else:
            flash("User not found.")
            return redirect(url_for('user'))

    return render_template('user_login.html')

# User dashboard
@app.route('/user_dashboard', methods=["GET", "POST"])
def user_dashboard():
    if 'user_email' not in session:
        flash("Please log in.")
        return redirect(url_for('user_login'))

    search_query = request.args.get('search_query', '').lower()
    posts_list = list(posts.find())

    # Filter posts based on search query
    if search_query:
        posts_list = [
            post for post in posts_list
            if search_query in post.get('title', '').lower() or search_query in post.get('description', '').lower()
        ]

    random.shuffle(posts_list)
    return render_template('user_dashboard.html', posts=posts_list, search_query=search_query)

# Like a post
@app.route('/like/<post_id>', methods=["POST"])
def like_post(post_id):
    if 'user_email' not in session:
        return jsonify({"success": False, "message": "Login required."})

    user_email = session['user_email']
    post = posts.find_one({"_id": ObjectId(post_id)})

    if post:
        # Check if the current user has already liked the post
        if user_email in post.get("liked_by", []):
            posts.update_one({"_id": ObjectId(post_id)}, {"$pull": {"liked_by": user_email}, "$inc": {"likes_count": -1}})
            action = "unlike"
        else:
            posts.update_one({"_id": ObjectId(post_id)}, {"$push": {"liked_by": user_email}, "$inc": {"likes_count": 1}})
            action = "like"
        
        updated_post = posts.find_one({"_id": ObjectId(post_id)})
        
        # Get the owner of the post
        post_owner_email = post['admin_email']
        
        # Insert a notification for the post owner
        notifications.insert_one({
            "post_id": post_id,
            "post_title": post['title'],
            "message": f"{user_email} has {action}d your post.",
            "read": False,  # Not read by default
            "user_email": post_owner_email,
        })

        return jsonify({"success": True, "likes": updated_post.get("likes_count", 0), "action": action})

    return jsonify({"success": False, "message": "Post not found."})

# Comment on a post
@app.route('/comment/<post_id>', methods=["POST"])
def comment_post(post_id):
    if 'user_email' not in session:
        return jsonify({"success": False, "message": "Login required."})

    user_email = session['user_email']
    user = users.find_one({"email": user_email})
    if not user:
        return jsonify({"success": False, "message": "User not found."})

    comment = request.json.get("comment")
    if comment:
        username = user['username']
        new_comment = {"username": username, "text": comment}
        posts.update_one(
            {"_id": ObjectId(post_id)},
            {"$push": {"comments": new_comment}}
        )

        # Get the owner of the post
        post = posts.find_one({"_id": ObjectId(post_id)})
        post_owner_email = post['admin_email']
        
        # Insert a notification for the post owner
        notifications.insert_one({
            "post_id": post_id,
            "post_title": post['title'],
            "message": f"{user_email} commented on your post.",
            "read": False,  # Not read by default
            "user_email": post_owner_email,
        })

        return jsonify({"success": True, "comment": new_comment})

    return jsonify({"success": False, "message": "Comment cannot be empty."})

# Admin dashboard
@app.route('/admin_dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if 'admin_email' not in session:
        flash("Please log in.")
        return redirect(url_for('admin_login'))

    # Get notifications for the admin
    notifications_list = list(notifications.find({"user_email": session['admin_email'], "read": False}))

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        category = request.form['category']

        media_files = request.files.getlist('media_files')

        media_urls = []
        for file in media_files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                media_urls.append('/static/uploads/' + filename)
                
        posts.insert_one({
            'admin_email': session['admin_email'],
            'title': title,
            'description': description,
            'media_urls': media_urls,
            'likes_count': 0,
            'category': category,
            'liked_by': [],
            'comments': []
        })
        flash("Post added successfully.")
        return redirect(url_for('admin_dashboard'))

    posts_list = list(posts.find({'admin_email': session['admin_email']}))
    return render_template('admin_dashboard.html', posts=posts_list, notifications=notifications_list)

# Mark notifications as read
@app.route('/mark_notification_read/<notification_id>', methods=['POST'])
def mark_notification_read(notification_id):
    notifications.update_one(
        {"_id": ObjectId(notification_id)},
        {"$set": {"read": True}}
    )
    return jsonify({"success": True})

# Admin login
@app.route('/admin_login', methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form['email']
        password = request.form['password']

        existing_admin = admins.find_one({'email': email})
        if existing_admin:
            hashed_password = existing_admin['password']
            if checkpw(password.encode('utf-8'), hashed_password):
                session['admin_email'] = email
                return redirect(url_for('admin_dashboard'))
            else:
                flash("Incorrect password.")
                return redirect(url_for('admin_login'))
        else:
            flash("Admin not found.")
            return redirect(url_for('login'))

    return render_template('admin_login.html')

@app.route('/edit_post/<post_id>', methods=['GET', 'POST'])
def edit_post(post_id):
    if 'admin_email' not in session:
        flash("Please log in.")
        return redirect(url_for('admin_login'))

    post = posts.find_one({"_id": ObjectId(post_id)})
    if not post:
        flash("Post not found.")
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        category = request.form['category']

        # Handling new media files
        new_media_files = request.files.getlist('media_files')
        media_urls = post['media_urls']  # Retain existing media files

        # Add new media if valid
        for file in new_media_files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                # Append relative path
                media_urls.append('/static/uploads/' + filename)

        # Handling removal of media
        media_to_remove = request.form.getlist('remove_media')
        for media in media_to_remove:
            if media in media_urls:
                media_urls.remove(media)
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], media.lstrip('/static/uploads/')))

        # Update post in the database
        posts.update_one(
            {"_id": ObjectId(post_id)},
            {"$set": {
                "title": title,
                "description": description,
                "category": category,
                "media_urls": media_urls
            }}
        )
        flash("Post updated successfully.")
        return redirect(url_for('admin_dashboard'))

    return render_template('edit_post.html', post=post)

@app.route('/faq')
def faq():
    return render_template('FQS.html')

@app.route('/help', methods=['POST'])
def help():
    name = request.form.get('name')
    email = request.form.get('email')
    message = request.form.get('message')

    if name and email and message:
        help_messages.insert_one({
            'name': name,
            'email': email,
            'message': message
        })
        flash("Your message has been sent successfully!")
        return redirect(url_for('faq'))
    else:
        flash("Please fill out all fields.")
        return redirect(url_for('faq'))
    

# Profile Management route
@app.route('/profile_management', methods=['GET', 'POST'])
def profile_management():
    if 'user_email' not in session:
        flash("Please log in.")
        return redirect(url_for('user_login'))

    user_email = session['user_email']
    user = users.find_one({'email': user_email})

    if request.method == 'POST':
        # Handle username, bio, and profile picture updates
        username = request.form['username']
        bio = request.form['bio']

        # Handle Profile Picture upload
        profile_picture = request.files.get('profile_picture')
        if profile_picture and allowed_file(profile_picture.filename):
            filename = secure_filename(profile_picture.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            profile_picture.save(file_path)
            profile_picture_url = '/static/uploads/' + filename
        else:
            profile_picture_url = user.get('profile_picture', '')  # retain the old picture if not updated

        # Update the user details in the database
        users.update_one(
            {'email': user_email},
            {'$set': {
                'username': username,
                'bio': bio,
                'profile_picture': profile_picture_url
            }}
        )
        flash("Profile updated successfully.")
        return redirect(url_for('profile_management'))

    return render_template('profile_management.html', user=user)

@app.route('/logout')
def logout():
    session.pop('admin_email', None)

    session.pop('user_email', None)
    return redirect(url_for('login'))

@app.route('/')
def home():
    return render_template('home.html')

if __name__ == "__main__":
    app.run(debug=True)