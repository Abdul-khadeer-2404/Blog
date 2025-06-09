from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, verify_jwt_in_request
from datetime import datetime, timedelta
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

# Configure database
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'blog.db')
print(f"\n=== Database Configuration ===")
print(f"Database path: {db_path}")

# Ensure the directory exists
os.makedirs(os.path.dirname(db_path), exist_ok=True)

# Configure SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configure JWT
app.config['JWT_SECRET_KEY'] = 'your-secret-key'  # Change this in production
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=1)
app.config['JWT_TOKEN_LOCATION'] = ['headers']
app.config['JWT_HEADER_NAME'] = 'Authorization'
app.config['JWT_HEADER_TYPE'] = 'Bearer'

# Initialize extensions
db = SQLAlchemy(app)
jwt = JWTManager(app)

# Configure upload folder
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Configure allowed file extensions
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
        print(f"\n=== Setting Password for {self.username} ===")
        try:
            self.password_hash = generate_password_hash(password)
            print("Password hash generated successfully")
            print(f"Hash length: {len(self.password_hash)}")
            print("=== Password Set Successfully ===\n")
        except Exception as e:
            print(f"Error setting password: {str(e)}")
            raise

    def check_password(self, password):
        print(f"\n=== Checking Password for {self.username} ===")
        try:
            result = check_password_hash(self.password_hash, password)
            print(f"Password check result: {result}")
            print("=== Password Check Complete ===\n")
            return result
        except Exception as e:
            print(f"Error checking password: {str(e)}")
            raise

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def to_dict(self, current_user_id=None):
        like_count = len(self.likes)
        is_liked = False
        
        if current_user_id:
            is_liked = any(like.user_id == current_user_id for like in self.likes)
        
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'created_at': self.created_at.isoformat(),
            'author': {
                'username': self.author.username if self.author else 'Unknown',
                'profile_picture': self.author.profile_picture if self.author else None
            },
            'like_count': like_count,
            'is_liked': is_liked
        }

class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Ensure a user can only like a post once
    __table_args__ = (db.UniqueConstraint('user_id', 'post_id', name='unique_user_post_like'),)
    
    user = db.relationship('User', backref='likes')
    post = db.relationship('Post', backref='likes')

