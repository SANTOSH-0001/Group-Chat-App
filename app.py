from flask_socketio import SocketIO, send, join_room, leave_room, emit
from flask import Flask, render_template, request, redirect, url_for
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import logging
logging.getLogger('engineio').setLevel(logging.ERROR)
logging.getLogger('socketio').setLevel(logging.ERROR)


from models import db, User, Message, Group, GroupMembers
import config

app = Flask(__name__)
app.config.from_object('config')

db.init_app(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

login_manager = LoginManager(app)
login_manager.login_view = 'signin'

# ---------------- User Loader ---------------- #
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---------------- ROUTES ---------------- #
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method=='POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        if User.query.filter((User.username==username)|(User.email==email)).first():
            return "Username or Email already exists"
        hashed = generate_password_hash(password)
        new_user = User(username=username,email=email,password=hashed)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('signin'))
    return render_template('signup.html')

@app.route('/signin', methods=['GET','POST'])
def signin():
    if request.method=='POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password,password):
            if user.banned:
                return "You are banned!"
            login_user(user)
            user.online = True
            db.session.commit()
            return redirect(url_for('chat_rooms'))
        return "Invalid credentials"
    return render_template('signin.html')

@app.route('/logout')
@login_required
def logout():
    current_user.online = False
    db.session.commit()
    logout_user()
    return redirect(url_for('signin'))

@app.route('/admin')
@login_required
def admin_panel():
    if current_user.role != 'admin':
        return "Unauthorized"
    users = User.query.all()
    return render_template('admin.html', users=users)

@app.route('/ban_user/<int:user_id>')
@login_required
def ban_user(user_id):
    if current_user.role != 'admin':
        return "Unauthorized"
    user = User.query.get(user_id)
    user.banned = True
    db.session.commit()
    return redirect(url_for('admin_panel'))

@app.route('/unban_user/<int:user_id>')
@login_required
def unban_user(user_id):
    if current_user.role != 'admin':
        return "Unauthorized"
    user = User.query.get(user_id)
    user.banned = False
    db.session.commit()
    return redirect(url_for('admin_panel'))

@app.route('/chat_rooms')
@login_required
def chat_rooms():
    rooms = ["General","Gaming","Tech","Random"]
    users = User.query.filter(User.id != current_user.id).all()
    return render_template('rooms.html', rooms=rooms, users=users)

@app.route('/chat/<room>')
@login_required
def chat(room):
    messages = Message.query.filter_by(room=room).order_by(Message.timestamp).all()
    return render_template('chat.html', username=current_user.username, room=room, messages=messages)

@app.route('/private/<int:user_id>')
@login_required
def private_chat(user_id):
    user = User.query.get(user_id)
    messages = Message.query.filter(
        ((Message.sender_id==current_user.id)&(Message.receiver_id==user.id))|
        ((Message.sender_id==user.id)&(Message.receiver_id==current_user.id))
    ).order_by(Message.timestamp).all()
    return render_template('private_chat.html', username=current_user.username, peer=user.username, messages=messages)

# ---------------- Private Group Chat ---------------- #
from models import Group, GroupMembers   # 👈 You must add these models

# @app.route('/create_group', methods=['POST','GET'])
# @login_required
# def create_group():
#     name = request.form['name']
#     member_ids = request.form.getlist('members')  # selected checkboxes

#     group = Group(name=name)
#     db.session.add(group)
#     db.session.commit()

#     # Add creator + members
#     db.session.add(GroupMembers(group_id=group.id, user_id=current_user.id))
#     for uid in member_ids:
#         db.session.add(GroupMembers(group_id=group.id, user_id=int(uid)))

#     db.session.commit()
#     return redirect(url_for('private_group_chat', group_id=group.id))

# @app.route('/create_group', methods=['GET','POST'])
# @login_required
# def create_group():
#     if request.method == 'POST':
#         name = request.form['name']
#         member_ids = request.form.getlist('members')

#         group = Group(name=name)
#         db.session.add(group)
#         db.session.commit()

