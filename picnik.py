import os
from io import BytesIO
from flask import Flask, flash, render_template, session, escape, request, \
    redirect, url_for, send_from_directory, send_file, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin
from werkzeug.utils import secure_filename
from flaskext.mysql import MySQL
from base64 import b64encode, b64decode


app = Flask(__name__, static_url_path="/static")
mysql = MySQL()
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = ''
app.config['MYSQL_DATABASE_DB'] = 'picnik'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
mysql.init_app(app)
conn = mysql.connect()
cursor = conn.cursor()
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql://root:@localhost/picnik"
db = SQLAlchemy(app)



login_manager = LoginManager()
app.secret_key = os.urandom(16)
login_manager.init_app(app)

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(255))

    def __init__(self, username, password):
        self.username = username
        self.password = password

    def __repr__(self):
        return "<User %r>" % self.username


class Uploads(db.Model):
    image_id = db.Column(db.Integer, primary_key=True)
    image = db.Column(db.LargeBinary)
    filename = db.Column(db.String(300))
    uploader = db.Column(db.String(300))
    tags = db.Column(db.String(300))
    status = db.Column(db.String(300))


class Post():
    def __init__(self, image_id, image, filename, uploader, tags, status, created_at):
        self.image_id = image_id
        self.image = image
        self.filename = filename
        self.uploader = uploader
        self.tags = tags
        self.status = status
        self.created_at = created_at

class Person():
    def __init__(self, username):
        self.username = username


admin = User("admin", "admin")


# db.create_all()
# db.session.add(admin)
# db.session.commit()
# User.query.all()

@login_manager.user_loader
def load_user(user_id):
    return User.get(int(user_id))


@app.route("/")
def index():
    if 'username' in session:
        return "Logged in as %s" % escape(session["username"])
    else:
        return redirect(url_for("login"))

def runbasicquery(selectwhat='*', fromwhere="uploads"):
    '''

    I wrote this function after literally about 80 hours of working on this
    project. I think I should've written it... maybe 79 hours ago? Maybe even
    79.5 hours ago.

    :param selectwhat:
    :param fromwhere:
    :return:
    '''
    if selectwhat == '*' and fromwhere == "uploads":
        query = f"SELECT {selectwhat} FROM {fromwhere};"
        cursor.execute(query)
        results = cursor.fetchall()
        postlist = []
        for post in results:
            temporarypost = Post(post[0], post[1], post[2], post[3], post[4], post[5], post[6])
            postlist.append(temporarypost)

        return postlist
    else:
        print("This function hasn't yet been designed for your query.")


@app.route("/following", methods=["GET", "POST"])
def following():
    query = f"SELECT * FROM uploads WHERE uploader IN (" \
        f"SELECT following FROM follow WHERE follower = '{session['username']}');"
    cursor.execute(query)
    results = cursor.fetchall()
    postlist = []
    for post in results:
        temporarypost = Post(post[0], post[1], post[2], post[3], post[4], post[5], post[6])
        postlist.append(temporarypost)

    return render_template("following.html", postlist=postlist)

@app.route("/home")
def home():
    if "username" in session:
        allposts = runbasicquery()

        return render_template("home.html", postlist=allposts)
    else:
        return "Please log in."


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        received_username = request.form["username"]
        received_password = request.form["password"]

        login_query = "SELECT * FROM users;"
        cursor.execute(login_query)
        login_query_results = cursor.fetchall()
        userlist = []
        for user in login_query_results:
            userlist.append(user)

        for user in userlist:
            if user[1] == received_username and user[2] == received_password:
                session["username"] = received_username
                return redirect(url_for("home"))
        error = "Invalid credentials. Please try again."





        # if request.form['username'] != 'admin' or request.form['password'] != 'admin':
        #     error = 'Invalid Credentials. Please try again.'
        # else:
        #     session["username"] = request.form["username"]
        #     return redirect(url_for('home'))
    return render_template('login.html', error=error)

@app.route("/logout")
def logout():
    # remove the username from the session if it's there
    session.pop("username", None)
    return redirect(url_for("index"))


@app.route("/about")
def about():
    return render_template("about.html")


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# time to see our files!
@app.route('/profile')
def profile():
    sql_fetch_blob_query = f"SELECT * FROM uploads WHERE uploader = '{session['username']}';"
    cursor.execute(sql_fetch_blob_query)
    posts = cursor.fetchall()
    postslist = []
    for post in posts:
        newpost = Post(post[0], post[1], post[2], post[3], post[4], post[5], post[6])
        postslist.append(newpost)

    fetchfavorites = f"SELECT * FROM uploads WHERE image_id IN (" \
        f"SELECT image_id FROM favorites WHERE username = '{session['username']}'" \
        f");"
    cursor.execute(fetchfavorites)
    fetchfavoritesresults = cursor.fetchall()
    favoritelist = []
    for post in fetchfavoritesresults:
        newfav = Post(post[0], post[1], post[2], post[3], post[4], post[5], post[6])
        favoritelist.append(newfav)

    fetchfollowing = f"SELECT * FROM follow WHERE follower = '{session['username']}';"
    cursor.execute(fetchfollowing)
    fetchfollowingresults = cursor.fetchall()
    followlist = []
    for followee in fetchfollowingresults:
        followlist.append(followee[2])

    return render_template("profile.html", postslist=postslist, favorites=favoritelist, followlist=followlist)