# Create database tables if they don't exist
with app.app_context():
    print("\n=== Database Initialization ===")
    try:
        # Check if database file exists
        if os.path.exists(db_path):
            print(f"Database file exists at: {db_path}")
            # Check file permissions
            if os.access(db_path, os.W_OK):
                print("Database file is writable")
            else:
                print("WARNING: Database file is not writable!")
        else:
            print("Database file does not exist, will be created")
            # Ensure directory is writable
            if os.access(os.path.dirname(db_path), os.W_OK):
                print("Database directory is writable")
            else:
                print("WARNING: Database directory is not writable!")
        
        # Create tables
        db.create_all()
        print("Database tables created successfully")
        
        # Verify tables were created
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"Available tables: {tables}")
        
        # Check if we have any users
        user_count = User.query.count()
        print(f"Current number of users in database: {user_count}")
        print("=== Database Initialization Complete ===\n")
    except Exception as e:
        print(f"Error during database initialization: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        raise

# Routes
@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        print("\n=== Registration Attempt ===")
        print(f"Received registration data: {data}")

        if not data:
            print("No data provided in request")
            return jsonify({'message': 'No data provided'}), 400

        # Validate required fields
        required_fields = ['username', 'email', 'password']
        for field in required_fields:
            if field not in data:
                print(f"Missing required field: {field}")
                return jsonify({'message': f'{field} is required'}), 400
            if not data[field]:
                print(f"Empty value for field: {field}")
                return jsonify({'message': f'{field} cannot be empty'}), 400

        # Validate email format
        if '@' not in data['email'] or '.' not in data['email']:
            print(f"Invalid email format: {data['email']}")
            return jsonify({'message': 'Invalid email format'}), 400

        try:
            # Check if username or email already exists
            existing_user = User.query.filter_by(username=data['username']).first()
            if existing_user:
                print(f"Username already exists: {data['username']}")
                return jsonify({'message': 'Username already exists'}), 400
                
            existing_email = User.query.filter_by(email=data['email']).first()
            if existing_email:
                print(f"Email already exists: {data['email']}")
                return jsonify({'message': 'Email already exists'}), 400

            # Create new user
            new_user = User(
                username=data['username'],
                email=data['email']
            )
            print(f"Creating new user: {new_user.username}")
            
            # Set password
            try:
                new_user.set_password(data['password'])
                print("Password set successfully")
            except Exception as e:
                print(f"Error setting password: {str(e)}")
                raise

            # Add user to database
            try:
                db.session.add(new_user)
                db.session.commit()
                print(f"User created successfully with ID: {new_user.id}")
            except Exception as e:
                db.session.rollback()
                print(f"Database error during user creation: {str(e)}")
                print(f"Error type: {type(e)}")
                import traceback
                print(f"Traceback: {traceback.format_exc()}")
                return jsonify({'message': f'Database error: {str(e)}'}), 500

            # Generate token
            try:
                # Create token with user ID
                access_token = create_access_token(identity=str(new_user.id))
                print(f"Generated token for user {new_user.id}")
            except Exception as e:
                print(f"Error generating token: {str(e)}")
                raise

            print("=== Registration Successful ===\n")
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
            print(f"Database error: {str(db_error)}")
            print(f"Error type: {type(db_error)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return jsonify({'message': f'Database error: {str(db_error)}'}), 500

    except Exception as e:
        print(f"Registration error: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({'message': f'An error occurred during registration: {str(e)}'}), 500

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        print("\n=== Login Attempt ===")
        print(f"Received login request for username: {data.get('username') if data else 'No data'}")

        if not data or 'username' not in data or 'password' not in data:
            print("Missing username or password in request")
            return jsonify({'message': 'Username and password are required'}), 400

        try:
            user = User.query.filter_by(username=data['username']).first()
            print(f"User found: {user is not None}")

            if not user:
                print(f"No user found with username: {data['username']}")
                return jsonify({'message': 'Invalid username or password'}), 401

            print(f"Attempting password check for user: {user.username}")
            if not user.check_password(data['password']):
                print("Password check failed")
                return jsonify({'message': 'Invalid username or password'}), 401

            print("Password check successful")
            try:
                # Create token with user ID as string
                access_token = create_access_token(identity=user)
                print(f"Generated token for user {user.id}")
            except Exception as token_error:
                print(f"Error generating token: {str(token_error)}")
                print(f"Token error type: {type(token_error)}")
                import traceback
                print(f"Token error traceback: {traceback.format_exc()}")
                return jsonify({'message': 'Error generating authentication token'}), 500

            print("=== Login Successful ===\n")
            return jsonify({
                'access_token': access_token,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email
                }
            }), 200

        except Exception as auth_error:
            print(f"Authentication error: {str(auth_error)}")
            print(f"Error type: {type(auth_error)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return jsonify({'message': 'An error occurred during authentication'}), 500

    except Exception as e:
        print(f"Login error: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
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

        # Handle file upload
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

        # Update other fields
        if 'username' in request.form:
            username = request.form['username']
            if username != user.username:
                existing_user = User.query.filter_by(username=username).first()
                if existing_user:
                    return jsonify({'message': 'Username already taken'}), 400
                user.username = username

        if 'email' in request.form:
            email = request.form['email']
            if email != user.email:
                existing_user = User.query.filter_by(email=email).first()
                if existing_user:
                    return jsonify({'message': 'Email already taken'}), 400
                user.email = email

        if 'bio' in request.form:
            user.bio = request.form['bio']

        db.session.commit()
        
        return jsonify({
            'message': 'Profile updated successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'bio': user.bio,
                'profile_picture': user.profile_picture
            }
        }), 200

    except Exception as e:
        print(f"Error updating profile: {str(e)}")
        return jsonify({'message': 'Failed to update profile'}), 500

@app.route('/api/posts', methods=['GET'])
def get_posts():
    try:
        posts = Post.query.options(db.joinedload(Post.author), db.joinedload(Post.likes)).order_by(Post.created_at.desc()).all()
        
        # Get current user if authenticated (optional)
        current_user_id = None
        try:
            verify_jwt_in_request(optional=True)
            current_user_id = get_jwt_identity()
            if current_user_id:
                current_user_id = int(current_user_id)
        except:
            pass  # No valid token, that's okay for public posts
        
        return jsonify([post.to_dict(current_user_id) for post in posts])
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
            
        posts = Post.query.options(db.joinedload(Post.author), db.joinedload(Post.likes)).filter_by(user_id=current_user_id).order_by(Post.created_at.desc()).all()
        return jsonify([post.to_dict(int(current_user_id)) for post in posts])
    except Exception as e:
        print(f"Error fetching user posts: {str(e)}")
        return jsonify({'message': 'Failed to fetch posts'}), 500

@app.route('/api/posts', methods=['POST'])
@jwt_required()
def create_post():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'message': 'User not found'}), 404
            
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
        post = Post.query.options(db.joinedload(Post.author), db.joinedload(Post.likes)).get(new_post.id)
        if not post:
            return jsonify({'message': 'Failed to create post'}), 500
            
        return jsonify(post.to_dict(int(current_user_id))), 201
    except Exception as e:
        print(f"Error creating post: {str(e)}")
        db.session.rollback()
        return jsonify({'message': 'Failed to create post'}), 500

@app.route('/api/posts/<int:post_id>/like', methods=['POST'])
@jwt_required()
def toggle_like(post_id):
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'message': 'User not found'}), 404
            
        post = Post.query.get(post_id)
        if not post:
            return jsonify({'message': 'Post not found'}), 404
            
        # Check if user already liked this post
        existing_like = Like.query.filter_by(user_id=current_user_id, post_id=post_id).first()
        
        if existing_like:
            # Unlike the post
            db.session.delete(existing_like)
            db.session.commit()
            
            # Get updated like count
            like_count = Like.query.filter_by(post_id=post_id).count()
            
            return jsonify({
                'message': 'Post unliked',
                'is_liked': False,
                'like_count': like_count
            }), 200
        else:
            # Like the post
            new_like = Like(user_id=current_user_id, post_id=post_id)
            db.session.add(new_like)
            db.session.commit()
            
            # Get updated like count
            like_count = Like.query.filter_by(post_id=post_id).count()
            
            return jsonify({
                'message': 'Post liked',
                'is_liked': True,
                'like_count': like_count
            }), 200
            
    except Exception as e:
        db.session.rollback()
        print(f"Error toggling like: {str(e)}")
        return jsonify({'message': 'Failed to toggle like'}), 500

