from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from datetime import datetime, timedelta
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

# Configuration
app.config['SECRET_KEY'] = 'your-secret-key'  # Change this to a secure secret key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'jwt-secret-key'  # Change this to a secure JWT secret key
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=1)

# Initialize extensions
db = SQLAlchemy(app)
jwt = JWTManager(app)

# Create uploads directory if it doesn't exist
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    profile_picture = db.Column(db.String(200))
    bio = db.Column(db.Text)
    posts = db.relationship('Post', backref='author', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'created_at': self.created_at.isoformat(),
            'author': {
                'username': self.author.username
            }
        }

# Delete existing database and create new one
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'blog.db')
if os.path.exists(db_path):
    print("Removing existing database...")
    os.remove(db_path)

# Create database tables
with app.app_context():
    print("Creating database tables...")
    db.create_all()
    print("Database tables created successfully")

# Routes
@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        print("Registration data received:", data)

        if not data:
            return jsonify({'message': 'No data provided'}), 400

        # Validate required fields
        required_fields = ['username', 'email', 'password']
        for field in required_fields:
            if field not in data:
                return jsonify({'message': f'{field} is required'}), 400
            if not data[field]:
                return jsonify({'message': f'{field} cannot be empty'}), 400

        # Validate email format
        if '@' not in data['email'] or '.' not in data['email']:
            return jsonify({'message': 'Invalid email format'}), 400

        # Check if username or email already exists
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'message': 'Username already exists'}), 400
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'message': 'Email already exists'}), 400

        try:
            # Create new user
            new_user = User(
                username=data['username'],
                email=data['email']
            )
            new_user.set_password(data['password'])
            
            db.session.add(new_user)
            db.session.commit()
            print(f"User created successfully with ID: {new_user.id}")

            # Generate token
            access_token = create_access_token(identity=new_user.id)
            print(f"Generated token for user {new_user.id}")
            
            return jsonify({
                'message': 'User created successfully',
                'access_token': access_token,
                'user': {
                    'id': new_user.id,
                    'username': new_user.username,
                    'email': new_user.email
                }
            }), 201

        except Exception as db_error:
            db.session.rollback()
            print("Database error:", str(db_error))
            return jsonify({'message': 'Database error occurred'}), 500

    except Exception as e:
        print("Registration error:", str(e))
        return jsonify({'message': f'An error occurred during registration: {str(e)}'}), 500

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        print('Login attempt for username:', data.get('username'))
        
        if not data or not data.get('username') or not data.get('password'):
            return jsonify({'message': 'Missing username or password'}), 400

        user = User.query.filter_by(username=data['username']).first()
        print('Found user:', user.username if user else None)

        if not user or not user.check_password(data['password']):
            print('No user found with username:', data['username'])
            return jsonify({'message': 'Invalid username or password'}), 401

        access_token = create_access_token(identity=user.id)
        print('Generated token for user:', user.username)

        return jsonify({
            'access_token': access_token,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'profile_picture': user.profile_picture,
                'bio': user.bio
            }
        }), 200

    except Exception as e:
        print('Login error:', str(e))
        return jsonify({'message': 'An error occurred during login'}), 500

@app.route('/api/profile', methods=['GET'])
@jwt_required()
def get_profile():
    try:
        current_user_id = get_jwt_identity()
        print(f"Fetching profile for user ID: {current_user_id}")
        
        # List all users in the database
        all_users = User.query.all()
        print("All users in database:", [(u.id, u.username) for u in all_users])
        
        user = User.query.get(current_user_id)
        if not user:
            print(f"User not found with ID: {current_user_id}")
            return jsonify({'message': 'User not found'}), 404

        print(f"Found user: {user.username}")
        return jsonify({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'profile_picture': user.profile_picture,
            'bio': user.bio
        }), 200
    except Exception as e:
        print(f"Error fetching profile: {str(e)}")
        return jsonify({'message': f'Failed to fetch profile: {str(e)}'}), 500

@app.route('/api/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'message': 'User not found'}), 404

        # Handle profile picture upload
        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file and allowed_file(file.filename):
                # Delete old profile picture if exists
                if user.profile_picture:
                    old_file_path = os.path.join(app.config['UPLOAD_FOLDER'], user.profile_picture)
                    if os.path.exists(old_file_path):
                        os.remove(old_file_path)
                
                # Save new profile picture
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{timestamp}_{filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                user.profile_picture = filename

        # Update other profile fields
        if 'username' in request.form:
            new_username = request.form['username']
            if new_username != user.username:
                existing_user = User.query.filter_by(username=new_username).first()
                if existing_user and existing_user.id != user.id:
                    return jsonify({'message': 'Username already taken'}), 400
                user.username = new_username

        if 'email' in request.form:
            new_email = request.form['email']
            if new_email != user.email:
                existing_user = User.query.filter_by(email=new_email).first()
                if existing_user and existing_user.id != user.id:
                    return jsonify({'message': 'Email already taken'}), 400
                user.email = new_email

        if 'bio' in request.form:
            user.bio = request.form['bio']

        db.session.commit()

        return jsonify({
            'message': 'Profile updated successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'profile_picture': user.profile_picture,
                'bio': user.bio
            }
        }), 200

    except Exception as e:
        print('Profile update error:', str(e))
        return jsonify({'message': 'Failed to update profile'}), 500

@app.route('/api/posts', methods=['GET'])
def get_posts():
    try:
        posts = Post.query.options(db.joinedload(Post.author)).order_by(Post.created_at.desc()).all()
        return jsonify([post.to_dict() for post in posts])
    except Exception as e:
        print(f"Error fetching posts: {str(e)}")
        return jsonify({'message': 'Failed to fetch posts'}), 500

@app.route('/api/posts/user', methods=['GET'])
@jwt_required()
def get_user_posts():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'message': 'User not found'}), 404
            
        posts = Post.query.options(db.joinedload(Post.author)).filter_by(user_id=current_user_id).order_by(Post.created_at.desc()).all()
        return jsonify({'posts': [post.to_dict() for post in posts]})
    except Exception as e:
        print(f"Error fetching user posts: {str(e)}")
        return jsonify({'message': 'Failed to fetch user posts'}), 500

@app.route('/api/posts', methods=['POST'])
@jwt_required()
def create_post():
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data or not data.get('title') or not data.get('content'):
            return jsonify({'message': 'Title and content are required'}), 400
            
        new_post = Post(
            title=data['title'],
            content=data['content'],
            user_id=current_user_id
        )
        
        db.session.add(new_post)
        db.session.commit()
        
        # Reload the post with author relationship
        post = Post.query.options(db.joinedload(Post.author)).get(new_post.id)
        return jsonify(post.to_dict()), 201
    except Exception as e:
        print(f"Error creating post: {str(e)}")
        return jsonify({'message': 'Failed to create post'}), 500

@app.route('/uploads/<filename>')
def get_profile_picture(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True) 