# @app.route('/submit', methods=['GET', 'POST'])
# def upload_file():
#     if request.method == 'POST':
#         file = request.files['file']
#         tags = request.form['tags']
#         status = request.form['status']
#         newfile = Uploads(filename=file.filename, image=file.read(),
#                           uploader='admin', tags=tags, status=status)
#         db.session.add(newfile)
#         db.session.commit()
#
#         if file and allowed_file(file.filename):
#             filename = secure_filename(file.filename)
#             file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
#             return redirect(url_for('uploaded_file', filename=filename))
#
#         # return "Saved " + file.filename + " to the database."
#     return render_template("submit.html")

#####################################
### Deprecated file upload scheme ###
#####################################

@app.route('/submit', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        image = file.read()
        file.seek(0)
        ########################################################################
        ### It took me 8 and a half hours of debugging to realize that I     ###
        ### needed to do file.seek(0)                                        ###
        ### Eight. And a half. Hours. It is 2:20 AM right now.               ###
        ########################################################################

        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            tags = request.form['tags']
            status = request.form['status']
            newfile = Uploads(filename=file.filename, image=image,
                              uploader=session["username"], tags=tags, status=status)
            db.session.add(newfile)
            db.session.commit()

            return redirect(url_for('uploaded_file', filename=filename))
    return render_template("submit.html")

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method=='POST':
        searchquery = request.form['searchquery']

        if searchquery:
            sql_query = f"SELECT * FROM uploads WHERE tags LIKE '%{searchquery}%';"
            cursor.execute(sql_query)
            posts = cursor.fetchall()
            postslist = []
            for post in posts:
                newpost = Post(post[0], post[1], post[2], post[3], post[4], post[5], post[6])
                postslist.append(newpost)

            return render_template('searchresults.html', postslist=postslist)
    return render_template('search.html')

# @app.route("/downloads/<pic>")
# def getimage(pic): # Please. Please get the image.
#     return send_file(
#         BytesIO(image_binary),
#         mimetype="image/jpg",
#         as_attachment=True,
#         attachment_filename=f""
#     )

# @app.route("/downloads/<name>")
# def get_image(name):
#
#     print(len(image_data))
#     return Response(image_data, mimetype="image/jpg")



@app.route("/external_profile/<username>", methods=["GET", "POST"])
def external_profile(username):
    query = f"SELECT * FROM uploads WHERE uploader = '{username}'"
    cursor.execute(query)
    queryresults = cursor.fetchall()
    postlist = []
    for post in queryresults:
        the_post = Post(post[0], post[1], post[2], post[3], post[4], post[5], post[6])
        postlist.append(the_post)

    if request.method == "POST":
        if request.form["follow"] == "followed":
            followquery = f"INSERT INTO follow(follower, following) VALUES('{session['username']}', '{username}');"
            cursor.execute(followquery)


    return render_template("external_user.html", postlist=postlist, username=username)


@app.route("/recommended", methods=["GET", "POST"])
def recommended():
    # Step 1: Find the tags of your favorites
    fav_tags_query = f"SELECT * FROM uploads WHERE image_id IN (" \
        f"SELECT image_id FROM favorites WHERE username = '{session['username']}');"
    cursor.execute(fav_tags_query)
    fav_tags_query_results = cursor.fetchall()
    fav_tags_list = []
    for tags in fav_tags_query_results:
        newpost = Post(tags[0], tags[1], tags[2], tags[3], tags[4], tags[5], tags[6])
        fav_tags_list.append(newpost)

    # Step 2: Find posts which share the above tags
    share_tags_list = []
    for fav_tags in fav_tags_list:
        share_tags_query = f"SELECT * FROM uploads WHERE tags LIKE '%{fav_tags.tags}%';"
        cursor.execute(share_tags_query)
        share_tags_query_results = cursor.fetchall()
        for tags in share_tags_query_results:
            newpost = Post(tags[0], tags[1], tags[2], tags[3], tags[4], tags[5], tags[6])
            share_tags_list.append(newpost)

    # Step 3: Remove your own favorites from this new recommended list
    favorites_query = f"SELECT image_id FROM favorites;"
    cursor.execute(favorites_query)
    favorites_query_results = cursor.fetchall()
    favorites = []
    for fav in favorites_query_results:
        favorites.append(fav[0])

    # print("share_tags_list:", share_tags_list[0].image_id)
    print("Favorites:", favorites)

    myuploadsquery = f"SELECT image_id FROM uploads WHERE uploader = '{session['username']}';"
    cursor.execute(myuploadsquery)
    myuploadsqueryresults = cursor.fetchall()
    myuploads = []
    for uploads in myuploadsqueryresults:
        myuploads.append(uploads[0])


    finallist = []
    for x in share_tags_list:
        print(x.image_id)
        if x.image_id not in favorites and x.image_id not in myuploads:
            finallist.append(x)

    return render_template("recommended.html", postlist=finallist)


class Favorite():
    def __init__(self, image_id):
        self.image_id = image_id

@app.route("/hot", methods=["GET", "POST"])
def hot():
    query = f"SELECT * FROM favorites;"
    cursor.execute(query)
    queryresults = cursor.fetchall()
    favlist = []
    for fav in queryresults:
        favlist.append(str(fav[2]))

    query = f"SELECT * FROM uploads WHERE image_id IN {tuple(favlist)};"
    print(query)
    cursor.execute(query)
    queryresults = cursor.fetchall()
    hotlist = []
    for post in queryresults:
        newpost = Post(post[0], post[1], post[2], post[3], post[4], post[5], post[6])
        hotlist.append(newpost)

    return render_template("hot.html", hotlist=hotlist)


    # # Step 1: Calculate number of users in entire network
    # countquery = f"SELECT * FROM users;"
    # cursor.execute(countquery)
    # countqueryresults = cursor.fetchall()
    # count = 0
    # for user in countqueryresults:
    #     count += 1
    #
    # # Step 2: Find posts which are liked by more than 66% of the user base
    # postquery = f"SELECT * FROM favorites;"
    # cursor.execute(postquery)
    # postqueryresults = cursor.fetchall()
    # postslikes = {}
    # for favorite in postqueryresults:
    #     thefavorite = Favorite(favorite[2])
    #     if thefavorite.image_id not in postslikes:
    #         postslikes[thefavorite.image_id] = 1
    #     else:
    #         postslikes[thefavorite.image_id] += 1
    #
    # hotlist = {}
    # for key in postslikes:
    #     if postslikes[key] > 1: # count*0.66:
    #         hotlist[key] = postslikes[key]
    #
    # return render_template("hot.html", hotlist=hotlist)




@app.route("/post/<id>", methods=["GET", "POST"])
def post(id):
    query = f"SELECT * FROM uploads WHERE image_id = {id}"
    cursor.execute(query)
    queryresults = cursor.fetchall()
    postlist = []
    for post in queryresults:
        newpost = Post(image_id=post[0],
                       image=post[1],
                       filename=post[2],
                       uploader=post[3],
                       tags=post[4],
                       status=post[5],
                       created_at=post[6])
        postlist.append(newpost)

    post = postlist[0]

    script_directory = os.path.dirname(__file__)
    relpath = "static\\images"
    path = os.path.join(script_directory, relpath, post.filename)
    with open(path, "wb") as f:
        f.write(post.image)

    if request.method == "POST":
        if request.form["like"] == "liked":
            insertquery = f"INSERT INTO favorites(username, image_id) VALUES('{session['username']}', {post.image_id});"
            cursor.execute(insertquery)

    img_path = "../static/images/" + post.filename
    return render_template("post.html", path=img_path, post=post)


    # filename = post.filename
    # response = make_response(post.image)
    # response.headers["Content-Type"] = "jpg"
    # response.headers["Content-Disposition"] = "attachment; filename=\"%s\"" % filename
    # return response

    # post = postslist[0]
    # image = post.image
    #
    # print(type(image))
    #
    # file = open("image.jpg", "wb")
    # file.write(image.decode("base64"))
    # file.close()
    #
    # return render_template("post.html")

    # query = "SELECT image FROM uploads WHERE image_id = 15"
    # cursor.execute(query)
    # data = cursor.fetchall()
    # filelike = data[0][0]
    # imgdata = b64decode(filelike)
    # filename = "name.jpg"
    # with open(filename, "wb") as f:
    #     f.write(imgdata)
    #
    # return render_template("post.html")

    # query = "SELECT image FROM uploads WHERE image_id = 15"
    # cursor.execute(query)
    # posts = cursor.fetchall()
    # postslist = []
    # for post in posts:
    #     newpost = Post(post[0], post[1], post[2], post[3], post[4])
    #     postslist.append(newpost)




    # filelike = postslist[0].image
    # imgdata = b64decode(filelike)
    # filename = "name.jpg"
    # with open(filename, "wb") as f:
    #     f.write(imgdata)
    #
    # return render_template("post.html", filename=filename)



    # image_data = b64encode(cursor.fetchall()[0])
    # img = 'name.jpg'
    # with open(img, "wb") as f:
    #     f.write(image_data)








    # for post in postslist:
    #     encoded_image_blob = b64encode(postslist[0].image)
    #     image = encoded_image_blob.decode("base64")


################################################################################
### DEPRECATED. It took me so, so long to try and get this to work, until I  ###
### realized I needed to do something else entirely. Something far, far      ###
### easier. *sigh*                                                           ###
################################################################################
# @app.route('/searchresults', methods=['GET', 'POST'])
# def searchresults():
#     return render_template("searchresults.html")

# app.jinja_env.globals.update(p=post())


if __name__ == "__main__":
    app.run(debug=True)