@app.route('/api/posts/<int:post_id>/likes', methods=['GET'])
def get_post_likes(post_id):
    try:
        post = Post.query.get(post_id)
        if not post:
            return jsonify({'message': 'Post not found'}), 404
            
        like_count = Like.query.filter_by(post_id=post_id).count()
        
        return jsonify({
            'post_id': post_id,
            'like_count': like_count
        }), 200
        
    except Exception as e:
        print(f"Error fetching likes: {str(e)}")
        return jsonify({'message': 'Failed to fetch likes'}), 500

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@jwt.user_identity_loader
def user_identity_lookup(user):
    print(f"Creating identity for user: {user.id if user else 'None'}")
    return str(user.id) if user else None

@jwt.user_lookup_loader
def user_lookup_callback(_jwt_header, jwt_data):
    try:
        identity = jwt_data["sub"]
        print(f"Looking up user with ID: {identity}")
        try:
            user_id = int(identity)
            user = User.query.filter_by(id=user_id).one_or_none()
            print(f"Found user: {user.username if user else 'None'}")
            return user
        except ValueError as ve:
            print(f"Invalid user ID format: {identity}")
            return None
    except Exception as e:
        print(f"Error in user lookup: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return None

@jwt.unauthorized_loader
def unauthorized_callback(error_string):
    return jsonify({'message': 'Missing or invalid token'}), 401

@jwt.invalid_token_loader
def invalid_token_callback(error_string):
    return jsonify({'message': 'Invalid token'}), 401

@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_data):
    return jsonify({'message': 'Token has expired'}), 401

@app.route('/api/posts/<int:post_id>', methods=['PUT'])
@jwt_required()
def update_post(post_id):
    try:
        current_user_id = get_jwt_identity()
        print(f"\n=== Update Post Attempt ===")
        print(f"User ID: {current_user_id}, Post ID: {post_id}")

        # Get the post
        post = Post.query.get_or_404(post_id)
        print(f"Found post: {post.title}")

        # Check if user is the author
        if post.user_id != int(current_user_id):
            print(f"User {current_user_id} is not the author of post {post_id}")
            return jsonify({'message': 'You can only edit your own posts'}), 403

        data = request.get_json()
        print(f"Update data received: {data}")

        if not data:
            print("No data provided")
            return jsonify({'message': 'No data provided'}), 400

        # Update post fields
        if 'title' in data:
            post.title = data['title']
        if 'content' in data:
            post.content = data['content']

        try:
            db.session.commit()
            print(f"Post {post_id} updated successfully")
            
            # Reload the post with author relationship
            updated_post = Post.query.options(db.joinedload(Post.author), db.joinedload(Post.likes)).get(post_id)
            if not updated_post:
                print("Failed to reload updated post")
                return jsonify({'message': 'Failed to update post'}), 500
                
            return jsonify(updated_post.to_dict(int(current_user_id))), 200
        except Exception as e:
            db.session.rollback()
            print(f"Database error: {str(e)}")
            print(f"Error type: {type(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return jsonify({'message': 'Error updating post'}), 500

    except Exception as e:
        print(f"Update post error: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({'message': 'An error occurred while updating the post'}), 500

@app.route('/api/posts/<int:post_id>', methods=['DELETE'])
@jwt_required()
def delete_post(post_id):
    try:
        current_user_id = get_jwt_identity()
        post = Post.query.get_or_404(post_id)
        
        # Check if user is the author
        if post.user_id != int(current_user_id):
            return jsonify({'message': 'You can only delete your own posts'}), 403
            
        db.session.delete(post)
        db.session.commit()
        return jsonify({'message': 'Post deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to delete post'}), 500

if __name__ == '__main__':
    app.run(debug=True)