#         # Add creator + members
#         db.session.add(GroupMembers(group_id=group.id, user_id=current_user.id))
#         for uid in member_ids:
#             db.session.add(GroupMembers(group_id=group.id, user_id=int(uid)))
#         db.session.commit()

#         return redirect(url_for('private_group_chat', group_id=group.id))

#     # GET request: show form
#     users = User.query.filter(User.id != current_user.id).all()
#     return render_template('create_group.html', users=users)
@app.route('/create_group', methods=['GET','POST'])
@login_required
def create_group():
    if request.method == 'POST':
        name = request.form['name']
        member_ids = request.form.getlist('members')
        initial_member = request.form.get('initial_member')
        if initial_member:
            member_ids.append(initial_member)

        group = Group(name=name)
        db.session.add(group)
        db.session.commit()

        # Add creator + members
        db.session.add(GroupMembers(group_id=group.id, user_id=current_user.id))
        for uid in member_ids:
            db.session.add(GroupMembers(group_id=group.id, user_id=int(uid)))
        db.session.commit()

        return redirect(url_for('private_group_chat', group_id=group.id))

    # GET request: show form
    users = User.query.filter(User.id != current_user.id).all()
    return render_template('create_group.html', users=users)


@app.route('/private_group/<int:group_id>')
@login_required
def private_group_chat(group_id):
    group = Group.query.get(group_id)
    messages = Message.query.filter_by(group_id=group_id).order_by(Message.timestamp).all()
    return render_template('private_group.html',
                           group=group,
                           username=current_user.username,
                           messages=messages)

# ---------------- SOCKET.IO EVENTS ---------------- #
@socketio.on('join')
def handle_join(data):
    room = data['room']
    join_room(room)
    send({'msg': f"{data['username']} joined {room}"}, to=room)

@socketio.on('room_message')
def handle_room_message(data):
    room = data['room']
    msg = data['msg']
    send({'msg': f"{data['username']}: {msg}"}, to=room)
    user = User.query.filter_by(username=data['username']).first()
    new_msg = Message(sender_id=user.id, room=room, content=msg)
    db.session.add(new_msg)
    db.session.commit()

@socketio.on('private_message')
def handle_private_message(data):
    sender = User.query.filter_by(username=data['username']).first()
    receiver = User.query.filter_by(username=data['peer']).first()
    msg = data['msg']
    send({'msg': f"{data['username']}: {msg}"}, to=f"private_{receiver.id}")
    new_msg = Message(sender_id=sender.id, receiver_id=receiver.id, content=msg)
    db.session.add(new_msg)
    db.session.commit()

@socketio.on('join_private')
def handle_join_private(data):
    join_room(f"private_{data['peer_id']}")

# ----- Private Group Events ----- #
@socketio.on('join_private_group')
def handle_join_private_group(data):
    group_id = data['group_id']
    join_room(f"group_{group_id}")
    send({'msg': f"{data['username']} joined the group"}, to=f"group_{group_id}")

@socketio.on('private_group_message')
def handle_private_group_message(data):
    group_id = data['group_id']
    msg = data['msg']
    sender = User.query.filter_by(username=data['username']).first()

    new_msg = Message(sender_id=sender.id, group_id=group_id, content=msg)
    db.session.add(new_msg)
    db.session.commit()

    send({'msg': f"{data['username']}: {msg}"}, to=f"group_{group_id}")

# ---------------- Typing Indicators ---------------- #
@socketio.on('typing')
def handle_typing(data):
    emit('typing', {'username': data['username']}, to=data['room'], include_self=False)

@socketio.on('stop_typing')
def handle_stop_typing(data):
    emit('stop_typing', {'username': data['username']}, to=data['room'], include_self=False)

# ---------------- Read Receipts ---------------- #
@socketio.on('message_read')
def handle_message_read(data):
    message_id = data.get('message_id')
    msg = Message.query.get(message_id)
    if msg:
        msg.read = True
        db.session.commit()
        sender = User.query.get(msg.sender_id)
        emit('message_read_receipt', {'message_id': message_id, 'reader': current_user.username},
             to=f"private_{sender.id}" if msg.receiver_id else msg.room)

# ------------------ RUN ------------------ #
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, debug=True)
